"""Engine A — AtelierProceduralProvider.

Talks to the upstream Atelier binary (unmodified) through its two supported interfaces:
  * MCP over stdio (persistent session; `atelier` with no arguments) — fast path.
  * `atelier call TOOL --stdin --home DIR` — one process per call; fallback.
Every document keeps Atelier's own `doc.recipe` (replayable with `atelier replay`).
"""
from __future__ import annotations

import json
import logging
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path

from PIL import Image

from ..util import StudioError
from .base import GenerationError, GenerationRequest, GenerationResult, JobContext, Provider, ProviderStatus

log = logging.getLogger("artstudio.atelier")
DOC_PLACEHOLDER = "$DOC"


class AtelierError(StudioError):
    pass


class AtelierClient:
    """One Atelier document store (`home`). Use as a context manager for an MCP session."""

    def __init__(self, binary: str, home: Path, transport: str = "mcp", timeout: float = 60.0):
        if not binary:
            raise AtelierError("Atelier binary not found. Build it (scripts/build-atelier.ps1) or set ATELIER_BIN.")
        self.binary, self.home, self.transport, self.timeout = binary, Path(home), transport, timeout
        self.home.mkdir(parents=True, exist_ok=True)
        self.proc = None
        self._q: queue.Queue = queue.Queue()
        self._id = 0
        self.calls = 0

    # ---- lifecycle
    def __enter__(self):
        if self.transport == "mcp":
            self._start_mcp()
        return self

    def __exit__(self, *exc):
        self.close()

    def _env(self):
        env = dict(os.environ)
        env["ATELIER_HOME"] = str(self.home)
        env.setdefault("RUST_LOG", "warn")
        return env

    def _start_mcp(self):
        self.proc = subprocess.Popen([self.binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     env=self._env(), text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._reader, daemon=True).start()
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "ai-game-art-studio", "version": "0.1.0"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _reader(self):
        for line in self.proc.stdout:
            try:
                self._q.put(json.loads(line))
            except ValueError:
                continue
        self._q.put(None)

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            try:
                m = self._q.get(timeout=self.timeout)
            except queue.Empty:
                raise AtelierError(f"Atelier MCP timeout on {method}") from None
            if m is None:
                raise AtelierError("Atelier MCP process exited")
            if m.get("id") == rid:
                if "error" in m:
                    raise AtelierError(m["error"].get("message", str(m["error"])))
                return m["result"]

    def close(self):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                self.proc.kill()
            self.proc = None

    # ---- calls
    def call(self, tool: str, args: dict) -> dict:
        self.calls += 1
        if self.proc:
            res = self._rpc("tools/call", {"name": tool, "arguments": args})
            if res.get("isError"):
                text = " ".join(c.get("text", "") for c in res.get("content", []))
                raise AtelierError(f"{tool}: {text[:500]}")
            if "structuredContent" in res:
                return res["structuredContent"]
            text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
            try:
                return json.loads(text)
            except ValueError:
                return {"text": text, "content": res.get("content", [])}
        r = subprocess.run([self.binary, "call", tool, "--stdin", "--home", str(self.home)], input=json.dumps(args),
                           capture_output=True, text=True, encoding="utf-8", timeout=self.timeout)
        if r.returncode != 0:
            raise AtelierError(f"{tool} failed: {(r.stdout + r.stderr).strip()[-600:]}")
        return json.loads(r.stdout.strip().splitlines()[-1])

    def run(self, calls: list[dict], doc_id: str | None = None, progress=None, cancel=None) -> str | None:
        """Execute a list of {"name","arguments"} calls. "$DOC" in arguments is replaced by the doc id
        returned by the first doc_new (or the provided doc_id)."""
        n = len(calls)
        for i, c in enumerate(calls):
            if cancel:
                cancel()
            args = json.loads(json.dumps(c.get("arguments", {})).replace(f'"{DOC_PLACEHOLDER}"', json.dumps(doc_id or "")))
            res = self.call(c["name"], args)
            if c["name"] == "doc_new":
                doc_id = res["doc_id"]
            if progress and (i % 10 == 0 or i == n - 1):
                progress((i + 1) / n, f"{c['name']} {i + 1}/{n}")
        return doc_id

    def tools(self) -> list[dict]:
        r = subprocess.run([self.binary, "tools", "--markdown"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        names = []
        for line in r.stdout.splitlines():
            if line.startswith("## ") or line.startswith("### "):
                names.append(line.lstrip("# ").strip("` "))
        return names

    def schema(self, tool: str) -> dict:
        r = subprocess.run([self.binary, "tools", "--schema", tool], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        if r.returncode:
            raise AtelierError(r.stderr.strip())
        return json.loads(r.stdout)

    def replay(self, recipe: Path, show: bool = False) -> dict:
        args = [self.binary, "replay", str(recipe), "--home", str(self.home)]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=600, env=self._env())
        if r.returncode:
            raise AtelierError(f"replay failed: {(r.stdout + r.stderr)[-600:]}")
        return {"stdout": r.stdout[-4000:]}

    def doc_dir(self, doc_id: str) -> Path:
        return self.home / "documents" / doc_id

    def export_frames(self, doc_id: str, out_dir: Path, tag: str | None = None) -> tuple[list[Image.Image], list[int], dict]:
        """Export via doc_export(op=sheet, meta=standard, scale=1) and slice using its JSON metadata."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        sheet = out_dir / "sheet.png"
        self.call("doc_export", {"doc_id": doc_id, "op": "sheet", "out_path": str(sheet.resolve()), "meta": "standard", "scale": 1})
        meta = json.loads(sheet.with_suffix(".json").read_text(encoding="utf-8"))
        names = sorted(meta["frames"], key=lambda k: int(k.rsplit(" ", 1)[-1]))
        frames, durs = [], []
        with Image.open(sheet) as im:
            im = im.convert("RGBA")
            for k in names:
                f = meta["frames"][k]["frame"]
                frames.append(im.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])))
                durs.append(int(meta["frames"][k].get("duration", 100)))
        return frames, durs, meta


class AtelierProceduralProvider(Provider):
    id = "atelier"
    name = "Atelier procedural (Rust engine)"
    kind = "procedural"

    def __init__(self, binary: str | None):
        self.binary = binary

    def status(self) -> ProviderStatus:
        if not self.binary:
            return ProviderStatus(False, "Atelier binary not found (build upstream/atelier with cargo or set ATELIER_BIN)")
        try:
            r = subprocess.run([self.binary, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            if r.returncode:
                return ProviderStatus(False, "atelier --version failed", {"stderr": r.stderr[-300:]})
            return ProviderStatus(True, "", {"binary": self.binary, "version": r.stdout.strip()})
        except (OSError, subprocess.TimeoutExpired) as e:
            return ProviderStatus(False, f"Cannot run Atelier: {e}")

    def capabilities(self) -> dict:
        from ..procedural import BUILDERS
        return {"builders": {k: {"description": b.DESCRIPTION, "params": b.PARAMS, "asset_type": b.ASSET_TYPE} for k, b in BUILDERS.items()},
                "replay": True, "tools": "atelier tools --markdown"}

    def client(self, home: Path, transport: str = "mcp") -> AtelierClient:
        return AtelierClient(self.binary, home, transport)

    def generate(self, req: GenerationRequest, ctx: JobContext) -> GenerationResult:
        """req.params: {"home": path, "builder": name, "builder_params": {...}} or {"recipe": path} or {"calls": [...]}."""
        from ..procedural import BUILDERS
        st = self.status()
        if not st.available:
            raise GenerationError(st.reason, "provider_unavailable")
        home = Path(req.params["home"])
        out = Path(req.out_dir or home / "out")
        with self.client(home) as c:
            if req.params.get("builder"):
                b = BUILDERS.get(req.params["builder"])
                if not b:
                    raise GenerationError(f"Unknown builder {req.params['builder']}", "bad_request")
                calls = b.build(**(req.params.get("builder_params") or {}))
            elif req.params.get("calls"):
                calls = req.params["calls"]
            else:
                calls = None
            if calls is not None:
                doc_id = c.run(calls, progress=lambda p, m: ctx.progress(p * 0.9, m), cancel=ctx.check_cancel)
            else:
                recipe = Path(req.params["recipe"])
                before = set(p.name for p in (home / "documents").glob("*")) if (home / "documents").exists() else set()
                c.close()
                AtelierClient(self.binary, home, "cli").replay(recipe)
                after = set(p.name for p in (home / "documents").glob("*"))
                new = sorted(after - before - {".transactions", ".store.lock"})
                doc_id = new[0] if new else json.loads(Path(recipe).read_text(encoding="utf-8").splitlines()[0])["arguments"].get("doc_id")
                c = AtelierClient(self.binary, home, "cli")
            frames, durs, meta = c.export_frames(doc_id, out)
            paths = []
            for i, f in enumerate(frames):
                p = out / f"frame_{i:03d}.png"
                f.save(p)
                paths.append(p)
            recipe_src = c.doc_dir(doc_id) / "doc.recipe"
            recipe_copy = out / "doc.recipe"
            if recipe_src.exists():
                shutil.copyfile(recipe_src, recipe_copy)
            ctx.progress(1.0, "exported")
            return GenerationResult(paths, {"doc_id": doc_id, "durations": durs, "recipe": str(recipe_copy), "calls": c.calls,
                                            "atelier_meta": meta.get("meta", {})})
