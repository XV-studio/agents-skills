#!/usr/bin/env python3
"""video-to-skill extractor: turn one or more videos (or clips of them) into
frames + contact sheets + a timestamped transcript that an agent can read.

Standard library only. Needs ffmpeg/ffprobe on PATH. Transcription is optional
and uses faster-whisper (preferred) or the openai-whisper package if installed.

Usage:
  extract_video.py INPUT [INPUT ...] [--max-frames 40] [--width 960]
                   [--lang auto] [--model small] [--no-audio] [--workdir DIR]
  extract_video.py --check

INPUT is a file, a directory, a glob, or a clip: path@START-END
(START/END as seconds, MM:SS or HH:MM:SS; either side may be empty).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mpg", ".mpeg", ".3gp", ".wmv", ".flv", ".ts"}
THUMB = 32  # side of the grayscale thumbnail used for near-duplicate detection
SHEET_COLS, SHEET_ROWS, SHEET_CELL_W = 4, 3, 480


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, **kw)


def parse_time(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    parts = [float(p) for p in value.split(":")]
    if len(parts) > 3:
        raise ValueError(value)
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def fmt_time(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def expand_inputs(raw_inputs: list[str]) -> list[dict]:
    """Resolve files / directories / globs / path@START-END clips, keeping order."""
    clips: list[dict] = []
    for raw in raw_inputs:
        path_part, start, end = raw, None, None
        match = re.match(r"^(.*)@([0-9:.]*)-([0-9:.]*)$", raw)
        if match and not os.path.exists(raw):
            path_part = match.group(1)
            start, end = parse_time(match.group(2)), parse_time(match.group(3))
        path = Path(os.path.expanduser(path_part))
        if path.is_dir():
            files = sorted(p for p in path.rglob("*") if p.suffix.lower() in VIDEO_EXT)
        elif path.is_file():
            files = [path]
        else:
            files = sorted(Path(p) for p in glob.glob(str(path), recursive=True)
                           if Path(p).suffix.lower() in VIDEO_EXT)
        if not files:
            print(f"warning: no video found for input: {raw}", file=sys.stderr)
        for file in files:
            clips.append({"path": file.resolve(), "start": start, "end": end})
    return clips


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {out.stderr.decode(errors='replace')[:300]}")
    info = json.loads(out.stdout)
    video = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if video is None:
        raise RuntimeError(f"no video stream in {path}")
    return {
        "duration": float(info["format"].get("duration") or video.get("duration") or 0),
        "width": int(video.get("width", 0)),
        "height": int(video.get("height", 0)),
        "has_audio": audio is not None,
    }


def window_args(start: float, length: float) -> list[str]:
    return ["-ss", f"{start:.3f}", "-t", f"{length:.3f}"]


def extract_frames(path: Path, out_dir: Path, start: float, length: float,
                   max_frames: int, width: int) -> list[dict]:
    """Uniformly sample frames, then drop consecutive near-duplicates."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = min(2.0, max_frames / max(length, 0.5))
    base = ["ffmpeg", "-v", "error", "-y", *window_args(start, length), "-i", str(path)]
    raw_dir = out_dir / "_raw"
    raw_dir.mkdir(exist_ok=True)
    res = run([*base, "-vf", f"fps={fps:.5f},scale='min({width},iw)':-2", "-q:v", "3",
               str(raw_dir / "f_%04d.jpg")])
    if res.returncode != 0:
        raise RuntimeError(f"frame extraction failed: {res.stderr.decode(errors='replace')[:300]}")
    thumbs = run([*base, "-vf", f"fps={fps:.5f},scale={THUMB}:{THUMB},format=gray",
                  "-f", "rawvideo", "-"]).stdout
    files = sorted(raw_dir.glob("f_*.jpg"))
    size = THUMB * THUMB
    frames: list[dict] = []
    last: bytes | None = None
    for index, file in enumerate(files):
        thumb = thumbs[index * size:(index + 1) * size]
        if last is not None and len(thumb) == size:
            diff = sum(abs(a - b) for a, b in zip(thumb, last)) / size
            if diff < 1.2:  # visually identical to the last kept frame
                continue
        if len(thumb) == size:
            last = thumb
        timestamp = start + index / fps
        name = f"t_{len(frames) + 1:03d}.jpg"
        shutil.move(str(file), out_dir / name)
        frames.append({"file": name, "t": round(timestamp, 2), "time": fmt_time(timestamp)})
    shutil.rmtree(raw_dir, ignore_errors=True)
    return frames


def build_sheets(frames_dir: Path, frames: list[dict], sheets_dir: Path) -> list[dict]:
    """Contact sheets: a cheap overview so the agent can pick which frames to open."""
    sheets_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = SHEET_COLS * SHEET_ROWS
    sheets = []
    for number, offset in enumerate(range(0, len(frames), per_sheet), start=1):
        chunk = frames[offset:offset + per_sheet]
        listing = sheets_dir / f"_list_{number}.txt"
        listing.write_text("".join(f"file '{frames_dir / f['file']}'\nduration 1\n" for f in chunk))
        name = f"sheet_{number:02d}.jpg"
        res = run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                   "-vf", f"scale={SHEET_CELL_W}:-2,tile={SHEET_COLS}x{SHEET_ROWS}",
                   "-frames:v", "1", "-q:v", "4", str(sheets_dir / name)])
        listing.unlink(missing_ok=True)
        if res.returncode == 0:
            sheets.append({"file": name, "frames": [f["file"] for f in chunk],
                           "from": chunk[0]["time"], "to": chunk[-1]["time"]})
    return sheets


def mean_volume(path: Path, start: float, length: float) -> float | None:
    res = run(["ffmpeg", "-v", "info", *window_args(start, length), "-i", str(path),
               "-vn", "-af", "volumedetect", "-f", "null", "-"])
    match = re.search(r"mean_volume:\s*(-?[0-9.]+|-inf) dB", res.stderr.decode(errors="replace"))
    if not match:
        return None
    return -120.0 if match.group(1) == "-inf" else float(match.group(1))


def transcriber(model: str):
    """Return (name, callable(wav, lang) -> (segments, language)) or (None, None)."""
    try:
        from faster_whisper import WhisperModel  # type: ignore

        def with_faster(wav: str, lang: str | None):
            import wave

            import numpy as np  # a faster-whisper dependency

            # Feed samples directly: the wav is already 16 kHz mono PCM, and this
            # avoids faster-whisper's own decoder, which breaks on some PyAV versions.
            with wave.open(wav, "rb") as handle:
                pcm = handle.readframes(handle.getnframes())
            audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            engine = WhisperModel(model, device="cpu", compute_type="int8")
            segments, info = engine.transcribe(audio, language=lang, vad_filter=True)
            return [(s.start, s.end, s.text.strip()) for s in segments], info.language
        return "faster-whisper", with_faster
    except ImportError:
        pass
    try:
        import whisper  # type: ignore

        def with_openai(wav: str, lang: str | None):
            result = whisper.load_model(model).transcribe(wav, language=lang)
            return ([(s["start"], s["end"], s["text"].strip()) for s in result["segments"]],
                    result.get("language"))
        return "openai-whisper", with_openai
    except ImportError:
        return None, None


def transcribe(path: Path, out_dir: Path, start: float, length: float,
               lang: str, model: str) -> dict:
    volume = mean_volume(path, start, length)
    if volume is not None and volume < -60:
        return {"status": "silent", "reason": f"silent track (mean volume {volume:.0f} dB)"}
    name, engine = transcriber(model)
    if engine is None:
        return {"status": "unavailable",
                "reason": "no transcription engine installed (pip install faster-whisper)"}
    wav = out_dir / "audio.wav"
    res = run(["ffmpeg", "-v", "error", "-y", *window_args(start, length), "-i", str(path),
               "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    if res.returncode != 0:
        return {"status": "failed", "reason": res.stderr.decode(errors="replace")[:200]}
    try:
        segments, language = engine(str(wav), None if lang == "auto" else lang)
    except Exception as exc:  # model download blocked, out of memory, ...
        return {"status": "failed", "reason": f"{name}: {exc}"[:300]}
    finally:
        wav.unlink(missing_ok=True)
    lines = [f"[{fmt_time(start + a)}-{fmt_time(start + b)}] {text}" for a, b, text in segments if text]
    (out_dir / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "ok", "engine": name, "language": language, "file": "transcript.txt",
            "segments": len(lines), "words": sum(len(line.split()) - 1 for line in lines)}


def check() -> int:
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        found = shutil.which(tool)
        ok &= bool(found)
        print(f"{'ok ' if found else 'MISSING'} {tool}: {found or 'install ffmpeg'}")
    name, _ = transcriber("small")
    print(f"{'ok ' if name else 'optional'} transcription: "
          f"{name or 'not installed -> spoken audio will be skipped (pip install faster-whisper)'}")
    return 0 if ok else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*")
    parser.add_argument("--check", action="store_true", help="report available tools and exit")
    parser.add_argument("--max-frames", type=int, default=40, help="frame budget per source (default 40)")
    parser.add_argument("--width", type=int, default=960, help="max frame width in px (use 1280+ for small on-screen text)")
    parser.add_argument("--lang", default="auto", help="spoken language code, or auto")
    parser.add_argument("--model", default="small", help="whisper model name")
    parser.add_argument("--no-audio", action="store_true", help="skip transcription")
    parser.add_argument("--workdir", default=os.environ.get("VIDEO_SKILL_WORKDIR"))
    args = parser.parse_args()

    if args.check:
        return check()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("error: ffmpeg and ffprobe are required", file=sys.stderr)
        return 3
    clips = expand_inputs(args.inputs)
    if not clips:
        print("error: no video inputs found", file=sys.stderr)
        return 2

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="video_skill_work-"))
    workdir.mkdir(parents=True, exist_ok=True)
    sources, combined = [], []
    for number, clip in enumerate(clips, start=1):
        path = clip["path"]
        slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:40] or "video"
        src_dir = workdir / "sources" / f"{number:02d}-{slug}"
        entry: dict = {"index": number, "id": f"V{number}", "filename": path.name, "path": str(path),
                       "dir": str(src_dir.relative_to(workdir))}
        try:
            info = probe(path)
            start = min(clip["start"] or 0.0, info["duration"])
            end = min(clip["end"] if clip["end"] is not None else info["duration"], info["duration"])
            if end <= start:
                raise RuntimeError(f"empty window {start}-{end} (duration {info['duration']:.1f}s)")
            length = end - start
            frames = extract_frames(path, src_dir / "frames", start, length, args.max_frames, args.width)
            sheets = build_sheets(src_dir / "frames", frames, src_dir / "sheets")
            if args.no_audio:
                transcript = {"status": "skipped", "reason": "--no-audio"}
            elif not info["has_audio"]:
                transcript = {"status": "silent", "reason": "no audio stream"}
            else:
                transcript = transcribe(path, src_dir, start, length, args.lang, args.model)
            entry.update({"sha256": sha256(path), "duration": round(info["duration"], 2),
                          "window": {"start": round(start, 2), "end": round(end, 2)},
                          "width": info["width"], "height": info["height"],
                          "frames": frames, "sheets": sheets, "transcript": transcript})
            combined.append(f"\n===== SOURCE {entry['id']}: {path.name} "
                            f"[{fmt_time(start)}-{fmt_time(end)}] =====\n")
            if transcript["status"] == "ok":
                combined.append((src_dir / "transcript.txt").read_text(encoding="utf-8"))
            else:
                combined.append(f"(no transcript: {transcript['reason']})\n")
            print(f"{entry['id']} {path.name}: {len(frames)} frames, transcript {transcript['status']}")
        except Exception as exc:
            entry["error"] = str(exc)
            print(f"{entry['id']} {path.name}: FAILED - {exc}", file=sys.stderr)
        sources.append(entry)

    (workdir / "full_transcript.txt").write_text("".join(combined), encoding="utf-8")
    good = [s for s in sources if "error" not in s]
    meta = {
        "schema_version": 1,
        "workdir": str(workdir),
        "total_sources": len(sources),
        "failed_sources": len(sources) - len(good),
        "total_duration": round(sum(s["window"]["end"] - s["window"]["start"] for s in good), 2),
        "total_frames": sum(len(s["frames"]) for s in good),
        "transcript_words": sum(s["transcript"].get("words", 0) for s in good),
        "sources": sources,
    }
    (workdir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Workdir -> {workdir}\nText -> {workdir / 'full_transcript.txt'}\nMeta -> {workdir / 'metadata.json'}")
    return 0 if good else 6


if __name__ == "__main__":
    sys.exit(main())
