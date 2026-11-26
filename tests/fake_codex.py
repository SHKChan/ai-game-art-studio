"""Test double for the `codex` CLI (offline tests only — never used for real art).

  fake_codex.py exec - --output-last-message FILE [--image IMG]...   (prompt on stdin) -> writes a JSON answer
  fake_codex.py app-server --listen stdio://                         -> minimal JSON-RPC image bridge

The app-server returns a synthetic strip of N flat-colour blocks (N parsed from "exactly N equal cells"),
which is enough to test slicing/alignment. FAKE_CODEX_MODE=fail makes both modes fail.
"""
import base64
import io
import json
import os
import re
import sys

MODE = os.environ.get("FAKE_CODEX_MODE", "ok")


def strip_png(n: int) -> str:
    from PIL import Image, ImageDraw
    cell = 48
    im = Image.new("RGBA", (cell * n, cell), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(n):
        x = i * cell
        d.rectangle([x + 14, 10 + (i % 3), x + 33, 44], fill=(60 + 20 * i % 190, 90, 160, 255))
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
    for m in re.finditer(r"- id=([a-z0-9_]+); name=([^;]*); frames=(\d+)", prompt):
        n = int(m.group(3))
        poses = [(f"姿势{i + 1}" if zh else f"pose {i + 1} of {m.group(2)}") for i in range(n)]
        acts.append({"id": m.group(1), "poses": poses,
                     "prompt": f"FAKE-CODEX prompt for {m.group(1)}: one transparent PNG sprite strip, exactly {n} equal cells; "
                               f"reference seen: {bool(images)}"})
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
            if MODE == "fail":
                send({"method": "turn/completed", "params": {"turn": {"status": "failed", "error": {"message": "image generation unavailable"}}}})
                continue
            send({"method": "item/completed", "params": {"item": {"type": "imageGeneration", "status": "completed",
                                                                   "result": strip_png(int(k.group(1)) if k else 1)}}})
            send({"method": "turn/completed", "params": {"turn": {"status": "completed"}}})


if __name__ == "__main__":
    if sys.argv[1] == "exec":
        do_exec(sys.argv[2:])
    elif sys.argv[1] == "app-server":
        do_app_server()
