"""Studio service layer shared by the HTTP API, the agent CLI and job handlers."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from PIL import Image

from . import actions as action_plans
from . import adapters
from .animation import TEMPLATES, add_layer, create_animation_asset, edit_frames, frame_path, reprocess, replace_frame
from .config import Config, find_ffmpeg, load_config
from .export import contact_sheet, export_assets
from .jobs import JobQueue
from .processing import importers
from .processing.frames import (depixelate, estimate_pixel_scale, remove_background, slice_auto, slice_grid)
from .prompts import build_keyframe_prompt, build_master_prompt
from .providers import Registry
from .providers.base import GenerationError, GenerationRequest
from .qa import check_asset, check_animation_set, check_character_directions
from .util import StudioError, new_id, now
from .workspace import Workspace

log = logging.getLogger("artstudio.service")


class Studio:
    def __init__(self, cfg: Config | None = None, workers: int = 2, enable_mock: bool = True):
        self.cfg = cfg or load_config()
        self.ws = Workspace(self.cfg.workspace_path)
        self.registry = Registry(self.cfg, self.ws.root, enable_mock=enable_mock)
        self.ffmpeg = find_ffmpeg(self.cfg)
        self.jobs = JobQueue(self.ws, {
            "procedural": self._job_procedural,
            "import": self._job_import,
            "generate": self._job_generate,
            "regenerate_frame": self._job_regenerate,
            "export": self._job_export,
            "batch_generate": self._job_batch_generate,
            "replay_recipe": self._job_replay,
            "action_prompts": self._job_action_prompts,
            "batch_actions": self._job_batch_actions,
        }, workers=workers)

    # ------------------------------------------------------------------ Engine A
    def procedural(self, pid: str, builder: str, params: dict | None = None, name: str | None = None,
                   character_id: str | None = None, ctx=None) -> dict:
        from .procedural import BUILDERS
        from .providers.base import JobContext
        b = BUILDERS.get(builder)
        if not b:
            raise StudioError(f"Unknown builder {builder}. Available: {sorted(BUILDERS)}")
        prov = self.registry.get("procedural")
        tmp = self.ws.root / "tmp" / new_id("atl")
        req = GenerationRequest("procedural", {"home": str(self.ws.engine_home(pid)), "builder": builder,
                                               "builder_params": params or {}}, out_dir=tmp)
        res = prov.generate(req, ctx or JobContext())
        frames = [(Image.open(p).convert("RGBA"), d) for p, d in zip(res.images, res.metadata["durations"])]
        asset = create_animation_asset(
            self.ws, pid, name or builder.replace("_", " ").title(), frames, anim_name=builder, mode="pixel",
            params={"mode": "pixel", "anchor": "source", "padding": 0, "canvas": list(frames[0][0].size),
                    "pivot": [frames[0][0].width // 2, frames[0][0].height - 1]},
            provider={"id": "procedural", "kind": "procedural", "is_test_fixture": False,
                      "details": {"calls": res.metadata["calls"]}},
            character_id=character_id, origin="procedural", asset_type=b.ASSET_TYPE if b.ASSET_TYPE != "animation" else "animation",
            loop=builder in ("fireball",), tags=["procedural", builder])
        d = self.ws.asset_dir(pid, asset["id"])
        rec_dst = d / "source" / "doc.recipe"
        shutil.copyfile(res.metadata["recipe"], rec_dst)
        asset["procedural"] = {"engine": "artstudio-pixel", "doc_id": res.metadata["doc_id"], "recipe": "source/doc.recipe",
                               "builder": builder, "params": params or {}}
        asset["source_files"].append({"path": "source/doc.recipe", "role": "engine-recipe", "origin": "procedural"})
        shutil.rmtree(tmp, ignore_errors=True)
        self.ws.save_asset(asset)
        check_asset(self.ws, asset)
        return self.ws.get_asset(pid, asset["id"])

    def draw_calls(self, pid: str, calls: list[dict], name: str, asset_type: str = "item", ctx=None) -> dict:
        """Run an agent-authored list of pixel-engine tool calls ({"name","arguments"}, "$DOC" = new doc id).
        Lets any item/effect/icon/tile be drawn without writing a builder."""
        from .providers.base import JobContext
        if not calls or calls[0].get("name") != "doc_new":
            raise StudioError("The first call must be doc_new")
        prov = self.registry.get("procedural")
        tmp = self.ws.root / "tmp" / new_id("drw")
        res = prov.generate(GenerationRequest("procedural", {"home": str(self.ws.engine_home(pid)), "calls": calls}, out_dir=tmp), ctx or JobContext())
        frames = [(Image.open(p).convert("RGBA"), d) for p, d in zip(res.images, res.metadata["durations"])]
        w, h = frames[0][0].size
        a = create_animation_asset(self.ws, pid, name, frames, anim_name="drawn", mode="pixel",
                                   params={"mode": "pixel", "anchor": "source", "padding": 0, "canvas": [w, h], "pivot": [w // 2, h - 1]},
                                   provider={"id": "procedural", "kind": "procedural", "is_test_fixture": False},
                                   origin="procedural", asset_type=asset_type, tags=["procedural", "agent-drawn"])
        d = self.ws.asset_dir(pid, a["id"])
        shutil.copyfile(res.metadata["recipe"], d / "source" / "doc.recipe")
        a["procedural"] = {"engine": "artstudio-pixel", "doc_id": res.metadata["doc_id"], "recipe": "source/doc.recipe", "builder": "agent-calls", "params": {}}
        shutil.rmtree(tmp, ignore_errors=True)
        self.ws.save_asset(a)
        check_asset(self.ws, a)
        return self.ws.get_asset(pid, a["id"])

    def replay_recipe(self, pid: str, recipe: Path, name: str, ctx=None) -> dict:
        from .providers.base import JobContext
        prov = self.registry.get("procedural")
        tmp = self.ws.root / "tmp" / new_id("rpl")
        res = prov.generate(GenerationRequest("procedural", {"home": str(self.ws.engine_home(pid)), "recipe": str(recipe)}, out_dir=tmp), ctx or JobContext())
        frames = [(Image.open(p).convert("RGBA"), d) for p, d in zip(res.images, res.metadata["durations"])]
        w, h = frames[0][0].size
        a = create_animation_asset(self.ws, pid, name, frames, anim_name="replay", mode="pixel",
                                   params={"mode": "pixel", "anchor": "source", "padding": 0, "canvas": [w, h], "pivot": [w // 2, h - 1]},
                                   provider={"id": "procedural", "kind": "procedural", "is_test_fixture": False},
                                   origin="procedural", asset_type="effect", tags=["procedural", "replay"])
        d = self.ws.asset_dir(pid, a["id"])
        shutil.copyfile(recipe, d / "source" / "doc.recipe")
        a["procedural"] = {"engine": "artstudio-pixel", "doc_id": res.metadata["doc_id"], "recipe": "source/doc.recipe", "builder": "replay", "params": {}}
        shutil.rmtree(tmp, ignore_errors=True)
        return self.ws.save_asset(a)

    # ------------------------------------------------------------------ Engine C
    def import_file(self, pid: str, path: Path, *, name: str | None = None, mode: str = "pixel", slicing: dict | None = None,
                    background: dict | None = None, normalize: dict | None = None, video: dict | None = None,
                    anim_name: str = "imported", direction: str = "none", character_id: str | None = None,
                    template: str | None = None, depixelate_block: int | str | None = None, fps: float | None = None,
                    provider: dict | None = None, origin: str = "imported", extra_files: list[Path] | None = None) -> dict:
        """Import PNG / sheet / PNG sequence / GIF / APNG / video and build a normalized animation asset."""
        path = Path(path)
        if not path.is_file():
            raise StudioError(f"File not found: {path}")
        kind = importers.sniff(path)
        rects = None
        steps = {"kind": kind}
        if extra_files:
            frames = importers.load_sequence([path] + [Path(p) for p in extra_files])
            steps["kind"] = "sequence"
        elif kind == "video":
            v = video or {}
            frames = importers.extract_video(path, self.ffmpeg, fps=float(v.get("fps", fps or 12)), max_frames=int(v.get("max_frames", 120)),
                                             start_s=float(v.get("start_s", 0)), duration_s=v.get("duration_s"), scale_width=v.get("scale_width"))
        elif kind == "animation":
            frames = importers.extract_animation(path)
        else:
            with Image.open(path) as im:
                sheet = im.convert("RGBA")
            if background and background.get("method", "auto") != "none":
                sheet, info = remove_background(sheet, mode=mode, method=background.get("method", "auto"), color=background.get("color"),
                                                tolerance=float(background.get("tolerance", 28)), connected=background.get("connected", True))
                steps["background"] = info
                background = None
            s = slicing or {"method": "single"}
            if s.get("method") == "grid":
                parts = slice_grid(sheet, int(s["cols"]), int(s["rows"]), s.get("count"), int(s.get("margin", 0)), int(s.get("spacing", 0)),
                                   tuple(s["cell"]) if s.get("cell") else None)
            elif s.get("method") == "auto":
                parts = slice_auto(sheet, int(s.get("merge_px", 4)), int(s.get("min_area", 16)))
            else:
                parts = [(sheet, [0, 0, sheet.width, sheet.height])]
            frames = [(p, int(s.get("duration_ms", 100))) for p, _ in parts]
            rects = [r for _, r in parts]
            steps["slicing"] = {**s, "frames": len(frames)}
        if fps and kind != "video":
            frames = [(im, round(1000 / fps)) for im, _ in frames]
        if background and background.get("method", "auto") != "none":
            out, infos = [], []
            for im, d in frames:
                im2, info = remove_background(im, mode=mode, method=background.get("method", "auto"), color=background.get("color"),
                                              tolerance=float(background.get("tolerance", 28)), connected=background.get("connected", True))
                out.append((im2, d)); infos.append(info)
            frames = out
            steps["background"] = infos[0] if infos else None
        if depixelate_block:
            blk = estimate_pixel_scale(frames[0][0]) if depixelate_block == "auto" else int(depixelate_block)
            frames = [(depixelate(im, blk), d) for im, d in frames]
            steps["depixelate_block"] = blk
        params = {"mode": mode, "anchor": "source", "padding": 4, **(normalize or {})}
        return create_animation_asset(self.ws, pid, name or path.stem, frames, anim_name=anim_name, direction=direction, mode=mode,
                                      params=params, provider=provider or {"id": "external", "kind": "import", "is_test_fixture": False},
                                      character_id=character_id, template=template, source_file=path, source_rects=rects,
                                      origin=origin, processing_note={"import": steps})

    # ------------------------------------------------------------------ Engine B
    def import_knight_sample(self, pid: str, character_id: str, actions: list[str] | None = None, mode: str = "pixel") -> list[dict]:
        """Bring the bundled knight sample (whole-character, side view, right-facing; AI-generated) into the studio."""
        mapping = {"idle": "idle", "run": "run", "dash": "dash", "light": "combo_attack", "heavy": "attack", "jump": "jump",
                   "hurt": "hit", "knockdown": "death"}
        out = []
        for meta in adapters.knight_actions():
            if actions and meta["id"] not in actions:
                continue
            frames, durs, _ = adapters.knight_frames(meta["id"])
            pv = meta["pivot"]
            ev = []
            a = create_animation_asset(
                self.ws, pid, f"Knight {meta['id']}", list(zip(frames, durs)), anim_name=meta["id"], direction="right", mode=mode,
                params={"mode": mode, "anchor": "source", "padding": 2, "canvas": list(meta["frame_size"]), "pivot": list(pv),
                        "source_pivot": list(pv)},
                provider={"id": "knight-sample", "kind": "ai_generated_sample", "is_test_fixture": False,
                          "details": {"source": f"samples/knight/{meta['id']}/atlas.png",
                                      "provenance": "Pixel Atelier knight sample: generated with Codex built-in imagegen and processed by Pixel Atelier (see samples/knight/NOTICE.md)",
                                      "sample_pivot": pv}},
                character_id=character_id, template=None, origin="generated",
                source_file=Path(meta["atlas_path"]), source_rects=[f["rect"] for f in meta["frames"]],
                events=[], loop=meta["id"] in ("idle", "run"), tags=["sample", "knight", f"action:{mapping.get(meta['id'], meta['id'])}"])
            out.append(a)
        return out

    def generate(self, pid: str, provider_id: str, *, kind: str = "keyframes", character_id: str | None = None,
                 template: str = "idle", direction: str = "none", workflow_id: str | None = None, params: dict | None = None,
                 reference: str | None = None, layout: dict | None = None, mode: str | None = None, note: str = "",
                 name: str | None = None, ctx=None, budget=None, prompt_language: str | None = None) -> dict:
        """Reference-driven generation. kind: master_candidate | keyframes (sheet -> animation)."""
        from .providers.base import JobContext
        ctx = ctx or JobContext()
        prov = self.registry.get(provider_id)
        st = prov.status()
        if not st.available:
            raise GenerationError(f"Provider '{provider_id}' unavailable: {st.reason}", "provider_unavailable")
        c = self.ws.get_character(pid, character_id) if character_id else None
        mode = mode or (c["art_style"] if c else "pixel")
        refs = []
        if reference:
            refs.append(Path(reference))
        elif c:
            m = c["masters"].get(direction) or c["masters"].get("primary") or next(iter(c["masters"].values()), None)
            if m:
                refs.append(self.ws.char_dir(pid, c["id"]) / m["file"])
        lang = prompt_language or self.ws.get_project(pid).get("prompt_language") or self.cfg.prompt_language
        if kind == "master_candidate":
            pr = build_master_prompt(c, direction if direction != "none" else "south", lang) if c else {"positive": note, "negative": ""}
        else:
            pr = build_keyframe_prompt(c, template, direction, mode, note=note, language=lang) if c else {"positive": note or template, "negative": ""}
        if budget is not None and prov.counts_toward_budget:
            budget.spend(1)
        out = self.ws.root / "tmp" / new_id("gen")
        req = GenerationRequest(kind, dict(params or {}), pr["positive"], pr.get("negative", ""), refs,
                                (params or {}).get("seed"), workflow_id, out)
        res = prov.generate(req, ctx)
        fixture = res.is_test_fixture or bool(res.metadata.get("is_test_fixture"))
        pmeta = {"id": provider_id, "kind": prov.kind, "is_test_fixture": fixture, "details": res.metadata}
        if kind == "master_candidate":
            if not c:
                raise StudioError("master_candidate requires a character")
            for img in res.images:
                self.ws.add_character_image(pid, c["id"], img, "candidate", direction if direction != "none" else "primary",
                                            note=pr["positive"][:200], is_test_fixture=fixture)
            shutil.rmtree(out, ignore_errors=True)
            return {"character": self.ws.get_character(pid, c["id"]), "provider": pmeta}
        lay = layout or {"method": "auto"}
        asset = self.import_file(pid, res.images[0], name=name or f"{(c or {}).get('name', 'gen')} {template} {direction}", mode=mode,
                                 slicing=lay, background={"method": "auto"} if lay.get("remove_background", True) else None,
                                 anim_name=template, direction=direction, character_id=character_id, template=template,
                                 provider=pmeta, origin="fixture" if fixture else "generated")
        asset["prompt"] = {"positive": pr["positive"], "negative": pr.get("negative", ""), "template": template}
        asset["reference_images"] = [str(p) for p in refs]
        for f in asset["animation"]["frames"]:
            f["generation"] = {"provider": provider_id, "workflow_id": workflow_id, "is_test_fixture": fixture,
                               "prompt_id": res.metadata.get("prompt_id")}
        if fixture:
            asset["tags"] = sorted(set(asset["tags"] + ["test-fixture"]))
        self.ws.save_asset(asset)
        shutil.rmtree(out, ignore_errors=True)
        check_asset(self.ws, asset)
        return self.ws.get_asset(pid, asset["id"])

    # ------------------------------------------------------------------ Engine B: action plans (sequential action frames)
    def prompt_language(self, pid: str, override: str | None = None) -> str:
        return override or self.ws.get_project(pid).get("prompt_language") or self.cfg.prompt_language

    def reference_for(self, pid: str, c: dict, direction: str = "none") -> Path | None:
        m = c["masters"]
        hit = m.get(direction) or m.get("right") or m.get("east") or m.get("south") or m.get("primary") or next(iter(m.values()), None)
        return self.ws.char_dir(pid, c["id"]) / hit["file"] if hit else None

    def create_character_from_reference(self, pid: str, name: str, image: Path, *, art_style: str = "pixel", view: str = "side",
                                        description: str = "") -> dict:
        """One step for the guided flow: create the character and lock the uploaded image as its master."""
        mode = "side2" if view == "side" else "four"
        c = self.ws.create_character(pid, name, mode, art_style, description=description,
                                     camera="side" if view == "side" else "three_quarter")
        direction = "right" if view == "side" else "south"
        c = self.ws.add_character_image(pid, c["id"], Path(image), "candidate", direction, note="reference (uploaded)")
        c = self.ws.review_candidate(pid, c["id"], c["candidates"][-1]["id"], "approved", "reference uploaded in guided flow")
        return c

    def set_character_reference(self, pid: str, cid: str, image: Path) -> dict:
        """Replace the reference used for action generation (keeps history; explicit replace of a locked master)."""
        c = self.ws.get_character(pid, cid)
        direction = "right" if c["direction_mode"] == "side2" else "south"
        c = self.ws.add_character_image(pid, cid, Path(image), "candidate", direction, note="reference (uploaded)")
        cand = c["candidates"][-1]["id"]
        if c["masters"].get(direction, {}).get("locked"):
            return self.ws.replace_master(pid, cid, direction, cand, "new reference uploaded in guided flow")
        return self.ws.review_candidate(pid, cid, cand, "approved", "reference uploaded in guided flow")

    def write_action_prompts(self, pid: str, cid: str, method: str = "template", action_ids: list[str] | None = None,
                             language: str | None = None, ctx=None) -> dict:
        c = self.ws.get_character(pid, cid)
        ref = self.reference_for(pid, c)
        return action_plans.write_prompts(self.ws, pid, cid, method, action_ids=action_ids, reference=ref, mode=c["art_style"],
                                          lang=self.prompt_language(pid, language), codex_bin=self.cfg.codex_bin,
                                          timeout=self.cfg.codex_timeout, cancel_check=ctx.check_cancel if ctx else None)

    def default_strip_workflow(self) -> str:
        ids = {w["id"] for w in self.registry.workflows.list()}
        return "sd-character-reference" if "sd-character-reference" in ids else "sd-image-to-image"

    @staticmethod
    def strip_reference(ref: Path, n: int, out_dir: Path, mode: str = "pixel", cell: int | None = None) -> Path:
        """ComfyUI img2img input: the reference repeated in n cells on white, so the model keeps the identity
        and only changes the pose per cell (denoise controls how much)."""
        with Image.open(ref) as im:
            r = im.convert("RGBA")
        r = r.crop(r.getchannel("A").getbbox() or (0, 0, r.width, r.height))
        cell = int(cell or max(64, min(512, (2048 // max(1, n)) // 8 * 8)))
        k = min(cell * 0.8 / r.width, cell * 0.85 / r.height)
        r = r.resize((max(1, round(r.width * k)), max(1, round(r.height * k))), Image.NEAREST if mode == "pixel" else Image.LANCZOS)
        strip = Image.new("RGBA", (cell * n, cell), (255, 255, 255, 255))
        for i in range(n):
            strip.alpha_composite(r, (i * cell + (cell - r.width) // 2, round(cell * 0.93) - r.height))
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "strip_reference.png"
        strip.convert("RGB").save(p)
        return p

    @staticmethod
    def strip_layout(img: Path, frames: int, mode: str, fixture: bool) -> tuple[dict, str]:
        with Image.open(img) as im:
            sheet = im.convert("RGBA")
        if sheet.getchannel("A").getextrema()[0] == 255:
            sheet, _ = remove_background(sheet, mode=mode)
        n = len(slice_auto(sheet))
        if n == frames or (fixture and n >= 1):
            return {"method": "auto"}, f"auto: {n} sprites found"
        return {"method": "grid", "cols": frames, "rows": 1}, f"grid {frames}x1 (auto found {n}, expected {frames})"

    def generate_action(self, pid: str, cid: str, action_id: str, provider_id: str, workflow_id: str | None = None,
                        params: dict | None = None, ctx=None, budget=None) -> dict:
        """Generate every frame of one action as a single sprite strip, then slice, align and store it."""
        from .providers.base import JobContext
        ctx = ctx or JobContext()
        c = self.ws.get_character(pid, cid)
        plan = action_plans.load_plan(self.ws, pid, cid)
        a = action_plans.get_action(plan, action_id)
        prov = self.registry.get(provider_id)
        st = prov.status()
        if not st.available:
            raise GenerationError(f"Provider '{provider_id}' unavailable: {st.reason}", "provider_unavailable")
        mode = c["art_style"]
        lang = plan.get("language") or self.prompt_language(pid)
        if not a["prompt"]:
            pr = action_plans.strip_prompt(c, plan, a, mode, lang)
            a.update(prompt=pr["positive"], negative=pr["negative"], prompt_source="template")
        ref = self.reference_for(pid, c, a["direction"])
        if ref is None and provider_id != "mock":
            raise StudioError("Add a reference image for this character first", code="no_reference")
        a["status"] = "generating"
        action_plans.save_plan(self.ws, pid, cid, plan)
        out = self.ws.root / "tmp" / new_id("act")
        params = dict(params or {})
        refs = [ref] if ref else []
        try:
            if provider_id == "comfyui":
                workflow_id = workflow_id or self.default_strip_workflow()
                params["reference_image"] = str(self.strip_reference(ref, a["frames"], out, mode, params.pop("cell", None)))
                params.setdefault("denoise", 0.62)
                refs = []
            if budget is not None and prov.counts_toward_budget:
                budget.spend(1)
            ctx.progress(0.02, f"{a['name']}: generating {a['frames']}-frame strip via {provider_id}")
            res = prov.generate(GenerationRequest("action_strip", params, a["prompt"], a["negative"], refs, params.get("seed"),
                                                  workflow_id, out), ctx)
            fixture = res.is_test_fixture or bool(res.metadata.get("is_test_fixture"))
            layout, layout_note = self.strip_layout(res.images[0], a["frames"], mode, fixture)
            pmeta = {"id": provider_id, "kind": prov.kind, "is_test_fixture": fixture,
                     "details": {k: v for k, v in res.metadata.items() if k != "events"}}
            asset = self.import_file(pid, res.images[0], name=f"{c['name']} — {a['name']}", mode=mode, slicing=layout,
                                     background={"method": "auto"}, anim_name=a["id"], direction=a["direction"], character_id=cid,
                                     template=a["preset"], provider=pmeta, origin="fixture" if fixture else "generated")
        except Exception:
            plan = action_plans.load_plan(self.ws, pid, cid)
            action_plans.get_action(plan, action_id)["status"] = "failed"
            action_plans.save_plan(self.ws, pid, cid, plan)
            raise
        finally:
            shutil.rmtree(out, ignore_errors=True)
        asset["animation"]["loop"]["enabled"] = bool(a["loop"])
        asset["prompt"] = {"positive": a["prompt"], "negative": a["negative"], "template": a["preset"] or a["id"]}
        asset["action"] = {"character_id": cid, "action_id": a["id"], "name": a["name"], "description": a["description"],
                           "poses": a["poses"], "prompt_source": a["prompt_source"], "layout": layout_note, "frames_requested": a["frames"]}
        asset["reference_images"] = [str(ref)] if ref else []
        for f in asset["animation"]["frames"]:
            f["generation"] = {"provider": provider_id, "workflow_id": workflow_id, "is_test_fixture": fixture,
                               "prompt_id": res.metadata.get("prompt_id")}
        asset["tags"] = sorted(set(asset["tags"] + [f"action:{a['id']}"] + (["test-fixture"] if fixture else [])))
        self.ws.save_asset(asset)
        check_asset(self.ws, asset)
        plan = action_plans.load_plan(self.ws, pid, cid)
        pa = action_plans.get_action(plan, action_id)
        pa.update(asset_id=asset["id"], status="generated", attempts=(pa.get("attempts") or []) + [asset["id"]])
        action_plans.save_plan(self.ws, pid, cid, plan)
        return self.ws.get_asset(pid, asset["id"])

    def regenerate_frame(self, pid: str, aid: str, index: int, provider_id: str, workflow_id: str | None = None,
                         params: dict | None = None, note: str = "", ctx=None, budget=None) -> dict:
        """Selective regeneration of one frame using the character master + the current frame as references."""
        from .providers.base import JobContext
        a = self.ws.get_asset(pid, aid)
        anim = a["animation"]
        prov = self.registry.get(provider_id)
        st = prov.status()
        if not st.available:
            raise GenerationError(f"Provider '{provider_id}' unavailable: {st.reason}", "provider_unavailable")
        if budget is not None and prov.counts_toward_budget:
            budget.spend(1)
        c = self.ws.get_character(pid, a["character_id"]) if a.get("character_id") else None
        refs = [frame_path(self.ws, a, anim["frames"][index], source=True)]
        if c and c["masters"]:
            m = c["masters"].get(anim["direction"]) or next(iter(c["masters"].values()))
            refs.insert(0, self.ws.char_dir(pid, c["id"]) / m["file"])
        tpl = anim.get("template") if anim.get("template") in TEMPLATES else "idle"
        lang = self.ws.get_project(pid).get("prompt_language") or self.cfg.prompt_language
        if c and a.get("action"):
            plan = action_plans.load_plan(self.ws, pid, c["id"])
            pa = next((x for x in plan["actions"] if x["id"] == a["action"]["action_id"]), None) or {
                **a["action"], "id": a["action"]["action_id"], "frames": len(anim["frames"]), "direction": anim["direction"]}
            pr = action_plans.frame_prompt(c, plan, pa, index, a["art_style"], plan.get("language") or lang)
            if note:
                pr["positive"] += (" 本轮修改：" if str(lang).startswith("zh") else " Revision: ") + note
        elif c:
            pr = build_keyframe_prompt(c, tpl, anim["direction"], a["art_style"], frame_index=min(index, len(TEMPLATES[tpl]["poses"]) - 1),
                                       note=note, language=lang)
        else:
            pr = {"positive": note, "negative": ""}
        out = self.ws.root / "tmp" / new_id("regen")
        res = prov.generate(GenerationRequest("pose_keyframe", dict(params or {}), pr["positive"], pr["negative"], refs, None, workflow_id, out), ctx or JobContext())
        with Image.open(res.images[0]) as im:
            img = im.convert("RGBA")
        bg = remove_background(img, mode=a["art_style"])[0] if img.getchannel("A").getextrema()[0] == 255 else img
        fixture = res.is_test_fixture or bool(res.metadata.get("is_test_fixture"))
        a = replace_frame(self.ws, a, index, bg, origin="fixture" if fixture else "generated",
                          generation={"provider": provider_id, "workflow_id": workflow_id, "is_test_fixture": fixture,
                                      "prompt": pr["positive"][:500], "metadata": {k: v for k, v in res.metadata.items() if k != "events"}})
        if fixture:
            a["provider"]["is_test_fixture"] = True
            self.ws.save_asset(a)
        shutil.rmtree(out, ignore_errors=True)
        return a

    # ------------------------------------------------------------------ hybrid + export
    def hybrid(self, pid: str, character_aid: str, effect_aid: str, anchor_event: str | None = "hit",
               offset=(0, 0), start_ms: int = 0, event_offset_ms: int = 0) -> dict:
        a = self.ws.get_asset(pid, character_aid)
        return add_layer(self.ws, a, effect_aid, role="effect", offset=offset, z=1, start_ms=start_ms, anchor_to_event=anchor_event,
                         event_offset_ms=event_offset_ms)

    def export(self, pid: str, asset_ids: list[str], **kw) -> dict:
        return export_assets(self.ws, pid, asset_ids, **kw)

    def contact_sheet_png(self, pid: str, aid: str, scale: int = 2) -> Image.Image:
        from .animation import load_frames
        a = self.ws.get_asset(pid, aid)
        return contact_sheet([im for _, im in load_frames(self.ws, a)], scale=scale, mode=a["art_style"])

    def character_report(self, pid: str, cid: str, required: list[str]) -> dict:
        c = self.ws.get_character(pid, cid)
        return {"masters": check_character_directions(c), "animations": check_animation_set(self.ws, pid, c, required)}

    def status(self) -> dict:
        return {"workspace": self.ws.summary(), "providers": self.registry.describe(),
                "ffmpeg": importers.video_to_gif_check(self.ffmpeg), "samples": adapters.available(), "time": now()}

    # ------------------------------------------------------------------ job handlers
    def _job_procedural(self, p, ctx, budget, job):
        a = self.procedural(job["project_id"], p["builder"], p.get("params"), p.get("name"), p.get("character_id"), ctx=ctx)
        return {"asset_id": a["id"]}

    def _job_replay(self, p, ctx, budget, job):
        a = self.replay_recipe(job["project_id"], Path(p["recipe"]), p.get("name", "replay"), ctx=ctx)
        return {"asset_id": a["id"]}

    def _job_import(self, p, ctx, budget, job):
        p = dict(p)
        path = Path(p.pop("path"))
        extra = [Path(x) for x in p.pop("extra_files", [])] or None
        a = self.import_file(job["project_id"], path, extra_files=extra, **p)
        check_asset(self.ws, a)
        return {"asset_id": a["id"]}

    def _job_generate(self, p, ctx, budget, job):
        r = self.generate(job["project_id"], ctx=ctx, budget=budget, **p)
        return {"asset_id": r.get("id")} if "id" in r else {"character_id": r["character"]["id"]}

    def _job_regenerate(self, p, ctx, budget, job):
        a = self.regenerate_frame(job["project_id"], ctx=ctx, budget=budget, **p)
        return {"asset_id": a["id"]}

    def _job_export(self, p, ctx, budget, job):
        m = self.export(job["project_id"], **p)
        return {"export_id": m["export_id"], "path": m["path"], "qa": m["qa"]["status"]}

    def _job_action_prompts(self, p, ctx, budget, job):
        ctx.progress(0.05, "writing prompts with Codex" if p.get("method") == "codex" else "building prompts")
        plan = self.write_action_prompts(job["project_id"], p["character_id"], p.get("method", "template"), p.get("action_ids"),
                                         p.get("language"), ctx=ctx)
        return {"character_id": p["character_id"], "actions": [a["id"] for a in plan["actions"]]}

    def _job_batch_actions(self, p, ctx, budget, job):
        """p: {"character_id", "action_ids", "provider_id", "workflow_id", "params"} — one strip per action, budgeted."""
        from .jobs import BudgetExceeded
        from .providers.base import Cancelled
        done, failed = [], {}
        ids = p["action_ids"]
        for i, aid in enumerate(ids):
            ctx.check_cancel()
            ctx.progress(i / len(ids), f"action {i + 1}/{len(ids)}: {aid}")
            try:
                a = self.generate_action(job["project_id"], p["character_id"], aid, p["provider_id"], p.get("workflow_id"),
                                         p.get("params"), ctx=ctx, budget=budget)
                done.append(a["id"])
            except (BudgetExceeded, Cancelled):
                raise
            except (GenerationError, StudioError, OSError, ValueError) as e:
                failed[aid] = str(e)
                if len(ids) == 1:
                    raise
        if not done and failed:
            raise GenerationError("All actions failed: " + "; ".join(f"{k}: {v}" for k, v in failed.items())[:1500], "execution_error")
        return {"asset_ids": done, "asset_id": done[-1] if done else None, "failed": failed, "budget_used": budget.used}

    def _job_batch_generate(self, p, ctx, budget, job):
        """p: {"items": [generate kwargs...]} — stops when the explicit budget is exhausted."""
        results = []
        items = p["items"]
        for i, item in enumerate(items):
            ctx.check_cancel()
            ctx.progress(i / len(items), f"item {i + 1}/{len(items)}")
            r = self.generate(job["project_id"], ctx=ctx, budget=budget, **item)
            results.append(r.get("id"))
        return {"asset_ids": results, "budget_used": budget.used}
