from typing import Dict, Any, List
from indicators import (
    calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_atr, detect_rsi_divergence
)

class WaveStrategyEngine:
    """
    Bộ phân tích sóng định lượng đa khung thời gian:
    - 15m: Trend Master (EMA 50 / 200, MACD Trend)
    - 5m: Sóng hồi quy / Vùng nén Bollinger Bands
    - 1m: Điểm kích hoạt (Trigger, RSI Divergence, Volume breakout)
    """
    def __init__(self):
        pass

    def analyze_multi_timeframe(
        self, 
        candles_15m: List[Dict[str, Any]], 
        candles_5m: List[Dict[str, Any]], 
        candles_1m: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not candles_15m or not candles_5m or not candles_1m:
            return {"status": "error", "message": "Chưa đủ dữ liệu nến 3 khung thời gian"}

        # 1. Phân tích khung 15m (Trend chính)
        closes_15m = [c["close"] for c in candles_15m]
        ema50_15m = calculate_ema(closes_15m, 50)
        ema200_15m = calculate_ema(closes_15m, 200)
        c_15m = closes_15m[-1]
        e50_15m = ema50_15m[-1] if ema50_15m else c_15m
        e200_15m = ema200_15m[-1] if ema200_15m else c_15m
        
        if c_15m > e50_15m > e200_15m:
            trend_15m = "STRONG_BULLISH"
        elif c_15m > e50_15m:
            trend_15m = "BULLISH"
        elif c_15m < e50_15m < e200_15m:
            trend_15m = "STRONG_BEARISH"
        elif c_15m < e50_15m:
            trend_15m = "BEARISH"
        else:
            trend_15m = "SIDEWAY"

        # 2. Phân tích khung 5m (Vùng nén & Hồi quy)
        closes_5m = [c["close"] for c in candles_5m]
        up_bb_5m, mid_bb_5m, low_bb_5m, bw_5m = calculate_bollinger_bands(closes_5m, 20, 2.0)
        rsi_5m = calculate_rsi(closes_5m, 14)
        c_5m = closes_5m[-1]
        
        # Nhận diện nén giá (Squeeze) khi Bandwidth thấp
        is_5m_squeeze = bw_5m[-1] < 0.015 if bw_5m else False
        pullback_zone = "NEAR_SUPPORT" if c_5m <= low_bb_5m[-1] * 1.002 else (
            "NEAR_RESISTANCE" if c_5m >= up_bb_5m[-1] * 0.998 else "MIDDLE"
        )

        # 3. Phân tích khung 1m (Điểm kích hoạt vào lệnh)
        closes_1m = [c["close"] for c in candles_1m]
        volumes_1m = [c["volume"] for c in candles_1m]
        rsi_1m = calculate_rsi(closes_1m, 14)
        macd_1m, sig_1m, hist_1m = calculate_macd(closes_1m)
        divergence_1m = detect_rsi_divergence(closes_1m, rsi_1m, lookback=15)
        
        # Kiểm tra volume đột biến (Volume Spike)
        avg_vol_1m = sum(volumes_1m[-20:]) / 20 if len(volumes_1m) >= 20 else (volumes_1m[-1] if volumes_1m else 1.0)
        vol_spike = (volumes_1m[-1] > avg_vol_1m * 1.6) if volumes_1m and avg_vol_1m > 0 else False
        
        # MACD cross
        macd_cross_bull = (hist_1m[-2] <= 0 and hist_1m[-1] > 0) if len(hist_1m) >= 2 else False
        macd_cross_bear = (hist_1m[-2] >= 0 and hist_1m[-1] < 0) if len(hist_1m) >= 2 else False

        # 4. Tính toán ATR và ngưỡng Hỗ trợ / Kháng cự động
        highs_5m = [c["high"] for c in candles_5m]
        lows_5m = [c["low"] for c in candles_5m]
        atr_5m = calculate_atr(highs_5m, lows_5m, closes_5m, 14)
        current_atr = atr_5m[-1] if atr_5m else (c_5m * 0.005)

        # Hỗ trợ (Support): Đáy gần nhất hoặc Lower Bollinger Band
        recent_low_5m = min(lows_5m[-15:]) if len(lows_5m) >= 15 else low_bb_5m[-1]
        support_level = round(min(recent_low_5m, low_bb_5m[-1]), 4 if c_5m < 1 else 2)

        # Kháng cự (Resistance): Đỉnh gần nhất hoặc Upper Bollinger Band
        recent_high_5m = max(highs_5m[-15:]) if len(highs_5m) >= 15 else up_bb_5m[-1]
        resistance_level = round(max(recent_high_5m, up_bb_5m[-1]), 4 if c_5m < 1 else 2)

        return {
            "current_price": closes_1m[-1],
            "atr": current_atr,
            "support_level": support_level,
            "resistance_level": resistance_level,
            "timeframe_15m": {
                "trend": trend_15m,
                "ema50": round(e50_15m, 4 if c_15m < 1 else 2),
                "ema200": round(e200_15m, 4 if c_15m < 1 else 2),
            },
            "timeframe_5m": {
                "rsi": round(rsi_5m[-1], 2),
                "squeeze": is_5m_squeeze,
                "pullback_zone": pullback_zone,
                "bollinger_upper": round(up_bb_5m[-1], 4 if c_5m < 1 else 2),
                "bollinger_lower": round(low_bb_5m[-1], 4 if c_5m < 1 else 2),
            },
            "timeframe_1m": {
                "rsi": round(rsi_1m[-1], 2),
                "macd_histogram": round(hist_1m[-1], 4),
                "macd_cross_bull": macd_cross_bull,
                "macd_cross_bear": macd_cross_bear,
                "divergence": divergence_1m,
                "volume_spike": vol_spike
            }
        }
