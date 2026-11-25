"""Provider registry. Availability is checked at runtime; nothing is substituted silently."""
from __future__ import annotations

from ..comfy.workflows import WorkflowLibrary
from ..config import APP_ROOT, Config, find_ffmpeg
from .procedural import ProceduralProvider
from .base import GenerationError, GenerationRequest, GenerationResult, JobContext, Provider, ProviderStatus
from .comfyui import ComfyUIProvider
from .others import CodexImageProvider, ExternalAssetProvider, MockGenerationProvider

# Extension points (see docs/integration-architecture.md): ExternalAPIProvider, ImageToVideoProvider,
# SkeletonAnimationProvider and additional MCP art tools implement the same Provider interface and
# are registered here. They are intentionally not implemented without a documented, verifiable API.


class Registry:
    def __init__(self, cfg: Config, workspace_root, enable_mock: bool = True):
        self.cfg = cfg
        self.workflows = WorkflowLibrary(APP_ROOT / "workflows" / "comfyui", workspace_root / "comfyui" / "workflows")
        self.providers: dict[str, Provider] = {
            "procedural": ProceduralProvider(),
            "comfyui": ComfyUIProvider(cfg.comfyui, self.workflows),
            "external": ExternalAssetProvider(find_ffmpeg(cfg)),
            "codex": CodexImageProvider(),
        }
        if enable_mock:
            self.providers["mock"] = MockGenerationProvider()

    def get(self, pid: str) -> Provider:
        if pid not in self.providers:
            raise GenerationError(f"Unknown provider {pid}", "bad_request")
        return self.providers[pid]

    def describe(self) -> list[dict]:
        return [p.describe() for p in self.providers.values()]


__all__ = ["Registry", "Provider", "ProviderStatus", "GenerationRequest", "GenerationResult", "JobContext", "GenerationError"]
