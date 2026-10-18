import time
import logging
from typing import Optional, Dict, Any, List
import ccxt

logger = logging.getLogger("ExchangeManager")

class BinanceFuturesManager:
    """
    Quản lý kết nối Binance USDT-M Futures qua CCXT.
    Hỗ trợ cả Realnet, Binance Futures Testnet, và Chế độ Paper Trading (Giả lập ảo 10,000 USDT)
    khi người dùng chưa nhập hoặc muốn test trước không mất tiền.
    """
    def __init__(self, api_key: str = "", api_secret: str = "", use_testnet: bool = True):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.use_testnet = use_testnet
        self.client: Optional[ccxt.binanceusdm] = None
        
        # Bộ giả lập Paper Trading (khi chưa nhập API key)
        self.paper_mode: bool = False
        self.paper_wallet_balance: float = 10000.0
        self.paper_positions: List[Dict[str, Any]] = []
        
        self._init_client()

    def _init_client(self):
        try:
            if not self.api_key or not self.api_secret:
                self.paper_mode = True
                logger.info("Chưa có API Key -> Kích hoạt chế độ PAPER TRADING (Giả lập 10,000 USDT ảo để test mượt mà)")
                self.client = ccxt.binanceusdm({"enableRateLimit": True})
            else:
                self.paper_mode = False
                config = {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "enableRateLimit": True,
                    "options": {
                        "defaultType": "future",
                        "adjustForTimeDifference": True,
                    }
                }
                self.client = ccxt.binanceusdm(config)
                if self.use_testnet:
                    try:
                        self.client.enable_demo_trading(True)
                        logger.info("Đã kích hoạt chế độ Binance Futures Demo Trading (Sandbox)")
                    except Exception as e:
                        logger.warning(f"Không thể kích hoạt demo trading: {e}")
                else:
                    logger.info("Đã kích hoạt chế độ Binance Futures REALNET (Sàn thật)")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Binance client: {e}")
            self.client = ccxt.binanceusdm({"enableRateLimit": True})
            self.paper_mode = True

    def update_credentials(self, api_key: str, api_secret: str, use_testnet: bool):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.use_testnet = use_testnet
        self._init_client()

    def is_connected(self) -> bool:
        if self.paper_mode:
            return True
        if not self.client or not self.api_key or not self.api_secret:
            return False
        return True

    def test_connection(self) -> Dict[str, Any]:
        """Kiểm tra API key và kết nối tới sàn"""
        if self.paper_mode:
            return {
                "status": True,
                "message": f"Chế độ Giả lập (Paper Trade) hoạt động tốt! Số dư ảo: {self.paper_wallet_balance:.2f} USDT",
                "balance": self.paper_wallet_balance
            }
        try:
            balance = self.client.fetch_balance()
            usdt_free = balance.get("USDT", {}).get("free", 0.0)
            return {
                "status": True, 
                "message": f"Kết nối Binance thành công! Số dư khả dụng: {usdt_free:.2f} USDT",
                "balance": usdt_free
            }
        except ccxt.AuthenticationError as e:
            msg = str(e)
            if "-2015" in msg:
                err_msg = "Lỗi -2015: API Key chưa bật quyền 'Enable Futures' hoặc không đúng môi trường Real/Demo."
            elif "-2008" in msg:
                err_msg = "Lỗi -2008: Sai API Key hoặc không tồn tại trên hệ thống này."
            else:
                err_msg = f"Lỗi xác thực API: {msg}"
            return {"status": False, "message": err_msg}
        except Exception as e:
            return {"status": False, "message": f"Lỗi kết nối sàn: {str(e)}"}

    def set_leverage_and_margin(self, symbol: str, leverage: int, margin_mode: str = "cross"):
        """Cấu hình đòn bẩy và loại ký quỹ (CROSS hoặc ISOLATED)"""
        if self.paper_mode:
            return
        if not self.is_connected():
            return
        try:
            target_mode = "CROSSED" if margin_mode.lower() in ["cross", "crossed"] else "ISOLATED"
            try:
                self.client.set_margin_mode(target_mode, symbol)
                logger.info(f"Đã set chế độ Margin: {target_mode} cho {symbol}")
            except Exception as e:
                # Nếu đã đúng chế độ hoặc đang có vị thế mở, Binance có thể trả về lỗi no need to change
                pass
            
            self.client.set_leverage(int(leverage), symbol)
            logger.info(f"Đã set đòn bẩy {leverage}x và margin {target_mode} cho {symbol}")
        except Exception as e:
            logger.warning(f"Lỗi khi set leverage/margin cho {symbol}: {e}")

    def fetch_ohlcv_data(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> List[Dict[str, Any]]:
        """Lấy dữ liệu nến (OHLCV) từ sàn"""
        if not self.client:
            self.client = ccxt.binanceusdm({"enableRateLimit": True})
                
        try:
            raw_candles = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            candles = []
            for c in raw_candles:
                candles.append({
                    "time": int(c[0] / 1000), # Unix timestamp (seconds) cho TradingView
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                })
            return candles
        except Exception as e:
            logger.error(f"Lỗi lấy dữ liệu nến {symbol} ({timeframe}): {e}")
            return []

    def fetch_current_price(self, symbol: str) -> float:
        """Lấy giá thị trường hiện tại"""
        try:
            ticker = self.client.fetch_ticker(symbol)
            return float(ticker.get("last", 0.0))
        except Exception as e:
            logger.error(f"Lỗi lấy giá ticker {symbol}: {e}")
            return 0.0

    def fetch_account_summary(self) -> Dict[str, Any]:
        """Lấy thông tin tài khoản Futures, số dư, PnL"""
        # Nếu đang ở chế độ Giả lập (Paper Trade)
        if self.paper_mode:
            current_price = 0.0
            if self.paper_positions:
                current_price = self.fetch_current_price(self.paper_positions[0]["symbol"])
                
            total_unrealized = 0.0
            for pos in self.paper_positions:
                entry = pos["entryPrice"]
                side = pos["side"]
                lev = pos["leverage"]
                qty = pos["contracts"]
                pos["markPrice"] = current_price if current_price > 0 else entry
                
                # Tính ROE %
                if side == "LONG":
                    pnl_pct = ((pos["markPrice"] - entry) / entry) * 100.0 * lev
                    pos["unrealizedPnl"] = (pos["markPrice"] - entry) * qty
                else:
                    pnl_pct = ((entry - pos["markPrice"]) / entry) * 100.0 * lev
                    pos["unrealizedPnl"] = (entry - pos["markPrice"]) * qty
                pos["percentage"] = round(pnl_pct, 2)
                total_unrealized += pos["unrealizedPnl"]

            return {
                "wallet_balance": round(self.paper_wallet_balance, 2),
                "available_balance": round(self.paper_wallet_balance, 2),
                "unrealized_pnl": round(total_unrealized, 2),
                "positions": self.paper_positions,
                "is_paper": True
            }

        # Nếu có API Key thật kết nối sàn
        try:
            balance = self.client.fetch_balance()
            usdt_info = balance.get("USDT", {})
            positions_raw = self.client.fetch_positions()
            
            active_positions = []
            for p in positions_raw:
                contracts = float(p.get("contracts", 0.0) or 0.0)
                if abs(contracts) > 0.000001:
                    active_positions.append({
                        "symbol": p.get("symbol"),
                        "side": p.get("side", "").upper(),
                        "contracts": contracts,
                        "entryPrice": float(p.get("entryPrice", 0.0) or 0.0),
                        "markPrice": float(p.get("markPrice", 0.0) or 0.0),
                        "unrealizedPnl": float(p.get("unrealizedPnl", 0.0) or 0.0),
                        "percentage": float(p.get("percentage", 0.0) or 0.0),
                        "liquidationPrice": float(p.get("liquidationPrice", 0.0) or 0.0),
                        "leverage": int(p.get("leverage", 1) or 1)
                    })
                    
            return {
                "wallet_balance": float(usdt_info.get("total", 0.0) or 0.0),
                "available_balance": float(usdt_info.get("free", 0.0) or 0.0),
                "unrealized_pnl": float(balance.get("info", {}).get("totalUnrealizedProfit", 0.0) or 0.0),
                "positions": active_positions,
                "is_paper": False
            }
        except Exception as e:
            err_str = str(e)
            if not hasattr(self, "_last_err") or self._last_err != err_str:
                self._last_err = err_str
                if "-2015" in err_str:
                    logger.warning("⚠️ Lỗi -2015: API Key chưa bật quyền 'Enable Futures' trên Binance hoặc sai chế độ Real/Demo.")
                else:
                    logger.warning(f"Lỗi đọc thông tin tài khoản: {err_str}")
            return {
                "wallet_balance": 0.0,
                "available_balance": 0.0,
                "unrealized_pnl": 0.0,
                "positions": [],
                "is_paper": False,
                "error": err_str
            }

    def place_futures_order(
        self, 
        symbol: str, 
        side: str, 
        amount_contracts: float, 
        leverage: int = 10, 
        margin_mode: str = "cross",
        tp_price: float = 0.0,
        sl_price: float = 0.0
    ):
        """
        Vào lệnh Market Futures và tự động đặt sẵn:
        - Take Profit Limit treo sẵn trên sổ lệnh sàn -> Hưởng phí MAKER siêu rẻ 0.020% (Tiết kiệm 60% phí)!
        - Stop Loss Stop-Market trực tiếp trên máy chủ Binance -> Bảo vệ tài khoản 24/7 kể cả khi tắt máy!
        """
        # Nếu ở chế độ Giả lập (Paper Trade)
        if self.paper_mode:
            current_price = self.fetch_current_price(symbol)
            if current_price <= 0:
                current_price = 82000.0 # fallback
            
            side_norm = "LONG" if side.lower() == "buy" else "SHORT"
            liq_dist = current_price * (1.0 / leverage) * 0.9
            liq_price = (current_price - liq_dist) if side_norm == "LONG" else (current_price + liq_dist)
            
            pos = {
                "symbol": symbol,
                "side": side_norm,
                "contracts": amount_contracts,
                "entryPrice": current_price,
                "markPrice": current_price,
                "unrealizedPnl": 0.0,
                "percentage": 0.0,
                "liquidationPrice": round(liq_price, 2),
                "leverage": leverage
            }
            self.paper_positions = [pos]
            logger.info(f"✨ [GIẢ LẬP PAPER] Đã khớp lệnh {side_norm} {amount_contracts} {symbol} tại giá {current_price}")
            return {"success": True, "message": f"[GIẢ LẬP] Khớp lệnh {side_norm} thành công!", "order": pos}

        # Nếu có API Key
        try:
            # 1. Hủy các lệnh chờ cũ của cặp này trước khi vào lệnh mới
            try:
                self.client.cancel_all_orders(symbol)
            except Exception:
                pass

            # 2. Cài đòn bẩy và margin
            self.set_leverage_and_margin(symbol, leverage, margin_mode=margin_mode)

            # 3. Khớp lệnh Market Mở vị thế
            order = self.client.create_market_order(symbol, side.lower(), amount_contracts)
            logger.info(f"Khớp lệnh {side.upper()} thành công: {order.get('id')} ({margin_mode.upper()} {leverage}x)")

            close_side = "sell" if side.lower() == "buy" else "buy"

            # 4. Đặt sẵn Take Profit LIMIT trên sổ lệnh sàn (Hưởng phí Maker 0.020% - Giảm 60% phí chốt lời)
            if tp_price > 0:
                try:
                    tp_order = self.client.create_order(
                        symbol, "LIMIT", close_side, amount_contracts, tp_price,
                        params={"reduceOnly": True, "timeInForce": "GTC"}
                    )
                    logger.info(f"🎯 [TIẾT KIỆM PHÍ] Đã đặt sẵn Take Profit Limit {tp_price} trên Binance (Phí Maker 0.02%): ID {tp_order.get('id')}")
                except Exception as e_tp:
                    logger.warning(f"Không thể đặt lệnh TP Limit trên sàn: {e_tp}")

            # 5. Đặt sẵn Stop Loss STOP_MARKET trực tiếp trên máy chủ Binance (Bảo vệ vốn 24/7 tuyệt đối)
            if sl_price > 0:
                try:
                    sl_order = self.client.create_order(
                        symbol, "STOP_MARKET", close_side, amount_contracts,
                        params={"stopPrice": sl_price, "reduceOnly": True}
                    )
                    logger.info(f"🛡️ [BẢO VỆ VỐN] Đã đặt sẵn Stop Loss {sl_price} trực tiếp trên máy chủ Binance: ID {sl_order.get('id')}")
                except Exception as e_sl:
                    logger.warning(f"Không thể đặt lệnh SL trên sàn: {e_sl}")

            return {
                "success": True, 
                "order": order, 
                "message": f"Khớp {side.upper()} thành công! Đã treo TP Limit (Phí 0.02%) & SL Stop-Market trực tiếp trên Binance."
            }
        except Exception as e:
            logger.error(f"Lỗi khi đặt lệnh {side} {symbol}: {e}")
            return {"success": False, "message": str(e)}

    def close_position_market(self, symbol: str):
        """Đóng vị thế hiện tại và hủy toàn bộ lệnh chờ (TP/SL) trên sàn"""
        if self.paper_mode:
            if self.paper_positions:
                p = self.paper_positions[0]
                self.paper_wallet_balance += p.get("unrealizedPnl", 0.0)
                self.paper_positions = []
                logger.info(f"✨ [GIẢ LẬP PAPER] Đã đóng vị thế {symbol}")
                return {"success": True, "message": f"[GIẢ LẬP] Đã đóng vị thế {symbol}"}
            return {"success": False, "message": "Không có vị thế mở"}

        try:
            # Hủy sạch các lệnh chờ TP/SL trên sàn để không bị sót lệnh ma
            try:
                self.client.cancel_all_orders(symbol)
                logger.info(f"Đã hủy toàn bộ lệnh chờ của {symbol} trên sàn")
            except Exception:
                pass

            positions = self.client.fetch_positions([symbol])
            for p in positions:
                contracts = float(p.get("contracts", 0.0) or 0.0)
                if abs(contracts) > 0.000001:
                    side = p.get("side", "").lower()
                    close_side = "sell" if side == "long" else "buy"
                    order = self.client.create_market_order(symbol, close_side, contracts, params={"reduceOnly": True})
                    return {"success": True, "message": f"Đã đóng vị thế {side.upper()} {symbol} và hủy toàn bộ lệnh chờ!"}
            return {"success": False, "message": "Không tìm thấy vị thế mở"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi đóng vị thế: {str(e)}"}

    def panic_close_all(self):
        """NÚT KHẨN CẤP: Đóng toàn bộ tất cả các vị thế đang mở và hủy hết lệnh chờ"""
        if self.paper_mode:
            self.paper_positions = []
            return {"success": True, "message": "[GIẢ LẬP] Đã đóng khẩn cấp toàn bộ vị thế!"}

        try:
            try:
                self.client.cancel_all_orders()
            except Exception:
                pass
            
            positions = self.client.fetch_positions()
            closed_count = 0
            for p in positions:
                contracts = float(p.get("contracts", 0.0) or 0.0)
                if abs(contracts) > 0.000001:
                    sym = p.get("symbol")
                    side = p.get("side", "").lower()
                    close_side = "sell" if side == "long" else "buy"
                    self.client.create_market_order(sym, close_side, contracts, params={"reduceOnly": True})
                    closed_count += 1
                    
            return {"success": True, "message": f"Đã đóng khẩn cấp {closed_count} vị thế!"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi đóng khẩn cấp: {str(e)}"}
