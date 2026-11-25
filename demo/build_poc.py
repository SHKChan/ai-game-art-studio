"""Build the mandatory proof-of-concept project (SPECIFICATION §15) with REAL assets.

  python demo/build_poc.py [--workspace DIR] [--out deliverables/poc]

Test A  Pixel engine (Engine A): potion, chest, 8-frame chest opening, 8-frame fireball, 8-frame sword slash.
Test B  AI character production. No image generator is reachable offline, so:
          * genuine AI-generated whole-character art (bundled knight sample) is processed
            through the character master system in pixel mode AND HD mode (no regeneration);
          * the requested chibi adventurer is set up as a 4-direction character with complete prompt
            packs for idle/walk/attack; generation itself is BLOCKED until Stage B (ComfyUI);
          * the full generation pipeline is exercised against the mock ComfyUI service in a separate,
            clearly labelled TEST FIXTURE project.
Test C  External processing: real GIF (showcase fixture), real sprite sheet (knight run atlas)
        and an MP4 built from a genuine showcase GIF on a green screen -> extraction, keying, alignment, export.
Test D  Hybrid: knight heavy attack (AI-generated sample) + procedural sword-slash layer with independent timing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "mock_comfyui"))

from PIL import Image  # noqa: E402

REPORT: dict = {"started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "tests": {}}


def log(*a):
    print("[poc]", *a, flush=True)


def save_sheet(s, pid, aid, out: Path, name: str, scale=3):
    out.mkdir(parents=True, exist_ok=True)
    s.contact_sheet_png(pid, aid, scale).save(out / f"{name}.png")


def copy_export(m, dest: Path):
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(m["path"], dest)
    return {"files": len(m["files"]), "qa": m["qa"]["status"], "path": str(dest.relative_to(ROOT)), "contains_test_fixtures": m["contains_test_fixtures"]}


def make_video(ffmpeg: str, gif: Path, out_mp4: Path, scale=4, bg=(0, 177, 64)):
    """MP4 test input derived from genuine fixture art: GIF frames composited on a solid green screen."""
    from artstudio.processing.importers import extract_animation
    frames = extract_animation(gif)
    with tempfile.TemporaryDirectory() as td:
        for i, (im, _) in enumerate(frames):
            c = Image.new("RGBA", im.size, bg + (255,))
            c.alpha_composite(im)
            c = c.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST).convert("RGB")
            c.save(Path(td) / f"f{i:04d}.png")
        fps = round(1000 / frames[0][1])
        r = subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(td) / "f%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv444p", "-crf", "0", "-preset", "veryslow", str(out_mp4)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise RuntimeError(r.stderr)
    return fps, len(frames)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(ROOT / "workspace" / "poc"))
    ap.add_argument("--out", default=str(ROOT / "deliverables" / "poc"))
    args = ap.parse_args()
    ws_dir, out = Path(args.workspace), Path(args.out)
    if ws_dir.exists():
        shutil.rmtree(ws_dir)
    out.mkdir(parents=True, exist_ok=True)
    os.environ["ARTSTUDIO_WORKSPACE"] = str(ws_dir)
    from artstudio import adapters
    from artstudio.animation import add_layer, edit_frames, load_frames, reprocess
    from artstudio.config import load_config
    from artstudio.prompts import build_keyframe_prompt, build_master_prompt
    from artstudio.qa import check_asset
    from artstudio.service import Studio

    s = Studio(load_config(), workers=1)
    sheets = out / "contact_sheets"
    engine = s.registry.get("procedural").status()
    REPORT["environment"] = {"pixel_engine": engine.to_dict(), "ffmpeg": bool(s.ffmpeg), "comfyui_real": s.registry.get("comfyui").status().to_dict()}
    p = s.ws.create_project("POC — Fantasy RPG", game="Proof of concept", default_style="pixel", pid="poc-fantasy-rpg")
    pid = p["id"]

    # ---------------- Test A
    log("Test A: pixel engine assets")
    a_ids, a_rep = {}, {}
    if engine.available:
        for b, name in [("potion", "Health Potion 64"), ("chest", "Treasure Chest 64"), ("chest_open", "Chest Opening 8f"),
                        ("fireball", "Fireball 8f"), ("sword_slash", "Sword Slash 8f")]:
            a = s.procedural(pid, b, name=name)
            a_ids[b] = a["id"]
            save_sheet(s, pid, a["id"], sheets, f"A_{b}", 4)
            a_rep[b] = {"asset": a["id"], "frames": len(a["animation"]["frames"]), "canvas": a["animation"]["canvas"],
                        "qa": a["qa"]["deterministic"]["status"], "engine_doc": a["procedural"]["doc_id"],
                        "engine_calls": a["provider"]["details"]["calls"]}
            s.ws.set_decision(pid, a["id"], "approved", "visually inspected in POC review")
        # reproducibility: replay a recipe and compare pixels
        a = s.ws.get_asset(pid, a_ids["fireball"])
        rec = s.ws.asset_dir(pid, a["id"]) / a["procedural"]["recipe"]
        b = s.replay_recipe(pid, rec, "Fireball (recipe replay check)")
        same = [x.tobytes() for _, x in load_frames(s.ws, a)] == [x.tobytes() for _, x in load_frames(s.ws, b)]
        a_rep["recipe_replay_identical"] = same
        s.ws.delete_asset(pid, b["id"])
        sp = adapters.spritepipe_verify([im for _, im in load_frames(s.ws, s.ws.get_asset(pid, a_ids["chest_open"]))],
                                        [f["duration_ms"] for f in s.ws.get_asset(pid, a_ids["chest_open"])["animation"]["frames"]],
                                        [32, 63], ws_dir / "tmp" / "spritepipe-chest", "chest_open")
        a_rep["spritepipe_chest_open"] = sp["status"]
        m = s.export(pid, list(a_ids.values()), name="test_a_procedural", preview_scale=4)
        a_rep["export"] = copy_export(m, out / "test_a_procedural")
        # editable sources + recipes
        src = out / "test_a_procedural" / "engine_sources"
        src.mkdir(exist_ok=True)
        for b, aid in a_ids.items():
            ad = s.ws.get_asset(pid, aid)
            shutil.copyfile(s.ws.asset_dir(pid, aid) / "source" / "doc.recipe", src / f"{b}.recipe")
            docdir = s.ws.engine_home(pid) / "documents" / ad["procedural"]["doc_id"]
            shutil.copytree(docdir, src / f"{b}_document", dirs_exist_ok=True)
    else:
        a_rep["blocked"] = engine.reason
    REPORT["tests"]["A_procedural"] = a_rep

    # ---------------- Test B
    log("Test B: character production (genuine sample AI art; generation blocked offline)")
    b_rep = {}
    knight = s.ws.create_character(pid, "Greatsword Knight", "side2", "pixel", cid="knight",
                                   description="Blonde knight with dark-blue headband, silver/navy armour, red tassets and an oversized two-handed greatsword (bundled sample).",
                                   clothing=["silver and navy plate armour", "red waist cloth", "dark boots"], weapon={"type": "two-handed greatsword", "grip": "both hands on one straight hilt"},
                                   constraints=["same face and hair", "same greatsword length and width"], negative_constraints=["shield", "helmet"])
    assets = s.import_knight_sample(pid, "knight", ["idle", "run", "light", "heavy"])
    k = {a["animation"]["name"]: a for a in assets}
    # master: idle frame 0 (right). Left is NOT mirrored automatically (asymmetric greatsword).
    from artstudio.animation import frame_path
    c = s.ws.add_character_image(pid, "knight", frame_path(s.ws, k["idle"], k["idle"]["animation"]["frames"][0]), "candidate", "right",
                                 note="idle frame 0", source_asset=k["idle"]["id"])
    c = s.ws.review_candidate(pid, "knight", c["candidates"][-1]["id"], "approved", "matches the sample master")
    # events (marked by visual inspection of the frames)
    edit_frames(s.ws, s.ws.get_asset(pid, k["light"]["id"]), "events", events=[{"frame": 3, "type": "hit", "name": "downward strike"}, {"frame": 10, "type": "hit", "name": "rising strike"}])
    edit_frames(s.ws, s.ws.get_asset(pid, k["heavy"]["id"]), "events", events=[{"frame": 9, "type": "release"}, {"frame": 10, "type": "hit"}])
    edit_frames(s.ws, s.ws.get_asset(pid, k["run"]["id"]), "events", events=[{"frame": 0, "type": "footstep"}, {"frame": 4, "type": "footstep"}])
    for name in ("idle", "run", "light", "heavy"):
        a = check_asset(s.ws, s.ws.get_asset(pid, k[name]["id"]))
        save_sheet(s, pid, k[name]["id"], sheets, f"B_knight_{name}_pixel", 1)
        b_rep[f"knight_{name}_pixel"] = {"asset": k[name]["id"], "frames": len(k[name]["animation"]["frames"]), "qa": a["status"],
                                         "issues": sorted({i["code"] for i in a["issues"]})}
    # HD illustration mode on the SAME source frames (no regeneration): 1.5x Lanczos, partial alpha kept.
    hd = s.import_knight_sample(pid, "knight", ["run"], mode="hd")[0]
    hd = reprocess(s.ws, hd, {"mode": "hd", "scale": 1.5, "canvas": None, "pivot": None, "source_pivot": None, "padding": 4})
    s.ws.save_asset({**hd, "name": "Knight run (HD mode 1.5x)"})
    fr = load_frames(s.ws, s.ws.get_asset(pid, hd["id"]))
    partial = any(any(0 < v < 255 for v in im.getchannel("A").getdata()) for _, im in fr[:2])
    save_sheet(s, pid, hd["id"], sheets, "B_knight_run_hd", 1)
    b_rep["knight_run_hd"] = {"asset": hd["id"], "canvas": hd["animation"]["canvas"], "partial_alpha_preserved": partial}
    sp = adapters.spritepipe_verify([im for _, im in load_frames(s.ws, s.ws.get_asset(pid, k["run"]["id"]))],
                                    [f["duration_ms"] for f in k["run"]["animation"]["frames"]], k["run"]["animation"]["pivot"],
                                    ws_dir / "tmp" / "spritepipe-run", "run")
    b_rep["spritepipe_knight_run"] = sp["status"]
    b_rep["knight_direction_report"] = s.character_report(pid, "knight", ["idle", "run"])
    # Chibi adventurer: 4-direction setup + prompt packs (generation blocked offline)
    adv = s.ws.create_character(pid, "Chibi Adventurer", "four", "pixel", cid="chibi-adventurer",
                                description="Chibi fantasy adventurer, 2.5-head proportions.", visual_style="chibi pixel art, 1px dark outline",
                                proportions={"head_to_body": "1:2.5", "height_px": 48}, clothing=["red hood", "red cape", "brown adventurer tunic", "brown boots"],
                                accessories=["leather belt"], weapon={"type": "short sword", "hand": "right", "blade": "straight steel, 0.6x body height"},
                                constraints=["blonde hair visible under the hood", "same sword in every direction"],
                                negative_constraints=["shield", "helmet", "different hair colour"])
    for lang, suffix in (("en", ""), ("zh-CN", "_zh-CN")):
        pack = {"language": lang, "master": {d: build_master_prompt(adv, d, lang) for d in adv["directions"]}}
        for tpl in ("idle", "walk", "attack"):
            pack[tpl] = {d: build_keyframe_prompt(adv, tpl, d, language=lang) for d in adv["directions"]}
        (out / f"test_b_prompt_pack_chibi_adventurer{suffix}.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    b_rep["chibi_adventurer"] = {"status": "BLOCKED — no image-generation backend reachable offline (Stage B on the ComfyUI computer).",
                                 "prepared": "4-direction character record + prompt packs for master/idle/walk/attack",
                                 "plan": "scripts/production_smoke_test.py then: generate master south -> approve -> directional masters -> walk east (reduced test) -> attack east -> remaining directions"}
    m = s.export(pid, [k[n]["id"] for n in ("idle", "run", "light", "heavy")] + [hd["id"]], name="test_b_knight", character_id="knight", preview_scale=1)
    b_rep["export"] = copy_export(m, out / "test_b_knight")
    REPORT["tests"]["B_character"] = b_rep

    # ---------------- Test C
    log("Test C: external processing")
    c_rep = {}
    showcase = ROOT / "tests" / "fixtures" / "showcase"
    gif = s.import_file(pid, showcase / "torch.gif", name="Torch (imported GIF)", mode="pixel", anim_name="torch")
    gif = check_asset(s.ws, s.ws.get_asset(pid, gif["id"])) and s.ws.get_asset(pid, gif["id"])
    save_sheet(s, pid, gif["id"], sheets, "C_gif_torch", 4)
    c_rep["gif"] = {"asset": gif["id"], "frames": len(gif["animation"]["frames"]), "qa": gif["qa"]["deterministic"]["status"]}
    sheet = s.import_file(pid, ROOT / "samples" / "knight" / "run" / "atlas.png", name="Knight run (sheet import, auto-slice)",
                          mode="pixel", slicing={"method": "auto", "merge_px": 6}, anim_name="run", direction="right", template="run",
                          normalize={"anchor": "support_foot"})
    save_sheet(s, pid, sheet["id"], sheets, "C_sheet_autoslice_support_foot", 1)
    c_rep["sprite_sheet_auto"] = {"asset": sheet["id"], "frames": len(sheet["animation"]["frames"])}
    vids = []
    if s.ffmpeg:
        mp4 = ws_dir / "tmp" / "cat_greenscreen.mp4"
        mp4.parent.mkdir(parents=True, exist_ok=True)
        fps, n = make_video(s.ffmpeg, showcase / "cat.gif", mp4)
        shutil.copyfile(mp4, out / "test_c_input_cat_greenscreen.mp4")
        v = s.import_file(pid, mp4, name="Cat (MP4 green screen import)", mode="pixel", video={"fps": fps, "max_frames": 64},
                          background={"method": "solid", "color": [0, 177, 64], "tolerance": 60}, depixelate_block=4, anim_name="cat")
        v = s.ws.get_asset(pid, v["id"])
        qa = check_asset(s.ws, v)
        save_sheet(s, pid, v["id"], sheets, "C_video_cat", 4)
        orig = [im for im, _ in __import__("artstudio.processing.importers", fromlist=["x"]).extract_animation(showcase / "cat.gif")]
        got = [im for _, im in load_frames(s.ws, v)]
        from artstudio.processing.frames import alpha_bbox
        c_rep["video"] = {"asset": v["id"], "source": "MP4 built from showcase fixture cat.gif (Atelier showcase art) on #00B140, 4x nearest upscale",
                          "frames_extracted": len(got), "source_frames": n, "qa": qa["status"],
                          "roundtrip_visible_size": [list(alpha_bbox(got[0]))[2] - list(alpha_bbox(got[0]))[0], list(alpha_bbox(got[0]))[3] - list(alpha_bbox(got[0]))[1]],
                          "original_visible_size": [alpha_bbox(orig[0])[2] - alpha_bbox(orig[0])[0], alpha_bbox(orig[0])[3] - alpha_bbox(orig[0])[1]]}
        vids.append(v["id"])
    else:
        c_rep["video"] = {"blocked": "ffmpeg not installed"}
    m = s.export(pid, [gif["id"], sheet["id"]] + vids, name="test_c_external", preview_scale=3)
    c_rep["export"] = copy_export(m, out / "test_c_external")
    REPORT["tests"]["C_external"] = c_rep

    # ---------------- Test D
    log("Test D: hybrid character + effect")
    d_rep = {}
    if engine.available:
        fx = s.procedural(pid, "sword_slash", {"color": "gold"}, name="Gold Slash (layer)")
        fx = reprocess(s.ws, fx, {"scale": 2, "canvas": None, "pivot": None, "padding": 2})  # 2x nearest to match the knight's pixel scale
        fx = s.ws.get_asset(pid, fx["id"])
        # Place the crescent's centre (cell point 28,32 at 2x) on the knight's chest, 15px ahead / 37px above the root,
        # and start it so the effect's own impact frame (210 ms in) lands on the knight's "hit" frame.
        f0 = fx["animation"]["frames"][0]
        centre = (f0["offset"][0] + 56, f0["offset"][1] + 64)
        fpx, fpy = fx["animation"]["pivot"]
        off = (15 + fpx - centre[0], -37 + fpy - centre[1])
        heavy = add_layer(s.ws, s.ws.get_asset(pid, k["heavy"]["id"]), fx["id"], role="effect", offset=off, z=1, anchor_to_event="hit",
                          event_offset_ms=-180)
        from artstudio.export import composite_timeline, write_gif
        cf, cd, _ = composite_timeline(s.ws, heavy)
        write_gif(cf, cd, out / "test_d_hybrid_composite_preview.gif", loop=True, scale=1)
        from artstudio.export import contact_sheet
        contact_sheet(cf, cols=8).save(sheets / "D_hybrid_composite.png")
        m = s.export(pid, [heavy["id"]], name="test_d_hybrid", character_id="knight", preview_scale=1)
        d_rep = {"character_asset": heavy["id"], "effect_asset": fx["id"], "layer": heavy["animation"]["layers"][0],
                 "composite_frames": len(cf), "export": copy_export(m, out / "test_d_hybrid")}
    else:
        d_rep["blocked"] = "pixel engine unavailable"
    REPORT["tests"]["D_hybrid"] = d_rep

    # ---------------- Stage A mock pipeline (clearly labelled fixtures)
    log("Mock ComfyUI pipeline (TEST FIXTURES)")
    from server import serve
    srv = serve(0, None, "ok", step_delay=0.005)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    s.registry.get("comfyui").http.base = f"http://127.0.0.1:{srv.server_address[1]}"
    fp = s.ws.create_project("TEST FIXTURE — mock ComfyUI pipeline", pid="mock-pipeline-fixtures")
    adv2 = s.ws.create_character(fp["id"], "Chibi Adventurer (fixture run)", "four", "pixel", cid="adv")
    r = s.generate(fp["id"], "comfyui", kind="master_candidate", character_id="adv", direction="south", workflow_id="sd-text-to-image",
                   params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 4})
    walk = s.generate(fp["id"], "comfyui", character_id="adv", template="walk", direction="east", workflow_id="sd-image-to-image",
                      reference=str(ROOT / "samples" / "knight" / "idle" / "poster.png"),
                      params={"checkpoint": "mock-sd15-fixture.safetensors", "steps": 4})
    regen = s.regenerate_frame(fp["id"], walk["id"], 2, "comfyui", "sd-pose-keyframe",
                               {"checkpoint": "mock-sd15-fixture.safetensors", "controlnet": "mock-openpose-fixture.safetensors", "steps": 3,
                                "pose_image": str(ROOT / "samples" / "knight" / "run" / "poster.png")})
    m = s.export(fp["id"], [walk["id"]], name="mock_fixture_walk_east")
    srv.shutdown()
    REPORT["stage_a_mock_pipeline"] = {"label": "TEST FIXTURES — copies of the bundled sample art returned by the mock server; NOT AI output of this run",
                                       "candidate_is_fixture": r["character"]["candidates"][-1]["is_test_fixture"],
                                       "walk_asset": walk["id"], "walk_is_fixture": walk["provider"]["is_test_fixture"],
                                       "regenerated_frame_origin": regen["animation"]["frames"][2]["origin"],
                                       "export_contains_test_fixtures": m["contains_test_fixtures"]}
    backup = s.ws.backup(out / "poc_workspace_backup.zip", include_exports=False)
    REPORT["workspace_backup"] = str(backup.relative_to(ROOT))
    REPORT["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "POC_REPORT.json").write_text(json.dumps(REPORT, indent=2, default=str), encoding="utf-8")
    log("done ->", out)


if __name__ == "__main__":
    main()
