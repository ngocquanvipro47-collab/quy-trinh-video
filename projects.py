"""
QUAN LY DU AN + TU LUU TIEN TRINH (session) cho Tool Quy Trinh Video.
- Data/session.json: trang thai dang lam (link, kich ban, cac lua chon, file voice)
  duoc tu luu moi khi thay doi -> tat tool / cap nhat xong mo lai van con nguyen.
- Data/projects/<ten du an>/: ban luu co ten cua mot du an, gom session.json
  + ban sao cac file ket qua (voice, SRT, bang CSV) neu da co.
"""
import json
import os
import re
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
SESSION_PATH = os.path.join(DATA_DIR, "session.json")
RESULT_FILES = ["voice.mp3", "voice_clone.wav", "voice_elevenlabs.mp3",
                "phu_de.srt", "bang_phan_canh.csv"]
VOICE_FILES = RESULT_FILES[:3]


def _atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_session():
    try:
        with open(SESSION_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_session(state):
    try:
        _atomic_write_json(SESSION_PATH, state or {})
    except Exception:
        pass


def clear_session():
    save_session({})


def sanitize_name(name):
    name = re.sub(r"[^\w\- ]+", "", str(name or ""), flags=re.UNICODE).strip()
    name = re.sub(r"\s+", " ", name)
    return name[:60]


def list_projects():
    try:
        names = []
        for d in os.listdir(PROJECTS_DIR):
            if os.path.isfile(os.path.join(PROJECTS_DIR, d, "session.json")):
                names.append(d)
        return sorted(names)
    except Exception:
        return []


def has_content(state):
    return bool((state.get("script") or "").strip() or state.get("audio"))


def save_project(name, state, out_dir):
    """Luu du an: session + ban sao file ket qua. Tra ve ten thu muc da dung."""
    name = sanitize_name(name) or datetime.now().strftime("Du an %Y-%m-%d %H%M")
    folder = os.path.join(PROJECTS_DIR, name)
    os.makedirs(folder, exist_ok=True)
    state = dict(state or {})
    # Sao chep file ket qua (voice / SRT / CSV) vao thu muc du an
    for fn in RESULT_FILES:
        src = os.path.join(out_dir, fn)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, os.path.join(folder, fn))
            except Exception:
                pass
    # Neu file voice dang dung nam ngoai thu muc ket qua, sao chep them
    audio = state.get("audio")
    if audio and os.path.isfile(audio):
        base = os.path.basename(audio)
        if base not in RESULT_FILES:
            try:
                shutil.copy2(audio, os.path.join(folder, base))
            except Exception:
                pass
        if os.path.isfile(os.path.join(folder, base)):
            state["audio"] = base  # luu ten file tuong doi trong thu muc du an
    _atomic_write_json(os.path.join(folder, "session.json"), state)
    return name


def load_project(name):
    """Doc du an: tra ve state, voi audio da tro vao ban sao trong thu muc du an."""
    folder = os.path.join(PROJECTS_DIR, name)
    with open(os.path.join(folder, "session.json"), encoding="utf-8") as f:
        state = json.load(f)
    audio = state.get("audio")
    if audio:
        cand = audio if os.path.isabs(audio) else os.path.join(folder, audio)
        if os.path.isfile(cand):
            state["audio"] = cand
        else:
            for fn in VOICE_FILES:
                p = os.path.join(folder, fn)
                if os.path.isfile(p):
                    state["audio"] = p
                    break
            else:
                state["audio"] = None
    return state
