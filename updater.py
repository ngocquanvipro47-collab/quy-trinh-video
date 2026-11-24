"""
TU CAP NHAT QUA GITHUB - giong co che cua VeTay.
Tool doc file update.json tren kho GitHub cong khai:
    https://raw.githubusercontent.com/ngocquanvipro47-collab/quy-trinh-video/main/update.json
Neu ban tren GitHub moi hon ban dang chay -> tai cac file .py moi ve ghi de,
nguoi dung tat tool mo lai la dung ban moi. Khong can tai lai file zip.

Luu y: run.bat KHONG nam trong danh sach tu cap nhat, vi no dang la file
dang chay (Windows doc file .bat theo tung dong, ghi de giua chung de gay loi).
"""
import json
import os
import urllib.request

REPO = "ngocquanvipro47-collab/quy-trinh-video"
BRANCH = "main"
LOCAL_VERSION = "1.11.0"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
UPDATE_URL = RAW_BASE + "update.json"
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_version(v):
    parts = []
    for p in str(v).strip().split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "QuyTrinhVideo-Updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def check_update():
    """Tra ve dict cua ban moi neu co ban moi hon, None neu dang la moi nhat."""
    data = json.loads(_fetch(UPDATE_URL).decode("utf-8"))
    remote = str(data.get("version", "")).strip()
    if remote and _parse_version(remote) > _parse_version(LOCAL_VERSION):
        return data
    return None


def do_update(say=None):
    """Tai cac file trong update.json ve ghi de. Tra ve phien ban moi."""
    data = check_update()
    if not data:
        return None
    files = data.get("files", [])
    for name in files:
        if say:
            say(f"Dang tai {name} ...")
        content = _fetch(RAW_BASE + name)
        dest = os.path.join(APP_DIR, name)
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(content)
        os.replace(tmp, dest)
    # Cap nhat ca ban ghi update.json o may de lan mo sau khong bao lai
    with open(os.path.join(APP_DIR, "update.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(data.get("version", ""))
