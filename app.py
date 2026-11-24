"""
Tool QUY TRINH VIDEO: Link YouTube -> Kich ban -> Voice -> SRT sieu toc
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

from projects import (clear_session, has_content, list_projects, list_voice_profiles,
                      load_project, load_session, load_voice_profile, save_project,
                      save_session, save_voice_profile)
from updater import LOCAL_VERSION, check_update, do_update
from clone_tts import XTTS_LANGS, elevenlabs_tts, f5_clone, vieneu_clone, xtts_clone
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
                f5_sample=None, f5_ref_text="", f5_name="", vn_sample=None, vn_name=""):
    try:
        if mode == "edge":
            out = os.path.join(OUT_DIR, "voice.mp3")
            make_voice(script, voice=voice, speed_percent=int(speed), out_path=out)
            return ("ĐÃ TẠO XONG VOICE (giọng có sẵn)! Nghe thử bên dưới, rồi sang thẻ 3.",
                    out, gr.update(), gr.update())
        if mode == "f5vi":
            out = os.path.join(OUT_DIR, "voice_f5.wav")
            out, used_ref = f5_clone(script, f5_sample, ref_text=f5_ref_text or "",
                                     out_path=out, return_ref=True)
            msg = ("ĐÃ CLONE XONG VOICE TIẾNG VIỆT BẰNG F5-TTS! Nghe thử bên dưới, rồi sang thẻ 3. "
                   "(Nhắc nhỏ: model F5-TTS có giấy phép phi thương mại.)")
            upd = gr.update()
            try:  # Tu dong luu giong vua clone vao kho giong de lan sau chon lai
                used_name = save_voice_profile(f5_name, f5_sample, used_ref)
                upd = gr.update(choices=list_voice_profiles(), value=used_name)
                msg += f" Đã LƯU giọng này vào kho giọng với tên '{used_name}' — lần sau chỉ cần chọn lại ở mục Giọng đã lưu."
            except Exception:
                pass
            return msg, out, upd, upd
        if mode == "vieneu":
            out = os.path.join(OUT_DIR, "voice_vieneu.wav")
            vieneu_clone(script, vn_sample, out_path=out)
            msg = ("ĐÃ CLONE XONG VOICE TIẾNG VIỆT BẰNG VieNeu v3 Turbo! Nghe thử bên dưới, "
                   "rồi sang thẻ 3. (VieNeu giấy phép Apache-2.0 — dùng cho kênh kiếm tiền được.)")
            upd = gr.update()
            try:  # Cung kho giong voi F5: clone bang engine nao cung luu lai duoc
                used_name = save_voice_profile(vn_name, vn_sample, "")
                upd = gr.update(choices=list_voice_profiles(), value=used_name)
                msg += f" Đã LƯU giọng này vào kho giọng với tên '{used_name}'."
            except Exception:
                pass
            return msg, out, upd, upd
        if mode == "xtts":
            out = os.path.join(OUT_DIR, "voice_clone.wav")
            xtts_clone(script, sample, language=clone_lang, out_path=out)
            return ("ĐÃ CLONE XONG VOICE BẰNG XTTS! Lần đầu chạy sẽ tải model khoảng 1,8 GB. "
                    "Nghe thử bên dưới, rồi sang thẻ 3."), out, gr.update(), gr.update()
        out = os.path.join(OUT_DIR, "voice_elevenlabs.mp3")
        elevenlabs_tts(script, (el_key or "").strip(), (el_voice_id or "").strip(), out_path=out)
        return ("ĐÃ TẠO XONG VOICE BẰNG GIỌNG CLONE ELEVENLABS! Nghe thử bên dưới, rồi sang thẻ 3.",
                out, gr.update(), gr.update())
    except Exception as e:
        return f"CÓ LỖI: {e}", None, gr.update(), gr.update()


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


_RESTARTER = r"""
import socket, subprocess, sys, time
app, cwd = sys.argv[1], sys.argv[2]
for _ in range(120):  # Cho toi da 60 giay cho cong 7860 duoc nha ra
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 7860))
        s.close()
        break
    except OSError:
        time.sleep(0.5)
subprocess.Popen([sys.executable, app], cwd=cwd)
"""


def _restart_later(delay=2.0):
    """Tu dong tat tool va mo lai ban moi sau khi cap nhat (nhu phan mem that).
    Ban cu thoat HAN roi ban moi moi mo, lai dung cong 7860 nhu cu:
    tranh loi 'mat ket noi' / nhay cong nhu truoc (ban moi mo khi cong con bi chiem)."""
    def _run():
        time.sleep(delay)
        try:
            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen([sys.executable, "-c", _RESTARTER,
                              os.path.abspath(__file__),
                              os.path.dirname(os.path.abspath(__file__))],
                             creationflags=flags, close_fds=True)
        except Exception:
            pass
        time.sleep(0.5)
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
/* Giao dien MAU 2 - CLEAN LIGHT (Kiu chon 2026-11-24): sang toi gian kieu Apple/Linear,
   nen xam rat nhat, the trang, diem nhan xanh duong #2563eb, tab gach chan. */
.gradio-container{max-width:1040px!important;margin:0 auto!important;font-size:14px;color:#0f172a}
body{background:#edf0f5!important}
#banner{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:15px 20px;
  box-shadow:0 2px 12px rgba(15,23,42,.05);margin-bottom:10px;display:flex;align-items:center;gap:14px}
#banner .ic{background:#2563eb;color:#fff;font-size:21px;width:46px;height:46px;min-width:46px;
  border-radius:12px;display:flex;align-items:center;justify-content:center;
  box-shadow:0 3px 8px rgba(37,99,235,.30)}
#banner .t{font-size:22px;font-weight:800;color:#0f172a;letter-spacing:.2px}
#banner .s{font-size:12.5px;color:#64748b;margin-top:2px}
#banner .v{display:inline-block;background:#dbeafe;color:#2563eb;border-radius:999px;
  padding:1px 10px;font-size:11.5px;font-weight:700;margin-left:8px;vertical-align:2px}
.tab-nav{border-bottom:1px solid #e2e8f0!important;gap:2px}
.tab-nav button{font-size:13.5px!important;font-weight:600;padding:9px 16px!important;
  color:#64748b!important;background:transparent!important;border:none!important;border-radius:0!important}
.tab-nav button.selected{color:#2563eb!important;box-shadow:inset 0 -3px 0 #2563eb}
button.primary{background:#2563eb!important;border:none!important;border-radius:11px!important;
  box-shadow:0 2px 8px rgba(37,99,235,.28);font-weight:700;color:#fff!important}
button.primary:hover{background:#1d4ed8!important}
button.secondary,button.sm{border-radius:10px!important;background:#ffffff!important;
  border:1px solid #dbe1ea!important;color:#334155!important}
.block{background:#ffffff!important;border:1px solid #e8ecf1!important;border-radius:14px!important;
  box-shadow:0 1px 2px rgba(15,23,42,.04)}
input,textarea{border-radius:10px!important;border-color:#dbe1ea!important}
.block label span{font-size:12px!important;color:#475569!important;font-weight:600}
footer{display:none!important}
"""

S = load_session()


def _saved_audio():
    p = S.get("audio")
    return p if p and os.path.isfile(p) else None


with gr.Blocks(title="Quy trình Video",
               theme=gr.themes.Soft(primary_hue=gr.themes.colors.blue,
                                    neutral_hue=gr.themes.colors.slate),
               css=APP_CSS) as demo:
    gr.HTML(f"""<div id="banner"><div class="ic">🎬</div><div><span class="t">Quy Trình Video</span><span class="v">v{LOCAL_VERSION}</span>
    <div class="s">YouTube → Kịch bản → Voice → SRT siêu tốc · Việc đang làm được TỰ LƯU, tắt mở lại không mất</div></div></div>""")
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
                         ("Clone VieNeu v3 Turbo TIẾNG VIỆT - NHANH, chạy CPU, miễn phí (Apache - dùng thương mại được)", "vieneu"),
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
                    f5_saved = gr.Dropdown(choices=list_voice_profiles(),
                                           label="Giọng đã clone đã lưu (chọn là dùng ngay, khỏi tải mẫu lại)", scale=2)
                    f5_name = gr.Textbox(label="Tên giọng (để lưu vào kho giọng)",
                                         placeholder="VD: Giọng Nhung bản tin", scale=2)
                    btn_save_voice = gr.Button("💾 Lưu giọng", size="sm", scale=1)
                with gr.Row():
                    f5_sample = gr.File(label="File giọng mẫu tiếng Việt 5-15 giây (1 người nói, ít tạp âm)",
                                        file_types=["audio", ".mp3", ".wav", ".m4a"])
                    f5_ref_text = gr.Textbox(
                        label="Lời thoại của đoạn mẫu (gõ đúng từng chữ đoạn mẫu đã nói — để trống thì tool tự nghe bằng Whisper)",
                        lines=2)
                gr.Markdown("_F5-TTS chạy trên máy bạn, miễn phí. Lần đầu bấm Tạo voice, tool sẽ TỰ CÀI "
                            "thư viện F5-TTS giúp bạn (~2-3 GB, cần mạng, chờ vài phút — xem tiến trình ở "
                            "cửa sổ đen của tool, đừng tắt) rồi tự tải model tiếng Việt ~1,35 GB. Giấy phép "
                            "model là phi thương mại — chỉ clone giọng của bạn hoặc người đã đồng ý._")
            with gr.Group(visible=S.get("mode") == "vieneu") as grp_vn:
                with gr.Row():
                    vn_saved = gr.Dropdown(choices=list_voice_profiles(),
                                           label="Giọng đã clone đã lưu (dùng chung kho giọng với F5)", scale=2)
                    vn_name = gr.Textbox(label="Tên giọng (để lưu vào kho giọng)",
                                         placeholder="VD: Giọng Nhung bản tin", scale=2)
                    btn_save_voice_vn = gr.Button("💾 Lưu giọng", size="sm", scale=1)
                vn_sample = gr.File(label="File giọng mẫu tiếng Việt 3-15 giây (1 người nói — VieNeu tự cắt còn 8 giây và tự khử nhiễu, KHÔNG cần gõ lời thoại mẫu)",
                                    file_types=["audio", ".mp3", ".wav", ".m4a"])
                gr.Markdown("_VieNeu v3 Turbo chạy ngay trên CPU bằng ONNX — nhanh hơn thời gian thực, "
                            "KHÔNG cần card đồ họa, cài nhẹ. Lần đầu bấm Tạo voice, tool TỰ CÀI thư viện "
                            "VieNeu và tự tải model. Âm thanh ra 48 kHz. Giấy phép Apache-2.0 — dùng cho "
                            "kênh bật kiếm tiền được. Chỉ clone giọng của bạn hoặc người đã đồng ý._")
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
                           gr.update(visible=m == "vieneu"), gr.update(visible=m == "xtts"),
                           gr.update(visible=m == "eleven")),
                inputs=mode_dd, outputs=[grp_edge, grp_f5, grp_vn, grp_xtts, grp_eleven])
            btn3 = gr.Button("🎙️ Tạo voice từ kịch bản", variant="primary")
            status3 = gr.Textbox(label="Trạng thái", lines=2)
            audio_out = gr.Audio(label="Voice (nghe thử / dùng cho thẻ 3 — hoặc tải file giọng của bạn vào đây)",
                                 type="filepath", value=_saved_audio())
            btn3.click(step3_voice, inputs=[script, mode_dd, voice_dd, speed, sample_up, clone_lang, el_key, el_voice,
                                            f5_sample, f5_ref_text, f5_name, vn_sample, vn_name],
                       outputs=[status3, audio_out, f5_saved, vn_saved])

            def ui_pick_voice(name):
                if not name:
                    return gr.update(), gr.update(), gr.update()
                try:
                    path, ref = load_voice_profile(name)
                    return path, ref, name
                except Exception:
                    return gr.update(), gr.update(), gr.update()

            def ui_save_voice(name, sample, ref):
                try:
                    used = save_voice_profile(name, sample, ref or "")
                    return (gr.update(choices=list_voice_profiles(), value=used),
                            f"Đã lưu giọng '{used}' vào kho giọng. Lần sau chỉ cần chọn lại ở mục Giọng đã lưu.")
                except Exception as e:
                    return gr.update(), f"Lưu giọng bị lỗi: {e}"

            f5_saved.change(ui_pick_voice, inputs=[f5_saved],
                            outputs=[f5_sample, f5_ref_text, f5_name])
            btn_save_voice.click(ui_save_voice, inputs=[f5_name, f5_sample, f5_ref_text],
                                 outputs=[f5_saved, status3])

            def ui_pick_voice_vn(name):
                if not name:
                    return gr.update(), gr.update()
                try:
                    path, _ref = load_voice_profile(name)
                    return path, name
                except Exception:
                    return gr.update(), gr.update()

            def ui_save_voice_vn(name, sample):
                try:
                    used = save_voice_profile(name, sample, "")
                    return (gr.update(choices=list_voice_profiles(), value=used),
                            f"Đã lưu giọng '{used}' vào kho giọng (dùng chung cho cả F5 và VieNeu).")
                except Exception as e:
                    return gr.update(), f"Lưu giọng bị lỗi: {e}"

            vn_saved.change(ui_pick_voice_vn, inputs=[vn_saved],
                            outputs=[vn_sample, vn_name])
            btn_save_voice_vn.click(ui_save_voice_vn, inputs=[vn_name, vn_sample],
                                    outputs=[vn_saved, status3])

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
                    f"Đã lưu dự án '{used}' (gồm kịch bản + file voice/SRT nếu đã có).")
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
