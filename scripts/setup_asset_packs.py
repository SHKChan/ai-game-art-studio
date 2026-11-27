"""Install downloaded asset-pack ZIPs where the studio's pack importer looks for them.

    python scripts/setup_asset_packs.py <zip> [<zip> …] [--dest assets_local/packs]

Recognised packs (detected from the ZIP contents, file names do not matter):
  tiny-rpg          Tiny RPG Character Asset Pack 01 / 02 (Zerie): Soldier, Orc, Demon_A, Blood Monster_A
  craftpix-dungeon  Craftpix "Free 2D Top-Down Pixel Dungeon Asset Pack"
  pvfx-foundry      PVFX Foundry 1.x effect sheets (CC0) — only the grid sheets + manifests are kept

The destination is git-ignored. Zerie's and Craftpix's art may be used in your games but not redistributed, so it must
never be committed or published with the studio. Then import in the UI (Library → Asset packs) or with
`python -m artstudio packs import --project <id> --pack <pack>`."""
from __future__ import annotations

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _safe(rel: str) -> bool:
    p = Path(rel)
    return bool(rel) and not p.is_absolute() and ".." not in p.parts and "__MACOSX" not in p.parts


def plan_tiny_rpg(names: list[str]):
    """Characters(100x100 split)/<Char>/… and Aseprite file/… → tiny-rpg/<Char>/…, tiny-rpg/_aseprite/…"""
    for n in names:
        m = re.search(r"Characters\(100x100 split\)/(.+)$", n)
        if m and n.lower().endswith(".png"):
            yield n, m.group(1)
        m = re.search(r"Aseprite file/([^/]+\.aseprite)$", n)
        if m:
            yield n, "_aseprite/" + m.group(1)


def plan_dungeon(names: list[str]):
    for n in names:
        m = re.search(r"(?:^|/)((?:PNG|Tiled_files)/[^/]+\.(?:png|tmx|tsx)|license\.txt|readme\.txt)$", n)
        if m:
            yield n, m.group(1)


def plan_pvfx(names: list[str]):
    keep_top = {"pack.json", "LICENSE.txt", "README.md", "FORMAT.md", "IMPORTING.md", "THIRD_PARTY_NOTICES.txt", "VERSION",
                "PROVENANCE.json", "CHANGELOG.md"}
    prefix = next((n[: -len("pack.json")] for n in names if n.endswith("pack.json") and "legacy/" not in n), "")
    for n in names:
        if not n.startswith(prefix):
            continue
        rel = n[len(prefix):]
        if rel in keep_top or (rel.startswith("effects/") and "/grid/" in rel and rel.rsplit("/", 1)[-1] in ("sprite-sheet.png", "manifest.json")):
            yield n, rel


def detect(names: list[str]) -> str | None:
    if any("Characters(100x100 split)/" in n for n in names):
        return "tiny-rpg"
    if any(n.endswith("Tiled_files/Dungeon1.tmx") for n in names) or any(n.endswith("PNG/walls_floor.png") for n in names):
        return "craftpix-dungeon"
    if any(n.endswith("pack.json") for n in names) and any("/grid/sprite-sheet.png" in n for n in names):
        return "pvfx-foundry"
    return None


PLANS = {"tiny-rpg": plan_tiny_rpg, "craftpix-dungeon": plan_dungeon, "pvfx-foundry": plan_pvfx}


def install(zpath: Path, dest: Path) -> tuple[str, int]:
    with zipfile.ZipFile(zpath) as z:
        names = [i.filename.replace("\\", "/") for i in z.infolist() if not i.is_dir()]
        pack = detect(names)
        if pack is None:
            raise SystemExit(f"{zpath.name}: not a recognised asset pack")
        n = 0
        for src, rel in PLANS[pack](names):
            if not _safe(src) or not _safe(rel):
                continue
            out = dest / pack / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(src))
            n += 1
    os.utime(dest / pack)   # bump mtime so a running studio re-reads the item list
    return pack, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("zips", nargs="+", type=Path)
    ap.add_argument("--dest", type=Path, default=ROOT / "assets_local" / "packs")
    a = ap.parse_args(argv)
    for z in a.zips:
        if not z.is_file():
            raise SystemExit(f"Not found: {z}")
        pack, n = install(z, a.dest)
        print(f"{z.name}: {pack} — {n} files → {a.dest / pack}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
