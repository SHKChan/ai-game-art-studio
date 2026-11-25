import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mock_comfyui"))

from PIL import Image, ImageDraw  # noqa: E402

KNIGHT = ROOT / "upstream" / "pixel-atelier" / "examples" / "knight"
SHOWCASE_GIF = ROOT / "upstream" / "atelier" / "showcase" / "gifs" / "opus-5.5-xhigh"


def temp_workspace():
    d = Path(tempfile.mkdtemp(prefix="artstudio-test-"))
    return d


def studio(tmp: Path, **kw):
    os.environ["ARTSTUDIO_WORKSPACE"] = str(tmp)
    from artstudio.config import load_config
    from artstudio.service import Studio
    cfg = load_config()
    for k, v in kw.items():
        setattr(cfg.comfyui, k, v)
    return Studio(cfg, workers=1)


def sprite(w=32, h=48, color=(200, 40, 40, 255), weapon=False, y_shift=0, x_shift=0, bg=(0, 0, 0, 0)):
    """Synthetic test sprite (geometric test fixture, not artwork)."""
    im = Image.new("RGBA", (w, h), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((10 + x_shift, 8 + y_shift, 21 + x_shift, 40 + y_shift), fill=color)
    d.ellipse((11 + x_shift, 2 + y_shift, 20 + x_shift, 11 + y_shift), fill=(240, 200, 160, 255))
    if weapon:
        d.line((22 + x_shift, 20 + y_shift, 30 + x_shift, 5 + y_shift), fill=(220, 220, 230, 255), width=2)
    return im


def mock_comfy(scenario="ok"):
    from server import serve
    srv = serve(0, None, scenario, step_delay=0.005)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def cleanup(p):
    shutil.rmtree(p, ignore_errors=True)
