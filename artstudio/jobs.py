"""Asynchronous local job queue: progress, cancellation, retry, resumable remote generation,
and an explicit generation budget for unattended batches. Jobs persist as JSON in <workspace>/jobs."""
from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
from typing import Callable

from .providers.base import Cancelled, GenerationError, JobContext
from .util import StudioError, check_id, new_id, now, read_json, write_json

log = logging.getLogger("artstudio.jobs")
TERMINAL = ("succeeded", "failed", "cancelled")


class BudgetExceeded(StudioError):
    pass


class Budget:
    """Counts generation calls to providers that cost inference (ComfyUI/Codex/...)."""

    def __init__(self, limit: int | None, used: int = 0):
        self.limit, self.used = limit, used
        self.lock = threading.Lock()

    def spend(self, n: int = 1):
        with self.lock:
            if self.limit is not None and self.used + n > self.limit:
                raise BudgetExceeded(f"Generation budget exhausted ({self.used}/{self.limit}); raise 'budget' to continue.")
            self.used += n


class JobQueue:
    def __init__(self, ws, handlers: dict[str, Callable], workers: int = 2):
        self.ws = ws
        self.dir = ws.root / "jobs"
        self.handlers = handlers
        self.q: queue.Queue = queue.Queue()
        self.ctx: dict[str, JobContext] = {}
        self.lock = threading.RLock()
        self._load()
        self.threads = [threading.Thread(target=self._worker, daemon=True, name=f"job-worker-{i}") for i in range(workers)]
        for t in self.threads:
            t.start()

    # ---------- persistence
    def _path(self, jid):
        return self.dir / f"{check_id(jid, 'job id')}.json"

    def _save(self, job):
        job["updated_at"] = now()
        write_json(self._path(job["id"]), job)

    def _load(self):
        for f in sorted(self.dir.glob("*.json")):
            try:
                job = read_json(f)
            except ValueError:
                continue
            if job["status"] in ("queued", "running"):
                # Resumable if the provider stored remote state (e.g. ComfyUI prompt_id); else re-queue cleanly.
                job["status"] = "queued"
                job.setdefault("log", []).append({"at": now(), "msg": "re-queued after restart" + (" (resuming remote job)" if job.get("state", {}).get("prompt_id") else "")})
                self._save(job)
                self.q.put(job["id"])

    def get(self, jid) -> dict:
        p = self._path(jid)
        if not p.exists():
            raise StudioError("Unknown job")
        return read_json(p)

    def list(self, limit: int = 100, project_id: str | None = None) -> list[dict]:
        jobs = [read_json(f) for f in self.dir.glob("*.json")]
        if project_id:
            jobs = [j for j in jobs if j.get("project_id") == project_id]
        return sorted(jobs, key=lambda j: j["created_at"], reverse=True)[:limit]

    # ---------- API
    def submit(self, kind: str, params: dict, project_id: str | None = None, budget: int | None = None,
               max_attempts: int = 1, label: str = "") -> dict:
        if kind not in self.handlers:
            raise StudioError(f"Unknown job kind {kind}")
        if kind.startswith("batch") and budget is None:
            raise StudioError("Batch jobs require an explicit generation budget (budget=N).")
        job = {"id": new_id("job"), "kind": kind, "label": label or kind, "project_id": project_id, "params": params,
               "status": "queued", "progress": 0.0, "message": "queued", "result": None, "error": None,
               "attempts": 0, "max_attempts": max(1, int(max_attempts)), "budget": budget, "budget_used": 0,
               "state": {}, "log": [], "created_at": now(), "updated_at": now()}
        self._save(job)
        self.q.put(job["id"])
        return job

    def cancel(self, jid) -> dict:
        with self.lock:
            job = self.get(jid)
            if job["status"] in TERMINAL:
                return job
            ctx = self.ctx.get(jid)
            if ctx:
                ctx.cancel_event.set()
                job["message"] = "cancelling..."
            else:
                job["status"] = "cancelled"
                job["message"] = "cancelled before start"
            self._save(job)
            return job

    def retry(self, jid) -> dict:
        job = self.get(jid)
        if job["status"] not in ("failed", "cancelled"):
            raise StudioError("Only failed or cancelled jobs can be retried")
        job.update(status="queued", error=None, progress=0.0, message="retry queued", max_attempts=job["attempts"] + 1)
        if job.get("error_code") not in ("timeout", "unreachable"):
            job["state"] = {}
        self._save(job)
        self.q.put(jid)
        return job

    def wait(self, jid, timeout: float = 120.0) -> dict:
        end = time.time() + timeout
        while time.time() < end:
            j = self.get(jid)
            if j["status"] in TERMINAL:
                return j
            time.sleep(0.05)
        raise TimeoutError(f"job {jid} did not finish in {timeout}s")

    # ---------- worker
    def _worker(self):
        while True:
            jid = self.q.get()
            try:
                self._run(jid)
            except Exception:  # noqa: BLE001
                log.error("job crashed id=%s %s", jid, traceback.format_exc())
            finally:
                self.q.task_done()

    def _run(self, jid):
        job = self.get(jid)
        if job["status"] != "queued":
            return
        handler = self.handlers[job["kind"]]
        last_save = [0.0]

        def progress(frac, msg):
            job["progress"] = round(frac, 4) if frac is not None else job["progress"]
            job["message"] = msg
            if time.time() - last_save[0] > 0.25:
                last_save[0] = time.time()
                job["state"] = ctx.state
                self._save(job)

        ctx = JobContext(progress)
        ctx.state = dict(job.get("state") or {})
        self.ctx[jid] = ctx
        budget = Budget(job.get("budget"), job.get("budget_used", 0))
        while True:
            job["attempts"] += 1
            job.update(status="running", started_at=now(), message="running", error=None)
            self._save(job)
            try:
                result = handler(job["params"], ctx, budget, job)
                job.update(status="succeeded", progress=1.0, result=result, message="done")
                break
            except Cancelled as e:
                job.update(status="cancelled", message=str(e))
                break
            except BudgetExceeded as e:
                job.update(status="failed", error=str(e), error_code="budget_exceeded", message="budget exceeded")
                break
            except GenerationError as e:
                job.update(status="failed", error=str(e), error_code=e.code, error_details=e.details, message=e.code)
                if e.retryable and job["attempts"] < job["max_attempts"]:
                    job["log"].append({"at": now(), "msg": f"attempt {job['attempts']} failed ({e.code}); retrying"})
                    time.sleep(min(5, 0.5 * job["attempts"]))
                    continue
                break
            except (StudioError, ValueError, OSError, KeyError) as e:
                job.update(status="failed", error=str(e), error_code="error", message="failed")
                break
            finally:
                job["budget_used"] = budget.used
                job["state"] = ctx.state
        job["finished_at"] = now()
        self._save(job)
        self.ctx.pop(jid, None)
        log.info("job finished id=%s kind=%s status=%s", jid, job["kind"], job["status"])
