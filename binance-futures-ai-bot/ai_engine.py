import json
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("AIEngine")

class AITradingEngine:
    """
    AI Trading Engine kế thừa triết lý của HKUDS/Vibe-Trading:
    - Tiếp nhận ma trận dữ liệu nến & chỉ báo đa khung (15m, 5m, 1m).
    - Tạo thảo luận chuyên sâu (AI Discussion / Chain-of-Thought) về cấu trúc thị trường.
    - Ra quyết định vào lệnh dứt khoát: LONG, SHORT hoặc STAND_BY (Đứng ngoài quan sát).
    - Hỗ trợ cả LLM (DeepSeek, OpenAI, Gemini) và Local Quant Engine (miễn phí, siêu nhanh).
    """
    def __init__(self, provider: str = "local_quant", api_key: str = "", model_name: str = "deepseek-chat"):
        self.provider = provider
        self.api_key = api_key.strip()
        self.model_name = model_name

    def update_settings(self, provider: str, api_key: str, model_name: str):
        self.provider = provider
        self.api_key = api_key.strip()
        self.model_name = model_name

    def evaluate_market(self, symbol: str, data: Dict[str, Any], leverage: int, stop_loss_pct: float) -> Dict[str, Any]:
        """Đánh giá thị trường và sinh tín hiệu kèm phân tích thảo luận"""
        if self.provider != "local_quant" and self.api_key:
            try:
                return self._call_llm_api(symbol, data, leverage, stop_loss_pct)
            except Exception as e:
                logger.warning(f"Lỗi gọi LLM API ({e}), tự động chuyển về Local Quant Engine")
                
        return self._local_quant_reasoning(symbol, data, leverage, stop_loss_pct)

    def _local_quant_reasoning(self, symbol: str, data: Dict[str, Any], leverage: int, stop_loss_pct: float) -> Dict[str, Any]:
        """
        Bộ tư duy định lượng lượng tử nội bộ (Dựa trên triết lý Alpha Zoo của Vibe-Trading):
        Tự động phân tích các yếu tố hội tụ (Confluence), viết ra nhận định chi tiết từng bước.
        """
        p = data.get("current_price", 0.0)
        t15 = data.get("timeframe_15m", {})
        t5 = data.get("timeframe_5m", {})
        t1 = data.get("timeframe_1m", {})

        trend_15m = t15.get("trend", "SIDEWAY")
        ema50 = t15.get("ema50", 0)
        rsi_5m = t5.get("rsi", 50)
        pullback = t5.get("pullback_zone", "MIDDLE")
        
        rsi_1m = t1.get("rsi", 50)
        hist_1m = t1.get("macd_histogram", 0)
        macd_bull = t1.get("macd_cross_bull", False)
        macd_bear = t1.get("macd_cross_bear", False)
        divergence = t1.get("divergence", "NONE")
        vol_spike = t1.get("volume_spike", False)

        discussion_steps = []
        direction = "NEUTRAL"
        action = "WAIT"
        confidence = 50
        reason = ""

        # Bước 1: Đánh giá xu hướng vĩ mô 15m
        discussion_steps.append(f"🔍 [15m Macro Trend] Giá hiện tại: {p}. Xu hướng chủ đạo: {trend_15m} (EMA50: {ema50}).")
        
        # Bước 2: Đánh giá vùng nén và hồi quy 5m
        discussion_steps.append(f"📊 [5m Zone] RSI 5m đạt {rsi_5m}, trạng thái vị trí: {pullback}. Bollinger Band Squeeze: {t5.get('squeeze')}.")

        # Bước 3: Đánh giá xung lực ngắn hạn 1m
        discussion_steps.append(f"⚡ [1m Trigger] RSI 1m: {rsi_1m}, MACD Histogram: {hist_1m}, Phân kỳ: {divergence}, Vol Spike: {vol_spike}.")

        # Quy tắc mở vị thế LONG (Mua đuổi theo sóng tăng)
        if "BULLISH" in trend_15m:
            if divergence == "BULLISH_DIVERGENCE" or (macd_bull and rsi_1m < 60) or (pullback == "NEAR_SUPPORT" and hist_1m > 0):
                direction = "BULLISH"
                action = "BUY"
                confidence = 85 if vol_spike else 78
                reason = "Xu hướng 15m tăng rõ nét kết hợp 1m có điểm kích hoạt Momentum tăng và phân kỳ hỗ trợ."
                discussion_steps.append("🎯 [KẾT LUẬN AI] Đồng pha 3 khung thời gian xác nhận SÓNG TĂNG. Khuyến nghị mở vị thế LONG.")
            else:
                direction = "BULLISH"
                action = "WAIT"
                confidence = 65
                reason = "Xu hướng 15m tăng nhưng 1m chưa có điểm vào tối ưu, đang chờ nến hồi."
                discussion_steps.append("⏳ [KẾT LUẬN AI] Xu hướng 15m tăng, nhưng khung 1m đang quá độ/chưa có xác nhận. Kiên nhẫn chờ điểm hồi.")
                
        # Quy tắc mở vị thế SHORT (Bán khống theo sóng giảm)
        elif "BEARISH" in trend_15m:
            if divergence == "BEARISH_DIVERGENCE" or (macd_bear and rsi_1m > 40) or (pullback == "NEAR_RESISTANCE" and hist_1m < 0):
                direction = "BEARISH"
                action = "SELL"
                confidence = 85 if vol_spike else 78
                reason = "Xu hướng 15m giảm mạnh, khung 5m chạm kháng cự và 1m kích hoạt tín hiệu gãy sóng."
                discussion_steps.append("🎯 [KẾT LUẬN AI] Đồng pha xác nhận SÓNG GIẢM. Khuyến nghị mở vị thế SHORT.")
            else:
                direction = "BEARISH"
                action = "WAIT"
                confidence = 65
                reason = "Xu hướng 15m giảm nhưng chưa có điểm kích hoạt Short đẹp trên 1m."
                discussion_steps.append("⏳ [KẾT LUẬN AI] Thị trường đang đà giảm, chờ nến hồi lên cản 1m để tìm điểm Short tối ưu.")
        else:
            direction = "NEUTRAL"
            action = "WAIT"
            confidence = 45
            reason = "Thị trường 15m đang đi ngang (Sideway) tích lũy, không vào lệnh để tránh bẫy thanh khoản."
            discussion_steps.append("🛡️ [KẾT LUẬN AI] Thị trường đi ngang không rõ xu hướng. Giữ tiền an toàn, ĐỨNG NGOÀI QUAN SÁT.")

        # Bước 4: AI tự động phân tích vùng Giá Dự Kiến (Target TP & Stop Loss) dựa trên Cấu trúc thị trường & ATR
        atr = data.get("atr", p * 0.005)
        sup = data.get("support_level", p * 0.99)
        res_lvl = data.get("resistance_level", p * 1.01)

        # Tính toán SL & TP động thông minh:
        # Long: SL đặt ngay dưới Hỗ Trợ 5m hoặc -1.5x ATR; TP đặt tại Kháng Cự 5m hoặc +2.5x ATR
        # Short: SL đặt ngay trên Kháng Cự 5m hoặc +1.5x ATR; TP đặt tại Hỗ Trợ 5m hoặc -2.5x ATR
        if action == "BUY" or (action == "WAIT" and "BULLISH" in trend_15m):
            sl_price = min(sup * 0.998, p - (1.5 * atr))
            tp_price = max(res_lvl * 1.002, p + (2.5 * atr))
            sl_pct = max(0.4, round(((p - sl_price) / p) * 100, 2))
            tp_pct = max(0.8, round(((tp_price - p) / p) * 100, 2))
        elif action == "SELL" or (action == "WAIT" and "BEARISH" in trend_15m):
            sl_price = max(res_lvl * 1.002, p + (1.5 * atr))
            tp_price = min(sup * 0.998, p - (2.5 * atr))
            sl_pct = max(0.4, round(((sl_price - p) / p) * 100, 2))
            tp_pct = max(0.8, round(((p - tp_price) / p) * 100, 2))
        else: # Sideway
            sl_price = p * (1.0 - stop_loss_pct / 100.0)
            tp_price = p * (1.0 + (stop_loss_pct * 2.0) / 100.0)
            sl_pct = stop_loss_pct
            tp_pct = stop_loss_pct * 2.0

        # Làm tròn theo độ lớn giá
        decimals = 6 if p < 0.01 else (4 if p < 1 else 2)
        sl_price = round(sl_price, decimals)
        tp_price = round(tp_price, decimals)

        # Bổ sung vào Thảo luận của AI
        discussion_steps.append(
            f"🎯 [MỤC TIÊU DỰ KIẾN TỪ AI] Target Chốt Lời (TP): {tp_price} (+{tp_pct}%), "
            f"Ngưỡng Cắt Lỗ (SL): {sl_price} (-{sl_pct}%). "
            f"Tỉ lệ R:R = 1:{(tp_pct / sl_pct if sl_pct > 0 else 2.0):.1f}."
        )

        discussion_text = "\n".join(discussion_steps)

        return {
            "symbol": symbol,
            "direction": direction,
            "action": action, # "BUY" (LONG), "SELL" (SHORT), "WAIT"
            "confidence": confidence,
            "reason": reason,
            "discussion": discussion_text,
            "current_price": p,
            "suggested_sl": sl_price,
            "suggested_tp": tp_price,
            "suggested_sl_pct": sl_pct,
            "suggested_tp_pct": tp_pct,
            "leverage": leverage
        }

    def _call_llm_api(self, symbol: str, data: Dict[str, Any], leverage: int, stop_loss_pct: float) -> Dict[str, Any]:
        """Gọi API LLM (DeepSeek / OpenAI / Gemini) với Prompt lượng tử"""
        system_prompt = (
            "Bạn là một chuyên gia giao dịch định lượng và AI Scalper chuyên nghiệp cho Binance Futures. "
            "Bạn phân tích thị trường theo phương pháp sóng đa khung thời gian (15m xác định xu hướng lớn, "
            "5m tìm vùng hồi quy/nén, 1m tìm điểm kích hoạt vào lệnh). "
            "Bạn LUÔN trả về JSON hợp lệ theo đúng cấu trúc yêu cầu."
        )
        user_prompt = f"""
Dữ liệu thị trường cho cặp {symbol}:
{json.dumps(data, indent=2, ensure_ascii=False)}

Cấu hình quản trị vốn:
- Đòn bẩy: {leverage}x
- Stop Loss %: {stop_loss_pct}%

YÊU CẦU:
1. Viết một đoạn 'discussion' phân tích thảo luận chi tiết (3-5 câu) như một trader chuyên nghiệp giải thích cấu trúc sóng, vùng hỗ trợ/kháng cự và lý do.
2. Quyết định hành động ('action'): 'BUY' (Mở LONG), 'SELL' (Mở SHORT), hoặc 'WAIT' (Đứng ngoài).
3. Độ tin cậy ('confidence'): từ 0 đến 100.
4. Hướng xu hướng ('direction'): 'BULLISH', 'BEARISH', hoặc 'NEUTRAL'.

Định dạng JSON bắt buộc:
{{
  "direction": "BULLISH" | "BEARISH" | "NEUTRAL",
  "action": "BUY" | "SELL" | "WAIT",
  "confidence": 85,
  "reason": "Tóm tắt 1 câu ngắn gọn",
  "discussion": "Chi tiết thảo luận của AI...",
  "suggested_sl": 0.0,
  "suggested_tp": 0.0
}}
"""
        url = "https://api.deepseek.com/chat/completions"
        if "openai" in self.provider:
            url = "https://api.openai.com/v1/chat/completions"
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        result["current_price"] = data.get("current_price", 0.0)
        result["leverage"] = leverage
        return result
