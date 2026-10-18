# ⚡ Vibe-Trading AI | Binance Futures Desktop Terminal

Hệ thống giao dịch tự động phái sinh (Binance USDT-M Futures) trên máy tính, tích hợp trí tuệ nhân tạo (AI Reasoning) và phương pháp phân tích định lượng đa khung thời gian (Multi-Timeframe 1m - 5m - 15m) kế thừa từ dự án [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading).

---

## 🌟 Tính Năng Nổi Bật

1. **Biểu đồ nến TradingView trực quan (TradingView Lightweight Charts):**
   - Hiển thị nến theo thời gian thực (Real-time K-line) 1m, 5m, 15m.
   - Tự động gắn mũi tên chỉ hướng vào lệnh trực tiếp trên nến (Mũi tên Xanh: **AI LONG**, Mũi tên Đỏ: **AI SHORT**).
2. **Khung AI Phân Tích & Thảo Luận Sóng (Live AI Discussion Stream):**
   - AI liên tục quét cấu trúc thị trường, phân tích xu hướng 15m (Macro Trend), vùng nén 5m (Bollinger Squeeze / Pullback) và điểm kích hoạt 1m (Trigger / RSI Divergence / MACD / Volume Spike).
   - Thảo luận chi tiết lý do vào lệnh hoặc tại sao nên đứng ngoài quan sát để bảo vệ vốn.
3. **Quản trị rủi ro & Bảo vệ tài sản tuyệt đối (Risk Guardrail):**
   - **Vốn ký quỹ cố định (Fixed Margin):** Mặc định $20 hoặc số tiền tùy chỉnh.
   - **Đòn bẩy (Leverage):** Hỗ trợ đòn bẩy tùy chỉnh (ví dụ 10x, 20x) với chế độ **ISOLATED MARGIN** (cô lập rủi ro, không lo ảnh hưởng toàn bộ ví).
   - **Stop Loss cứng theo %:** Tự động cắt lỗ ngay khi giá đi ngược % đã đặt (ví dụ 1.5%).
   - **Take Profit theo %:** Tự động chốt lời với tỉ lệ Risk:Reward tối ưu.
   - **Nút Khẩn Cấp (Panic Close All):** Đóng tức thì toàn bộ vị thế và hủy mọi lệnh chờ chỉ với 1 click.
4. **Công tắc Auto-Trade:**
   - Tùy chọn Bật/Tắt chế độ tự động vào lệnh.
   - Khi Tắt: Hoạt động như một trợ lý AI phân tích và đưa ra tín hiệu cho bạn xem.
   - Khi Bật: Tự động gửi lệnh lên sàn Binance khi độ tin cậy của AI $\ge 75\%$.

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Động

### Cách 1: Chạy trực tiếp bằng file `.bat`
Chỉ cần nhấp đúp chuột vào file:
```
run_app.bat
```

### Cách 2: Chạy bằng dòng lệnh Terminal
```bash
cd C:\Users\Admin\.gemini\antigravity\scratch\binance-futures-ai-bot
python main.py
```

Sau khi chạy, phần mềm sẽ mở một cửa sổ ứng dụng Desktop độc lập (Native Window) hoặc mở tại địa chỉ:
👉 **`http://127.0.0.1:8000`**

---

## 🔑 Hướng Dẫn Cấu Hình API Key

Nhấp vào biểu tượng **Bánh răng Cài Đặt (Settings)** ở góc phải trên cùng của phần mềm:
1. **Chế độ Thử Nghiệm (Binance Futures Testnet):**
   - Đánh dấu tick vào ô *"Sử dụng Binance Futures Testnet"*.
   - Đăng ký API Key Testnet miễn phí tại: [https://testnet.binancefuture.com](https://testnet.binancefuture.com) (Được cấp sẵn 10,000 USDT ảo để test mà không lo mất tiền thật).
2. **Chế độ Đánh Thật (Binance Realnet):**
   - Bỏ tick ô Testnet.
   - Nhập API Key & Secret Key tạo từ tài khoản Binance của bạn (bật quyền **Enable Futures**).
3. **Lựa chọn bộ não AI:**
   - **Local Quant Engine (Mặc định):** Hoàn toàn miễn phí, chạy offline, phân tích toán học cực nhanh theo công thức của Vibe-Trading.
   - **DeepSeek AI:** Rẻ và siêu thông minh trong phân tích cấu trúc thị trường. Nhập API Key từ platform.deepseek.com.
   - **OpenAI (GPT-4o):** Phân tích sâu theo văn phong chuyên gia.
