"""Run the studio's offline test suite (Stage A): unit, engine, pipeline, encoding and integration tests
(mock ComfyUI runs in-process).   python scripts/run_tests.py
"""
import subprocess
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore", DeprecationWarning)
sys.path.insert(0, str(ROOT / "tests"))
suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT / "tests"))
res = unittest.TextTestRunner(verbosity=1).run(suite)
code = 0 if res.wasSuccessful() else 1
sys.exit(code)
