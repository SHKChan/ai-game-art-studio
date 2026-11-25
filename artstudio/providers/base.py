"""Provider abstraction. Providers report real availability at runtime; an unavailable provider
is shown as unavailable and is never silently replaced by another technology."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class ProviderUnavailable(RuntimeError):
    pass


class GenerationError(RuntimeError):
    def __init__(self, message: str, code: str = "generation_failed", details: dict | None = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.retryable = retryable


class Cancelled(RuntimeError):
    pass


@dataclass
class ProviderStatus:
    available: bool
    reason: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self):
        return {"available": self.available, "reason": self.reason, "details": self.details}


@dataclass
class GenerationRequest:
    kind: str                         # e.g. text_to_image, image_to_image, procedural, pose_keyframe ...
    params: dict = field(default_factory=dict)
    prompt: str = ""
    negative_prompt: str = ""
    reference_images: list[Path] = field(default_factory=list)
    seed: int | None = None
    workflow_id: str | None = None
    out_dir: Path | None = None


@dataclass
class GenerationResult:
    images: list[Path]
    metadata: dict = field(default_factory=dict)
    is_test_fixture: bool = False


ProgressFn = Callable[[float, str], None]


class JobContext:
    """Passed to providers: progress reporting + cooperative cancellation."""

    def __init__(self, progress: ProgressFn | None = None):
        self._progress = progress or (lambda p, m: None)
        self.cancel_event = threading.Event()
        self.state: dict = {}  # provider-specific resumable state (e.g. remote prompt_id), persisted by the job queue

    def progress(self, fraction: float, message: str = "") -> None:
        self._progress(max(0.0, min(1.0, float(fraction))), message)

    def check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise Cancelled("Cancelled by user")


class Provider:
    id = "base"
    name = "Base"
    kind = "abstract"
    paid = False           # counts against generation budget when True or when remote inference
    counts_toward_budget = False

    def status(self) -> ProviderStatus:
        raise NotImplementedError

    def capabilities(self) -> dict:
        return {}

    def generate(self, req: GenerationRequest, ctx: JobContext) -> GenerationResult:
        raise NotImplementedError

    def cancel(self, ctx: JobContext) -> bool:
        ctx.cancel_event.set()
        return True

    def describe(self) -> dict:
        s = self.status()
        return {"id": self.id, "name": self.name, "kind": self.kind, "status": s.to_dict(), "capabilities": self.capabilities(),
                "counts_toward_budget": self.counts_toward_budget}
