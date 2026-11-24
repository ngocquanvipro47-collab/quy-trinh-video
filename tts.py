"""
Tao voice tu kich ban bang Edge TTS (giong doc mien phi cua Microsoft,
cung cong nghe VeTay dang dung). Can co mang Internet khi chay.

NGUYEN TAC DOC CHUAN: giong phai DUNG NGON NGU cua kich ban.
Kich ban tieng Han thi chon giong Han, tieng Nhat chon giong Nhat...
Chon sai ngon ngu la doc sai ngay, du giong hay den may.
"""
import asyncio
import os

# Moi ngon ngu co nhieu giong nam/nu de chon (Edge TTS - mien phi)
VOICE_CATALOG = {
    "Tiếng Việt": [
        ("vi-VN-NamMinhNeural", "Nam miền Bắc - NamMinh (trầm, rõ, hợp kênh sức khỏe)"),
        ("vi-VN-HoaiMyNeural", "Nữ miền Bắc - HoaiMy (ấm, thân thiện)"),
    ],
    "English": [
        ("en-US-GuyNeural", "Nam Mỹ - Guy (rõ, tự nhiên)"),
        ("en-US-ChristopherNeural", "Nam Mỹ - Christopher (trầm, kể chuyện)"),
        ("en-US-EricNeural", "Nam Mỹ - Eric (điềm đạm)"),
        ("en-US-JennyNeural", "Nữ Mỹ - Jenny (thân thiện)"),
        ("en-US-AriaNeural", "Nữ Mỹ - Aria (sáng, rõ)"),
        ("en-GB-RyanNeural", "Nam Anh - Ryan"),
        ("en-GB-SoniaNeural", "Nữ Anh - Sonia"),
    ],
    "日本語 (Nhật)": [
        ("ja-JP-KeitaNeural", "Nam Nhật - Keita"),
        ("ja-JP-NanamiNeural", "Nữ Nhật - Nanami"),
    ],
    "한국어 (Hàn)": [
        ("ko-KR-InJoonNeural", "Nam Hàn - InJoon (trầm, hợp video sức khỏe Hàn)"),
        ("ko-KR-SunHiNeural", "Nữ Hàn - SunHi"),
        ("ko-KR-GookMinNeural", "Nam Hàn - GookMin"),
    ],
    "Deutsch (Đức)": [
        ("de-DE-ConradNeural", "Nam Đức - Conrad"),
        ("de-DE-KatjaNeural", "Nữ Đức - Katja"),
    ],
    "ไทย (Thái)": [
        ("th-TH-NiwatNeural", "Nam Thái - Niwat"),
        ("th-TH-PremwadeeNeural", "Nữ Thái - Premwadee"),
    ],
    "中文 (Trung)": [
        ("zh-CN-YunyangNeural", "Nam Trung - Yunyang (giọng dẫn chương trình)"),
        ("zh-CN-XiaoxiaoNeural", "Nữ Trung - Xiaoxiao"),
    ],
}

# Danh sach phang cho o chon trong giao dien: nhan hien thi -> ma giong
VOICE_CHOICES = [(f"[{lang}] {label}", vid)
                 for lang, items in VOICE_CATALOG.items() for vid, label in items]

# Ban do cu (tuong thich nguoc)
VOICES = {vid: label for items in VOICE_CATALOG.values() for vid, label in items}


async def _save(text, voice, rate, out_path):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(out_path)


def make_voice(text: str, voice: str = "vi-VN-NamMinhNeural",
               speed_percent: int = 0, out_path: str = None) -> str:
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Kich ban dang trong, chua co gi de doc.")
    if out_path is None:
        out_path = os.path.join(os.getcwd(), "voice.mp3")
    rate = f"{speed_percent:+d}%"
    asyncio.run(_save(text, voice, rate, out_path))
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Tao voice that bai. Kiem tra lai ket noi mang roi thu lai.")
    return out_path
