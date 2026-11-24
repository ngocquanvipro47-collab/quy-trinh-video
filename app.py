"""
Tool QUY TRINH VIDEO: Link YouTube -> Kich ban -> Voice -> SRT + Bang tu khoa Canva
Buoc 1: Dan link YouTube, lay loi thoai tu phu de video (ke ca phu de tu dong).
Buoc 2: Sua kich ban thanh cua minh ngay trong o text (hoac dan kich ban cua ban vao).
Buoc 3: Tao voice tieng Viet bang Edge TTS (hoac tai file giong cua ban len).
Buoc 4: Tao file SRT + Bang phan canh co san TU KHOA CANVA cho tung canh.
"""
import os
import re
import subprocess
import sys
import threading
import time

import gradio as gr

from projects import (clear_session, has_content, list_projects, load_project,
                      load_session, save_project, save_session)
from updater import LOCAL_VERSION, check_update, do_update
from clone_tts import XTTS_LANGS, elevenlabs_tts, f5_clone, xtts_clone
from engine import transcribe_to_srt
from tts import VOICE_CHOICES, make_voice
from youtube_script import clean_error, fetch_youtube_script

OUT_DIR = os.path.join(os.getcwd(), "ket_qua")
os.makedirs(OUT_DIR, exist_ok=True)


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


def step3_voice(script, mode, voice, speed, sample, clone_lang, el_key, el_voice_id,
                f5_sample=None, f5_ref_text=""):
    try:
        if mode == "edge":
            out = os.path.join(OUT_DIR, "voice.mp3")
            make_voice(script, voice=voice, speed_percent=int(speed), out_path=out)
            return "ĐÃ TẠO XONG VOICE (giọng có sẵn)! Nghe thử bên dưới, rồi sang Bước 4.", out
        if mode == "f5vi":
            out = os.path.join(OUT_DIR, "voice_f5.wav")
            f5_clone(script, f5_sample, ref_text=f5_ref_text or "", out_path=out)
            return ("ĐÃ CLONE XONG VOICE TIẾNG VIỆT BẰNG F5-TTS! Nghe thử bên dưới, rồi sang thẻ 3. "
                    "(Nhắc nhỏ: model F5-TTS có giấy phép phi thương mại.)"), out
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


def step4_srt(voice_file, model_size, max_chars):
    """Chi tao SRT - che do SIEU TOC: nghe theo lo tren GPU + beam=1 + model nhe.
    Da bo phan tich tu khoa Canva / bang CSV theo yeu cau cua Kiu (2026-11-24)."""
    if not voice_file:
        return "Chưa có file voice. Hãy tạo voice ở thẻ 2 hoặc tải file giọng của bạn lên ô voice ở thẻ 2.", None, ""
    try:
        srt_path = os.path.join(OUT_DIR, "phu_de.srt")
        _srt, _txt, n_cues = transcribe_to_srt(
            voice_file, output_srt=srt_path, model_size=model_size,
            language="vi", max_chars=int(max_chars), device="auto",
            beam_size=1, batched=True)
        preview = open(srt_path, encoding="utf-8").read()
        return (f"HOÀN TẤT! Đã tạo file SRT ({n_cues} dòng phụ đề) ở chế độ siêu tốc. "
                "Bấm tải file .SRT bên dưới về dùng luôn."), srt_path, preview
    except Exception as e:
        return f"CÓ LỖI: {e}", None, ""


def ui_check_update():
    try:
        info = check_update()
        if not info:
            return f"Bạn đang dùng bản mới nhất (v{LOCAL_VERSION})."
        return (f"CÓ BẢN MỚI v{info['version']}! {info.get('notes', '')}\n"
                "Bấm nút 'Cập nhật ngay' bên cạnh để tự cập nhật, không cần tải lại file zip.")
    except Exception as e:
        return f"Không kiểm tra được cập nhật (kiểm tra lại mạng rồi thử lại): {e}"


def _restart_later(delay=2.5):
    """Tu dong tat tool va mo lai ban moi sau khi cap nhat (nhu phan mem that)."""
    def _run():
        time.sleep(delay)
        try:
            subprocess.Popen([sys.executable, os.path.abspath(__file__)],
                             cwd=os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_run, daemon=True).start()


def ui_do_update():
    try:
        v = do_update()
        if not v:
            return f"Bạn đang dùng bản mới nhất (v{LOCAL_VERSION}), không cần cập nhật."
        _restart_later()
        return (f"ĐÃ CẬP NHẬT LÊN v{v}! Tool sẽ TỰ TẮT và MỞ LẠI sau vài giây — "
                "nội dung đang làm đã được tự lưu, mở lại là thấy nguyên như cũ.")
    except Exception as e:
        return f"Cập nhật bị lỗi: {e}"


APP_CSS = """
.gradio-container{max-width:1020px!important;margin:0 auto!important;font-size:14px}
body{background:linear-gradient(180deg,#ecfdf5 0,#f8fafc 260px)!important}
#banner{background:linear-gradient(92deg,#0f766e,#14b8a6 55%,#06b6d4);border-radius:16px;
  padding:16px 20px 13px;color:#fff;box-shadow:0 6px 18px rgba(13,148,136,.28);margin-bottom:10px}
#banner .t{font-size:22px;font-weight:800;letter-spacing:.2px}
#banner .s{font-size:12.5px;color:#d7f9f3;margin-top:2px}
#banner .v{display:inline-block;background:rgba(255,255,255,.22);border:1px solid rgba(255,255,255,.45);
  border-radius:999px;padding:1px 10px;font-size:11.5px;margin-left:8px;vertical-align:2px}
.tab-nav{border-bottom:2px solid #a7f3ea!important;gap:4px}
.tab-nav button{font-size:13.5px!important;font-weight:600;padding:8px 16px!important;
  border-radius:12px 12px 0 0!important;color:#0f766e!important}
.tab-nav button.selected{background:linear-gradient(180deg,#14b8a6,#0f766e)!important;color:#fff!important}
button.primary{background:linear-gradient(92deg,#0f766e,#14b8a6)!important;border:none!important;
  border-radius:10px!important;box-shadow:0 3px 10px rgba(20,184,166,.35);font-weight:700}
button.secondary,button.sm{border-radius:10px!important}
.block{border-radius:14px!important}
input,textarea{border-radius:9px!important}
.block label span{font-size:12px!important}
footer{display:none!important}
"""

S = load_session()


def _saved_audio():
    p = S.get("audio")
    return p if p and os.path.isfile(p) else None


with gr.Blocks(title="Quy trình Video",
               theme=gr.themes.Soft(primary_hue=gr.themes.colors.teal,
                                    neutral_hue=gr.themes.colors.slate),
               css=APP_CSS) as demo:
    gr.HTML(f"""<div id="banner"><span class="t">🎬 Quy Trình Video</span><span class="v">v{LOCAL_VERSION}</span>
    <div class="s">YouTube → Kịch bản → Voice → SRT siêu tốc · Việc đang làm được TỰ LƯU, tắt mở lại không mất</div></div>""")
    with gr.Row():
        upd_status = gr.Textbox(label="Cập nhật phần mềm (qua GitHub)", lines=1, scale=4, interactive=False)
        btn_check = gr.Button("🔄 Kiểm tra", size="sm", scale=1)
        btn_do = gr.Button("⬆️ Cập nhật ngay", size="sm", variant="primary", scale=1)
    btn_check.click(ui_check_update, outputs=upd_status)
    btn_do.click(ui_do_update, outputs=upd_status)
    with gr.Row():
        proj_name = gr.Textbox(label="Tên dự án", placeholder="VD: Video suc khoe 01", scale=2, lines=1)
        btn_save_proj = gr.Button("💾 Lưu dự án", size="sm", scale=1)
        btn_new_proj = gr.Button("✨ Dự án mới", size="sm", scale=1)
        proj_dd = gr.Dropdown(choices=list_projects(), label="Dự án đã lưu", scale=2)
        btn_load_proj = gr.Button("📂 Mở dự án", size="sm", scale=1)
    proj_status = gr.Textbox(label="Dự án", lines=1, interactive=False)

    with gr.Tabs():
        with gr.Tab("1 · Kịch bản"):
            with gr.Row():
                url = gr.Textbox(label="Link video YouTube", scale=3, value=S.get("url", ""))
                src_lang = gr.Dropdown(
                    choices=[("Hàn", "ko"), ("Việt", "vi"), ("Anh", "en"), ("Nhật", "ja"), ("Tự động", "auto")],
                    value=S.get("src_lang", "ko"), label="Tiếng gốc", scale=1)
                btn1 = gr.Button("⬇️ Lấy kịch bản", variant="primary", scale=1)
            with gr.Row():
                status1 = gr.Textbox(label="Trạng thái", lines=2, scale=3)
                title_box = gr.Textbox(label="Tiêu đề video gốc", lines=2, scale=2, value=S.get("title", ""))
            with gr.Accordion("Nâng cao", open=False):
                cookies_cb = gr.Checkbox(value=False, label="Dùng cookie từ Chrome (bật khi bị lỗi 429; "
                                                            "cần đã đăng nhập YouTube trên Chrome, nếu báo lỗi cookie thì tắt hẳn Chrome rồi bấm lại)")
            script = gr.Textbox(label="Kịch bản — sửa / dịch / viết lại thành của bạn tại đây",
                                lines=8, max_lines=16, value=S.get("script", ""))
            btn1.click(step1_fetch, inputs=[url, src_lang, cookies_cb],
                       outputs=[status1, title_box, script])

        with gr.Tab("2 · Tạo voice"):
            mode_dd = gr.Dropdown(
                choices=[("Giọng có sẵn - miễn phí (Edge TTS)", "edge"),
                         ("Clone F5-TTS TIẾNG VIỆT - offline, miễn phí (giấy phép phi thương mại)", "f5vi"),
                         ("Clone XTTS - offline (Anh/Nhật/Hàn/Đức... không có tiếng Việt)", "xtts"),
                         ("Clone ElevenLabs - trả phí (có tiếng Việt, chuẩn nhất)", "eleven")],
                value=S.get("mode", "edge"), label="Chế độ")
            with gr.Group(visible=S.get("mode", "edge") == "edge") as grp_edge:
                with gr.Row():
                    voice_dd = gr.Dropdown(choices=VOICE_CHOICES, value=S.get("voice", "vi-VN-NamMinhNeural"),
                                           label="Chọn giọng (đúng ngôn ngữ của kịch bản mới đọc chuẩn)", scale=2)
                    speed = gr.Slider(-30, 30, value=S.get("speed", 0), step=1, label="Tốc độ (%)", scale=1)
            with gr.Group(visible=S.get("mode") == "f5vi") as grp_f5:
                with gr.Row():
                    f5_sample = gr.File(label="File giọng mẫu tiếng Việt 5-15 giây (1 người nói, ít tạp âm)",
                                        file_types=["audio", ".mp3", ".wav", ".m4a"])
                    f5_ref_text = gr.Textbox(
                        label="Lời thoại của đoạn mẫu (gõ đúng từng chữ đoạn mẫu đã nói — để trống thì tool tự nghe bằng Whisper)",
                        lines=2)
                gr.Markdown("_F5-TTS chạy trên máy bạn, miễn phí. Lần đầu bấm Tạo voice, tool tự tải model "
                            "tiếng Việt ~1,35 GB (cần đã cài thêm: `pip install f5-tts`). Giấy phép model là "
                            "phi thương mại — chỉ clone giọng của bạn hoặc người đã đồng ý._")
            with gr.Group(visible=S.get("mode") == "xtts") as grp_xtts:
                with gr.Row():
                    sample_up = gr.File(label="File giọng mẫu 6-30 giây (1 người nói, ít tạp âm)",
                                        file_types=["audio", ".mp3", ".wav", ".m4a"])
                    clone_lang = gr.Dropdown(choices=[(v, k) for k, v in XTTS_LANGS.items()],
                                             value=S.get("clone_lang", "ko"),
                                             label="Ngôn ngữ đọc bằng giọng clone")
            with gr.Group(visible=S.get("mode") == "eleven") as grp_eleven:
                with gr.Row():
                    el_key = gr.Textbox(label="ElevenLabs API key", type="password")
                    el_voice = gr.Textbox(label="Voice ID (giọng đã clone trên elevenlabs.io)")
            mode_dd.change(
                lambda m: (gr.update(visible=m == "edge"), gr.update(visible=m == "f5vi"),
                           gr.update(visible=m == "xtts"), gr.update(visible=m == "eleven")),
                inputs=mode_dd, outputs=[grp_edge, grp_f5, grp_xtts, grp_eleven])
            btn3 = gr.Button("🎙️ Tạo voice từ kịch bản", variant="primary")
            status3 = gr.Textbox(label="Trạng thái", lines=2)
            audio_out = gr.Audio(label="Voice (nghe thử / dùng cho thẻ 3 — hoặc tải file giọng của bạn vào đây)",
                                 type="filepath", value=_saved_audio())
            btn3.click(step3_voice, inputs=[script, mode_dd, voice_dd, speed, sample_up, clone_lang, el_key, el_voice,
                                            f5_sample, f5_ref_text],
                       outputs=[status3, audio_out])

        with gr.Tab("3 · SRT siêu tốc"):
            with gr.Row():
                model_dd = gr.Dropdown(choices=[("base - Nhanh (mặc định)", "base"),
                                                ("turbo - Nhanh + chính xác (nên dùng khi có card đồ họa)", "turbo"),
                                                ("small - Chính xác hơn, chậm hơn", "small"),
                                                ("tiny - Siêu nhanh, kém chính xác", "tiny"),
                                                ("medium - Chậm", "medium"), ("large-v3 - Chậm nhất", "large-v3")],
                                       value=S.get("model", "base"), label="Model nghe")
                maxc = gr.Slider(28, 84, value=S.get("maxc", 42), step=1, label="Số chữ tối đa / dòng phụ đề")
            btn4 = gr.Button("📝 Tạo SRT ngay", variant="primary")
            status4 = gr.Textbox(label="Trạng thái", lines=2)
            srt_out = gr.File(label="Tải file .SRT")
            srt_preview = gr.Textbox(label="Xem trước nội dung SRT", lines=6, max_lines=12)
            btn4.click(step4_srt, inputs=[audio_out, model_dd, maxc],
                       outputs=[status4, srt_out, srt_preview])
            gr.Markdown("_Chế độ siêu tốc: nghe theo lô trên card đồ họa + giải mã nhanh. "
                        "Voice lấy từ thẻ 2 (giọng vừa tạo hoặc file bạn tải lên ô voice ở thẻ 2)._")

    # ---------- Tu luu tien trinh + Du an ----------
    STATE_INPUTS = [url, src_lang, title_box, script, mode_dd, voice_dd, speed,
                    clone_lang, model_dd, maxc, audio_out]
    STATE_KEYS = ["url", "src_lang", "title", "script", "mode", "voice", "speed",
                  "clone_lang", "model", "maxc", "audio"]

    def _collect(*vals):
        save_session(dict(zip(STATE_KEYS, vals)))

    for _c in STATE_INPUTS:
        _c.change(_collect, inputs=STATE_INPUTS)

    def _state_from(vals):
        return dict(zip(STATE_KEYS, vals))

    def ui_save_project(name, *vals):
        try:
            used = save_project(name, _state_from(vals), OUT_DIR)
            return (gr.update(choices=list_projects(), value=used),
                    f"Đã lưu dự án '{used}' (gồm kịch bản + file voice/SRT/CSV nếu đã có).")
        except Exception as e:
            return gr.update(), f"Lưu dự án bị lỗi: {e}"

    def ui_new_project(*vals):
        try:
            msg = "Đã bắt đầu dự án mới tinh."
            state = _state_from(vals)
            if has_content(state):
                used = save_project("", {**state, "_auto": True}, OUT_DIR)
                msg = (f"Đã tự lưu dự án trước vào mục '{used}' (mở lại bằng nút Mở dự án) "
                       "và bắt đầu dự án mới tinh.")
            clear_session()
            return ("", "", "", "", "", "", None, None, "",
                    "", gr.update(choices=list_projects(), value=None), msg)
        except Exception as e:
            return ("", "", "", "", "", "", None, None, "",
                    "", gr.update(), f"Tạo dự án mới bị lỗi: {e}")

    def ui_load_project(name):
        if not name:
            return (gr.update(),) * 11 + ("Chưa chọn dự án nào để mở.",)
        try:
            st = load_project(name)
            return (st.get("url", ""), st.get("src_lang", "ko"), st.get("title", ""),
                    st.get("script", ""), st.get("mode", "edge"),
                    st.get("voice", "vi-VN-NamMinhNeural"), st.get("speed", 0),
                    st.get("clone_lang", "ko"), st.get("model", "base"),
                    st.get("maxc", 42),
                    st.get("audio"), f"Đã mở dự án '{name}'.")
        except Exception as e:
            return (gr.update(),) * 11 + (f"Mở dự án bị lỗi: {e}",)

    btn_save_proj.click(ui_save_project, inputs=[proj_name] + STATE_INPUTS,
                        outputs=[proj_dd, proj_status])
    btn_new_proj.click(ui_new_project, inputs=STATE_INPUTS,
                       outputs=[url, title_box, script, status1, status3, status4,
                                audio_out, srt_out, srt_preview,
                                proj_name, proj_dd, proj_status])
    btn_load_proj.click(ui_load_project, inputs=[proj_dd],
                        outputs=STATE_INPUTS + [proj_status])

if __name__ == "__main__":
    demo.launch(inbrowser=True)
