"""Local workspace persistence: projects, characters, assets, versions, backups.

Layout (all JSON is atomic-written; binary art is plain PNG):

  <workspace>/studio.json
  <workspace>/projects/<pid>/project.json
  <workspace>/projects/<pid>/characters/<cid>/character.json   (+ masters/, candidates/)
  <workspace>/projects/<pid>/assets/<aid>/asset.json           (+ source/, frames/, versions/)
  <workspace>/projects/<pid>/exports/<eid>/...
  <workspace>/projects/<pid>/engine/                            (pixel engine document store)
  <workspace>/jobs/<jid>.json
  <workspace>/comfyui/workflows/<wid>.json
"""
from __future__ import annotations

import copy
import json
import shutil
import threading
import zipfile
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .schema import require_valid
from .tagging import normalize_tags
from .util import StudioError, check_id, new_id, now, read_json, safe_join, sha256_file, slug, write_json

DIRECTION_SETS = {
    "side2": ["right", "left"],
    "four": ["south", "east", "north", "west"],
    "eight": ["south", "south_east", "east", "north_east", "north", "north_west", "west", "south_west"],
}
MIRROR_PAIRS = {"left": "right", "west": "east", "north_west": "north_east", "south_west": "south_east"}

_LOCK = threading.RLock()


class Conflict(StudioError):
    pass


class Workspace:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        meta = self.root / "studio.json"
        if not meta.exists():
            write_json(meta, {"format": "ai-game-art-studio-workspace", "schema_version": SCHEMA_VERSION,
                              "app_version": __version__, "created_at": now()})
        else:
            self.migrate()
        for d in ("projects", "jobs", "comfyui/workflows", "tmp"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

    # ---------- migration / backup ----------
    def migrate(self) -> dict:
        meta = read_json(self.root / "studio.json")
        v = meta.get("schema_version", 0)
        if v > SCHEMA_VERSION:
            raise StudioError(f"Workspace schema {v} is newer than this app ({SCHEMA_VERSION}); upgrade the app.")
        if v < SCHEMA_VERSION:  # future migrations chain here: v0 -> v1 ...
            meta["schema_version"] = SCHEMA_VERSION
            meta["migrated_at"] = now()
            write_json(self.root / "studio.json", meta)
        return meta

    def backup(self, dest: Path, include_exports: bool = True) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for f in self.root.rglob("*"):
                rel = f.relative_to(self.root)
                if not f.is_file() or rel.parts[0] == "tmp" or ".store.lock" in f.name:
                    continue
                if not include_exports and "exports" in rel.parts:
                    continue
                z.write(f, str(rel))
        return dest

    @staticmethod
    def restore(archive: Path, target: Path) -> "Workspace":
        target = Path(target)
        if target.exists() and any(target.iterdir()):
            raise StudioError("Restore target must be empty")
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                safe_join(target, *Path(name).parts)  # refuse traversal entries
            z.extractall(target)
        return Workspace(target)

    # ---------- projects ----------
    def project_dir(self, pid: str) -> Path:
        return safe_join(self.root / "projects", check_id(pid, "project id"))

    def list_projects(self) -> list[dict]:
        out = []
        for f in sorted((self.root / "projects").glob("*/project.json")):
            p = read_json(f)
            p["counts"] = {"assets": len(list((f.parent / "assets").glob("*/asset.json"))),
                           "characters": len(list((f.parent / "characters").glob("*/character.json")))}
            out.append(p)
        return sorted(out, key=lambda p: p.get("updated_at", 0), reverse=True)

    def create_project(self, name: str, game: str = "", genre: str = "", default_style: str = "pixel",
                       pid: str | None = None) -> dict:
        if not name or len(name) > 120:
            raise StudioError("Project name must be 1-120 characters")
        if default_style not in ("pixel", "hd"):
            raise StudioError("default_style must be pixel or hd")
        pid = check_id(pid) if pid else slug(name) + "-" + new_id()[:6]
        d = self.project_dir(pid)
        if d.exists():
            raise StudioError("Project already exists")
        p = {"schema_version": SCHEMA_VERSION, "id": pid, "name": name, "game": game, "genre": genre,
             "default_style": default_style, "prompt_language": "en", "created_at": now(), "updated_at": now()}
        for sub in ("assets", "characters", "exports", "engine"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        write_json(d / "project.json", p)
        return p

    def get_project(self, pid: str) -> dict:
        f = self.project_dir(pid) / "project.json"
        if not f.is_file():
            raise StudioError(f"Unknown project {pid}")
        return read_json(f)

    def trash_project(self, pid: str, confirm: str | None = None) -> dict:
        """Delete a project by moving its folder to <workspace>/_trash/ (recoverable: move it back into projects/).
        `confirm` must equal the project's name (or id) so a stray click cannot delete it."""
        import time
        p = self.get_project(pid)
        if confirm is not None and confirm.strip() not in (p["name"], pid):
            raise StudioError("Type the project name exactly to confirm deletion", code="confirm_mismatch")
        dest_root = self.root / "_trash"
        dest_root.mkdir(parents=True, exist_ok=True)
        dest = dest_root / f"{pid}-{time.strftime('%Y%m%d-%H%M%S')}"
        n = 1
        while dest.exists():
            n += 1
            dest = dest_root / f"{pid}-{time.strftime('%Y%m%d-%H%M%S')}-{n}"
        src = self.project_dir(pid)
        for attempt in range(5):            # Windows: a file viewer / antivirus may hold a handle for a moment
            try:
                shutil.move(str(src), str(dest))
                break
            except PermissionError:
                if attempt == 4:
                    raise StudioError("A file in this project is in use (close any viewer and try again)", code="in_use")
                time.sleep(0.4)
        return {"deleted": pid, "name": p["name"], "trash": str(dest)}

    def update_project(self, pid: str, patch: dict) -> dict:
        allowed = {"name", "game", "genre", "default_style", "prompt_language"}
        bad = set(patch) - allowed
        if bad:
            raise StudioError(f"Fields not editable: {sorted(bad)}")
        if "prompt_language" in patch and patch["prompt_language"] not in ("en", "zh-CN"):
            raise StudioError("prompt_language must be en or zh-CN")
        p = self.get_project(pid)
        p.update(patch)
        p["updated_at"] = now()
        write_json(self.project_dir(pid) / "project.json", p)
        return p

    def engine_home(self, pid: str) -> Path:
        d = self.project_dir(pid) / "engine"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---------- characters ----------
    def char_dir(self, pid: str, cid: str) -> Path:
        return safe_join(self.project_dir(pid), "characters", check_id(cid, "character id"))

    def create_character(self, pid: str, name: str, direction_mode: str = "four", art_style: str = "pixel",
                         **fields) -> dict:
        self.get_project(pid)
        if direction_mode not in DIRECTION_SETS:
            raise StudioError("direction_mode must be side2, four or eight")
        cid = fields.pop("cid", None) or slug(name) + "-" + new_id()[:6]
        c = {"schema_version": SCHEMA_VERSION, "id": cid, "project_id": pid, "name": name,
             "description": fields.get("description", ""), "art_style": art_style,
             "visual_style": fields.get("visual_style", ""), "camera": fields.get("camera", "three_quarter" if direction_mode != "side2" else "side"),
             "direction_mode": direction_mode, "directions": list(DIRECTION_SETS[direction_mode]),
             "mirroring": {"enabled": bool(fields.get("mirroring", False)), "pairs": {}},
             "proportions": fields.get("proportions", {}), "palette": fields.get("palette", []), "palette_frozen": False,
             "clothing": fields.get("clothing", []), "accessories": fields.get("accessories", []),
             "weapon": fields.get("weapon", {}), "constraints": fields.get("constraints", []),
             "negative_constraints": fields.get("negative_constraints", []), "concept_art": [],
             "masters": {}, "candidates": [], "history": [], "created_at": now(), "updated_at": now()}
        if c["mirroring"]["enabled"]:
            c["mirroring"]["pairs"] = {k: v for k, v in MIRROR_PAIRS.items() if k in c["directions"]}
        require_valid(c, "character")
        d = self.char_dir(pid, cid)
        for sub in ("masters", "candidates", "concept"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        write_json(d / "character.json", c)
        return c

    def list_characters(self, pid: str) -> list[dict]:
        return [read_json(f) for f in sorted((self.project_dir(pid) / "characters").glob("*/character.json"))]

    def get_character(self, pid: str, cid: str) -> dict:
        f = self.char_dir(pid, cid) / "character.json"
        if not f.is_file():
            raise StudioError(f"Unknown character {cid}")
        return read_json(f)

    def save_character(self, c: dict) -> dict:
        with _LOCK:
            old = self.get_character(c["project_id"], c["id"])
            for direction, m in old.get("masters", {}).items():
                new = c.get("masters", {}).get(direction)
                if m.get("locked") and (new is None or new.get("file") != m["file"]) and not c.get("_replace_locked"):
                    raise Conflict(f"Master '{direction}' is locked; use replace_master explicitly.")
            c.pop("_replace_locked", None)
            c["updated_at"] = now()
            require_valid(c, "character")
            write_json(self.char_dir(c["project_id"], c["id"]) / "character.json", c)
            return c

    def update_character(self, pid: str, cid: str, patch: dict) -> dict:
        allowed = {"name", "description", "visual_style", "camera", "proportions", "palette", "palette_frozen",
                   "clothing", "accessories", "weapon", "constraints", "negative_constraints", "mirroring", "art_style"}
        bad = set(patch) - allowed
        if bad:
            raise StudioError(f"Fields not editable: {sorted(bad)}")
        c = self.get_character(pid, cid)
        c.update(copy.deepcopy(patch))
        c["history"].append({"at": now(), "event": "updated", "fields": sorted(patch)})
        return self.save_character(c)

    def add_character_image(self, pid: str, cid: str, image_path: Path, kind: str, direction: str = "primary",
                            note: str = "", is_test_fixture: bool = False, source_asset: str | None = None) -> dict:
        """kind: concept | candidate. Copies the image into the character folder."""
        c = self.get_character(pid, cid)
        d = self.char_dir(pid, cid)
        sub = "concept" if kind == "concept" else "candidates"
        name = new_id(kind[:4]) + ".png"
        dst = d / sub / name
        shutil.copyfile(image_path, dst)
        rel = f"{sub}/{name}"
        if kind == "concept":
            c["concept_art"].append(rel)
        else:
            if direction != "primary" and direction not in c["directions"]:
                raise StudioError(f"Direction {direction} not in {c['directions']}")
            c["candidates"].append({"id": name[:-4], "file": rel, "direction": direction, "status": "candidate",
                                    "note": note, "created_at": now(), "is_test_fixture": is_test_fixture,
                                    "source_asset": source_asset})
        c["history"].append({"at": now(), "event": f"{kind}_added", "file": rel, "direction": direction})
        return self.save_character(c)

    def review_candidate(self, pid: str, cid: str, cand_id: str, decision: str, note: str = "") -> dict:
        if decision not in ("approved", "rejected"):
            raise StudioError("decision must be approved or rejected")
        c = self.get_character(pid, cid)
        cand = next((x for x in c["candidates"] if x["id"] == cand_id), None)
        if not cand:
            raise StudioError("Unknown candidate")
        cand["status"] = decision
        cand["review_note"] = note
        c["history"].append({"at": now(), "event": f"candidate_{decision}", "candidate": cand_id, "note": note})
        if decision == "approved":
            direction = cand["direction"]
            current = c["masters"].get(direction)
            if current and current.get("locked"):
                raise Conflict(f"Master '{direction}' is locked. Use replace_master to replace it explicitly.")
            self._set_master(c, direction, cand)
        return self.save_character(c)

    def _set_master(self, c: dict, direction: str, cand: dict) -> None:
        d = self.char_dir(c["project_id"], c["id"])
        dst = d / "masters" / f"{direction}-{new_id()[:6]}.png"
        shutil.copyfile(d / cand["file"], dst)
        c["masters"][direction] = {"file": f"masters/{dst.name}", "locked": True, "approved_at": now(),
                                   "source_asset": cand.get("source_asset"), "candidate": cand["id"],
                                   "is_test_fixture": bool(cand.get("is_test_fixture")), "sha256": sha256_file(dst)}
        c["history"].append({"at": now(), "event": "master_locked", "direction": direction, "file": c["masters"][direction]["file"]})

    def replace_master(self, pid: str, cid: str, direction: str, cand_id: str, reason: str) -> dict:
        if not reason:
            raise StudioError("Replacing a locked master requires a reason")
        c = self.get_character(pid, cid)
        cand = next((x for x in c["candidates"] if x["id"] == cand_id), None)
        if not cand or cand["direction"] != direction:
            raise StudioError("Candidate not found for that direction")
        old = c["masters"].get(direction)
        c["history"].append({"at": now(), "event": "master_replaced", "direction": direction,
                             "previous": old and old["file"], "reason": reason})
        cand["status"] = "approved"
        self._set_master(c, direction, cand)
        c["_replace_locked"] = True
        return self.save_character(c)

    def unlock_master(self, pid: str, cid: str, direction: str, reason: str) -> dict:
        if not reason:
            raise StudioError("Unlocking requires a reason")
        c = self.get_character(pid, cid)
        if direction not in c["masters"]:
            raise StudioError("No master for that direction")
        c["masters"][direction]["locked"] = False
        c["history"].append({"at": now(), "event": "master_unlocked", "direction": direction, "reason": reason})
        return self.save_character(c)

    def missing_directions(self, c: dict) -> list[str]:
        mirrored = c["mirroring"]["pairs"] if c["mirroring"].get("enabled") else {}
        return [d for d in c["directions"] if d not in c["masters"] and mirrored.get(d) not in c["masters"]]

    # ---------- assets ----------
    def asset_dir(self, pid: str, aid: str) -> Path:
        return safe_join(self.project_dir(pid), "assets", check_id(aid, "asset id"))

    def new_asset(self, pid: str, type_: str, name: str, art_style: str, provider: dict, **fields) -> dict:
        self.get_project(pid)
        aid = fields.pop("aid", None) or slug(name) + "-" + new_id()[:6]
        a = {"schema_version": SCHEMA_VERSION, "id": aid, "type": type_, "name": name, "project_id": pid,
             "character_id": fields.get("character_id"), "art_style": art_style, "tags": normalize_tags(fields.get("tags", [])),
             "provider": provider, "prompt": fields.get("prompt"), "reference_images": fields.get("reference_images", []),
             "source_files": [], "processed_files": [], "processing": fields.get("processing", {}),
             "procedural": fields.get("procedural"), "versions": [], "status": "draft",
             "qa": {"deterministic": {"status": "not_run"}, "visual": {"status": "not_run", "kind": "probabilistic", "notes": ""},
                    "manual": {"decision": "pending", "note": "", "at": None}},
             "exports": [], "created_at": now(), "updated_at": now()}
        if fields.get("animation") is not None:
            a["animation"] = fields["animation"]
        d = self.asset_dir(pid, aid)
        for sub in ("source", "frames", "versions"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        require_valid(a, "asset")
        write_json(d / "asset.json", a)
        return a

    def get_asset(self, pid: str, aid: str) -> dict:
        f = self.asset_dir(pid, aid) / "asset.json"
        if not f.is_file():
            raise StudioError(f"Unknown asset {aid}")
        return read_json(f)

    def list_assets(self, pid: str, type_: str | None = None, character_id: str | None = None) -> list[dict]:
        out = []
        for f in sorted((self.project_dir(pid) / "assets").glob("*/asset.json")):
            a = read_json(f)
            if (type_ and a["type"] != type_) or (character_id and a.get("character_id") != character_id):
                continue
            out.append(a)
        return sorted(out, key=lambda a: a["updated_at"], reverse=True)

    def save_asset(self, a: dict, snapshot_note: str | None = None, expected_updated_at: float | None = None) -> dict:
        with _LOCK:
            d = self.asset_dir(a["project_id"], a["id"])
            if expected_updated_at is not None:
                cur = read_json(d / "asset.json")
                if abs(cur["updated_at"] - expected_updated_at) > 1e-6:
                    raise Conflict("Asset was modified elsewhere; reload before saving.")
            if snapshot_note is not None:
                self._snapshot(a, d, snapshot_note)
            a["updated_at"] = now()
            a["tags"] = normalize_tags(a.get("tags"))   # English-only search tags
            require_valid(a, "asset")
            write_json(d / "asset.json", a)
            return a

    def _snapshot(self, a: dict, d: Path, note: str) -> None:
        """Version history: copy manifest + current frames into versions/vN (reversible edits)."""
        v = (a["versions"][-1]["version"] + 1) if a["versions"] else 1
        vd = d / "versions" / f"v{v}"
        vd.mkdir(parents=True, exist_ok=True)
        for sub in ("frames", "patches"):
            if (d / sub).is_dir():
                shutil.copytree(d / sub, vd / sub, dirs_exist_ok=True)
        prev = d / "asset.json"
        if prev.exists():
            shutil.copyfile(prev, vd / "asset.json")
        a["versions"].append({"version": v, "created_at": now(), "note": note, "snapshot": f"versions/v{v}"})

    def restore_version(self, pid: str, aid: str, version: int) -> dict:
        d = self.asset_dir(pid, aid)
        vd = d / "versions" / f"v{int(version)}"
        if not (vd / "asset.json").is_file():
            raise StudioError("Unknown version")
        cur = self.get_asset(pid, aid)
        self._snapshot(cur, d, f"before restore of v{version}")
        old = read_json(vd / "asset.json")
        old["versions"] = cur["versions"]
        for sub in ("frames", "patches"):
            if (vd / sub).is_dir():
                shutil.rmtree(d / sub, ignore_errors=True)
                shutil.copytree(vd / sub, d / sub)
        return self.save_asset(old)

    def delete_asset(self, pid: str, aid: str) -> None:
        d = self.asset_dir(pid, aid)
        trash = self.root / "tmp" / "trash" / f"{pid}--{aid}-{new_id()[:6]}"
        trash.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(trash))  # recoverable

    def set_decision(self, pid: str, aid: str, decision: str, note: str = "") -> dict:
        if decision not in ("approved", "rejected", "pending"):
            raise StudioError("decision must be approved, rejected or pending")
        a = self.get_asset(pid, aid)
        a["qa"]["manual"] = {"decision": decision, "note": note, "at": now()}
        a["status"] = {"approved": "approved", "rejected": "rejected", "pending": "candidate"}[decision]
        return self.save_asset(a)

    def add_file(self, a: dict, path: Path, kind: str, role: str, origin: str) -> dict:
        """Register a file already inside the asset directory."""
        d = self.asset_dir(a["project_id"], a["id"])
        rel = Path(path).resolve().relative_to(d).as_posix()
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        rec = {"path": rel, "sha256": sha256_file(path), "role": role, "origin": origin, "width": w, "height": h}
        key = "source_files" if kind == "source" else "processed_files"
        a[key] = [x for x in a[key] if x["path"] != rel] + [rec]
        return rec

    def export_dir(self, pid: str, eid: str | None = None) -> Path:
        eid = eid or new_id("exp")
        d = safe_join(self.project_dir(pid), "exports", check_id(eid))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def summary(self) -> dict:
        return {"root": str(self.root), "meta": read_json(self.root / "studio.json"),
                "projects": len(list((self.root / "projects").glob("*/project.json")))}


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
