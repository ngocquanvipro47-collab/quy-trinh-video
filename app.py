"""
Tool QUY TRINH VIDEO: Link YouTube -> Kich ban -> Voice -> SRT + Bang tu khoa Canva
Buoc 1: Dan link YouTube, lay loi thoai tu phu de video (ke ca phu de tu dong).
Buoc 2: Sua kich ban thanh cua minh ngay trong o text (hoac dan kich ban cua ban vao).
Buoc 3: Tao voice tieng Viet bang Edge TTS (hoac tai file giong cua ban len).
Buoc 4: Tao file SRT + Bang phan canh co san TU KHOA CANVA cho tung canh.
"""
import csv
import os
import re

import gradio as gr

from updater import LOCAL_VERSION, check_update, do_update
from clone_tts import XTTS_LANGS, elevenlabs_tts, xtts_clone
from engine import transcribe_to_srt
from keywords import canva_keywords
from tts import VOICE_CHOICES, make_voice
from youtube_script import clean_error, fetch_youtube_script

OUT_DIR = os.path.join(os.getcwd(), "ket_qua")
os.makedirs(OUT_DIR, exist_ok=True)
HEADERS = ["Cảnh / Thời gian", "Lời đọc", "Từ khóa Canva", "Từ khóa Canva (EN)", "Trạng thái"]


def step1_fetch(url, src_lang, use_cookies):
    if not url or "youtu" not in url:
        return "Hãy dán link YouTube hợp lệ.", "", ""
    try:
        title, lang, text = fetch_youtube_script(url.strip(), src_lang, use_cookies=bool(use_cookies))
        return (f"ĐÃ LẤY ĐƯỢC KỊCH BẢN!\nVideo: {title}\nPhụ đề đã dùng: {lang}\n"
                f"Độ dài: {len(text)} ký tự.\n"
                "Giờ sang Bước 2: sửa lại nội dung trong ô bên dưới thành kịch bản của bạn "
                "(dịch / viết lại theo ý mình), rồi tạo voice."), title, text
    except Exception as e:
        return f"CÓ LỖI: {clean_error(e)}", "", ""


def step3_voice(script, mode, voice, speed, sample, clone_lang, el_key, el_voice_id):
    try:
        if mode == "edge":
            out = os.path.join(OUT_DIR, "voice.mp3")
            make_voice(script, voice=voice, speed_percent=int(speed), out_path=out)
            return "ĐÃ TẠO XONG VOICE (giọng có sẵn)! Nghe thử bên dưới, rồi sang Bước 4.", out
        if mode == "xtts":
            out = os.path.join(OUT_DIR, "voice_clone.wav")
            xtts_clone(script, sample, language=clone_lang, out_path=out)
            return ("ĐÃ CLONE XONG VOICE BẰNG XTTS! Lần đầu chạy sẽ tải model khoảng 1,8 GB. "
                    "Nghe thử bên dưới, rồi sang Bước 4."), out
        out = os.path.join(OUT_DIR, "voice_elevenlabs.mp3")
        elevenlabs_tts(script, (el_key or "").strip(), (el_voice_id or "").strip(), out_path=out)
        return "ĐÃ TẠO XONG VOICE BẰNG GIỌNG CLONE ELEVENLABS! Nghe thử bên dưới, rồi sang Bước 4.", out
    except Exception as e:
        return f"CÓ LỖI: {e}", None


def parse_srt(path):
    cues = []
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8").read().strip())
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        def to_sec(ts):
            ts = ts.strip().replace(",", ".")
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
        start, end = lines[1].split("-->")
        cues.append((to_sec(start), to_sec(end), " ".join(lines[2:])))
    return cues


def merge_scenes(cues):
    """Gom cac dong phu de ngan thanh tung CANH loi doc tron y (10-25 giay),
    nhu ban sua tay 1_Canva.srt: 80 manh vun -> 19 canh.
    Quy tac: tich luy cho den khi du 10 giay VA het cau (dau ., !, ?, …, ”),
    hoac vuot 25 giay thi cat; mon moi ("Mon N: ...") luon bat dau canh moi.
    Ban cu chi gom manh <1 giay hoac <12 ky tu nen bang ra vo manh, tim Canva cham."""
    scenes = []
    cur = None  # [start, end, text]
    for start, end, text in cues:
        if cur is None:
            cur = [start, end, text]
            continue
        new_dish = re.search(r"món\s*\d+\s*:", text, re.I)
        dur = end - cur[0]
        ends_sentence = cur[2].rstrip().endswith((".", "!", "?", "…", "”", '"'))
        if new_dish or (dur >= 10.0 and ends_sentence) or dur >= 25.0:
            scenes.append(tuple(cur))
            cur = [start, end, text]
        else:
            cur[1] = end
            cur[2] = (cur[2] + " " + text).strip()
    if cur is not None:
        scenes.append(tuple(cur))
    return scenes


def step4_srt(voice_file, model_size, max_chars, subject_vn):
    if not voice_file:
        return "Chưa có file voice. Hãy tạo voice ở Bước 3 hoặc tải file giọng của bạn lên.", None, None, [], ""
    try:
        srt_path = os.path.join(OUT_DIR, "phu_de.srt")
        transcribe_to_srt(voice_file, output_srt=srt_path, model_size=model_size,
                          language="vi", max_chars=int(max_chars), device="auto")
        cues = merge_scenes(parse_srt(srt_path))
        rows = []
        for i, (start, end, text) in enumerate(cues, 1):
            kw_vn, kw_en = canva_keywords(text, subject_vn=subject_vn.strip() or "người cao tuổi")
            rows.append([f"{i} | {start:.3f} → {end:.3f}", text, kw_vn, kw_en, "Chưa dựng"])
        csv_path = os.path.join(OUT_DIR, "bang_phan_canh.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADERS)
            w.writerows(rows)
        preview = open(srt_path, encoding="utf-8").read()
        return (f"HOÀN TẤT! Đã tạo SRT ({len(rows)} cảnh) và bảng phân cảnh kèm từ khóa Canva.\n"
                "Mở file bang_phan_canh.csv bằng Excel để xem/in bảng như ảnh mẫu."), srt_path, csv_path, rows, preview
    except Exception as e:
        return f"CÓ LỖI: {e}", None, None, [], ""


def ui_check_update():
    try:
        info = check_update()
        if not info:
            return f"Bạn đang dùng bản mới nhất (v{LOCAL_VERSION})."
        return (f"CÓ BẢN MỚI v{info['version']}! {info.get('notes', '')}\n"
                "Bấm nút 'Cập nhật ngay' bên cạnh để tự cập nhật, không cần tải lại file zip.")
    except Exception as e:
        return f"Không kiểm tra được cập nhật (kiểm tra lại mạng rồi thử lại): {e}"


def ui_do_update():
    try:
        v = do_update()
        if not v:
            return f"Bạn đang dùng bản mới nhất (v{LOCAL_VERSION}), không cần cập nhật."
        return (f"ĐÃ CẬP NHẬT LÊN v{v}!\n"
                "Hãy TẮT hẳn cửa sổ tool này rồi mở lại run.bat để dùng bản mới.")
    except Exception as e:
        return f"Cập nhật bị lỗi: {e}"


with gr.Blocks(title="Quy trình Video: YouTube → Voice → SRT + Từ khóa Canva") as demo:
    gr.Markdown("# 🎬 Quy trình Video: YouTube → Kịch bản → Voice → SRT + Từ khóa Canva")
    with gr.Row():
        btn_check = gr.Button("🔄 Kiểm tra cập nhật", scale=1)
        btn_do = gr.Button("⬆️ Cập nhật ngay", variant="primary", scale=1)
        upd_status = gr.Textbox(label=f"Cập nhật phần mềm qua GitHub (bản đang chạy: v{LOCAL_VERSION})",
                                lines=2, scale=3, interactive=False)
    btn_check.click(ui_check_update, outputs=upd_status)
    btn_do.click(ui_do_update, outputs=upd_status)
    gr.Markdown("## Bước 1 — Lấy kịch bản từ link YouTube")
    with gr.Row():
        url = gr.Textbox(label="Dán link video YouTube", scale=3)
        src_lang = gr.Dropdown(
            choices=[("Tiếng Hàn (kênh Hàn)", "ko"), ("Tiếng Việt", "vi"), ("Tiếng Anh", "en"),
                     ("Tiếng Nhật", "ja"), ("Tự động - có phụ đề nào lấy phụ đề đó", "auto")],
            value="ko", label="Ngôn ngữ gốc của video", scale=1)
    cookies_cb = gr.Checkbox(value=False, label="Dùng cookie từ Chrome (bật khi bị lỗi 429 - cần đã đăng nhập YouTube trên Chrome; "
                                                "nếu Chrome đang mở mà báo lỗi cookie, hãy tắt hẳn Chrome rồi bấm lại)")
    btn1 = gr.Button("⬇️ LẤY KỊCH BẢN TỪ LINK", variant="primary")
    status1 = gr.Textbox(label="Trạng thái bước 1", lines=4)
    title_box = gr.Textbox(label="Tiêu đề video gốc")

    gr.Markdown("## Bước 2 — Sửa thành kịch bản của bạn")
    script = gr.Textbox(label="Kịch bản (kịch bản gốc hiện ở đây — hãy sửa / dịch / viết lại thành của bạn, "
                              "hoặc xóa đi và dán kịch bản của bạn vào)", lines=12)
    btn1.click(step1_fetch, inputs=[url, src_lang, cookies_cb], outputs=[status1, title_box, script])

    gr.Markdown("## Bước 3 — Tạo voice")
    mode_dd = gr.Dropdown(
        choices=[("Giọng có sẵn (Edge TTS - miễn phí, nhiều giọng Việt/Anh/Nhật/Hàn/Đức/Thái/Trung)", "edge"),
                 ("CLONE giọng bằng XTTS - offline, miễn phí (Anh/Nhật/Hàn/Đức... KHÔNG có tiếng Việt)", "xtts"),
                 ("CLONE giọng bằng ElevenLabs - online, trả phí (clone được cả TIẾNG VIỆT, đọc chuẩn nhất)", "eleven")],
        value="edge", label="Chế độ tạo voice")
    with gr.Row():
        voice_dd = gr.Dropdown(choices=VOICE_CHOICES, value="vi-VN-NamMinhNeural",
                               label="[Chế độ giọng có sẵn] Chọn giọng - NHỚ chọn giọng đúng ngôn ngữ của kịch bản mới đọc chuẩn")
        speed = gr.Slider(-30, 30, value=0, step=1, label="Tốc độ đọc (%) - trừ là chậm lại, cộng là nhanh hơn")
    with gr.Row():
        sample_up = gr.File(label="[Chế độ XTTS] File giọng mẫu để clone (6-30 giây, 1 người nói, ít tạp âm)",
                            file_types=["audio", ".mp3", ".wav", ".m4a"])
        clone_lang = gr.Dropdown(choices=[(v, k) for k, v in XTTS_LANGS.items()], value="ko",
                                 label="[Chế độ XTTS] Ngôn ngữ sẽ đọc bằng giọng clone")
    with gr.Row():
        el_key = gr.Textbox(label="[ElevenLabs] API key (chỉ lưu trên máy của bạn)", type="password")
        el_voice = gr.Textbox(label="[ElevenLabs] Voice ID của giọng đã clone trên elevenlabs.io")
    btn3 = gr.Button("🎙️ TẠO VOICE TỪ KỊCH BẢN", variant="primary")
    status3 = gr.Textbox(label="Trạng thái bước 3", lines=3)
    audio_out = gr.Audio(label="Nghe thử voice / file voice sẽ dùng ở Bước 4", type="filepath")
    btn3.click(step3_voice, inputs=[script, mode_dd, voice_dd, speed, sample_up, clone_lang, el_key, el_voice],
               outputs=[status3, audio_out])
    gr.Markdown("_Không muốn dùng giọng máy? Cứ tải thẳng file giọng của bạn vào ô nghe thử ở trên._")

    gr.Markdown("## Bước 4 — Xuất SRT + Bảng phân cảnh có từ khóa Canva")
    with gr.Row():
        model_dd = gr.Dropdown(choices=[("small - Khuyên dùng", "small"), ("base - Nhanh", "base"),
                                        ("medium - Chính xác hơn", "medium"), ("large-v3 - Tốt nhất, nặng", "large-v3")],
                               value="small", label="Model nghe (độ chính xác)")
        maxc = gr.Slider(28, 84, value=42, step=1, label="Số chữ tối đa / 1 dòng phụ đề")
        subject = gr.Textbox(value="người cao tuổi", label="Chủ thể chính của kênh (để ghép vào từ khóa Canva)")
    btn4 = gr.Button("📝 TẠO SRT + BẢNG TỪ KHÓA CANVA", variant="primary", size="lg")
    status4 = gr.Textbox(label="Trạng thái bước 4", lines=3)
    with gr.Row():
        srt_out = gr.File(label="Tải file .SRT")
        csv_out = gr.File(label="Tải bảng phân cảnh .CSV (mở bằng Excel)")
    table = gr.Dataframe(headers=HEADERS, label="Bảng phân cảnh - xem trước", wrap=True)
    srt_preview = gr.Textbox(label="Xem trước nội dung SRT", lines=10)
    btn4.click(step4_srt, inputs=[audio_out, model_dd, maxc, subject],
               outputs=[status4, srt_out, csv_out, table, srt_preview])
    gr.Markdown("**Mẹo từ khóa:** cột Từ khóa Canva đã được rút gọn theo công thức *Chủ thể + Hành động + Bối cảnh* "
                "(cách Canva tìm ra ảnh/video sát nhất). Cột tiếng Anh thường cho nhiều kết quả đẹp hơn khi tìm trên Canva.")

if __name__ == "__main__":
    demo.launch(inbrowser=True)
