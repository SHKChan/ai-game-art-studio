"""Test double for the `codex` CLI (offline tests only — never used for real art).

  fake_codex.py exec - --output-last-message FILE [--image IMG]...   (prompt on stdin) -> writes a JSON answer
  fake_codex.py app-server --listen stdio://                         -> minimal JSON-RPC image bridge

The app-server returns a synthetic sheet of N flat-colour blocks laid out in the grid the prompt asks for
("C columns x R rows" / "固定 C 列 × R 行", or "exactly N equal cells" in one row), which is enough to test
cutting/alignment. FAKE_CODEX_MODE=fail makes both modes fail; FAKE_CODEX_MODE=bad_once (with FAKE_CODEX_STATE=<file>)
leaves the last cell empty on the first image only, to exercise automatic regeneration.
"""
import base64
import io
import json
import os
import re
import sys

MODE = os.environ.get("FAKE_CODEX_MODE", "ok")


def strip_png(n: int, cols: int | None = None, rows: int = 1, draw: int | None = None) -> str:
    from PIL import Image, ImageDraw
    cell = 48
    cols = cols or n
    im = Image.new("RGBA", (cell * cols, cell * rows), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(n if draw is None else draw):
        x, y = i % cols * cell, i // cols * cell
        d.rectangle([x + 14, y + 10 + (i % 3), x + 33, y + 44], fill=(60 + 20 * i % 190, 90, 160, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def do_exec(argv):
    out = argv[argv.index("--output-last-message") + 1]
    images = [argv[i + 1] for i, a in enumerate(argv) if a == "--image"]
    prompt = sys.stdin.read()
    if MODE == "fail":
        sys.stderr.write("not logged in\n")
        sys.exit(2)
    zh = "Simplified Chinese" in prompt
    acts = []
    for m in re.finditer(r"- id=([a-z0-9_]+); name=([^;]*); frames=(\d+); grid=(\d+) columns x (\d+) rows", prompt):
        n, c, r = int(m.group(3)), int(m.group(4)), int(m.group(5))
        poses = [(f"姿势{i + 1}" if zh else f"pose {i + 1} of {m.group(2)}") for i in range(n)]
        acts.append({"id": m.group(1), "poses": poses,
                     "prompt": f"FAKE-CODEX prompt for {m.group(1)}: one transparent PNG sprite sheet, {n} frames in "
                               f"{c} columns x {r} rows; reference seen: {bool(images)}"})
    answer = {"identity": "小骑士，金发，蓝色披风" if zh else "small knight, blonde hair, blue cape (fake codex)", "actions": acts}
    with open(out, "w", encoding="utf-8") as f:
        f.write("Here you go:\n```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```")
    print("done")


def do_app_server():
    def send(o):
        sys.stdout.write(json.dumps(o) + "\n")
        sys.stdout.flush()
    for line in sys.stdin:
        m = json.loads(line)
        meth, rid = m.get("method"), m.get("id")
        if meth == "initialize":
            send({"id": rid, "result": {}})
        elif meth == "model/list":
            send({"id": rid, "result": {"data": [{"model": "fake-model", "isDefault": True}]}})
        elif meth == "thread/start":
            send({"id": rid, "result": {"thread": {"id": "t1"}}})
        elif meth == "turn/start":
            send({"id": rid, "result": {}})
            text = " ".join(i.get("text", "") for i in m["params"]["input"] if i.get("type") == "text")
            k = re.search(r"exactly (\d+) equal cells", text)
            g = re.search(r"(\d+) columns x (\d+) rows", text) or re.search(r"固定 (\d+) 列 × (\d+) 行", text)
            nf = re.search(r"design (\d+) connected key poses", text) or re.search(r"设计 (\d+) 个连贯", text) or re.search(r"(\d+) frames in", text)
            if MODE == "fail":
                send({"method": "turn/completed", "params": {"turn": {"status": "failed", "error": {"message": "image generation unavailable"}}}})
                continue
            if g:
                cols, rows = int(g.group(1)), int(g.group(2))
                n = int(nf.group(1)) if nf else cols * rows
            else:
                n = int(k.group(1)) if k else 1
                cols, rows = n, 1
            draw = None
            state = os.environ.get("FAKE_CODEX_STATE")
            if MODE == "bad_once" and state and not os.path.exists(state):
                open(state, "w").close()
                draw = n - 1
            send({"method": "item/completed", "params": {"item": {"type": "imageGeneration", "status": "completed",
                                                                   "result": strip_png(n, cols, rows, draw)}}})
            send({"method": "turn/completed", "params": {"turn": {"status": "completed"}}})


if __name__ == "__main__":
    if sys.argv[1] == "exec":
        do_exec(sys.argv[2:])
    elif sys.argv[1] == "app-server":
        do_app_server()
