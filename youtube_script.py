"""
Lay kich ban (loi thoai) tu link YouTube bang phu de cua video.

Cach lam (v1.1 - sua loi 429 Too Many Requests):
- Buoc A: chi XEM danh sach phu de video dang co (khong tai gi ca).
- Buoc B: chon dung 1 ban phu de tot nhat roi chi tai 1 ban do.
  Ban cu tai tat ca cac ban phu de (ke ca cac ban dich tu dong kieu 'vi-ko')
  nen bi YouTube chan 429.
- Neu van bi 429: cho vai giay roi tu thu lai (toi da 3 lan).
- Co tuy chon dung cookie tu trinh duyet Chrome (dang nhap YouTube san)
  de YouTube bot chan hon.
"""
import glob
import os
import re
import tempfile
import time

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def clean_error(e) -> str:
    """Lam sach ma mau ANSI va tien to ERROR: kho doc trong thong bao loi."""
    msg = ANSI_RE.sub("", str(e))
    msg = re.sub(r"ERROR:\s*", "", msg)
    if "429" in msg or "Too Many Requests" in msg:
        msg += ("\n\nYouTube dang tam chan vi gui qua nhieu yeu cau (loi 429). "
                "Hay cho 2-5 phut roi bam lai, va bat tuy chon 'Dung cookie tu Chrome' o Buoc 1.")
    return msg.strip()


def clean_vtt(vtt_text: str) -> str:
    """Chuyen noi dung file .vtt thanh van ban loi thoai sach:
    bo dong thoi gian, bo the <...>, gop cac dong cuon bi lap cua phu de tu dong."""
    out = []
    for raw in vtt_text.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line:
            out.append(line)
    # Phu de tu dong cua YouTube "cuon" theo tu: dong sau chua duoi cua dong truoc
    # cong them tu moi -> ghep bang cach tim doan chong lap dai nhat theo TU.
    words = []
    for line in out:
        lw = line.split()
        overlap = 0
        for k in range(min(len(words), len(lw)), 0, -1):
            if words[-k:] == lw[:k]:
                overlap = k
                break
        words.extend(lw[overlap:])
    return re.sub(r"\s+", " ", " ".join(words)).strip()


def lang_order(prefer_lang: str):
    base = ["vi", "en", "ko", "ja", "de", "th"]
    if prefer_lang in (None, "", "auto"):
        return base
    return [prefer_lang] + [x for x in base if x != prefer_lang]


def choose_track(info: dict, prefer_lang: str = "ko"):
    """
    Chon 1 ban phu de tot nhat tu info cua yt-dlp.
    Uu tien: phu de CHINH THUC theo thu tu ngon ngu -> phu de TU DONG theo thu tu ngon ngu.
    Bo qua cac ban dich tu dong (ten co dang 'vi-ko', 'ko-vi'...).
    Tra ve (ten ban, la_tu_dong) hoac (None, None).
    """
    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}

    def is_translation(key):
        return bool(re.fullmatch(r"[a-z]{2,3}-[a-z]{2,3}", key or "")) and "-" in key \
            and not re.fullmatch(r"[a-z]{2,3}-[A-Z]{2}", key or "")

    def pick(tracks):
        keys = [k for k in tracks.keys() if not is_translation(k)]
        for lang in lang_order(prefer_lang):
            for k in keys:
                if k == lang or k.startswith(lang + "-"):
                    return k
        return None

    k = pick(subs)
    if k:
        return k, False
    k = pick(autos)
    if k:
        return k, True
    return None, None


def fetch_youtube_script(url: str, prefer_lang: str = "ko", use_cookies: bool = False):
    """
    Tra ve (tieu de video, ngon ngu phu de da dung, noi dung kich ban).
    """
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    common = {"quiet": True, "no_warnings": True, "no_color": True,
              "skip_download": True, "retries": 3, "sleep_interval": 2,
              "extractor_args": {"youtube": {"player_client": ["android", "web"]}}}
    if use_cookies:
        common["cookiesfrombrowser"] = ("chrome",)

    # --- Buoc A: xem danh sach phu de (nhe, it bi chan) ---
    last_err = None
    info = None
    for attempt in range(3):
        try:
            with YoutubeDL(common) as ydl:
                info = ydl.extract_info(url, download=False)
            break
        except DownloadError as e:
            last_err = e
            if "429" in str(e) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(clean_error(e))
    if not info:
        raise RuntimeError(clean_error(last_err) if last_err else "Khong doc duoc thong tin video.")
    title = info.get("title", "")

    track, is_auto = choose_track(info, prefer_lang)
    if not track:
        raise RuntimeError(
            "Video nay khong co phu de (ke ca phu de tu dong) nen khong lay duoc kich ban. "
            "Hay thu video khac, hoac dan thang loi thoai vao o Buoc 2.")

    # --- Buoc B: chi tai dung 1 ban phu de da chon ---
    tmp = tempfile.mkdtemp(prefix="ytscript_")
    opts = dict(common)
    opts.update({
        "writesubtitles": not is_auto,
        "writeautomaticsub": is_auto,
        "subtitleslangs": [track],
        "subtitlesformat": "vtt",
        "outtmpl": os.path.join(tmp, "sub"),
    })
    for attempt in range(3):
        try:
            with YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
            break
        except DownloadError as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(clean_error(e))

    files = sorted(glob.glob(os.path.join(tmp, "sub*.vtt")))
    if not files:
        raise RuntimeError("Da chon duoc phu de nhung tai ve that bai. Hay bam thu lai sau vai phut.")
    with open(files[0], encoding="utf-8") as f:
        text = clean_vtt(f.read())
    if not text:
        raise RuntimeError("Tai duoc phu de nhung khong doc duoc loi thoai. Hay thu video khac.")
    return title, track + (" (phụ đề tự động)" if is_auto else " (phụ đề chính thức)"), text
