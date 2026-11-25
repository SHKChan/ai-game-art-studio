"""Encoding regression tests: the studio and the upstream Pixel Atelier code it uses must work on
non-UTF-8 locales (e.g. Windows GBK/cp936/cp1252). Simulated on POSIX with the C locale and UTF-8 mode off."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = dict(os.environ, LC_ALL="C", LANG="C", PYTHONCOERCECLOCALE="0", PYTHONUTF8="0")
LEGACY.pop("ARTSTUDIO_NO_UTF8_RELAUNCH", None)


class EncodingTests(unittest.TestCase):
    def test_no_locale_default_text_io_in_studio_code(self):
        bad = []
        for f in (ROOT / "artstudio").rglob("*.py"):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"read_text\(\)|text=True(?!.*encoding)", line):
                    bad.append(f"{f.relative_to(ROOT)}:{n}")
        self.assertEqual(bad, [])

    @unittest.skipIf(os.name == "nt", "POSIX locale simulation")
    def test_cli_relaunches_in_utf8_mode_under_legacy_locale(self):
        ws = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, "-X", "utf8=0", "-m", "artstudio", "--workspace", ws, "knight-sample", "--project", "p", "--actions", "idle"],
                           cwd=ROOT, env=LEGACY, capture_output=True)
        # project 'p' does not exist -> clean JSON error, never a UnicodeError
        self.assertNotIn(b"UnicodeDecodeError", r.stderr + r.stdout)
        r = subprocess.run([sys.executable, "-X", "utf8=0", "-m", "artstudio", "--workspace", ws, "project", "create", "\u5973\u9a91\u58eb RPG", "--id", "p"],
                           cwd=ROOT, env=LEGACY, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-500:])
        code = ("import sys; sys.path.insert(0, 'upstream/pixel-atelier/bridge'); from pathlib import Path; "
                "from projects import ProjectStore, create_knight; s = ProjectStore(Path(sys.argv[1])); "
                "p = s.save(create_knight(Path('upstream/pixel-atelier/examples/knight'))); print(s.get(p['id'])['spec']['identity'][:4])")
        broken = subprocess.run([sys.executable, "-X", "utf8=0", "-c", code, tempfile.mkdtemp()], cwd=ROOT, env=LEGACY, capture_output=True)
        fixed = subprocess.run([sys.executable, "-X", "utf8", "-c", code, tempfile.mkdtemp()], cwd=ROOT, env=LEGACY, capture_output=True)
        self.assertNotEqual(broken.returncode, 0, "expected upstream failure without UTF-8 mode (documents the bug)")
        self.assertEqual(fixed.returncode, 0, fixed.stderr.decode("utf-8", "replace")[-500:])


if __name__ == "__main__":
    unittest.main()
