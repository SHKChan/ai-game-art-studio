"""Encoding regression tests. All studio text I/O is explicit UTF-8, so Chinese/English data must work on
non-UTF-8 locales (Windows GBK/cp936/cp1252). Simulated on POSIX with the C locale, UTF-8 mode OFF and
the safety-net relaunch DISABLED — i.e. the code itself must be correct."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = dict(os.environ, LC_ALL="C", LANG="C", PYTHONCOERCECLOCALE="0", PYTHONUTF8="0", ARTSTUDIO_NO_UTF8_RELAUNCH="1")
LEGACY.pop("PYTHONIOENCODING", None)


class EncodingTests(unittest.TestCase):
    def test_no_locale_default_text_io(self):
        bad = []
        for f in list((ROOT / "artstudio").rglob("*.py")) + list((ROOT / "mock_comfyui").rglob("*.py")):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"read_text\(\)|write_text\([^)]*\)\s*$|text=True(?!.*encoding)", line) and "encoding" not in line:
                    bad.append(f"{f.relative_to(ROOT)}:{n}")
                if re.search(r"\bopen\([^)]*['\"][rwa]\+?['\"]", line) and "encoding" not in line and "Image.open" not in line:
                    bad.append(f"{f.relative_to(ROOT)}:{n}")
        self.assertEqual(bad, [])

    @unittest.skipIf(os.name == "nt", "POSIX locale simulation")
    def test_chinese_data_on_legacy_locale_without_utf8_mode(self):
        ws = tempfile.mkdtemp()
        base = [sys.executable, "-X", "utf8=0", "-m", "artstudio", "--workspace", ws]

        def run(*args, expect=0):
            r = subprocess.run(base + list(args), cwd=ROOT, env=LEGACY, capture_output=True)
            self.assertNotIn(b"UnicodeDecodeError", r.stderr)
            self.assertNotIn(b"UnicodeEncodeError", r.stderr)
            self.assertEqual(r.returncode, expect, r.stderr.decode("utf-8", "replace")[-800:])
            return r
        run("project", "create", "女骑士 RPG", "--id", "p")
        run("character", "create", "--project", "p", "--name", "芽耳兽", "--directions", "four",
            "--patch", '{"description": "红色兜帽的冒险者", "clothing": ["红色披风"]}')
        run("knight-sample", "--project", "p", "--actions", "idle")
        run("procedural", "potion", "--project", "p", "--name", "生命药水")
        r = run("--lang", "zh-CN", "project", "show", "missing", expect=2)  # clean, localised error
        self.assertIn("项目不存在".encode("utf-8"), r.stdout)
        code = ("import sys; from artstudio.adapters import sheet_prompt_zh; from artstudio.pipeline.spritepipe import init_project, build_project; "
                "p = sheet_prompt_zh('\\u9a91\\u58eb', 'idle'); r = build_project(init_project(sys.argv[1], demo=True) and sys.argv[1]); "
                "print(r['status'])")
        r = subprocess.run([sys.executable, "-X", "utf8=0", "-c", code, str(Path(tempfile.mkdtemp()) / "sp")], cwd=ROOT, env=LEGACY, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-800:])
        self.assertIn(b"TECHNICAL_VERIFIED", r.stdout)


if __name__ == "__main__":
    unittest.main()
