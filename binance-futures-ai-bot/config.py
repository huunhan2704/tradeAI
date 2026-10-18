import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict

CONFIG_FILE = Path(__file__).parent / "config.json"

@dataclass
class AppConfig:
    # Binance Futures API Credentials
    api_key: str = ""
    api_secret: str = ""
    use_testnet: bool = True  # True: Binance Futures Testnet, False: Live
    
    # Trading Pair & Timeframes
    symbol: str = "BTC/USDT:USDT"  # CCXT unified futures symbol format
    timeframe_main: str = "15m"   # Xu hướng chính (Trend filter)
    timeframe_pullback: str = "5m" # Vùng nén / hồi quy
    timeframe_trigger: str = "1m"  # Điểm kích hoạt vào lệnh
    
    # Leverage & Capital Management
    leverage: int = 10            # Đòn bẩy (ví dụ: 10x)
    margin_mode: str = "cross"    # "cross" (ký quỹ toàn ví) hoặc "isolated" (cô lập)
    order_margin_usdt: float = 20.0 # Số tiền ký quỹ cố định cho mỗi lệnh ($)
    
    # Risk Management & Stop Loss
    stop_loss_pct: float = 1.5    # Cắt lỗ cứng theo % biến động giá (hoặc % ký quỹ)
    take_profit_pct: float = 3.0  # Chốt lời theo %
    max_open_positions: int = 1   # Số vị thế tối đa cùng lúc
    max_daily_loss_usdt: float = 50.0 # Chốt chặn lỗ tối đa trong ngày
    
    # Automation & AI Engine
    auto_trade_enabled: bool = False # Công tắc tự động vào lệnh (Mặc định False để an toàn)
    ai_provider: str = "local_quant" # "local_quant", "openai", "deepseek", "gemini"
    ai_api_key: str = ""
    ai_model_name: str = "deepseek-chat"
    ai_analysis_interval_sec: int = 15 # Tần suất AI phân tích lại (giây)

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4, ensure_ascii=False)

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception:
                pass
        config = cls()
        config.save()
        return config
