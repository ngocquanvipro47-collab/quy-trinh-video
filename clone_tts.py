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
