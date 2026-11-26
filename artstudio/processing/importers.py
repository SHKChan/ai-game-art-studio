"""Asset Import — external asset import: PNG, PNG sequences, sprite sheets, GIF/APNG, MP4/WebM."""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence

from ..util import StudioError

log = logging.getLogger("artstudio.import")
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}
IMAGE_EXT = {".png", ".gif", ".apng", ".webp", ".jpg", ".jpeg"}
MAX_FRAMES = 512


def sniff(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    with Image.open(path) as im:
        n = getattr(im, "n_frames", 1)
        if n > 1 and im.format in ("GIF", "PNG", "WEBP"):
            return "animation"
        return "image"


def extract_animation(path: Path, max_frames: int = MAX_FRAMES) -> list[tuple[Image.Image, int]]:
    """Fully composited frames + durations for GIF / APNG / animated WebP.
    Pillow applies disposal/blending when seeking, and convert('RGBA') yields the composite."""
    out = []
    with Image.open(path) as im:
        if getattr(im, "n_frames", 1) > max_frames:
            raise StudioError(f"Animation has {im.n_frames} frames; limit is {max_frames}")
        for frame in ImageSequence.Iterator(im):
            dur = int(frame.info.get("duration", im.info.get("duration", 100)) or 100)
            out.append((frame.convert("RGBA").copy(), max(10, dur)))
    if not out:
        raise StudioError("No frames decoded")
    return out


def extract_video(path: Path, ffmpeg: str | None, fps: float = 12.0, max_frames: int = 240,
                  start_s: float = 0.0, duration_s: float | None = None, scale_width: int | None = None) -> list[tuple[Image.Image, int]]:
    """Extract frames with ffmpeg (argument list, no shell). Returns frames at a fixed fps."""
    if not ffmpeg:
        raise StudioError("ffmpeg is not installed or configured (ARTSTUDIO_FFMPEG); video import unavailable.")
    if not (0.5 <= fps <= 60):
        raise StudioError("fps must be between 0.5 and 60")
    path = Path(path).resolve()
    with tempfile.TemporaryDirectory(prefix="artstudio-vid-") as td:
        vf = [f"fps={fps}"]
        if scale_width:
            vf.append(f"scale={int(scale_width)}:-1:flags=lanczos")
        args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
        if start_s:
            args += ["-ss", str(float(start_s))]
        args += ["-i", str(path)]
        if duration_s:
            args += ["-t", str(float(duration_s))]
        # Keep alpha when the codec has it (VP8/VP9 alpha WebM); otherwise RGB -> opaque.
        args += ["-vf", ",".join(vf), "-frames:v", str(int(max_frames)), "-pix_fmt", "rgba", str(Path(td) / "f%05d.png")]
        log.info("ffmpeg extract path=%s fps=%s", path.name, fps)
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        if r.returncode != 0:
            raise StudioError("ffmpeg failed: " + r.stderr.strip()[-400:])
        files = sorted(Path(td).glob("f*.png"))
        if not files:
            raise StudioError("ffmpeg produced no frames")
        dur = round(1000 / fps)
        frames = []
        for f in files:
            with Image.open(f) as im:
                frames.append((im.convert("RGBA").copy(), dur))
        return frames


def load_sequence(paths: list[Path]) -> list[tuple[Image.Image, int]]:
    """Transparent PNG sequence (natural sort by filename)."""
    import re

    def key(p):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]

    out = []
    for p in sorted(paths, key=key):
        with Image.open(p) as im:
            out.append((im.convert("RGBA").copy(), 100))
    return out


def video_to_gif_check(ffmpeg: str | None) -> dict:
    if not ffmpeg:
        return {"available": False, "reason": "ffmpeg not found"}
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        return {"available": r.returncode == 0, "version": r.stdout.splitlines()[0] if r.stdout else ""}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"available": False, "reason": str(e)}
