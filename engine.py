"""
Engine tao SRT tu voice - dung faster-whisper (chay offline tren may cua ban)
- Nhan dien giong noi tieng Viet (hoac tu dong nhan dien ngon ngu)
- Lay moc thoi gian tung TU, roi gom tu thanh dong phu de ngan, de doc
- Xuat file .srt chuan + file .txt loi thoai
"""
import os
import re

# ---------- Dinh dang thoi gian SRT: 00:00:01,500 ----------
def format_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------- Gom danh sach tu -> cac dong phu de (cue) ----------
def group_words(words, max_chars=42, max_duration=4.0, pause_break=0.6):
    """
    words: list dict {'word': str, 'start': float, 'end': float}
    Chia dong khi:
      - Het cau (. ? ! ...)
      - Cau da dai >= max_chars va gap dau phay / het y
      - Khoang ngung giua 2 tu > pause_break giay
      - Dong da keo dai > max_duration giay
    """
    cues = []
    cur = []

    def flush():
        if cur:
            text = "".join(w["word"] for w in cur).strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                cues.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": text})
            cur.clear()

    for i, w in enumerate(words):
        if cur:
            gap = w["start"] - cur[-1]["end"]
            dur = w["end"] - cur[0]["start"]
            cur_text_len = len("".join(x["word"] for x in cur))
            prev_text = cur[-1]["word"].strip()
            if gap > pause_break or dur > max_duration:
                flush()
            elif prev_text.endswith((".", "?", "!", "...")):
                flush()
            elif cur_text_len >= max_chars and prev_text.endswith((",", ";", ":")):
                flush()
            elif cur_text_len >= max_chars + 18:
                flush()
        cur.append(w)
    flush()
    # Dam bao end > start va khong chong lan
    for i, c in enumerate(cues):
        if c["end"] <= c["start"]:
            c["end"] = c["start"] + 0.5
        if i + 1 < len(cues) and c["end"] > cues[i + 1]["start"]:
            c["end"] = cues[i + 1]["start"]
    return cues


def cues_to_srt(cues) -> str:
    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(str(i))
        lines.append(f"{format_ts(c['start'])} --> {format_ts(c['end'])}")
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines)


# ---------- Windows: tim them DLL cua CUDA trong cac goi pip nvidia (neu co) ----------
def _add_cuda_dll_dirs():
    """May Windows thieu cublas64_12.dll trong PATH la loi rat hay gap.
    Neu nguoi dung co cai goi pip nvidia-cublas-cu12 / nvidia-cudnn-cu12 thi
    nap thu muc bin cua chung vao danh sach tim DLL."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import nvidia
        for base in list(nvidia.__path__):
            for sub in ("cublas", "cudnn", "cuda_runtime"):
                bin_dir = os.path.join(base, sub, "bin")
                if os.path.isdir(bin_dir):
                    try:
                        os.add_dll_directory(bin_dir)
                    except Exception:
                        pass
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


def _run_transcribe(model_size, device, compute_type, input_path, lang, say,
                    beam_size=5, batched=False):
    """Chay nghe 1 lan bang device chi dinh. PHAI tieu thu het generator
    segments o trong ham nay, vi loi GPU (thieu cublas...) chi xuat hien
    khi bat dau nghe that, khong xuat hien luc tai model.
    batched=True: nghe theo LO (BatchedInferencePipeline) - nhanh hon nhieu lan tren GPU.
    beam_size=1: giai ma tham lam (greedy) - nhanh hon dang ke, do chinh xac giam rat it."""
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    say(f"Da tai model '{model_size}' - chay bang "
        f"{'card do hoa (GPU)' if device == 'cuda' else 'CPU'}")
    say("Dang nghe va chep loi...")
    if batched:
        from faster_whisper import BatchedInferencePipeline
        pipe = BatchedInferencePipeline(model=model)
        segments, info = pipe.transcribe(
            input_path, language=lang, word_timestamps=True,
            vad_filter=True, batch_size=16,
        )
    else:
        segments, info = model.transcribe(
            input_path, language=lang, word_timestamps=True,
            vad_filter=True, beam_size=beam_size,
        )
    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": w.start, "end": w.end})
        else:
            words.append({"word": seg.text, "start": seg.start, "end": seg.end})
    say(f"Ngon ngu nhan dien: {info.language} (do tin cay {info.language_probability:.0%})")
    return words


# ---------- Ham chinh: file voice -> file SRT ----------
def transcribe_to_srt(input_path, output_srt=None, model_size="small",
                      language="vi", max_chars=42, progress=None, device="auto",
                      beam_size=5, batched=False):
    """
    model_size: tiny / base / small / turbo / medium / large-v3
    language: 'vi' = tieng Viet, 'auto'/None = tu dong nhan dien, hoac ma khac: en, ko, ja, de, th...
    device: 'auto' = thu GPU truoc, loi GPU thi TU DONG chuyen sang CPU (khong sap)
            'cpu' = chay CPU ngay tu dau, 'cuda' = bat buoc GPU
    beam_size=1 + batched=True = che do SIEU TOC (mac dinh cua the SRT trong tool).
    Tra ve: (duong dan file srt, duong dan file txt, so dong phu de)
    """
    def say(msg):
        print(msg)
        if progress:
            progress(msg)

    _add_cuda_dll_dirs()
    lang = language if language not in (None, "", "auto") else None

    if device == "cpu":
        words = _run_transcribe(model_size, "cpu", "int8", input_path, lang, say,
                                beam_size=beam_size, batched=False)
    elif device == "cuda":
        words = _run_transcribe(model_size, "cuda", "float16", input_path, lang, say,
                                beam_size=beam_size, batched=batched)
    else:  # auto: GPU theo lo -> GPU thuong -> CPU, loi o dau thi lui o do
        attempts = [("cuda", "float16", batched), ("cuda", "float16", False),
                    ("cpu", "int8", False)]
        seen, words, last_err = set(), None, None
        for dev, ct, bat in attempts:
            if (dev, bat) in seen:
                continue
            seen.add((dev, bat))
            try:
                words = _run_transcribe(model_size, dev, ct, input_path, lang, say,
                                        beam_size=beam_size, batched=bat)
                break
            except Exception as e:
                last_err = e
                say(f"Cach nghe {dev}{' theo lo' if bat else ''} khong dung duoc ({e}). Dang thu cach tiep theo...")
        if words is None:
            raise last_err

    if not words:
        raise RuntimeError("Khong nghe thay loi thoai nao trong file. Hay kiem tra lai file giong.")

    cues = group_words(words, max_chars=int(max_chars))
    srt_text = cues_to_srt(cues)

    if output_srt is None:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_srt = os.path.join(os.path.dirname(os.path.abspath(input_path)), base + ".srt")
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(srt_text)

    output_txt = os.path.splitext(output_srt)[0] + ".txt"
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(" ".join(c["text"] for c in cues))

    say(f"Xong! Da tao {len(cues)} dong phu de.")
    return output_srt, output_txt, len(cues)
