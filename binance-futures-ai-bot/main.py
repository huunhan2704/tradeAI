import os
import sys
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import webview

from config import AppConfig
from exchange_manager import BinanceFuturesManager
from wave_strategy import WaveStrategyEngine
from ai_engine import AITradingEngine
from risk_engine import RiskAndExecutionEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MainApp")

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Vibe-Trading AI Futures")

# 1. Tải cấu hình
config = AppConfig.load()

# 2. Khởi tạo các module
exchange = BinanceFuturesManager(
    api_key=config.api_key,
    api_secret=config.api_secret,
    use_testnet=config.use_testnet
)
wave_engine = WaveStrategyEngine()
ai_engine = AITradingEngine(
    provider=config.ai_provider,
    api_key=config.ai_api_key,
    model_name=config.ai_model_name
)
risk_engine = RiskAndExecutionEngine(exchange)

# Cache kết quả phân tích gần nhất
latest_analysis: Dict[str, Any] = {}

# Serve file giao diện HTML
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_file = BASE_DIR / "ui" / "index.html"
    with open(html_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/get_config")
async def get_config():
    return JSONResponse(content={
        "api_key": config.api_key,
        "api_secret": config.api_secret,
        "use_testnet": config.use_testnet,
        "symbol": config.symbol,
        "leverage": config.leverage,
        "margin_mode": config.margin_mode,
        "order_margin_usdt": config.order_margin_usdt,
        "stop_loss_pct": config.stop_loss_pct,
        "take_profit_pct": config.take_profit_pct,
        "auto_trade_enabled": config.auto_trade_enabled,
        "ai_provider": config.ai_provider,
        "ai_api_key": config.ai_api_key,
    })

@app.post("/api/save_config")
async def save_config(req: Request):
    data = await req.json()
    config.api_key = data.get("api_key", config.api_key)
    config.api_secret = data.get("api_secret", config.api_secret)
    config.use_testnet = data.get("use_testnet", config.use_testnet)
    config.margin_mode = data.get("margin_mode", config.margin_mode)
    config.ai_provider = data.get("ai_provider", config.ai_provider)
    config.ai_api_key = data.get("ai_api_key", config.ai_api_key)
    config.save()
    
    # Cập nhật credentials
    exchange.update_credentials(config.api_key, config.api_secret, config.use_testnet)
    ai_engine.update_settings(config.ai_provider, config.ai_api_key, config.ai_model_name)
    return JSONResponse(content={"status": "success", "message": "Đã lưu cấu hình!"})

@app.post("/api/toggle_auto")
async def toggle_auto(req: Request):
    data = await req.json()
    config.auto_trade_enabled = bool(data.get("enabled", False))
    config.save()
    logger.info(f"Trạng thái Auto-Trade: {'BẬT' if config.auto_trade_enabled else 'TẮT'}")
    return JSONResponse(content={"status": "success", "auto_trade_enabled": config.auto_trade_enabled})

@app.get("/api/market_data")
async def get_market_data(symbol: str = "BTC/USDT:USDT", timeframe: str = "1m"):
    global latest_analysis
    
    # Lấy nến hiển thị cho chart
    candles = exchange.fetch_ohlcv_data(symbol, timeframe=timeframe, limit=120)
    current_price = candles[-1]["close"] if candles else 0.0

    # Lấy nến 3 khung để phân tích sóng đa khung
    candles_15m = exchange.fetch_ohlcv_data(symbol, timeframe="15m", limit=60)
    candles_5m = exchange.fetch_ohlcv_data(symbol, timeframe="5m", limit=60)
    candles_1m = candles if timeframe == "1m" else exchange.fetch_ohlcv_data(symbol, timeframe="1m", limit=60)

    # Phân tích sóng
    wave_analysis = wave_engine.analyze_multi_timeframe(candles_15m, candles_5m, candles_1m)
    
    # AI đánh giá và tạo thảo luận
    ai_decision = ai_engine.evaluate_market(symbol, wave_analysis, config.leverage, config.stop_loss_pct)
    wave_analysis["ai_decision"] = ai_decision
    latest_analysis = wave_analysis

    # BỘ GIÁM SÁT STOP LOSS THỜI GIAN THỰC
    if current_price > 0:
        sl_event = risk_engine.check_and_enforce_stop_loss(symbol, current_price)
        if sl_event:
            logger.warning(f"Sự kiện đóng lệnh: {sl_event['reason']}")

    # Lấy thông tin tài khoản
    account = exchange.fetch_account_summary()

    # THỰC THI TỰ ĐỘNG NẾU AUTO TRADE ĐƯỢC BẬT
    if config.auto_trade_enabled and ai_decision.get("action") in ["BUY", "SELL"]:
        confidence = ai_decision.get("confidence", 0)
        if confidence >= 75:
            action = ai_decision.get("action")
            s_sl = ai_decision.get("suggested_sl", 0.0)
            s_tp = ai_decision.get("suggested_tp", 0.0)
            res = risk_engine.execute_auto_trade(
                symbol=symbol,
                action=action,
                current_price=current_price,
                order_margin_usdt=config.order_margin_usdt,
                leverage=config.leverage,
                stop_loss_pct=config.stop_loss_pct,
                take_profit_pct=config.take_profit_pct,
                reason=ai_decision.get("reason", ""),
                margin_mode=config.margin_mode,
                exact_sl_price=s_sl,
                exact_tp_price=s_tp
            )
            logger.info(f"Kết quả Auto-Trade: {res}")

    return JSONResponse(content={
        "candles": candles,
        "analysis": wave_analysis,
        "account": account
    })

@app.post("/api/update_trade_params")
async def update_trade_params(req: Request):
    """Đồng bộ ngay khi người dùng gõ thay đổi Đòn bẩy, Ký quỹ, Vốn hoặc Stop Loss trên giao diện"""
    data = await req.json()
    if "margin" in data:
        config.order_margin_usdt = float(data["margin"])
    if "leverage" in data:
        config.leverage = int(data["leverage"])
        exchange.set_leverage_and_margin(config.symbol, config.leverage, config.margin_mode)
    if "sl" in data:
        config.stop_loss_pct = float(data["sl"])
    if "tp" in data:
        config.take_profit_pct = float(data["tp"])
    if "margin_mode" in data:
        config.margin_mode = data["margin_mode"].lower()
        exchange.set_leverage_and_margin(config.symbol, config.leverage, config.margin_mode)
    config.save()
    return JSONResponse(content={"status": "success", "config": {
        "order_margin_usdt": config.order_margin_usdt,
        "leverage": config.leverage,
        "margin_mode": config.margin_mode,
        "stop_loss_pct": config.stop_loss_pct,
        "take_profit_pct": config.take_profit_pct
    }})

@app.post("/api/execute_manual")
async def execute_manual(req: Request):
    data = await req.json()
    side = data.get("side", "BUY")
    margin = float(data.get("margin", config.order_margin_usdt))
    leverage = int(data.get("leverage", config.leverage))
    sl = float(data.get("sl", config.stop_loss_pct))
    tp = float(data.get("tp", config.take_profit_pct))
    symbol = data.get("symbol", config.symbol)
    margin_mode = data.get("margin_mode", config.margin_mode)

    # Đồng bộ cấu hình
    config.order_margin_usdt = margin
    config.leverage = leverage
    config.stop_loss_pct = sl
    config.take_profit_pct = tp
    config.margin_mode = margin_mode
    config.save()

    current_price = exchange.fetch_current_price(symbol)
    if current_price <= 0:
        return JSONResponse(content={"success": False, "message": "Không lấy được giá thị trường"})

    res = risk_engine.execute_auto_trade(
        symbol=symbol,
        action=side,
        current_price=current_price,
        order_margin_usdt=margin,
        leverage=leverage,
        stop_loss_pct=sl,
        take_profit_pct=tp,
        reason="Thủ công từ giao diện",
        margin_mode=margin_mode
    )
    return JSONResponse(content=res)

@app.post("/api/close_position")
async def close_position(req: Request):
    data = await req.json()
    symbol = data.get("symbol", config.symbol)
    res = exchange.close_position_market(symbol)
    return JSONResponse(content=res)

@app.post("/api/panic_close")
async def panic_close():
    res = exchange.panic_close_all()
    risk_engine.active_trade = None
    return JSONResponse(content=res)

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    # Chạy Server trong background thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(1.5)
    
    logger.info("⚡ Giao diện Web/API đã sẵn sàng tại: http://127.0.0.1:8000")
    
    # Khởi động Native Desktop Window
    try:
        window = webview.create_window(
            title="⚡ Vibe-Trading AI | Binance Futures Desktop Terminal",
            url="http://127.0.0.1:8000",
            width=1400,
            height=900,
            resizable=True
        )
        webview.start()
    except Exception as e:
        logger.warning(f"Không thể khởi động webview desktop window ({e}). Đang mở trình duyệt mặc định...")
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")
        while True:
            time.sleep(1)
