"""
CLONE GIONG (nhan ban giong noi tu 1 doan ghi am mau)

Hai duong:
1) XTTS v2 - chay OFFLINE tren may cua ban, MIEN PHI, clone tu mau 6-30 giay.
   Ngon ngu doc duoc: Anh, Nhat, Han, Duc, Phap, Tay Ban Nha, Bo Dao Nha, Nga,
   Y, Trung, Ba Lan, Tho, Ha Lan... NHUNG KHONG co tieng Viet (gioi han cua model).
   Can cai them: pip install coqui-tts  (xem requirements_clone.txt)
2) ElevenLabs - dich vu online TRA PHI, clone duoc ca TIENG VIET va doc 32 ngon ngu
   bang chinh giong da clone. Ban tao giong clone tren web ElevenLabs (tai mau len),
   roi dan API key + Voice ID vao tool. API key chi luu tren may cua ban.
   Luu y: chi clone giong cua chinh ban hoac giong da duoc chu giong dong y.
"""
import json
import os
import re
import urllib.error
import urllib.request

XTTS_LANGS = {
    "en": "English - Tiếng Anh", "ja": "日本語 - Tiếng Nhật", "ko": "한국어 - Tiếng Hàn",
    "de": "Deutsch - Tiếng Đức", "fr": "Français - Tiếng Pháp", "es": "Español - Tây Ban Nha",
    "pt": "Português - Bồ Đào Nha", "ru": "Русский - Tiếng Nga", "it": "Italiano - Ý",
    "zh-cn": "中文 - Tiếng Trung", "pl": "Polski - Ba Lan", "tr": "Türkçe - Thổ Nhĩ Kỳ",
    "nl": "Nederlands - Hà Lan",
}

_xtts_model = None


def xtts_clone(text: str, sample_path: str, language: str = "en", out_path: str = None) -> str:
    """Clone giong bang XTTS v2 chay tren may. language: ma trong XTTS_LANGS (khong co 'vi')."""
    global _xtts_model
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Kich ban dang trong, chua co gi de doc.")
    if not sample_path or not os.path.exists(sample_path):
        raise RuntimeError("Chua co file giong mau. Hay tai len 1 doan ghi am 6-30 giay, "
                           "chi co 1 nguoi noi, cang it tap am cang giong.")
    if language not in XTTS_LANGS:
        raise RuntimeError("XTTS khong ho tro ngon ngu nay (va khong co tieng Viet). "
                           "Tieng Viet hay dung ElevenLabs o che do ben canh.")
    try:
        from TTS.api import TTS as CoquiTTS
    except ImportError:
        raise RuntimeError(
            "Chua cai thu vien clone giong XTTS. Hay chay lenh: pip install coqui-tts\n"
            "(goi nay nang khoang 2-3 GB vi kem PyTorch; nen dung Python 3.10 hoac 3.11 cho phan clone. "
            "Cac buoc khac cua tool khong bi anh huong.)")
    if out_path is None:
        out_path = os.path.join(os.getcwd(), "voice_clone.wav")
    if _xtts_model is None:
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
        except Exception:
            pass
        _xtts_model = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    _xtts_model.tts_to_file(text=text, speaker_wav=sample_path,
                            language=language, file_path=out_path)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Clone giong that bai. Hay thu doan giong mau sach hon (it tap am).")
    return out_path


# ================= F5-TTS TIENG VIET (ViVoice) =================
# Model F5-TTS fine-tune 1000 gio tieng Viet cua hynt tren HuggingFace:
#   https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice
# Clone giong tu mau ngan (kem loi thoai cua mau), chay offline, mien phi.
# GIAY PHEP CUA MODEL: CC-BY-NC-SA-4.0 -> CHI DUNG PHI THUONG MAI.
F5_BASE_URL = "https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice/resolve/main/"
F5_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data", "models", "f5_vivoice")
F5_CKPT_SIZE = 1348597231  # model_last.pt tren HuggingFace

_f5_model = None


def _f5_download(filename, dest, say):
    url = F5_BASE_URL + filename
    req = urllib.request.Request(url, headers={"User-Agent": "QuyTrinhVideo-F5"})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        last_pct = -1
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct >= last_pct + 10:
                    last_pct = pct
                    say(f"Đang tải model F5-TTS: {pct}% ({done // 1048576}/{total // 1048576} MB)...")
    os.replace(tmp, dest)


def _f5_ensure_files(say):
    """Tai model_last.pt (~1,35 GB) + vocab (config.json) ve Data/models/f5_vivoice neu chua co."""
    os.makedirs(F5_DIR, exist_ok=True)
    ckpt = os.path.join(F5_DIR, "model_last.pt")
    vocab = os.path.join(F5_DIR, "vocab.txt")
    if not os.path.isfile(ckpt) or os.path.getsize(ckpt) != F5_CKPT_SIZE:
        say("Lần đầu dùng F5-TTS: đang tải model tiếng Việt (~1,35 GB), chờ chút nhé...")
        _f5_download("model_last.pt", ckpt, say)
    if not os.path.isfile(vocab):
        _f5_download("config.json", vocab, say)  # config.json cua repo chinh la file vocab
    return ckpt, vocab


def _split_chunks(text, max_len=160):
    """Chia kich ban dai thanh tung doan ngan (F5 doc tot nhat o doan < ~30 giay)."""
    parts = re.split(r"(?<=[.!?…])\s+|\n+", text)
    chunks, cur = [], ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > max_len:  # cau qua dai: cat o dau phay gan nhat
            cut = p.rfind(",", 0, max_len)
            if cut < 40:
                cut = max_len
            chunks.append(p[:cut + 1].strip() if cut < len(p) else p)
            p = p[cut + 1:].strip() if cut < len(p) else ""
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= max_len:
            cur = cur + " " + p
        else:
            chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c]


def _auto_ref_text(sample_path, say):
    """Tu nghe loi thoai cua doan giong mau bang Whisper (khi nguoi dung de trong o loi mau)."""
    from engine import _run_transcribe
    try:
        words = _run_transcribe("small", "cuda", "float16", sample_path, "vi", say)
    except Exception:
        words = _run_transcribe("small", "cpu", "int8", sample_path, "vi", say)
    text = re.sub(r"\s+", " ", "".join(w["word"] for w in words)).strip()
    if not text:
        raise RuntimeError("Không nghe rõ lời trong đoạn giọng mẫu. Hãy gõ tay lời thoại của đoạn mẫu vào ô 'Lời thoại của đoạn mẫu'.")
    say(f"Đã tự nhận diện lời của giọng mẫu: “{text}”")
    return text


def _write_wav(path, wave, sr):
    try:
        import soundfile as sf
        sf.write(path, wave, sr)
    except ImportError:
        import struct
        import wave as wave_mod
        import numpy as np
        pcm = (np.clip(wave, -1.0, 1.0) * 32767).astype("<i2")
        with wave_mod.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm.tobytes())


def _import_f5():
    try:
        from f5_tts.api import F5TTS
        return F5TTS
    except ImportError:
        return None


def ensure_f5(say=print):
    """Chua co thu vien f5-tts thi TU CAI bang chinh Python dang chay tool
    (dung moi truong .venv cua tool), khoi can nguoi dung go lenh."""
    F5TTS = _import_f5()
    if F5TTS is not None:
        return F5TTS
    say("Chưa có thư viện F5-TTS — tool đang TỰ CÀI giúp bạn (khoảng 2-3 GB, "
        "mất vài phút, cần có mạng). Cứ để yên, đừng tắt cửa sổ tool...")
    import subprocess
    import sys
    proc = subprocess.run([sys.executable, "-m", "pip", "install", "f5-tts"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-400:]
        raise RuntimeError(
            "Tự cài F5-TTS thất bại. Hãy chụp màn hình lỗi này gửi Muse xem giúp.\n"
            f"Chi tiết cuối log cài đặt: {tail}")
    F5TTS = _import_f5()
    if F5TTS is None:
        raise RuntimeError("Đã cài xong F5-TTS nhưng cần khởi động lại tool. "
                           "Hãy tắt tool, mở lại run.bat rồi bấm Tạo voice lần nữa.")
    say("Đã cài xong thư viện F5-TTS!")
    return F5TTS


def _make_f5(F5TTS, ckpt, vocab, device):
    """Tao F5TTS tu thich ung theo phien ban thu vien f5-tts tren may:
    ban moi (1.1+) khong con nhan 'vocoder_name' va ten model la F5TTS_v1_Base;
    ban cu nhan vocoder_name='vocos' va ten F5TTS_Base. Chi truyen tham so ma
    dung phien ban do ho tro (xem chu ky ham) - tranh loi 'unexpected keyword argument'."""
    import inspect
    try:
        params = inspect.signature(F5TTS.__init__).parameters
    except (TypeError, ValueError):
        params = {}
    kwargs = {"ckpt_file": ckpt, "vocab_file": vocab, "device": device}
    if "vocoder_name" in params:
        kwargs["vocoder_name"] = "vocos"
        kwargs["model"] = "F5TTS_Base"
    elif "model" in params:
        kwargs["model"] = "F5TTS_v1_Base"
    try:
        return F5TTS(**kwargs)
    except TypeError:
        # Phong xa: thu lai voi bo tham so toi thieu nhat
        return F5TTS(ckpt_file=ckpt, vocab_file=vocab, device=device)


def f5_clone(text: str, sample_path: str, ref_text: str = "", out_path: str = None,
             speed: float = 1.0, say=print, return_ref: bool = False):
    """Clone giong TIENG VIET bang F5-TTS ViVoice, chay offline tren may.
    sample_path: doan giong mau 5-15 giay, 1 nguoi noi, it tap am.
    ref_text: loi thoai dung nguyen van cua doan mau (de trong = tool tu nghe bang Whisper).
    LUU Y GIAY PHEP MODEL: CC-BY-NC-SA-4.0 - chi dung phi thuong mai."""
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Kich ban dang trong, chua co gi de doc.")
    if not sample_path or not os.path.exists(sample_path):
        raise RuntimeError("Chua co file giong mau. Hay tai len 1 doan ghi am 5-15 giay, "
                           "chi co 1 nguoi noi, cang it tap am cang giong.")
    F5TTS = ensure_f5(say)
    global _f5_model
    ckpt, vocab = _f5_ensure_files(say)
    ref_text = (ref_text or "").strip()
    if not ref_text:
        say("Chưa có lời thoại của giọng mẫu — tool tự nghe bằng Whisper...")
        ref_text = _auto_ref_text(sample_path, say)
    if out_path is None:
        out_path = os.path.join(os.getcwd(), "voice_f5.wav")
    if _f5_model is None:
        device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
        except Exception:
            pass
        say(f"Đang nạp model F5-TTS (chạy bằng {'card đồ họa GPU' if device == 'cuda' else 'CPU'})...")
        _f5_model = _make_f5(F5TTS, ckpt, vocab, device)
    import numpy as np
    chunks = _split_chunks(text.lower())
    ref_lower = ref_text.lower()
    waves, sr_out = [], 24000
    for i, chunk in enumerate(chunks, 1):
        say(f"Đang đọc đoạn {i}/{len(chunks)}...")
        try:
            wave, sr, _spec = _f5_model.infer(ref_file=sample_path, ref_text=ref_lower,
                                              gen_text=chunk, speed=float(speed))
        except TypeError:
            wave, sr, _spec = _f5_model.infer(ref_file=sample_path, ref_text=ref_lower,
                                              gen_text=chunk)
        sr_out = sr
        waves.append(np.asarray(wave, dtype="float32"))
        waves.append(np.zeros(int(sr * 0.12), dtype="float32"))  # nghi ngan giua cac doan
    full = np.concatenate(waves) if len(waves) > 1 else waves[0]
    _write_wav(out_path, full, sr_out)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Clone giong that bai. Hay thu doan giong mau sach hon (it tap am).")
    say("Đã clone xong voice tiếng Việt bằng F5-TTS!")
    if return_ref:
        return out_path, ref_text
    return out_path


def elevenlabs_tts(text: str, api_key: str, voice_id: str, out_path: str = None,
                   model_id: str = "eleven_multilingual_v2") -> str:
    """Doc bang giong da clone tren ElevenLabs (doc duoc ca tieng Viet).
    model eleven_multilingual_v2: doc 29+ ngon ngu bang cung 1 giong clone."""
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Kich ban dang trong, chua co gi de doc.")
    if not api_key or not voice_id:
        raise RuntimeError("Can dan API key va Voice ID cua ElevenLabs. "
                           "Lay o elevenlabs.io: Profile -> API Key; Voice ID o muc Voices cua ban.")
    if out_path is None:
        out_path = os.path.join(os.getcwd(), "voice_elevenlabs.mp3")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    body = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"ElevenLabs bao loi {e.code}: {detail}")
    with open(out_path, "wb") as f:
        f.write(data)
    if os.path.getsize(out_path) == 0:
        raise RuntimeError("ElevenLabs tra ve file rong. Kiem tra lai Voice ID va so du tai khoan.")
    return out_path
