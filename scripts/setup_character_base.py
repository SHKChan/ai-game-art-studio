"""Unzip the Craftpix "Free Base 4-Direction Male/Female Character" packs where the character kit looks for them.

    python scripts/setup_character_base.py <male.zip> <female.zip> [--dest assets_local/craftpix-base]

Only PNG/, ASEPRITE/ and License.txt are extracted. The destination is git-ignored: the Craftpix free licence allows
using the art in your games but not redistributing it, so it must never be committed or published with the studio."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = ("PNG/", "ASEPRITE/", "License.txt")


def sex_of(path: Path, default: str) -> str:
    n = path.name.lower()
    return "female" if "female" in n else ("male" if "male" in n else default)


def extract(zpath: Path, dest: Path) -> int:
    n = 0
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or not name.startswith(KEEP) or ".." in Path(name).parts:
                continue
            out = dest / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(info))
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("zips", nargs=2, type=Path, help="male zip, female zip (order is guessed from the file names)")
    ap.add_argument("--dest", type=Path, default=ROOT / "assets_local" / "craftpix-base")
    a = ap.parse_args(argv)
    for z, default in zip(a.zips, ("male", "female")):
        sex = sex_of(z, default)
        n = extract(z, a.dest / sex)
        print(f"{sex}: {n} files → {a.dest / sex}")
    sys.path.insert(0, str(ROOT))
    import os
    os.environ.setdefault("ARTSTUDIO_CHARKIT_DIR", str(a.dest))
    from artstudio.charkit import available
    print("character kit ready" if available() else "WARNING: pack layout not recognised (expected PNG/<Action>/…)")


if __name__ == "__main__":
    main()
