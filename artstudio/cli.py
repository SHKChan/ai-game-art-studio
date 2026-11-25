"""Agent-facing CLI. Every command prints JSON on stdout (logs go to stderr) so agents can chain calls.

  python -m artstudio status
  python -m artstudio project create "My RPG" --style pixel
  python -m artstudio procedural potion --project P
  python -m artstudio import sheet.png --project P --opts '{"slicing":{"method":"grid","cols":4,"rows":2}}'
  python -m artstudio export --project P --assets A1 A2 --formats atlas cocos gif json
  python -m artstudio serve
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _j(x):
    if hasattr(sys.stdout, "reconfigure") and (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(x, ensure_ascii=False, indent=2, default=str))


def _ctx():
    from .providers.base import JobContext
    return JobContext(lambda p, m: print(f"[{p * 100:5.1f}%] {m}", file=sys.stderr))


def build_parser():
    ap = argparse.ArgumentParser(prog="artstudio", description="AI Game Art Studio — agent CLI")
    ap.add_argument("--workspace", help="workspace directory (default: ./workspace or ARTSTUDIO_WORKSPACE)")
    ap.add_argument("--config", help="studio.config.json path")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="start the web studio")
    s.add_argument("--host")
    s.add_argument("--port", type=int)
    s.add_argument("--no-mock", action="store_true", help="hide the mock provider")

    sub.add_parser("status", help="workspace + provider availability")
    sub.add_parser("builders", help="list Atelier procedural builders and animation templates")

    p = sub.add_parser("project")
    p.add_argument("action", choices=["list", "create", "show"])
    p.add_argument("name", nargs="?")
    p.add_argument("--style", default="pixel", choices=["pixel", "hd"])
    p.add_argument("--game", default="")
    p.add_argument("--id")

    c = sub.add_parser("character")
    c.add_argument("action", choices=["create", "show", "update", "add-image", "review", "replace-master", "unlock", "report", "list"])
    c.add_argument("--project", required=True)
    c.add_argument("--id")
    c.add_argument("--name")
    c.add_argument("--directions", default="four", choices=["side2", "four", "eight"])
    c.add_argument("--style", default="pixel", choices=["pixel", "hd"])
    c.add_argument("--patch", help="JSON fields for update/create")
    c.add_argument("--image")
    c.add_argument("--kind", default="candidate", choices=["candidate", "concept"])
    c.add_argument("--direction", default="primary")
    c.add_argument("--candidate")
    c.add_argument("--decision", choices=["approved", "rejected"])
    c.add_argument("--reason", default="")
    c.add_argument("--animations", nargs="*", default=["idle", "walk", "attack"])

    pr = sub.add_parser("procedural", help="draw with Atelier via a builder")
    pr.add_argument("builder")
    pr.add_argument("--project", required=True)
    pr.add_argument("--params", default="{}")
    pr.add_argument("--name")
    pr.add_argument("--character")

    dr = sub.add_parser("draw", help="run an agent-authored Atelier call list (JSON array or JSONL; \"$DOC\" = the new doc id)")
    dr.add_argument("file")
    dr.add_argument("--project", required=True)
    dr.add_argument("--name", required=True)
    dr.add_argument("--type", default="item", choices=["item", "icon", "effect", "tileset", "environment", "ui", "other"])

    rp = sub.add_parser("replay", help="replay an Atelier .recipe into a new asset")
    rp.add_argument("recipe")
    rp.add_argument("--project", required=True)
    rp.add_argument("--name", default="replay")

    im = sub.add_parser("import", help="import PNG/sheet/sequence/GIF/APNG/video")
    im.add_argument("files", nargs="+")
    im.add_argument("--project", required=True)
    im.add_argument("--opts", default="{}", help="JSON: name, mode, slicing, background, normalize, video, anim_name, direction, character_id, template, depixelate_block, fps")

    g = sub.add_parser("generate", help="reference-driven generation through a provider")
    g.add_argument("--project", required=True)
    g.add_argument("--provider", required=True)
    g.add_argument("--workflow")
    g.add_argument("--character")
    g.add_argument("--kind", default="keyframes", choices=["keyframes", "master_candidate"])
    g.add_argument("--template", default="idle")
    g.add_argument("--direction", default="none")
    g.add_argument("--params", default="{}")
    g.add_argument("--layout", default='{"method":"auto"}')
    g.add_argument("--reference")
    g.add_argument("--note", default="")
    g.add_argument("--budget", type=int, help="max generation calls (required for --batch)")
    g.add_argument("--batch-directions", nargs="*")

    rg = sub.add_parser("regenerate", help="selective frame regeneration")
    rg.add_argument("--project", required=True)
    rg.add_argument("--asset", required=True)
    rg.add_argument("--index", type=int, required=True)
    rg.add_argument("--provider", required=True)
    rg.add_argument("--workflow")
    rg.add_argument("--params", default="{}")
    rg.add_argument("--note", default="")

    fr = sub.add_parser("frames", help="frame edit operations")
    fr.add_argument("--project", required=True)
    fr.add_argument("--asset", required=True)
    fr.add_argument("op", choices=["reorder", "move", "duplicate", "delete", "duration", "durations", "fps", "reject", "restore", "loop", "pivot", "nudge", "events", "phase", "airborne"])
    fr.add_argument("--args", default="{}", help="JSON kwargs, e.g. '{\"index\":2,\"duration_ms\":120}'")

    rp2 = sub.add_parser("reprocess")
    rp2.add_argument("--project", required=True)
    rp2.add_argument("--asset", required=True)
    rp2.add_argument("--params", default="{}")

    q = sub.add_parser("qa", help="deterministic checks")
    q.add_argument("--project", required=True)
    q.add_argument("--asset", required=True)
    q.add_argument("--spritepipe", action="store_true", help="also run Pixel Atelier spritepipe build/check")

    d = sub.add_parser("decide", help="manual approval / rejection")
    d.add_argument("--project", required=True)
    d.add_argument("--asset", required=True)
    d.add_argument("decision", choices=["approved", "rejected", "pending"])
    d.add_argument("--note", default="")

    h = sub.add_parser("hybrid", help="attach an effect layer to a character animation")
    h.add_argument("--project", required=True)
    h.add_argument("--character-asset", required=True)
    h.add_argument("--effect-asset", required=True)
    h.add_argument("--event", default="hit")
    h.add_argument("--offset", type=int, nargs=2, default=[0, 0])

    e = sub.add_parser("export")
    e.add_argument("--project", required=True)
    e.add_argument("--assets", nargs="+", required=True)
    e.add_argument("--name", default="export")
    e.add_argument("--formats", nargs="*")
    e.add_argument("--character")
    e.add_argument("--preview-scale", type=int, default=2)

    cs = sub.add_parser("contact-sheet")
    cs.add_argument("--project", required=True)
    cs.add_argument("--asset", required=True)
    cs.add_argument("--out", required=True)
    cs.add_argument("--scale", type=int, default=2)

    jb = sub.add_parser("jobs")
    jb.add_argument("action", choices=["list", "show", "cancel", "retry"])
    jb.add_argument("--id")

    wf = sub.add_parser("workflows")
    wf.add_argument("action", choices=["list", "import", "check", "show"])
    wf.add_argument("--file")
    wf.add_argument("--id")
    wf.add_argument("--name")
    wf.add_argument("--category")
    wf.add_argument("--params", default="{}")

    bk = sub.add_parser("backup")
    bk.add_argument("out")
    bk.add_argument("--no-exports", action="store_true")
    rs = sub.add_parser("restore")
    rs.add_argument("archive")
    rs.add_argument("target")

    ks = sub.add_parser("knight-sample", help="import Pixel Atelier's knight example as a character")
    ks.add_argument("--project", required=True)
    ks.add_argument("--character")
    ks.add_argument("--actions", nargs="*")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    import os
    from .config import load_config, setup_logging
    if args.workspace:
        os.environ["ARTSTUDIO_WORKSPACE"] = args.workspace
    cfg = load_config(args.config)
    setup_logging(cfg.log_level)
    if args.cmd == "restore":
        from .workspace import Workspace
        w = Workspace.restore(Path(args.archive), Path(args.target))
        return _j(w.summary())
    from .service import Studio
    from .util import StudioError
    from .providers.base import GenerationError
    try:
        return _run(args, cfg, Studio)
    except (StudioError, GenerationError) as e:
        _j({"error": str(e), "code": getattr(e, "code", "error"), "details": getattr(e, "details", None)})
        return 2


def _run(args, cfg, Studio):
    if args.cmd == "serve":
        from .server.app import make_server
        host, port = args.host or cfg.host, args.port or cfg.port
        studio = Studio(cfg, enable_mock=not args.no_mock)
        srv = make_server(studio, host, port)
        print(f"AI Game Art Studio running at http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}/  (workspace: {studio.ws.root})", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    s = Studio(cfg, workers=1)
    a = args
    if a.cmd == "status":
        return _j(s.status())
    if a.cmd == "builders":
        from .animation import template_info
        from .procedural import BUILDERS
        return _j({"builders": {k: {"description": b.DESCRIPTION, "params": b.PARAMS} for k, b in BUILDERS.items()}, "animation_templates": template_info()})
    if a.cmd == "project":
        if a.action == "list":
            return _j(s.ws.list_projects())
        if a.action == "create":
            return _j(s.ws.create_project(a.name, a.game, "", a.style, a.id))
        return _j({"project": s.ws.get_project(a.name), "assets": [x["id"] for x in s.ws.list_assets(a.name)],
                   "characters": [x["id"] for x in s.ws.list_characters(a.name)]})
    if a.cmd == "character":
        patch = json.loads(a.patch) if a.patch else {}
        if a.action == "list":
            return _j(s.ws.list_characters(a.project))
        if a.action == "create":
            return _j(s.ws.create_character(a.project, a.name, a.directions, a.style, **patch))
        if a.action == "show":
            return _j(s.ws.get_character(a.project, a.id))
        if a.action == "update":
            return _j(s.ws.update_character(a.project, a.id, patch))
        if a.action == "add-image":
            return _j(s.ws.add_character_image(a.project, a.id, Path(a.image), a.kind, a.direction))
        if a.action == "review":
            return _j(s.ws.review_candidate(a.project, a.id, a.candidate, a.decision, a.reason))
        if a.action == "replace-master":
            return _j(s.ws.replace_master(a.project, a.id, a.direction, a.candidate, a.reason))
        if a.action == "unlock":
            return _j(s.ws.unlock_master(a.project, a.id, a.direction, a.reason))
        return _j(s.character_report(a.project, a.id, a.animations))
    if a.cmd == "procedural":
        return _j(_brief(s.procedural(a.project, a.builder, json.loads(a.params), a.name, a.character, ctx=_ctx())))
    if a.cmd == "draw":
        text = Path(a.file).read_text(encoding="utf-8").strip()
        calls = json.loads(text) if text.startswith("[") else [json.loads(x) for x in text.splitlines() if x.strip() and not x.startswith("#")]
        return _j(_brief(s.draw_calls(a.project, calls, a.name, a.type, ctx=_ctx())))
    if a.cmd == "replay":
        return _j(_brief(s.replay_recipe(a.project, Path(a.recipe), a.name, ctx=_ctx())))
    if a.cmd == "import":
        opts = json.loads(a.opts)
        r = s.import_file(a.project, Path(a.files[0]), extra_files=[Path(x) for x in a.files[1:]] or None, **opts)
        from .qa import check_asset
        check_asset(s.ws, r)
        return _j(_brief(s.ws.get_asset(a.project, r["id"])))
    if a.cmd == "generate":
        kw = dict(provider_id=a.provider, kind=a.kind, character_id=a.character, template=a.template, direction=a.direction,
                  workflow_id=a.workflow, params=json.loads(a.params), reference=a.reference, layout=json.loads(a.layout), note=a.note)
        if a.batch_directions:
            if a.budget is None:
                raise SystemExit("--budget is required for batch generation")
            job = s.jobs.submit("batch_generate", {"items": [dict(kw, direction=d) for d in a.batch_directions]}, project_id=a.project, budget=a.budget)
            return _j(s.jobs.wait(job["id"], 3600))
        from .jobs import Budget
        r = s.generate(a.project, ctx=_ctx(), budget=Budget(a.budget) if a.budget is not None else None, **kw)
        return _j(_brief(r) if "animation" in r else r)
    if a.cmd == "regenerate":
        return _j(_brief(s.regenerate_frame(a.project, a.asset, a.index, a.provider, a.workflow, json.loads(a.params), a.note, ctx=_ctx())))
    if a.cmd == "frames":
        from .animation import edit_frames
        return _j(_brief(edit_frames(s.ws, s.ws.get_asset(a.project, a.asset), a.op, **json.loads(a.args))))
    if a.cmd == "reprocess":
        from .animation import reprocess
        return _j(_brief(reprocess(s.ws, s.ws.get_asset(a.project, a.asset), json.loads(a.params))))
    if a.cmd == "qa":
        from .qa import check_asset
        asset = s.ws.get_asset(a.project, a.asset)
        out = {"deterministic": check_asset(s.ws, asset)}
        if a.spritepipe:
            from . import adapters
            from .animation import load_frames
            from .util import new_id
            pairs = load_frames(s.ws, asset)
            out["pixel_atelier_spritepipe"] = adapters.spritepipe_verify([im for _, im in pairs], [f["duration_ms"] for f, _ in pairs],
                                                                         asset["animation"]["pivot"], s.ws.root / "tmp" / new_id("sp"), asset["animation"]["name"])
        return _j(out)
    if a.cmd == "decide":
        return _j(_brief(s.ws.set_decision(a.project, a.asset, a.decision, a.note)))
    if a.cmd == "hybrid":
        return _j(_brief(s.hybrid(a.project, a.character_asset, a.effect_asset, a.event or None, tuple(a.offset))))
    if a.cmd == "export":
        m = s.export(a.project, a.assets, name=a.name, formats=a.formats or None, character_id=a.character, preview_scale=a.preview_scale)
        return _j({"export_id": m["export_id"], "path": m["path"], "qa": m["qa"], "files": m["files"], "contains_test_fixtures": m["contains_test_fixtures"]})
    if a.cmd == "contact-sheet":
        s.contact_sheet_png(a.project, a.asset, a.scale).save(a.out)
        return _j({"written": a.out})
    if a.cmd == "jobs":
        if a.action == "list":
            return _j([{k: j[k] for k in ("id", "kind", "status", "progress", "message", "error")} for j in s.jobs.list()])
        if a.action == "show":
            return _j(s.jobs.get(a.id))
        if a.action == "cancel":
            return _j(s.jobs.cancel(a.id))
        return _j(s.jobs.retry(a.id))
    if a.cmd == "workflows":
        if a.action == "list":
            return _j(s.registry.workflows.list())
        if a.action == "show":
            return _j(s.registry.workflows.get(a.id))
        if a.action == "import":
            return _j(s.registry.workflows.import_workflow(Path(a.file).read_text(encoding="utf-8"), name=a.name or Path(a.file).stem,
                                                           category=a.category or "text_to_image", wid=a.id))
        return _j(s.registry.get("comfyui").check_workflow(a.id, json.loads(a.params)))
    if a.cmd == "backup":
        return _j({"written": str(s.ws.backup(Path(a.out), not a.no_exports))})
    if a.cmd == "knight-sample":
        cid = a.character or s.ws.create_character(a.project, "Knight (Pixel Atelier sample)", "side2", "pixel")["id"]
        return _j({"character_id": cid, "assets": [x["id"] for x in s.import_pixel_atelier_knight(a.project, cid, a.actions)]})
    return 1


def _brief(a: dict) -> dict:
    out = {k: a.get(k) for k in ("id", "name", "type", "art_style", "status", "character_id")}
    out["provider"] = a.get("provider", {}).get("id")
    out["is_test_fixture"] = a.get("provider", {}).get("is_test_fixture", False)
    if "animation" in a:
        an = a["animation"]
        out["animation"] = {"name": an["name"], "direction": an["direction"], "frames": len(an["frames"]), "canvas": an["canvas"],
                            "pivot": an["pivot"], "loop": an["loop"]["enabled"], "events": an.get("events", []), "layers": an.get("layers", [])}
    out["qa"] = a.get("qa", {}).get("deterministic", {}).get("status")
    return out


if __name__ == "__main__":
    sys.exit(main() or 0)
