# Chạy tool ngay trên GitHub (Codespaces) — không cần cài gì trên máy

Codespaces là một máy ảo của GitHub mở ngay trong trình duyệt.

## Cách chạy (lần đầu hơi chờ, các lần sau nhanh)
1. Vào trang kho: https://github.com/ngocquanvipro47-collab/quy-trinh-video
2. Bấm nút xanh **Code** → chọn thẻ **Codespaces** → **Create codespace on main**.
3. Chờ máy ảo khởi động (lần đầu khoảng 2-5 phút, nó tự cài sẵn thư viện).
4. Ở khung Terminal (thanh gõ lệnh) phía dưới, gõ: `python app.py` rồi Enter.
5. Hiện thông báo cổng 7860 thì bấm **Open in Browser** — giao diện tool mở ra, dùng y như trên máy nhà.

## Lưu ý quan trọng
- **Hạn mức miễn phí:** tài khoản cá nhân được 120 giờ-lõi/tháng (máy 2 lõi = khoảng 60 giờ chạy). Dùng xong nhớ **tắt máy ảo**: vào https://github.com/codespaces → bấm dấu ... ở máy của tool → **Stop codespace**. Để quên là nó tự tắt sau 30 phút không dùng, nhưng cứ tắt tay cho chắc.
- **Bước 4 (tạo SRT) trên Codespaces chạy bằng CPU** (máy ảo không có card đồ họa) — chọn model **base** hoặc **small**, file dài sẽ chậm hơn máy nhà có RTX 2060.
- **Bước 1 (lấy phụ đề YouTube)** từ IP máy ảo đôi khi bị YouTube hỏi kiểm tra robot. Cách xử lý: thử lại sau ít phút, hoặc bỏ qua Bước 1 và dán thẳng kịch bản vào ô Bước 2.
- File kết quả (voice, SRT, bảng CSV) nằm **trong máy ảo**: muốn lấy về máy nhà, bấm chuột phải vào file trong cây thư mục bên trái → **Download**. Máy ảo bị xóa sau 30 ngày không mở lại, nên tải kết quả về ngay khi làm xong.
- Tạo voice (Bước 3, giọng có sẵn + ElevenLabs) chạy trên Codespaces rất hợp vì nó dùng mạng là chính.
