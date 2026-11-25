"""Entry point. Runs the studio in Python UTF-8 mode (PEP 540) as a safety net: all studio code already
uses explicit UTF-8, but third-party code or user scripts may rely on locale defaults (GBK/cp936/cp1252)."""
import os
import subprocess
import sys

if not sys.flags.utf8_mode and os.environ.get("ARTSTUDIO_NO_UTF8_RELAUNCH") != "1":
    env = dict(os.environ, PYTHONUTF8="1", ARTSTUDIO_NO_UTF8_RELAUNCH="1")
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "artstudio", *sys.argv[1:]], env=env))

from .cli import main  # noqa: E402

sys.exit(main() or 0)
