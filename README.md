# Tool Quy Trình Video: YouTube → Kịch bản → Voice → SRT + Từ khóa Canva 🎬

Đúng quy trình làm video của bạn, gói trong 1 giao diện:

1. **Lấy kịch bản từ link YouTube** — dán link, tool lấy lời thoại từ phụ đề của video (ưu tiên phụ đề chính thức, không có thì lấy phụ đề tự động). Hợp với các kênh sức khỏe Hàn Quốc: chọn ngôn ngữ gốc "Tiếng Hàn".
2. **Sửa thành kịch bản của mình** — kịch bản gốc hiện trong ô text, bạn sửa/dịch/viết lại trực tiếp, hoặc dán kịch bản của bạn vào.
3. **Tạo voice** — giọng đọc tiếng Việt bằng Edge TTS (miễn phí, cùng công nghệ VeTay): NamMinh (nam, trầm) hoặc HoaiMy (nữ, ấm), chỉnh được tốc độ. Không thích giọng máy thì tải file giọng của bạn lên thay.
4. **Xuất SRT + Bảng phân cảnh** — tool nghe lại voice, tạo file .srt, đồng thời phân tích từng cảnh thành **từ khóa Canva** và xuất bảng giống hệt mẫu của bạn (Cảnh/Thời gian | Lời đọc | Từ khóa Canva | Trạng thái) dưới dạng file CSV mở bằng Excel.

## Giọng đọc & Clone giọng (v1.2)
Bước 3 có 3 chế độ:
1. **Giọng có sẵn (Edge TTS, miễn phí)** — 20 giọng: Việt (NamMinh, HoaiMy), Anh Mỹ/Anh Anh (7 giọng), Nhật, Hàn (3 giọng), Đức, Thái, Trung. **Nguyên tắc đọc chuẩn: giọng phải đúng ngôn ngữ của kịch bản** — kịch bản tiếng Hàn chọn giọng Hàn, tiếng Nhật chọn giọng Nhật. Chọn sai ngôn ngữ là đọc sai ngay.
2. **Clone giọng bằng XTTS (offline, miễn phí)** — tải lên đoạn giọng mẫu 6–30 giây (1 người nói, ít tạp âm), tool nhân bản giọng đó để đọc tiếng Anh/Nhật/Hàn/Đức/Pháp/Tây Ban Nha/Trung... **Giới hạn thật: XTTS không có tiếng Việt.** Cần cài thêm: `pip install -r requirements_clone.txt` (nặng ~2–3 GB, nên dùng Python 3.10/3.11). Lần đầu chạy tải model ~1,8 GB.
3. **Clone giọng bằng ElevenLabs (online, trả phí)** — đường duy nhất clone được **tiếng Việt** mà vẫn đọc đa ngôn ngữ bằng cùng một giọng. Cách làm: đăng ký elevenlabs.io → mục Voices → tạo giọng clone từ file ghi âm của bạn → lấy API key (Profile → API Key) và Voice ID → dán vào tool. API key chỉ nhập trên máy của bạn.

Mẹo đọc chuẩn ở mọi chế độ: viết số thành chữ khi cần đọc rõ (ví dụ "năm mươi nghìn"), thêm dấu câu để giọng ngắt nghỉ đúng chỗ, và tên riêng nước ngoài nên viết phiên âm nếu giọng hay đọc sai.
Chỉ clone giọng của chính bạn hoặc giọng đã được chủ giọng đồng ý.

## Từ khóa Canva được tạo thế nào để "sát nhất"?
- Rút gọn theo công thức **Chủ thể + Hành động + Bối cảnh** — cách Canva tìm ảnh/video chuẩn nhất (không bao giờ dùng cả câu lời đọc để tìm).
- Ưu tiên hành động nhìn thấy được và cụ thể nhất trong câu: "đo huyết áp" thắng "sức khỏe", "đi bộ trong công viên" thắng "xương khớp".
- Câu mở đầu/chung chung không có hình ảnh cụ thể → dùng từ khóa mặc định của kênh (chủ thể + "sinh hoạt tại nhà") — đúng như bảng mẫu của bạn.
- Mỗi cảnh có thêm **từ khóa tiếng Anh**: tìm trên Canva bằng tiếng Anh thường ra nhiều kết quả đẹp hơn.
- Đổi "Chủ thể chính của kênh" ở Bước 4 nếu làm kênh khác (ví dụ: trẻ em, bà bầu).

## Mới ở v1.3 — Từ khóa món ăn / nấu nướng (học từ bảng 19 cảnh mướp đã sửa tay)
- Thêm từ điển **món ăn và nấu nướng**: tên món ("Món 1: Canh mướp hầm xương ống" → đúng tên món đó làm từ khóa), động tác nấu (hầm, xào, hấp, nấu chung) và nguyên liệu (mướp, xương ống, mề gà, trứng gà, lạc/đậu phộng, gừng hành tím). Bản v1.2 gặp 3 câu này đều rơi về từ khóa mặc định chung chung — v1.3 ra đúng ngay.
- Sửa lỗi nhầm nguy hiểm: **"xương ống / hầm xương" (nấu canh) không còn bị nhận thành "đau xương khớp" (bệnh)** — hai nghĩa của chữ "xương" đã tách riêng. Tương tự: cảnh giải thích công dụng ("mướp tốt cho xương khớp") ra từ khóa bác sĩ tư vấn, còn cảnh nói "đầy bụng" thì triệu chứng thắng.
- **Gom cảnh theo ý trọn vẹn (10–25 giây)** thay vì theo mảnh phụ đề: Bước 4 giờ gom các dòng phụ đề ngắn thành từng cảnh đúng 1 ý (đủ 10 giây và hết câu mới cắt, tối đa 25 giây, món mới luôn mở cảnh mới) — đúng kiểu bảng 19 cảnh bạn sửa tay từ 80 mảnh vụn, thay vì bản cũ chỉ gom mảnh dưới 1 giây.
- Kèm file `test_keywords_v13.py`: chạy `python test_keywords_v13.py` để kiểm chứng lại với chính bảng 19 cảnh mướp — kết quả hiện tại: khớp 17/19, 2 cảnh còn lại lệch theo hướng chấp nhận được (cảnh 1 là lời chào, từ khóa "ăn uống lành mạnh" của bản tay đến từ bối cảnh kênh chứ không có trong câu; cảnh 7 máy chọn hình món ăn thay vì hình "đi bộ dẻo dai"), gom cảnh giữ nguyên 19/19 trên file SRT đã sửa.

## Chạy tool
Giải nén → nhấp đúp **run.bat** (lần đầu tự cài thư viện) → giao diện mở trên trình duyệt.
Bước 1 và 3 cần Internet (lấy phụ đề YouTube + tạo voice). Bước 4 chạy offline trên máy; máy thiếu thư viện CUDA thì tool tự chạy bằng CPU (chậm hơn một chút, không lỗi).

## Lỗi 429 "Too Many Requests" ở Bước 1 (đã sửa ở v1.1)
Bản cũ xin YouTube tải TẤT CẢ các bản phụ đề cùng lúc (kể cả các bản dịch tự động kiểu "vi-ko") nên bị YouTube chặn. Bản v1.1 chỉ xem danh sách phụ đề, chọn đúng 1 bản tốt nhất rồi tải 1 bản đó, và tự chờ-thử-lại khi bị 429. Nếu vẫn bị chặn (IP bị YouTube để ý sau nhiều lần tải): chờ 2–5 phút, và bật ô **"Dùng cookie từ Chrome"** ở Bước 1 (cần đã đăng nhập YouTube trên Chrome; nếu báo lỗi cookie khi Chrome đang mở, tắt hẳn Chrome rồi bấm lại).

## Lưu ý
- Tôn trọng bản quyền: hãy viết lại kịch bản thành nội dung của bạn (Bước 2) thay vì dùng nguyên văn video gốc.
- Video không có phụ đề nào (kể cả tự động) thì Bước 1 không lấy được — hãy chọn video khác.

## Tự cập nhật qua GitHub (từ v1.4.0)
Tool nằm trên kho GitHub công khai `ngocquanvipro47-collab/quy-trinh-video`.
Trong giao diện có 2 nút ở trên cùng: **Kiểm tra cập nhật** và **Cập nhật ngay**.
Khi có bản mới, chỉ cần bấm Cập nhật ngay — tool tự tải các file mới từ GitHub về ghi đè,
bạn tắt tool rồi mở lại run.bat là dùng bản mới, **không phải tải lại file zip**.
(File run.bat không tự cập nhật vì nó là file đang chạy; gần như không bao giờ cần đổi nó.)
