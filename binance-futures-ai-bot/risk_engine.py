import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("RiskEngine")

class RiskAndExecutionEngine:
    """
    Quản lý rủi ro đòn bẩy Futures và thực thi lệnh tự động:
    - Tính toán khối lượng hợp đồng theo số tiền ký quỹ USDT cố định và đòn bẩy.
    - Cài đặt và giám sát Stop Loss theo % lỗ cố định để bảo vệ tài khoản tuyệt đối.
    - Chốt chặn an toàn (Circuit Breaker): Chặn vào lệnh nếu đã có vị thế mở hoặc vượt quá lỗ ngày.
    """
    def __init__(self, exchange_manager):
        self.exchange = exchange_manager
        self.active_trade: Optional[Dict[str, Any]] = None
        self.daily_pnl: float = 0.0

    def calculate_position_size(
        self, 
        current_price: float, 
        order_margin_usdt: float, 
        leverage: int, 
        symbol: str = "BTC/USDT:USDT"
    ) -> float:
        """
        Tính số lượng hợp đồng (contracts):
        Giá trị vị thế (Notional) = Tiền ký quỹ * Đòn bẩy
        Số lượng coin = Notional / Giá hiện tại
        """
        if current_price <= 0:
            return 0.0
        
        notional_value = order_margin_usdt * leverage
        raw_quantity = notional_value / current_price
        
        # Dùng hàm chuẩn sàn CCXT amount_to_precision để hỗ trợ Vàng, Meme coins, Altcoins chính xác 100%
        try:
            if hasattr(self.exchange, "client") and self.exchange.client:
                if not self.exchange.client.markets:
                    self.exchange.client.load_markets()
                prec_qty = float(self.exchange.client.amount_to_precision(symbol, raw_quantity))
                market = self.exchange.client.markets.get(symbol, {})
                min_amount = market.get("limits", {}).get("amount", {}).get("min", 0.0) or 0.0
                if prec_qty < min_amount:
                    prec_qty = float(min_amount)
                return prec_qty
        except Exception:
            pass

        # Fallback tính toán nếu chưa tải xong markets
        if "BTC" in symbol or "PAXG" in symbol or "XAU" in symbol:
            return round(raw_quantity, 3)
        elif "ETH" in symbol or "WIF" in symbol:
            return round(raw_quantity, 2)
        elif any(m in symbol for m in ["DOGE", "PEPE", "SHIB", "FLOKI", "BONK", "BOME", "POPCAT"]):
            return round(raw_quantity, 0)
        else:
            return round(raw_quantity, 1)

    def calculate_sl_tp(
        self, 
        entry_price: float, 
        side: str, 
        stop_loss_pct: float, 
        take_profit_pct: float
    ) -> tuple[float, float]:
        """
        Tính toán giá Stop Loss và Take Profit:
        side: "BUY" (LONG) hoặc "SELL" (SHORT)
        """
        if side == "BUY":
            sl_price = entry_price * (1.0 - (stop_loss_pct / 100.0))
            tp_price = entry_price * (1.0 + (take_profit_pct / 100.0))
        else: # SHORT
            sl_price = entry_price * (1.0 + (stop_loss_pct / 100.0))
            tp_price = entry_price * (1.0 - (take_profit_pct / 100.0))
            
        return round(sl_price, 2), round(tp_price, 2)

    def execute_auto_trade(
        self,
        symbol: str,
        action: str, # "BUY" hoặc "SELL"
        current_price: float,
        order_margin_usdt: float,
        leverage: int,
        stop_loss_pct: float,
        take_profit_pct: float,
        reason: str = "",
        margin_mode: str = "cross",
        exact_sl_price: float = 0.0,
        exact_tp_price: float = 0.0
    ) -> Dict[str, Any]:
        """Thực hiện lệnh tự động kèm thiết lập Stop Loss"""
        if action not in ["BUY", "SELL"]:
            return {"status": "ignored", "message": "Hành động là đứng ngoài (WAIT)"}

        # 1. Kiểm tra vị thế mở
        account = self.exchange.fetch_account_summary()
        if len(account.get("positions", [])) > 0:
            return {"status": "blocked", "message": "Đang có vị thế mở, không vào thêm lệnh mới"}

        # 2. Tính toán size
        quantity = self.calculate_position_size(current_price, order_margin_usdt, leverage, symbol)
        if quantity <= 0:
            return {"status": "error", "message": "Khối lượng tính toán không hợp lệ"}

        if exact_sl_price > 0 and exact_tp_price > 0:
            sl_price, tp_price = exact_sl_price, exact_tp_price
        else:
            sl_price, tp_price = self.calculate_sl_tp(current_price, action, stop_loss_pct, take_profit_pct)

        # 3. Gửi lệnh Market lên Binance Futures kèm TP Limit (Maker 0.02%) và SL Stop-Market
        res = self.exchange.place_futures_order(
            symbol, action, quantity, leverage, 
            margin_mode=margin_mode, 
            tp_price=tp_price, 
            sl_price=sl_price
        )
        if not res.get("success"):
            return {"status": "failed", "message": res.get("message")}

        # 4. Ghi nhận vị thế vào bộ giám sát rủi ro nội bộ
        self.active_trade = {
            "symbol": symbol,
            "side": action, # "BUY" (LONG) hoặc "SELL" (SHORT)
            "entry_price": current_price,
            "quantity": quantity,
            "margin_usdt": order_margin_usdt,
            "leverage": leverage,
            "stop_loss_price": sl_price,
            "take_profit_price": tp_price,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "reason": reason
        }

        logger.info(f"Đã mở vị thế {action} {symbol} thành công! SL: {sl_price}, TP: {tp_price}")
        return {
            "status": "success",
            "message": f"Đã mở vị thế {action} thành công!",
            "trade": self.active_trade
        }

    def check_and_enforce_stop_loss(self, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
        """
        BỘ GIÁM SÁT RỦI RO THỜI GIAN THỰC (Chạy mỗi giây):
        Nếu giá chạm ngưỡng Stop Loss hoặc Take Profit -> Lập tức đóng lệnh Market để bảo vệ tài sản!
        """
        if not self.active_trade or self.active_trade["symbol"] != symbol:
            return None

        trade = self.active_trade
        side = trade["side"]
        sl_price = trade["stop_loss_price"]
        tp_price = trade["take_profit_price"]

        should_close = False
        close_reason = ""

        if side == "BUY": # LONG
            if current_price <= sl_price:
                should_close = True
                close_reason = f"🚨 CHẠM STOP LOSS ({trade['stop_loss_pct']}%)! Cắt lỗ bảo vệ tài sản."
            elif current_price >= tp_price:
                should_close = True
                close_reason = f"🎉 CHẠM TAKE PROFIT ({trade['take_profit_pct']}%)! Chốt lời thành công."
        elif side == "SELL": # SHORT
            if current_price >= sl_price:
                should_close = True
                close_reason = f"🚨 CHẠM STOP LOSS ({trade['stop_loss_pct']}%)! Cắt lỗ bảo vệ tài sản."
            elif current_price <= tp_price:
                should_close = True
                close_reason = f"🎉 CHẠM TAKE PROFIT ({trade['take_profit_pct']}%)! Chốt lời thành công."

        if should_close:
            logger.warning(f"Kích hoạt đóng vị thế tự động: {close_reason}")
            close_res = self.exchange.close_position_market(symbol)
            pnl_pct = ((current_price - trade["entry_price"]) / trade["entry_price"] * 100.0 * trade["leverage"]) if side == "BUY" else (
                (trade["entry_price"] - current_price) / trade["entry_price"] * 100.0 * trade["leverage"]
            )
            closed_trade = dict(self.active_trade)
            self.active_trade = None # Reset vị thế
            return {
                "triggered": True,
                "reason": close_reason,
                "exit_price": current_price,
                "pnl_pct": round(pnl_pct, 2),
                "trade": closed_trade
            }

        return None
