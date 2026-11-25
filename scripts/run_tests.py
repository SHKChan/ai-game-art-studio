"""Run the studio's offline test suite (Stage A). Atelier-dependent tests skip if the binary is missing.
  python scripts/run_tests.py            unit + integration (mock ComfyUI)
  python scripts/run_tests.py --upstream also run Pixel Atelier's own tests
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
if "--upstream" in sys.argv:
    print("\n== upstream/pixel-atelier tests ==")
    code |= subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT / "upstream" / "pixel-atelier")
sys.exit(code)
