"""Configuration: JSON file + ARTSTUDIO_* environment variables. No secrets are stored here."""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("artstudio")


def default_workspace() -> Path:
    # Generated assets live outside the application source tree by default.
    return APP_ROOT / "workspace"


@dataclass
class ComfyConfig:
    url: str = "http://127.0.0.1:8188"
    connect_timeout_s: float = 5.0
    job_timeout_s: float = 600.0
    poll_interval_s: float = 1.0
    use_websocket: bool = True
    api_key_env: str = ""  # optional name of an env var holding a bearer token (never stored in config)


@dataclass
class Config:
    workspace: str = ""
    host: str = "127.0.0.1"
    port: int = 8870
    ffmpeg_bin: str = ""
    comfyui: ComfyConfig = field(default_factory=ComfyConfig)
    # Default max paid/remote generation calls per unattended batch; batch jobs must set their own.
    default_generation_budget: int = 0
    log_level: str = "INFO"
    language: str = "en"            # en | zh-CN — CLI/API message language (UI chooses its own)
    prompt_language: str = "en"     # en | zh-CN — default generation prompt language
    codex_bin: str = ""             # path to the codex CLI (default: found on PATH, incl. codex.cmd on Windows)
    codex_timeout: int = 300        # seconds per Codex call (prompt writing / image generation)

    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace).expanduser().resolve() if self.workspace else default_workspace()

    def to_dict(self) -> dict:
        return asdict(self)


def _merge(cfg: Config, data: dict) -> None:
    for k, v in data.items():
        if k == "comfyui" and isinstance(v, dict):
            for ck, cv in v.items():
                if hasattr(cfg.comfyui, ck):
                    setattr(cfg.comfyui, ck, cv)
        elif hasattr(cfg, k):
            setattr(cfg, k, v)


def load_config(path: str | os.PathLike | None = None) -> Config:
    cfg = Config()
    candidates = [Path(path)] if path else [Path(os.environ.get("ARTSTUDIO_CONFIG", "")), APP_ROOT / "studio.config.json"]
    for c in candidates:
        if c and str(c) not in ("", ".") and c.is_file():
            _merge(cfg, json.loads(c.read_text(encoding="utf-8")))
            break
    env = os.environ
    if env.get("ARTSTUDIO_WORKSPACE"):
        cfg.workspace = env["ARTSTUDIO_WORKSPACE"]
    if env.get("ARTSTUDIO_HOST"):
        cfg.host = env["ARTSTUDIO_HOST"]
    if env.get("ARTSTUDIO_PORT"):
        cfg.port = int(env["ARTSTUDIO_PORT"])
    if env.get("ARTSTUDIO_FFMPEG"):
        cfg.ffmpeg_bin = env["ARTSTUDIO_FFMPEG"]
    if env.get("ARTSTUDIO_CODEX"):
        cfg.codex_bin = env["ARTSTUDIO_CODEX"]
    if env.get("ARTSTUDIO_LANG"):
        cfg.language = env["ARTSTUDIO_LANG"]
    if env.get("COMFYUI_URL"):
        cfg.comfyui.url = env["COMFYUI_URL"]
    if env.get("COMFYUI_TIMEOUT"):
        cfg.comfyui.job_timeout_s = float(env["COMFYUI_TIMEOUT"])
    return cfg


def find_ffmpeg(cfg: Config) -> str | None:
    if cfg.ffmpeg_bin and Path(cfg.ffmpeg_bin).is_file():
        return cfg.ffmpeg_bin
    return shutil.which("ffmpeg")


def setup_logging(level: str = "INFO") -> None:
    """Structured (key=value) logging to stderr."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
        stream=sys.stderr,
    )
