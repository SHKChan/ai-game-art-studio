"""ComfyUIProvider — primary AI image-generation backend, via ComfyUI's documented server API:

  GET  /system_stats            server availability + version
  GET  /object_info             node discovery (inputs, COMBO model lists)
  POST /upload/image            reference / mask upload (multipart)
  POST /prompt                  submit {prompt, client_id} -> {prompt_id, number, node_errors}
  WS   /ws?clientId=...         status / execution_start / executing / progress / executed /
                                execution_success / execution_error / execution_interrupted
  GET  /history/{prompt_id}     outputs + status
  GET  /view?filename&subfolder&type   output retrieval
  GET  /queue, POST /queue {delete:[...]}, POST /interrupt   queue monitoring / cancellation

The provider never assumes a model, checkpoint, LoRA or custom node; workflow templates declare them
and they are validated against /object_info before submission.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import socket
import time
import uuid
from pathlib import Path
from urllib import error, parse, request

from ..comfy.workflows import WorkflowLibrary, bind, validate_against_server
from ..comfy.ws import WebSocket, WebSocketError
from ..config import ComfyConfig
from .base import Cancelled, GenerationError, GenerationRequest, GenerationResult, JobContext, Provider, ProviderStatus

log = logging.getLogger("artstudio.comfyui")


class ComfyHTTP:
    def __init__(self, cfg: ComfyConfig):
        self.cfg = cfg
        self.base = cfg.url.rstrip("/")
        tok = os.environ.get(cfg.api_key_env) if cfg.api_key_env else None
        self.headers = {"Authorization": f"Bearer {tok}"} if tok else {}

    def _req(self, method, path, data=None, headers=None, timeout=None, raw=False):
        h = dict(self.headers)
        h.update(headers or {})
        body = data
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
        req = request.Request(self.base + path, data=body, method=method, headers=h)
        try:
            with request.urlopen(req, timeout=timeout or self.cfg.connect_timeout_s) as r:
                payload = r.read()
                return payload if raw else (json.loads(payload) if payload else {})
        except error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(text)
            except ValueError:
                detail = {"raw": text[:500]}
            raise GenerationError(f"ComfyUI HTTP {e.code} on {path}", "http_error", {"status": e.code, "body": detail},
                                  retryable=e.code >= 500) from None
        except (error.URLError, socket.timeout, ConnectionError, TimeoutError) as e:
            raise GenerationError(f"ComfyUI unreachable at {self.base}: {getattr(e, 'reason', e)}", "unreachable",
                                  retryable=True) from None

    def get(self, path, **kw):
        return self._req("GET", path, **kw)

    def post(self, path, data=None, **kw):
        return self._req("POST", path, data, **kw)

    def upload_image(self, path: Path, overwrite: bool = True, subfolder: str = "artstudio") -> dict:
        boundary = "----artstudio" + uuid.uuid4().hex
        ctype = mimetypes.guess_type(str(path))[0] or "image/png"
        parts = []
        for k, v in (("type", "input"), ("overwrite", "true" if overwrite else "false"), ("subfolder", subfolder)):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        fname = Path(path).name
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{fname}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                     + Path(path).read_bytes() + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self.post("/upload/image", b"".join(parts), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                         timeout=60)

    def ws_url(self, client_id: str) -> str:
        u = parse.urlparse(self.base)
        scheme = "wss" if u.scheme == "https" else "ws"
        return f"{scheme}://{u.netloc}{u.path}/ws?clientId={client_id}"


class ComfyUIProvider(Provider):
    id = "comfyui"
    name = "ComfyUI"
    kind = "image_generation"
    counts_toward_budget = True

    def __init__(self, cfg: ComfyConfig, library: WorkflowLibrary):
        self.cfg = cfg
        self.library = library
        self.http = ComfyHTTP(cfg)
        self._object_info_cache: tuple[float, dict] | None = None

    # ---------- capability checks
    def status(self) -> ProviderStatus:
        try:
            stats = self.http.get("/system_stats")
        except GenerationError as e:
            return ProviderStatus(False, str(e), {"url": self.cfg.url})
        sysinfo = stats.get("system", {})
        details = {"url": self.cfg.url, "comfyui_version": sysinfo.get("comfyui_version"), "python": sysinfo.get("python_version"),
                   "devices": [{"name": d.get("name"), "type": d.get("type"), "vram_total": d.get("vram_total")} for d in stats.get("devices", [])],
                   "is_mock": self.is_mock(stats)}
        return ProviderStatus(True, "", details)

    @staticmethod
    def is_mock(stats: dict) -> bool:
        return "mock" in str(stats.get("system", {}).get("comfyui_version", "")).lower()

    def object_info(self, refresh: bool = False) -> dict:
        if not refresh and self._object_info_cache and time.time() - self._object_info_cache[0] < 60:
            return self._object_info_cache[1]
        info = self.http.get("/object_info", timeout=max(30, self.cfg.connect_timeout_s))
        self._object_info_cache = (time.time(), info)
        return info

    def capabilities(self) -> dict:
        return {"categories": sorted({t["category"] for t in self.library.list() if t.get("valid")}),
                "workflows": [{"id": t["id"], "category": t["category"], "verification": t["verification"]} for t in self.library.list()]}

    def check_workflow(self, wid: str, params: dict | None = None) -> dict:
        tpl = self.library.get(wid)
        info = self.object_info(refresh=True)
        prompt = None
        if params is not None:
            fake_uploads = {k: "__pending_upload__.png" for k, s in tpl["inputs"].items() if s["type"] in ("image", "mask")}
            prompt, _ = bind(tpl, params, fake_uploads)
        return validate_against_server(tpl, info, prompt)

    def queue(self) -> dict:
        q = self.http.get("/queue")
        return {"running": [x[1] for x in q.get("queue_running", [])], "pending": [x[1] for x in q.get("queue_pending", [])]}

    # ---------- generation
    def generate(self, req: GenerationRequest, ctx: JobContext) -> GenerationResult:
        if not req.workflow_id:
            raise GenerationError("ComfyUI generation needs a workflow template id", "bad_request")
        tpl = self.library.get(req.workflow_id)
        st = self.status()
        if not st.available:
            raise GenerationError(st.reason, "provider_unavailable", retryable=True)
        is_mock = bool(st.details.get("is_mock"))
        out_dir = Path(req.out_dir or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        params = dict(req.params)
        if req.prompt:
            params.setdefault("prompt", req.prompt)
        if req.negative_prompt:
            params.setdefault("negative_prompt", req.negative_prompt)
        if req.seed is not None:
            params.setdefault("seed", req.seed)
        prompt_id = ctx.state.get("prompt_id")  # resume: reattach to an already-submitted prompt
        client_id = ctx.state.get("client_id") or uuid.uuid4().hex
        bound = ctx.state.get("bound", {})
        if not prompt_id:
            ctx.progress(0.02, "uploading references")
            uploads = {}
            image_inputs = [k for k, s in tpl["inputs"].items() if s["type"] in ("image", "mask")]
            refs = list(req.reference_images)
            for k in image_inputs:
                src = params.get(k) or (refs.pop(0) if refs else None)
                if src:
                    r = self.http.upload_image(Path(src))
                    uploads[k] = (r.get("subfolder") + "/" if r.get("subfolder") else "") + r["name"]
            api_prompt, bound = bind(tpl, params, uploads)
            check = validate_against_server(tpl, self.object_info(refresh=True), api_prompt)
            if not check["ok"]:
                code = "missing_nodes" if check["missing_nodes"] else ("missing_models" if check["missing_models"] else "invalid_values")
                raise GenerationError(f"Workflow '{tpl['id']}' is not runnable on this server: {code}", code, check)
            ctx.check_cancel()
            resp = self.http.post("/prompt", {"prompt": api_prompt, "client_id": client_id}, timeout=30)
            if resp.get("node_errors"):
                raise GenerationError("ComfyUI rejected the workflow", "invalid_workflow", {"node_errors": resp["node_errors"]})
            prompt_id = resp["prompt_id"]
            ctx.state.update(prompt_id=prompt_id, client_id=client_id, bound=bound, submitted_at=time.time())
            log.info("comfy submitted prompt_id=%s workflow=%s", prompt_id, tpl["id"])
        ctx.progress(0.05, f"queued {prompt_id}")
        history = self._wait(prompt_id, client_id, ctx)
        entry = history.get(prompt_id, {})
        st_ = entry.get("status", {})
        if st_.get("status_str") == "error":
            msgs = [m for m in st_.get("messages", []) if m and m[0] == "execution_error"]
            raise GenerationError("ComfyUI execution failed", "execution_error", {"messages": msgs[:3]})
        images = []
        wanted = {o["node"] for o in tpl["outputs"]}
        for nid, out in entry.get("outputs", {}).items():
            if wanted and nid not in wanted:
                continue
            for key in ("images", "gifs", "videos"):
                for im in out.get(key, []):
                    q = parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
                    data = self.http.get(f"/view?{q}", raw=True, timeout=120)
                    dst = out_dir / f"{prompt_id[:8]}_{nid}_{len(images):02d}{Path(im['filename']).suffix or '.png'}"
                    dst.write_bytes(data)
                    images.append(dst)
        if not images:
            raise GenerationError("Prompt finished but produced no retrievable outputs", "no_outputs", {"outputs": list(entry.get("outputs", {}))})
        ctx.progress(1.0, f"{len(images)} output(s)")
        meta = {"provider": "comfyui", "server": self.cfg.url, "comfyui_version": st.details.get("comfyui_version"),
                "workflow_id": tpl["id"], "workflow_category": tpl["category"], "workflow_verification": tpl["verification"],
                "prompt_id": prompt_id, "params": bound, "outputs": [p.name for p in images],
                "is_test_fixture": is_mock}
        if is_mock:
            meta["warning"] = "TEST FIXTURE from the mock ComfyUI service — not AI-generated artwork."
        return GenerationResult(images, meta, is_test_fixture=is_mock)

    def _wait(self, prompt_id: str, client_id: str, ctx: JobContext) -> dict:
        deadline = time.time() + self.cfg.job_timeout_s
        ws = None
        if self.cfg.use_websocket:
            try:
                ws = WebSocket(self.http.ws_url(client_id), timeout=self.cfg.connect_timeout_s, headers=self.http.headers)
                ws.settimeout(self.cfg.poll_interval_s)
            except (OSError, WebSocketError) as e:
                log.warning("websocket unavailable (%s); falling back to polling", e)
                ws = None
        try:
            while time.time() < deadline:
                if ctx.cancel_event.is_set():
                    self._cancel_remote(prompt_id)
                    raise Cancelled("Cancelled by user")
                if ws:
                    try:
                        msg = ws.recv_json()
                        if msg is None:
                            raise WebSocketError("closed")
                        done = self._on_ws(msg, prompt_id, ctx)
                        if done == "error":
                            break
                        if done:
                            break
                        continue
                    except socket.timeout:
                        pass
                    except (OSError, WebSocketError, ValueError) as e:
                        log.warning("websocket dropped (%s); polling /history", e)
                        try:
                            ws.close()
                        except Exception:  # noqa: BLE001
                            pass
                        ws = None
                h = self.http.get(f"/history/{prompt_id}", timeout=15)
                if prompt_id in h and (h[prompt_id].get("status", {}).get("completed") or h[prompt_id].get("status", {}).get("status_str") in ("success", "error")):
                    return h
                if not ws:
                    try:
                        q = self.queue()
                        pos = (q["pending"].index(prompt_id) + 1) if prompt_id in q["pending"] else 0
                        ctx.progress(0.05, "running" if prompt_id in q["running"] else (f"queued (position {pos})" if pos else "waiting"))
                    except GenerationError:
                        pass
                    time.sleep(self.cfg.poll_interval_s)
            else:
                self._cancel_remote(prompt_id)
                raise GenerationError(f"Timed out after {self.cfg.job_timeout_s:.0f}s", "timeout", retryable=True)
        finally:
            if ws:
                ws.close()
        for _ in range(20):
            h = self.http.get(f"/history/{prompt_id}", timeout=15)
            if prompt_id in h:
                return h
            time.sleep(0.25)
        raise GenerationError("Execution finished but history is missing", "no_history", retryable=True)

    def _on_ws(self, msg: dict, prompt_id: str, ctx: JobContext):
        t, d = msg.get("type"), msg.get("data", {})
        if d.get("prompt_id") not in (None, prompt_id):
            return False
        if t == "progress":
            frac = d.get("value", 0) / max(1, d.get("max", 1))
            ctx.progress(0.1 + 0.85 * frac, f"node {d.get('node')} step {d.get('value')}/{d.get('max')}")
        elif t == "executing":
            if d.get("node") is None and d.get("prompt_id") == prompt_id:
                return True
            ctx.state["last_node"] = d.get("node")
        elif t == "execution_success":
            return True
        elif t == "execution_error":
            return "error"
        elif t == "execution_interrupted":
            raise Cancelled("Interrupted on the ComfyUI server")
        return False

    def _cancel_remote(self, prompt_id: str) -> None:
        try:
            q = self.queue()
            if prompt_id in q["pending"]:
                self.http.post("/queue", {"delete": [prompt_id]})
            elif prompt_id in q["running"]:
                self.http.post("/interrupt", {"prompt_id": prompt_id})
        except GenerationError as e:
            log.warning("remote cancel failed: %s", e)
