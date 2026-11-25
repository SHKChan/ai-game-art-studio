"""Mock ComfyUI HTTP/WebSocket service for OFFLINE TESTING ONLY.

Implements the documented ComfyUI server contracts used by ComfyUIProvider:
  GET /system_stats, GET /object_info[/{class}], POST /upload/image, POST /prompt, GET /queue,
  POST /queue {delete|clear}, POST /interrupt, GET /history[/{id}], GET /view, WS /ws?clientId=

It does not run any model. "Outputs" are copies of genuine existing artwork from the upstream
repositories (Pixel Atelier knight example), and every response identifies itself as a mock:
system_stats.system.comfyui_version contains "mock", and history entries carry
"artstudio_mock": "TEST FIXTURE". Never present these results as AI-generated artwork.

Scenarios (CLI --scenario or POST /mock/scenario {"scenario": ...}):
  ok | fail | timeout | disconnect | slow
Missing models / missing nodes / invalid workflows are produced naturally by validation.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import queue
import re
import shutil
import socket
import struct
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = {
    "sheet": ROOT / "upstream" / "pixel-atelier" / "examples" / "knight" / "run" / "atlas.png",
    "pose": ROOT / "upstream" / "pixel-atelier" / "examples" / "knight" / "idle" / "poster.png",
    "attack": ROOT / "upstream" / "pixel-atelier" / "examples" / "knight" / "light" / "atlas.png",
}
CKPTS = ["mock-sd15-fixture.safetensors", "mock-sdxl-fixture.safetensors"]
CONTROLNETS = ["mock-openpose-fixture.safetensors"]
LORAS = ["mock-pixelart-fixture.safetensors"]
SAMPLERS = ["euler", "euler_ancestral", "dpmpp_2m"]
SCHEDULERS = ["normal", "karras"]
IMG = lambda: ("IMAGE",)
OBJECT_INFO = {
    "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [CKPTS]}}, "output": ["MODEL", "CLIP", "VAE"], "output_node": False},
    "LoraLoader": {"input": {"required": {"model": ["MODEL"], "clip": ["CLIP"], "lora_name": [LORAS], "strength_model": ["FLOAT", {}], "strength_clip": ["FLOAT", {}]}}, "output": ["MODEL", "CLIP"], "output_node": False},
    "CLIPTextEncode": {"input": {"required": {"text": ["STRING", {"multiline": True}], "clip": ["CLIP"]}}, "output": ["CONDITIONING"], "output_node": False},
    "EmptyLatentImage": {"input": {"required": {"width": ["INT", {}], "height": ["INT", {}], "batch_size": ["INT", {}]}}, "output": ["LATENT"], "output_node": False},
    "KSampler": {"input": {"required": {"model": ["MODEL"], "seed": ["INT", {}], "steps": ["INT", {}], "cfg": ["FLOAT", {}],
                                        "sampler_name": [SAMPLERS], "scheduler": [SCHEDULERS], "positive": ["CONDITIONING"],
                                        "negative": ["CONDITIONING"], "latent_image": ["LATENT"], "denoise": ["FLOAT", {}]}}, "output": ["LATENT"], "output_node": False},
    "VAEDecode": {"input": {"required": {"samples": ["LATENT"], "vae": ["VAE"]}}, "output": ["IMAGE"], "output_node": False},
    "VAEEncode": {"input": {"required": {"pixels": ["IMAGE"], "vae": ["VAE"]}}, "output": ["LATENT"], "output_node": False},
    "VAEEncodeForInpaint": {"input": {"required": {"pixels": ["IMAGE"], "vae": ["VAE"], "mask": ["MASK"], "grow_mask_by": ["INT", {}]}}, "output": ["LATENT"], "output_node": False},
    "LoadImage": {"input": {"required": {"image": [["__uploaded__"], {"image_upload": True}]}}, "output": ["IMAGE", "MASK"], "output_node": False},
    "LoadImageMask": {"input": {"required": {"image": [["__uploaded__"], {}], "channel": [["alpha", "red", "green", "blue"]]}}, "output": ["MASK"], "output_node": False},
    "ImageScale": {"input": {"required": {"image": ["IMAGE"], "upscale_method": [["nearest-exact", "bilinear", "lanczos"]], "width": ["INT", {}], "height": ["INT", {}], "crop": [["disabled", "center"]]}}, "output": ["IMAGE"], "output_node": False},
    "ControlNetLoader": {"input": {"required": {"control_net_name": [CONTROLNETS]}}, "output": ["CONTROL_NET"], "output_node": False},
    "ControlNetApplyAdvanced": {"input": {"required": {"positive": ["CONDITIONING"], "negative": ["CONDITIONING"], "control_net": ["CONTROL_NET"], "image": ["IMAGE"],
                                                       "strength": ["FLOAT", {}], "start_percent": ["FLOAT", {}], "end_percent": ["FLOAT", {}]}}, "output": ["CONDITIONING", "CONDITIONING"], "output_node": False},
    "SaveImage": {"input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING", {}]}}, "output": [], "output_node": True},
    "PreviewImage": {"input": {"required": {"images": ["IMAGE"]}}, "output": [], "output_node": True},
}


class State:
    def __init__(self, workdir: Path, scenario: str = "ok", step_delay: float = 0.02):
        self.dir = workdir
        (workdir / "input" / "artstudio").mkdir(parents=True, exist_ok=True)
        (workdir / "output").mkdir(parents=True, exist_ok=True)
        self.scenario = scenario
        self.step_delay = step_delay
        self.queue: list[dict] = []
        self.running: dict | None = None
        self.history: dict = {}
        self.clients: dict[str, tuple[socket.socket, threading.Lock]] = {}
        self.lock = threading.RLock()
        self.interrupt = threading.Event()
        self.counter = 0
        self.work = queue.Queue()
        threading.Thread(target=self.executor, daemon=True).start()

    def uploads(self):
        return sorted(str(p.relative_to(self.dir / "input")).replace("\\", "/") for p in (self.dir / "input").rglob("*") if p.is_file())

    # ---- websocket push
    def send(self, client_id, msg):
        c = self.clients.get(client_id)
        if not c:
            return
        sock, lock = c
        data = json.dumps(msg).encode()
        n = len(data)
        hdr = struct.pack("!BB", 0x81, n) if n < 126 else (struct.pack("!BBH", 0x81, 126, n) if n < 65536 else struct.pack("!BBQ", 0x81, 127, n))
        try:
            with lock:
                sock.sendall(hdr + data)
        except OSError:
            self.clients.pop(client_id, None)

    def drop(self, client_id):
        c = self.clients.pop(client_id, None)
        if c:
            try:
                c[0].shutdown(socket.SHUT_RDWR)
                c[0].close()
            except OSError:
                pass

    def queue_status(self):
        return {"exec_info": {"queue_remaining": len(self.queue) + (1 if self.running else 0)}}

    # ---- validation (mirrors ComfyUI's /prompt validation shape)
    def validate(self, prompt: dict):
        errors = {}
        uploads = set(self.uploads())
        for nid, node in prompt.items():
            ct = node.get("class_type")
            info = OBJECT_INFO.get(ct)
            if info is None:
                return {"type": "invalid_prompt", "message": f"Cannot execute because node {ct} does not exist.", "details": f"Node ID '#{nid}'"}, {}
            req = info["input"].get("required", {})
            errs = []
            for k, spec in req.items():
                v = node.get("inputs", {}).get(k)
                if v is None:
                    errs.append({"type": "required_input_missing", "message": "Required input is missing", "details": k})
                    continue
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    if v[0] not in prompt:
                        errs.append({"type": "bad_linked_input", "message": "Bad linked input", "details": k})
                    continue
                if isinstance(spec[0], list):
                    choices = uploads if spec[0] == ["__uploaded__"] else set(spec[0])
                    if v not in choices:
                        errs.append({"type": "value_not_in_list", "message": "Value not in list", "details": f"{k}: '{v}' not in list"})
            if errs:
                errors[nid] = {"errors": errs, "dependent_outputs": [], "class_type": ct}
        if not any(OBJECT_INFO[n["class_type"]]["output_node"] for n in prompt.values()):
            return {"type": "prompt_no_outputs", "message": "Prompt has no outputs", "details": ""}, {}
        if errors:
            return {"type": "prompt_outputs_failed_validation", "message": "Prompt outputs failed validation", "details": ""}, errors
        return None, {}

    def executor(self):
        while True:
            item = self.work.get()
            with self.lock:
                if item not in self.queue:
                    continue
                self.queue.remove(item)
                self.running = item
            try:
                self.execute(item)
            finally:
                with self.lock:
                    self.running = None

    def execute(self, item):
        pid, cid, prompt = item["prompt_id"], item["client_id"], item["prompt"]
        self.interrupt.clear()
        self.send(cid, {"type": "status", "data": {"status": self.queue_status()}})
        self.send(cid, {"type": "execution_start", "data": {"prompt_id": pid, "timestamp": int(time.time() * 1000)}})
        msgs = [["execution_start", {"prompt_id": pid}]]
        outputs = {}
        scenario = self.scenario
        for nid, node in prompt.items():
            if self.interrupt.is_set():
                break
            self.send(cid, {"type": "executing", "data": {"node": nid, "display_node": nid, "prompt_id": pid}})
            if node["class_type"] == "KSampler":
                steps = int(node["inputs"].get("steps", 20))
                for st in range(1, steps + 1):
                    if self.interrupt.is_set():
                        break
                    if scenario == "disconnect" and st == max(1, steps // 2):
                        self.drop(cid)  # simulate a dropped WebSocket; execution continues server-side
                    time.sleep(self.step_delay * (5 if scenario == "slow" else 1))
                    self.send(cid, {"type": "progress", "data": {"value": st, "max": steps, "prompt_id": pid, "node": nid}})
                if scenario == "fail":
                    err = {"prompt_id": pid, "node_id": nid, "node_type": "KSampler", "exception_message": "MOCK: simulated CUDA out of memory",
                           "exception_type": "torch.OutOfMemoryError", "traceback": [], "current_inputs": {}, "current_outputs": {}}
                    self.send(cid, {"type": "execution_error", "data": err})
                    msgs.append(["execution_error", err])
                    self.history[pid] = {"prompt": [item["number"], pid, prompt, {}, []], "outputs": {},
                                         "status": {"status_str": "error", "completed": False, "messages": msgs}, "artstudio_mock": "TEST FIXTURE"}
                    return
                if scenario == "timeout":
                    while not self.interrupt.wait(0.1):
                        pass
            if OBJECT_INFO[node["class_type"]]["output_node"]:
                has_ref = any(n["class_type"] == "LoadImage" for n in prompt.values())
                has_pose = any(n["class_type"].startswith("ControlNet") for n in prompt.values())
                fx = FIXTURES["attack" if has_pose else ("sheet" if has_ref else "pose")]
                prefix = str(node["inputs"].get("filename_prefix", "ComfyUI"))
                prefix = re.sub(r"[^A-Za-z0-9_-]", "_", prefix)[:40] or "ComfyUI"
                self.counter += 1
                fname = f"{prefix}_{self.counter:05d}_.png"
                typ = "output" if node["class_type"] == "SaveImage" else "temp"
                (self.dir / typ).mkdir(exist_ok=True)
                shutil.copyfile(fx, self.dir / typ / fname)
                outputs[nid] = {"images": [{"filename": fname, "subfolder": "", "type": typ}]}
                self.send(cid, {"type": "executed", "data": {"node": nid, "display_node": nid, "output": outputs[nid], "prompt_id": pid}})
        if self.interrupt.is_set():
            msgs.append(["execution_interrupted", {"prompt_id": pid}])
            self.send(cid, {"type": "execution_interrupted", "data": {"prompt_id": pid, "node_id": None, "node_type": None, "executed": []}})
            self.history[pid] = {"prompt": [item["number"], pid, prompt, {}, []], "outputs": {},
                                 "status": {"status_str": "error", "completed": False, "messages": msgs}, "artstudio_mock": "TEST FIXTURE"}
            return
        msgs.append(["execution_success", {"prompt_id": pid}])
        self.history[pid] = {"prompt": [item["number"], pid, prompt, {}, list(outputs)], "outputs": outputs,
                             "status": {"status_str": "success", "completed": True, "messages": msgs},
                             "meta": {k: {"node_id": k} for k in outputs}, "artstudio_mock": "TEST FIXTURE"}
        self.send(cid, {"type": "executing", "data": {"node": None, "prompt_id": pid}})
        self.send(cid, {"type": "execution_success", "data": {"prompt_id": pid, "timestamp": int(time.time() * 1000)}})
        self.send(cid, {"type": "status", "data": {"status": self.queue_status()}})


def make_handler(state: State):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length", "0"))
            return self.rfile.read(n) if n else b""

        def do_GET(self):
            u = urlparse(self.path)
            p = u.path
            if p == "/ws":
                return self._ws(parse_qs(u.query).get("clientId", [uuid.uuid4().hex])[0])
            if p == "/system_stats":
                return self._json(200, {"system": {"os": "mock", "python_version": "mock", "embedded_python": False,
                                                   "comfyui_version": "0.0.0-mock-fixture", "argv": ["mock"]},
                                        "devices": [{"name": "MOCK (no GPU, fixtures only)", "type": "cpu", "index": 0, "vram_total": 0, "vram_free": 0}]})
            if p == "/object_info":
                info = json.loads(json.dumps(OBJECT_INFO))
                ups = state.uploads()
                for k in ("LoadImage", "LoadImageMask"):
                    info[k]["input"]["required"]["image"][0] = ups
                return self._json(200, {k: {**v, "name": k, "display_name": k, "category": "mock"} for k, v in info.items()})
            if p.startswith("/object_info/"):
                k = p.split("/")[-1]
                return self._json(200, {k: OBJECT_INFO[k]} if k in OBJECT_INFO else {})
            if p == "/queue":
                with state.lock:
                    run = [[state.running["number"], state.running["prompt_id"], {}, {}, []]] if state.running else []
                    pend = [[q["number"], q["prompt_id"], {}, {}, []] for q in state.queue]
                return self._json(200, {"queue_running": run, "queue_pending": pend})
            if p == "/history":
                return self._json(200, state.history)
            if p.startswith("/history/"):
                k = p.split("/")[-1]
                return self._json(200, {k: state.history[k]} if k in state.history else {})
            if p == "/view":
                q = parse_qs(u.query)
                typ = q.get("type", ["output"])[0]
                if typ not in ("output", "input", "temp"):
                    return self._json(400, {"error": "bad type"})
                f = (state.dir / typ / q.get("subfolder", [""])[0] / q.get("filename", [""])[0]).resolve()
                if not str(f).startswith(str((state.dir / typ).resolve())) or not f.is_file():
                    return self._json(404, {"error": "not found"})
                data = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            p = urlparse(self.path).path
            raw = self._body()
            if p == "/upload/image":
                return self._upload(raw)
            try:
                data = json.loads(raw or b"{}")
            except ValueError:
                return self._json(400, {"error": "invalid json"})
            if p == "/mock/scenario":
                state.scenario = data.get("scenario", "ok")
                return self._json(200, {"scenario": state.scenario})
            if p == "/prompt":
                prompt = data.get("prompt")
                if not isinstance(prompt, dict):
                    return self._json(400, {"error": {"type": "invalid_prompt", "message": "Invalid prompt", "details": ""}, "node_errors": {}})
                err, node_errors = state.validate(prompt)
                if err:
                    return self._json(400, {"error": err, "node_errors": node_errors})
                with state.lock:
                    state.counter += 1
                    item = {"prompt_id": str(uuid.uuid4()), "number": state.counter, "client_id": data.get("client_id", ""), "prompt": prompt}
                    state.queue.append(item)
                state.work.put(item)
                return self._json(200, {"prompt_id": item["prompt_id"], "number": item["number"], "node_errors": {}})
            if p == "/queue":
                with state.lock:
                    if data.get("clear"):
                        state.queue.clear()
                    for d in data.get("delete", []):
                        state.queue[:] = [q for q in state.queue if q["prompt_id"] != d]
                return self._json(200, {})
            if p == "/interrupt":
                state.interrupt.set()
                return self._json(200, {})
            self._json(404, {"error": "not found"})

        def _upload(self, raw):
            ctype = self.headers.get("Content-Type", "")
            m = re.search(r"boundary=([^;]+)", ctype)
            if not m:
                return self._json(400, {"error": "multipart required"})
            boundary = m.group(1).strip('"').encode()
            fields, fileinfo = {}, None
            for part in raw.split(b"--" + boundary):
                if b"\r\n\r\n" not in part:
                    continue
                head, body = part.split(b"\r\n\r\n", 1)
                body = body[:-2] if body.endswith(b"\r\n") else body
                name = re.search(rb'name="([^"]+)"', head)
                fn = re.search(rb'filename="([^"]*)"', head)
                if not name:
                    continue
                if fn:
                    fileinfo = (fn.group(1).decode(), body)
                else:
                    fields[name.group(1).decode()] = body.decode()
            if not fileinfo:
                return self._json(400, {"error": "no image"})
            sub = re.sub(r"[^A-Za-z0-9_-]", "", fields.get("subfolder", ""))
            fname = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(fileinfo[0]).name) or "upload.png"
            d = state.dir / "input" / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / fname).write_bytes(fileinfo[1])
            return self._json(200, {"name": fname, "subfolder": sub, "type": "input"})

        def _ws(self, client_id):
            key = self.headers.get("Sec-WebSocket-Key")
            if not key:
                return self._json(400, {"error": "websocket required"})
            acc = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", acc)
            self.end_headers()
            self.wfile.flush()
            sock = self.connection
            state.clients[client_id] = (sock, threading.Lock())
            state.send(client_id, {"type": "status", "data": {"status": state.queue_status(), "sid": client_id}})
            try:
                while True:
                    hdr = self.rfile.read(2)
                    if len(hdr) < 2:
                        break
                    op, n = hdr[0] & 0x0F, hdr[1] & 0x7F
                    if n == 126:
                        n = struct.unpack("!H", self.rfile.read(2))[0]
                    elif n == 127:
                        n = struct.unpack("!Q", self.rfile.read(8))[0]
                    self.rfile.read(4 + n)
                    if op == 0x8:
                        break
            except OSError:
                pass
            state.clients.pop(client_id, None)
            self.close_connection = True

    return H


def serve(port: int = 8188, workdir: Path | None = None, scenario: str = "ok", host: str = "127.0.0.1", step_delay: float = 0.02):
    import tempfile
    wd = Path(workdir or tempfile.mkdtemp(prefix="mock-comfy-"))
    state = State(wd, scenario, step_delay)
    srv = ThreadingHTTPServer((host, port), make_handler(state))
    srv.daemon_threads = True
    srv.state = state
    return srv


def main():
    ap = argparse.ArgumentParser(description="Mock ComfyUI (test fixtures only)")
    ap.add_argument("--port", type=int, default=8188)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--scenario", default="ok", choices=["ok", "fail", "timeout", "disconnect", "slow"])
    ap.add_argument("--workdir")
    a = ap.parse_args()
    srv = serve(a.port, Path(a.workdir) if a.workdir else None, a.scenario, a.host)
    print(f"MOCK ComfyUI (TEST FIXTURES ONLY) on http://{a.host}:{a.port} scenario={a.scenario}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
