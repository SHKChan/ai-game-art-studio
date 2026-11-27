"""Local web server for the Visual Animation Laboratory (stdlib only).

Security: binds to loopback by default; Host header allow-list; per-process session token in an
HttpOnly SameSite=Strict cookie required for /api and /files; Origin check on writes; request size
limits; all file access through safe_join; no shell execution from UI input (subprocesses use fixed
argument lists for ffmpeg only).
"""
from __future__ import annotations

import http.cookies
import json
import logging
import mimetypes
import re
import secrets
import shutil
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .. import __version__
from ..animation import clear_patch, edit_frames, reprocess, replace_frame, save_frame_edits, template_info
from ..i18n import localize, localize_exc, normalize
from ..providers.base import GenerationError
from ..qa import check_asset
from ..qa.visual import record_visual_review
from ..util import StudioError, decode_data_url, new_id, open_image_bytes, read_json, safe_join
from ..workspace import Conflict

log = logging.getLogger("artstudio.server")
WEB = Path(__file__).resolve().parents[1] / "web"
MAX_BODY = 200 * 1024 * 1024
TOKEN = secrets.token_urlsafe(32)
ROUTES: list[tuple[str, re.Pattern, callable]] = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


def _save_upload(studio, name: str, data: str) -> Path:
    raw = decode_data_url(data)
    ext = Path(name or "upload.png").suffix.lower()
    if ext not in (".png", ".gif", ".apng", ".webp", ".jpg", ".jpeg", ".mp4", ".webm", ".mov", ".json", ".recipe"):
        raise StudioError(f"Unsupported file type {ext}")
    d = studio.ws.root / "tmp" / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (new_id("up") + ext)
    p.write_bytes(raw)
    return p


# ------------------------------------------------------------------ API routes
@route("GET", r"/api/status")
def api_status(s, h, m, q, body):
    return {"version": __version__, **s.status()}


@route("GET", r"/api/providers")
def api_providers(s, h, m, q, body):
    return s.registry.describe()


@route("GET", r"/api/templates")
def api_templates(s, h, m, q, body):
    from ..procedural import BUILDERS
    return {"animations": template_info(),
            "builders": {k: {"description": b.DESCRIPTION, "params": b.PARAMS, "asset_type": b.ASSET_TYPE} for k, b in BUILDERS.items()}}


@route("GET", r"/api/projects")
def api_projects(s, h, m, q, body):
    return s.ws.list_projects()


@route("POST", r"/api/projects")
def api_create_project(s, h, m, q, body):
    return s.ws.create_project(body["name"], body.get("game", ""), body.get("genre", ""), body.get("default_style", "pixel"))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/settings")
def api_project_settings(s, h, m, q, body):
    return s.ws.update_project(m["pid"], body)


@route("DELETE", r"/api/projects/(?P<pid>[a-z0-9_-]+)")
def api_delete_project(s, h, m, q, body):
    busy = [j for j in s.jobs.list(1000, m["pid"]) if j["status"] in ("queued", "running")]
    if busy:
        raise StudioError("This project has queued or running jobs — wait for them or cancel them first", code="project_busy")
    return s.ws.trash_project(m["pid"], (body or {}).get("confirm", ""))


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)")
def api_project(s, h, m, q, body):
    pid = m["pid"]
    return {"project": s.ws.get_project(pid), "assets": s.ws.list_assets(pid), "characters": s.ws.list_characters(pid)}


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)")
def api_asset(s, h, m, q, body):
    return s.ws.get_asset(m["pid"], m["aid"])


@route("DELETE", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)")
def api_delete_asset(s, h, m, q, body):
    s.ws.delete_asset(m["pid"], m["aid"])
    return {"deleted": m["aid"]}


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/frames")
def api_frames(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    op = body.pop("op")
    return edit_frames(s.ws, a, op, **body)


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/pixels")
def api_pixels(s, h, m, q, body):
    """Sprite editor save: full edited frames (data URLs); the server stores the difference as per-frame patches."""
    a = s.ws.get_asset(m["pid"], m["aid"])
    edits = [{"index": int(e["index"]), "image": open_image_bytes(decode_data_url(e["image"])).convert("RGBA")}
             for e in body.get("edits", [])]
    if not edits:
        raise StudioError("No edited frames")
    a = save_frame_edits(s.ws, a, edits)
    check_asset(s.ws, a)
    return s.ws.get_asset(m["pid"], m["aid"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/pixels/clear")
def api_pixels_clear(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    return clear_patch(s.ws, a, int(body["index"]))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/recut")
def api_recut(s, h, m, q, body):
    a = s.recut_action(m["pid"], m["aid"], body.get("settings", {}))
    check_asset(s.ws, a)
    return s.ws.get_asset(m["pid"], m["aid"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/reprocess")
def api_reprocess(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    a = reprocess(s.ws, a, body.get("params", {}))
    check_asset(s.ws, a)
    return s.ws.get_asset(m["pid"], m["aid"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/replace")
def api_replace(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    im = open_image_bytes(decode_data_url(body["image"])).convert("RGBA")
    a = replace_frame(s.ws, a, int(body["index"]), im, origin="manual")
    check_asset(s.ws, a)
    return s.ws.get_asset(m["pid"], m["aid"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/regenerate")
def api_regenerate(s, h, m, q, body):
    params = {"aid": m["aid"], "index": int(body["index"]), "provider_id": body["provider_id"],
              "workflow_id": body.get("workflow_id"), "params": body.get("params", {}), "note": body.get("note", "")}
    return s.jobs.submit("regenerate_frame", params, project_id=m["pid"], label=f"regenerate frame {body['index']}",
                         max_attempts=int(body.get("max_attempts", 1)))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/decision")
def api_decision(s, h, m, q, body):
    return s.ws.set_decision(m["pid"], m["aid"], body["decision"], body.get("note", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/qa")
def api_qa(s, h, m, q, body):
    return check_asset(s.ws, s.ws.get_asset(m["pid"], m["aid"]))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/visual-review")
def api_visual(s, h, m, q, body):
    return record_visual_review(s.ws, s.ws.get_asset(m["pid"], m["aid"]), body.get("findings", {}), body.get("reviewer", "user"), body.get("notes", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/layers")
def api_layers(s, h, m, q, body):
    return s.hybrid(m["pid"], m["aid"], body["effect_id"], body.get("anchor_event") or None, tuple(body.get("offset", [0, 0])),
                    int(body.get("start_ms", 0)))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/restore")
def api_restore(s, h, m, q, body):
    return s.ws.restore_version(m["pid"], m["aid"], int(body["version"]))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/meta")
def api_meta(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    for k in ("name", "tags", "character_id", "type"):
        if k in body:
            a[k] = body[k]
    if "direction" in body:
        a["animation"]["direction"] = body["direction"]
    if "anim_name" in body:
        a["animation"]["name"] = body["anim_name"]
    return s.ws.save_asset(a, snapshot_note="metadata")


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/document")
def api_engine_doc(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    proc = a.get("procedural") or {}
    if not proc.get("doc_id"):
        raise StudioError("Not a procedural asset", code="not_procedural")
    ddir = safe_join(s.ws.engine_home(m["pid"]), "documents", proc["doc_id"])
    if not (ddir / "doc.json").is_file():
        raise StudioError("Engine document not found in this project (replay the recipe to rebuild it)", code="document_missing")
    doc = read_json(ddir / "doc.json")
    recipe = (ddir / "doc.recipe").read_text(encoding="utf-8").splitlines() if (ddir / "doc.recipe").exists() else []
    cels = sorted(p.name for p in (ddir / "cels").glob("*.png"))
    return {"doc_id": proc["doc_id"], "doc": doc, "cels": cels, "recipe_lines": len(recipe),
            "recipe_head": [json.loads(x)["name"] for x in recipe[:400] if x.strip() and not x.startswith("#")],
            "builder": proc.get("builder"), "params": proc.get("params")}


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/replay")
def api_replay(s, h, m, q, body):
    a = s.ws.get_asset(m["pid"], m["aid"])
    rec = safe_join(s.ws.asset_dir(m["pid"], m["aid"]), a["procedural"]["recipe"])
    return s.jobs.submit("replay_recipe", {"recipe": str(rec), "name": a["name"] + " (replay)"}, project_id=m["pid"], label="replay recipe")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/procedural")
def api_procedural(s, h, m, q, body):
    if body.get("edits"):
        from ..procedural.edits import normalize
        normalize(body["edits"])  # validate now (400) rather than failing later in the job
    return s.jobs.submit("procedural", {"builder": body["builder"], "params": body.get("params", {}), "name": body.get("name"),
                                        "character_id": body.get("character_id"), "edits": body.get("edits") or None},
                         project_id=m["pid"], label=f"Pixel Forge {body['builder']}")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/import")
def api_import(s, h, m, q, body):
    files = body.get("files") or [{"name": body["filename"], "data": body["data"]}]
    paths = [_save_upload(s, f["name"], f["data"]) for f in files]
    if paths[0].suffix == ".recipe":
        return s.jobs.submit("replay_recipe", {"recipe": str(paths[0]), "name": body.get("name") or files[0]["name"]}, project_id=m["pid"], label="import recipe")
    opts = {k: body[k] for k in ("name", "mode", "slicing", "background", "normalize", "video", "anim_name", "direction", "character_id",
                                 "template", "depixelate_block", "fps") if body.get(k) not in (None, "")}
    opts.setdefault("name", Path(files[0]["name"]).stem[:100] or "import")
    return s.jobs.submit("import", {"path": str(paths[0]), "extra_files": [str(p) for p in paths[1:]], **opts}, project_id=m["pid"],
                         label=f"import {files[0]['name']}")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/generate")
def api_generate(s, h, m, q, body):
    keys = ("provider_id", "kind", "character_id", "template", "direction", "workflow_id", "params", "layout", "mode", "note", "name", "prompt_language")
    p = {k: body[k] for k in keys if k in body}
    if body.get("reference_data"):
        p["reference"] = str(_save_upload(s, "ref.png", body["reference_data"]))
    return s.jobs.submit("generate", p, project_id=m["pid"], label=f"generate {p.get('template', '')} via {p['provider_id']}",
                         max_attempts=int(body.get("max_attempts", 1)))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/batch")
def api_batch(s, h, m, q, body):
    if "budget" not in body:
        raise StudioError("Batch jobs require an explicit generation budget")
    return s.jobs.submit("batch_generate", {"items": body["items"]}, project_id=m["pid"], budget=int(body["budget"]), label="batch generate")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/export")
def api_export(s, h, m, q, body):
    kw = {k: body[k] for k in ("asset_ids", "name", "formats", "preview_scale", "trim", "padding", "extrude", "max_atlas", "pot", "character_id")
          if k in body}
    return s.jobs.submit("export", kw, project_id=m["pid"], label=f"export {kw.get('name', '')}")


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/exports")
def api_exports(s, h, m, q, body):
    out = []
    for f in sorted((s.ws.project_dir(m["pid"]) / "exports").glob("*/export_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        man = read_json(f)
        out.append({"export_id": man["export_id"], "name": man["name"], "created_at": man["created_at"], "files": man["files"],
                    "qa": man["qa"]["status"], "contains_test_fixtures": man["contains_test_fixtures"],
                    "animations": [a["key"] for a in man["animations"]], "zip": man.get("zip")})
    return out


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/knight-sample")
def api_knight(s, h, m, q, body):
    cid = body.get("character_id")
    if not cid:
        c = s.ws.create_character(m["pid"], "Knight (sample)", direction_mode="side2", art_style="pixel",
                                  description="Blonde greatsword knight from the bundled sample art (right-facing side view).")
        cid = c["id"]
    assets = s.import_knight_sample(m["pid"], cid, body.get("actions"))
    return {"character_id": cid, "assets": [a["id"] for a in assets]}


# characters
@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters")
def api_create_char(s, h, m, q, body):
    b = dict(body)
    return s.ws.create_character(m["pid"], b.pop("name"), b.pop("direction_mode", "four"), b.pop("art_style", "pixel"), **b)


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)")
def api_char(s, h, m, q, body):
    c = s.ws.get_character(m["pid"], m["cid"])
    c["missing_directions"] = s.ws.missing_directions(c)
    c["assets"] = [{"id": a["id"], "name": a["name"], "anim": a.get("animation", {}).get("name"), "direction": a.get("animation", {}).get("direction"),
                    "status": a["status"]} for a in s.ws.list_assets(m["pid"], character_id=m["cid"])]
    return c


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/update")
def api_char_update(s, h, m, q, body):
    return s.ws.update_character(m["pid"], m["cid"], body)


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/images")
def api_char_image(s, h, m, q, body):
    p = _save_upload(s, body.get("filename", "image.png"), body["data"])
    if body.get("from_asset"):
        pass
    return s.ws.add_character_image(m["pid"], m["cid"], p, body.get("kind", "candidate"), body.get("direction", "primary"), body.get("note", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/frame-as-candidate")
def api_frame_candidate(s, h, m, q, body):
    from ..animation import frame_path
    a = s.ws.get_asset(m["pid"], body["asset_id"])
    f = a["animation"]["frames"][int(body["index"])]
    return s.ws.add_character_image(m["pid"], m["cid"], frame_path(s.ws, a, f), "candidate", body.get("direction", "primary"),
                                    note=f"frame {body['index']} of {a['id']}", is_test_fixture=bool(a["provider"].get("is_test_fixture")),
                                    source_asset=a["id"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/candidates/(?P<cand>[a-z0-9_-]+)/review")
def api_review(s, h, m, q, body):
    return s.ws.review_candidate(m["pid"], m["cid"], m["cand"], body["decision"], body.get("note", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/masters/(?P<dir>[a-z_]+)/replace")
def api_replace_master(s, h, m, q, body):
    return s.ws.replace_master(m["pid"], m["cid"], m["dir"], body["candidate_id"], body.get("reason", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/masters/(?P<dir>[a-z_]+)/unlock")
def api_unlock(s, h, m, q, body):
    return s.ws.unlock_master(m["pid"], m["cid"], m["dir"], body.get("reason", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/report")
def api_char_report(s, h, m, q, body):
    return s.character_report(m["pid"], m["cid"], body.get("animations", ["idle", "walk", "attack"]))


# Pixel Forge (procedural builders + quick edits)
def _default_loop(b) -> bool:
    v = getattr(b, "LOOP", False)
    return bool(v() if callable(v) else v)


@route("GET", r"/api/forge/builders")
def api_forge_builders(s, h, m, q, body):
    from ..procedural import BUILDERS
    from ..procedural.edits import DEFAULTS
    group = {"effect": "Skills & effects", "icon": "Items & icons", "item": "Items & icons", "animation": "Items & icons",
             "environment": "Scenery"}
    from ..tagging import builder_tags
    return {"builders": {k: {"description": b.DESCRIPTION, "params": b.PARAMS, "asset_type": b.ASSET_TYPE,
                             "tags": [t for t in builder_tags(k) if t not in ("procedural", k)],
                             "loop": _default_loop(b),
                             "group": getattr(b, "GROUP", None) or group.get(b.ASSET_TYPE, "Other")} for k, b in BUILDERS.items()},
            "edit_defaults": DEFAULTS}


# ------------------------------------------------------------------ asset packs
_PACK_ITEM_KEYS = ("id", "name", "type", "group", "frames", "tags", "description")


def _pack_opts(q) -> dict:
    out = {}
    for k in ("tier", "variants", "shadows"):
        if k in q:
            v = q[k][0]
            out[k] = v.lower() in ("1", "true", "yes") if k in ("variants", "shadows") else v
    return out


@route("GET", r"/api/packs")
def api_packs(s, h, m, q, body):
    from .. import packs
    return {"packs": packs.list_packs()}


@route("GET", r"/api/packs/(?P<pack>[a-z0-9_-]+)/items")
def api_pack_items(s, h, m, q, body):
    from .. import packs
    packs.get_pack(m["pack"])
    tags = [t for t in (q.get("tags", [""])[0]).split(",") if t]
    allitems = packs.items(m["pack"], _pack_opts(q))
    lst = packs.items(m["pack"], _pack_opts(q), tags=tags, query=q.get("q", [None])[0])
    return {"count": len(lst), "total": len(allitems), "tags": packs.tag_counts(allitems),
            "items": [{k: i.get(k) for k in _PACK_ITEM_KEYS} for i in lst]}


@route("GET", r"/api/packs/(?P<pack>[a-z0-9_-]+)/thumb")
def api_pack_thumb(s, h, m, q, body):
    return (s.pack_thumbnail(m["pack"], q["item"][0], _pack_opts(q)).read_bytes(), "image/png")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/packs/import")
def api_pack_import(s, h, m, q, body):
    from .. import packs
    packs.get_pack(body["pack"])
    s.ws.get_project(m["pid"])
    params = {"pack": body["pack"], "items": body.get("items") or None, "tags": body.get("tags") or None,
              "query": body.get("query") or None, "options": body.get("options") or {}, "force": bool(body.get("force"))}
    return s.jobs.submit("import_pack", params, project_id=m["pid"], label=f"import pack {body['pack']}")


@route("POST", r"/api/forge/preview")
def api_forge_preview(s, h, m, q, body):
    return s.forge_preview(body["builder"], body.get("params") or {}, body.get("edits") or {})


@route("GET", r"/api/forge/thumb/(?P<b>[a-z0-9_]+)\.png")
def api_forge_thumb(s, h, m, q, body):
    return (s.forge_thumbnail(m["b"]).read_bytes(), "image/png")


# guided flow: character animation (Motion Studio action plans)
@route("GET", r"/api/action-presets")
def api_action_presets(s, h, m, q, body):
    from ..actions import presets
    return presets()


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/from-reference")
def api_char_from_ref(s, h, m, q, body):
    p = _save_upload(s, body.get("filename", "reference.png"), body["data"])
    return s.create_character_from_reference(m["pid"], body["name"], p, art_style=body.get("art_style", "pixel"),
                                             view=body.get("view", "side"), description=body.get("description", ""))


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/from-description")
def api_char_from_desc(s, h, m, q, body):
    c = s.create_character_from_description(m["pid"], body["name"], body.get("description", ""), art_style=body.get("art_style", "pixel"),
                                            view=body.get("view", "side"), visual_style=body.get("visual_style", ""))
    return {"character": c, "job": _ref_job(s, m["pid"], c["id"], body)}


def _ref_job(s, pid, cid, body):
    n = max(1, min(8, int(body.get("count", 4))))
    return s.jobs.submit("reference_candidates", {"character_id": cid, "provider_id": body["provider_id"], "count": n,
                                                  "note": body.get("note", ""), "workflow_id": body.get("workflow_id") or None,
                                                  "params": body.get("params", {})},
                         project_id=pid, budget=n, label=f"{n} reference candidates via {body['provider_id']}")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/reference-candidates")
def api_char_ref_candidates(s, h, m, q, body):
    if body.get("description"):
        c = s.ws.get_character(m["pid"], m["cid"])
        c["description"] = str(body["description"])[:2000]
        s.ws.save_character(c)
    return _ref_job(s, m["pid"], m["cid"], body)


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/pick-reference")
def api_char_pick_reference(s, h, m, q, body):
    return s.pick_reference(m["pid"], m["cid"], body["candidate_id"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/reference")
def api_char_reference(s, h, m, q, body):
    p = _save_upload(s, body.get("filename", "reference.png"), body["data"])
    return s.set_character_reference(m["pid"], m["cid"], p)


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/plan")
def api_plan(s, h, m, q, body):
    from ..actions import load_plan
    return load_plan(s.ws, m["pid"], m["cid"])


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/plan")
def api_plan_save(s, h, m, q, body):
    from ..actions import save_plan
    body.setdefault("language", s.prompt_language(m["pid"]))
    return save_plan(s.ws, m["pid"], m["cid"], body)


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/plan/prompts")
def api_plan_prompts(s, h, m, q, body):
    method = body.get("method", "template")
    p = {"character_id": m["cid"], "method": method, "action_ids": body.get("action_ids"), "language": body.get("language")}
    if method == "template":  # instant: no job needed
        return {"plan": s.write_action_prompts(m["pid"], m["cid"], "template", body.get("action_ids"), body.get("language"))}
    return s.jobs.submit("action_prompts", p, project_id=m["pid"], label="write prompts with Codex")


@route("POST", r"/api/projects/(?P<pid>[a-z0-9_-]+)/characters/(?P<cid>[a-z0-9_-]+)/plan/generate")
def api_plan_generate(s, h, m, q, body):
    from ..actions import load_plan
    plan = load_plan(s.ws, m["pid"], m["cid"])
    ids = body.get("action_ids") or [a["id"] for a in plan["actions"]]
    if not ids:
        raise StudioError("No actions in the plan; add at least one action first")
    p = {"character_id": m["cid"], "action_ids": ids, "provider_id": body["provider_id"],
         "workflow_id": body.get("workflow_id") or None, "params": body.get("params", {})}
    label = f"generate {', '.join(ids)} via {body['provider_id']}" if len(ids) <= 3 else f"generate {len(ids)} actions via {body['provider_id']}"
    return s.jobs.submit("batch_actions", p, project_id=m["pid"], budget=int(body.get("budget", len(ids))), label=label)


@route("POST", r"/api/prompt-preview")
def api_prompt_preview(s, h, m, q, body):
    from ..prompts import build_keyframe_prompt, build_master_prompt
    c = s.ws.get_character(body["project_id"], body["character_id"])
    lang = body.get("prompt_language") or s.ws.get_project(body["project_id"]).get("prompt_language") or s.cfg.prompt_language
    if body.get("kind") == "master_candidate":
        return build_master_prompt(c, body.get("direction", "south"), lang)
    return build_keyframe_prompt(c, body.get("template", "idle"), body.get("direction", "none"), body.get("mode"), note=body.get("note", ""), language=lang)


# jobs
@route("GET", r"/api/jobs")
def api_jobs(s, h, m, q, body):
    return s.jobs.list(int(q.get("limit", ["50"])[0]), q.get("project", [None])[0])


@route("GET", r"/api/jobs/(?P<jid>[a-z0-9_-]+)")
def api_job(s, h, m, q, body):
    return s.jobs.get(m["jid"])


@route("POST", r"/api/jobs/(?P<jid>[a-z0-9_-]+)/cancel")
def api_cancel(s, h, m, q, body):
    return s.jobs.cancel(m["jid"])


@route("POST", r"/api/jobs/(?P<jid>[a-z0-9_-]+)/retry")
def api_retry(s, h, m, q, body):
    return s.jobs.retry(m["jid"])


# comfy workflows
@route("GET", r"/api/workflows")
def api_workflows(s, h, m, q, body):
    return s.registry.workflows.list()


@route("GET", r"/api/workflows/(?P<wid>[a-z0-9_-]+)")
def api_workflow(s, h, m, q, body):
    return s.registry.workflows.get(m["wid"])


@route("POST", r"/api/workflows/import")
def api_wf_import(s, h, m, q, body):
    wf = body["workflow"]
    if isinstance(wf, str) and wf.startswith("data:"):
        wf = decode_data_url(wf).decode("utf-8")
    return s.registry.workflows.import_workflow(wf, name=body["name"], category=body["category"], wid=body.get("id"),
                                                description=body.get("description", ""), overrides=body.get("overrides"))


@route("POST", r"/api/workflows/(?P<wid>[a-z0-9_-]+)/check")
def api_wf_check(s, h, m, q, body):
    return s.registry.get("comfyui").check_workflow(m["wid"], body.get("params"))


@route("DELETE", r"/api/workflows/(?P<wid>[a-z0-9_-]+)")
def api_wf_delete(s, h, m, q, body):
    s.registry.workflows.delete(m["wid"])
    return {"deleted": m["wid"]}


@route("GET", r"/api/comfyui/queue")
def api_comfy_queue(s, h, m, q, body):
    return s.registry.get("comfyui").queue()


# ------------------------------------------------------------------ handler
class Handler(BaseHTTPRequestHandler):
    server_version = "AIGameArtStudio/" + __version__
    studio = None
    allowed_hosts: set = set()

    def log_message(self, fmt, *args):
        log.debug("http %s", fmt % args)

    def _send(self, code, body: bytes, ctype="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):  # browser navigated away mid-response: nothing to do
            self.close_connection = True

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode())

    def _lang(self):
        return normalize(self.headers.get("X-Studio-Lang") or self.headers.get("Accept-Language") or self.studio.cfg.language)

    def _host_ok(self):
        return self.headers.get("Host", "") in self.allowed_hosts

    def _authed(self):
        c = http.cookies.SimpleCookie()
        try:
            c.load(self.headers.get("Cookie", ""))
        except http.cookies.CookieError:
            return False
        return "artstudio" in c and secrets.compare_digest(c["artstudio"].value, TOKEN)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        if not self._host_ok():
            return self._json(403, {"error": "invalid Host header"})
        u = urlparse(self.path)
        path = u.path
        if method == "GET" and path in ("/", "/index.html"):
            body = (WEB / "index.html").read_bytes()
            return self._send(200, body, "text/html; charset=utf-8",
                              {"Set-Cookie": f"artstudio={TOKEN}; HttpOnly; SameSite=Strict; Path=/",
                               "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'"})
        if method == "GET" and path.startswith("/static/"):
            try:
                f = safe_join(WEB, path[len("/static/"):])
            except StudioError:
                return self._json(404, {"error": "not found"})
            if f.is_file():
                return self._send(200, f.read_bytes(), mimetypes.guess_type(str(f))[0] or "application/octet-stream")
            return self._json(404, {"error": "not found"})
        if method == "GET" and path == "/health":
            return self._json(200, {"ok": True, "version": __version__})
        if not self._authed():
            return self._json(401, {"error": localize("Open the studio at / first (session cookie missing).", None, self._lang()), "code": "unauthorized"})
        if method != "GET":
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self._json(403, {"error": "invalid origin"})
        if method == "GET" and path.startswith("/files/"):
            return self._file(path)
        body = {}
        if method in ("POST", "DELETE"):
            n = int(self.headers.get("Content-Length", "0") or 0)
            if n > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            if n:
                try:
                    body = json.loads(self.rfile.read(n))
                except ValueError:
                    return self._json(400, {"error": "invalid JSON"})
        for meth, rx, fn in ROUTES:
            if meth != method:
                continue
            mm = rx.match(path)
            if mm:
                t0 = time.time()
                try:
                    res = fn(self.studio, self, mm.groupdict(), parse_qs(u.query), body)
                    if isinstance(res, tuple):
                        return self._send(200, res[0], res[1])
                    return self._json(200, res)
                except Conflict as e:
                    return self._json(409, {"error": localize_exc(e, self._lang()), "code": "conflict", "detail": str(e)})
                except (StudioError, GenerationError, KeyError, ValueError, TypeError) as e:
                    log.info("api error path=%s err=%s", path, e)
                    msg = str(e) if not isinstance(e, KeyError) else f"missing field {e}"
                    return self._json(400, {"error": localize(msg, getattr(e, "code", None), self._lang()),
                                            "code": getattr(e, "code", None) or "error", "detail": msg})
                except Exception as e:  # noqa: BLE001
                    log.error("api crash path=%s %s", path, traceback.format_exc())
                    return self._json(500, {"error": f"internal error: {e}"})
                finally:
                    log.debug("api path=%s ms=%d", path, (time.time() - t0) * 1000)
        return self._json(404, {"error": "not found"})

    def _file(self, path):
        parts = [p for p in path.split("/")[2:] if p]
        try:
            if len(parts) < 3:
                raise StudioError("bad path")
            pid, area = parts[0], parts[1]
            if area not in ("assets", "characters", "exports", "engine"):
                raise StudioError("bad area")
            if area == "engine":
                f = safe_join(self.studio.ws.engine_home(pid), "documents", *parts[2:])
            else:
                f = safe_join(self.studio.ws.project_dir(pid), area, *parts[2:])
        except StudioError:
            return self._json(404, {"error": "not found"})
        if not f.is_file():
            return self._json(404, {"error": "not found"})
        ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if f.suffix in (".recipe", ".plist"):
            ctype = "text/plain; charset=utf-8"
        return self._send(200, f.read_bytes(), ctype)


@route("GET", r"/api/projects/(?P<pid>[a-z0-9_-]+)/assets/(?P<aid>[a-z0-9_-]+)/contact-sheet\.png")
def api_contact(s, h, m, q, body):
    import io
    im = s.contact_sheet_png(m["pid"], m["aid"], int(q.get("scale", ["2"])[0]))
    b = io.BytesIO()
    im.save(b, "PNG")
    return (b.getvalue(), "image/png")


def make_server(studio, host="127.0.0.1", port=8870):
    if host not in ("127.0.0.1", "localhost", "::1"):
        log.warning("Binding to non-loopback host %s: the studio has no user accounts; only do this on a trusted network.", host)
    Handler.studio = studio
    Handler.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}", f"{host}:{port}"}
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    return srv
