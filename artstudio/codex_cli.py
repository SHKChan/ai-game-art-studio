"""Locating and running the Codex CLI (a logged-in `codex`; no API keys are handled here).

Two uses:
  * `exec_text` — `codex exec` non-interactively: read a reference image and answer in text (prompt writing).
  * `app_server_command` — the command for the app-server image bridge (`providers/codex_rpc.py`).

Windows: npm installs `codex.cmd`; `shutil.which` resolves it and it is started with a fixed argument list.
The prompt is passed on stdin (UTF-8), never on the command line, so long Chinese/English text is safe.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("artstudio.codex")


class CodexError(RuntimeError):
    pass


def resolve(codex_bin: str = "") -> list[str] | None:
    """Command prefix for the codex CLI, or None when it is not installed.
    `codex_bin` may be a path or a command line (e.g. "python fake_codex.py" in tests)."""
    raw = codex_bin or os.environ.get("ARTSTUDIO_CODEX", "")
    if raw:
        parts = shlex.split(raw, posix=os.name != "nt") if (" " in raw and not Path(raw).exists()) else [raw]
        exe = shutil.which(parts[0]) or (parts[0] if Path(parts[0]).exists() else None)
        return [exe, *parts[1:]] if exe else None
    exe = shutil.which("codex")
    return [exe] if exe else None


def exec_text(prompt: str, images: list[Path] | None = None, *, codex_bin: str = "", timeout: int = 300,
              cancel_check=None) -> str:
    """Run `codex exec` read-only with optional images; return the final agent message."""
    cmd = resolve(codex_bin)
    if not cmd:
        raise CodexError("codex CLI not found (install it and run `codex login`, or set codex_bin)")
    with tempfile.TemporaryDirectory(prefix="artstudio-codex-") as tmp:
        out = Path(tmp) / "last_message.txt"
        args = [*cmd, "exec", "-", "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
                "--output-last-message", str(out)]
        for im in images or []:
            args += ["--image", str(Path(im).resolve())]
        log.info("codex exec images=%d chars=%d", len(images or []), len(prompt))
        try:
            proc = subprocess.Popen(args, cwd=tmp, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", errors="replace")
        except OSError as e:
            raise CodexError(f"could not start codex: {e}") from e
        try:
            stdout, stderr = proc.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise CodexError(f"codex exec timed out after {timeout}s")
        if cancel_check:
            cancel_check()
        text = out.read_text(encoding="utf-8") if out.is_file() else ""
        if proc.returncode != 0 and not text.strip():
            tail = (stderr or stdout or "").strip()[-800:]
            raise CodexError(f"codex exec failed (exit {proc.returncode}): {tail}")
        return text.strip() or (stdout or "").strip()


def app_server_command(codex_bin: str = "") -> list[str]:
    cmd = resolve(codex_bin)
    if not cmd:
        raise CodexError("codex CLI not found")
    return [*cmd, "app-server", "--listen", "stdio://"]


def extract_json(text: str):
    """First JSON object in a model answer (tolerates ```json fences and prose around it)."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fence.group(1)] if fence else []
    start = text.find("{")
    if start >= 0:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    for c in candidates:
        try:
            return json.loads(c)
        except ValueError:
            continue
    raise CodexError("Codex did not return valid JSON")
