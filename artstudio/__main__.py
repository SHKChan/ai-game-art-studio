"""Entry point. Re-launches itself in Python UTF-8 mode when needed.

Upstream Pixel Atelier (used as a library) reads/writes Chinese JSON with the *locale default* encoding.
On Windows that is GBK/cp936 or cp1252 and leads to UnicodeEncode/DecodeError or GBK files that other
machines cannot read. UTF-8 mode (PEP 540) makes every default text encoding UTF-8 without touching upstream.
"""
import os
import subprocess
import sys

if not sys.flags.utf8_mode and os.environ.get("ARTSTUDIO_NO_UTF8_RELAUNCH") != "1":
    env = dict(os.environ, PYTHONUTF8="1", ARTSTUDIO_NO_UTF8_RELAUNCH="1")
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "artstudio", *sys.argv[1:]], env=env))

from .cli import main  # noqa: E402

sys.exit(main() or 0)
