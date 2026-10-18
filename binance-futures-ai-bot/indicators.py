import numpy as np

def calculate_ema(prices: list[float], period: int) -> list[float]:
    """Tính Exponential Moving Average (EMA)"""
    if len(prices) < period:
        return [prices[-1]] * len(prices) if prices else []
    
    alpha = 2.0 / (period + 1.0)
    ema = [prices[0]]
    for p in prices[1:]:
        ema.append(alpha * p + (1.0 - alpha) * ema[-1])
    return ema

def calculate_rsi(prices: list[float], period: int = 14) -> list[float]:
    """Tính Relative Strength Index (RSI)"""
    if len(prices) <= period:
        return [50.0] * len(prices)
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi = [50.0] * period
    for i in range(period, len(prices)):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi

def calculate_macd(prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Tính MACD line, Signal line, Histogram"""
    if len(prices) < slow + signal:
        return [0.0] * len(prices), [0.0] * len(prices), [0.0] * len(prices)
    
    ema_fast = np.array(calculate_ema(prices, fast))
    ema_slow = np.array(calculate_ema(prices, slow))
    macd_line = ema_fast - ema_slow
    signal_line = np.array(calculate_ema(macd_line.tolist(), signal))
    hist = macd_line - signal_line
    return macd_line.tolist(), signal_line.tolist(), hist.tolist()

def calculate_bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0):
    """Tính Bollinger Bands (Upper, Middle, Lower, Bandwidth)"""
    if len(prices) < period:
        p = prices[-1] if prices else 0.0
        return [p]*len(prices), [p]*len(prices), [p]*len(prices), [0.0]*len(prices)
    
    upper = []
    middle = []
    lower = []
    bandwidth = []
    
    for i in range(len(prices)):
        if i < period - 1:
            upper.append(prices[i])
            middle.append(prices[i])
            lower.append(prices[i])
            bandwidth.append(0.0)
        else:
            window = prices[i - period + 1 : i + 1]
            ma = float(np.mean(window))
            std = float(np.std(window))
            up = ma + num_std * std
            dn = ma - num_std * std
            bw = (up - dn) / ma if ma != 0 else 0.0
            
            upper.append(up)
            middle.append(ma)
            lower.append(dn)
            bandwidth.append(bw)
            
    return upper, middle, lower, bandwidth

def calculate_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    """Tính Average True Range (ATR)"""
    if len(closes) < 2:
        return [0.0] * len(closes)
    
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
        
    return calculate_ema(trs, period)

def detect_rsi_divergence(prices: list[float], rsi: list[float], lookback: int = 15) -> str:
    """
    Phát hiện phân kỳ RSI:
    - Bullish Divergence (Phân kỳ tăng): Giá tạo đáy thấp hơn nhưng RSI tạo đáy cao hơn -> Tín hiệu ĐẢO CHIỀU TĂNG.
    - Bearish Divergence (Phân kỳ giảm): Giá tạo đỉnh cao hơn nhưng RSI tạo đỉnh thấp hơn -> Tín hiệu ĐẢO CHIỀU GIẢM.
    """
    if len(prices) < lookback or len(rsi) < lookback:
        return "NONE"
    
    p_window = prices[-lookback:]
    r_window = rsi[-lookback:]
    
    # Kiểm tra đáy
    p_min_idx = int(np.argmin(p_window))
    if p_min_idx == lookback - 1 and p_window[-1] < p_window[0] and r_window[-1] > r_window[0] and r_window[-1] < 35:
        return "BULLISH_DIVERGENCE"
        
    # Kiểm tra đỉnh
    p_max_idx = int(np.argmax(p_window))
    if p_max_idx == lookback - 1 and p_window[-1] > p_window[0] and r_window[-1] < r_window[0] and r_window[-1] > 65:
        return "BEARISH_DIVERGENCE"
        
    return "NONE"
