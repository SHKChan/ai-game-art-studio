"""Pixel Forge provider — runs procedural builders, agent-authored call lists and recipes on the studio's own
pixel engine (artstudio.engine). In-process, no external binary; always available."""
from __future__ import annotations

import shutil
from pathlib import Path

from ..engine import Engine, EngineError
from .base import GenerationError, GenerationRequest, GenerationResult, JobContext, Provider, ProviderStatus


class ProceduralProvider(Provider):
    id = "procedural"
    name = "Pixel Forge"
    kind = "procedural"

    def status(self) -> ProviderStatus:
        from ..engine.tools import TOOLS
        return ProviderStatus(True, "", {"engine": "artstudio-pixel", "tools": sorted(TOOLS)})

    def capabilities(self) -> dict:
        from ..procedural import BUILDERS
        return {"builders": {k: {"description": b.DESCRIPTION, "params": b.PARAMS, "asset_type": b.ASSET_TYPE} for k, b in BUILDERS.items()},
                "replay": True, "agent_calls": True}

    def engine(self, home: Path) -> Engine:
        return Engine(home)

    def generate(self, req: GenerationRequest, ctx: JobContext) -> GenerationResult:
        """req.params: {"home", "builder" + "builder_params"} | {"home", "calls"} | {"home", "recipe"}."""
        from ..procedural import BUILDERS, cached_build
        home = Path(req.params["home"])
        out = Path(req.out_dir or home / "out")
        out.mkdir(parents=True, exist_ok=True)
        from ..procedural.edits import EditError, apply_post, normalize, recolor_calls
        eng = Engine(home)
        try:
            edits = normalize(req.params.get("edits")) if req.params.get("edits") else None
        except EditError as e:
            raise GenerationError(str(e), "bad_request") from None
        try:
            if req.params.get("builder") or req.params.get("calls"):
                if req.params.get("builder"):
                    b = BUILDERS.get(req.params["builder"])
                    if not b:
                        raise GenerationError(f"Unknown builder {req.params['builder']}", "bad_request")
                    try:
                        calls = cached_build(req.params["builder"], req.params.get("builder_params") or {})
                    except (TypeError, ValueError, KeyError) as e:
                        raise GenerationError(f"Invalid parameters for {req.params['builder']}: {e}", "bad_request") from None
                else:
                    calls = req.params["calls"]
                if edits:
                    calls = recolor_calls(calls, edits)
                doc_id = eng.run(calls, progress=lambda p, m: ctx.progress(p * 0.9, m), cancel=ctx.check_cancel)
                if edits:
                    apply_post(eng, doc_id, edits, calls)
            elif req.params.get("recipe"):
                doc_id = eng.replay(Path(req.params["recipe"]))
            else:
                raise GenerationError("Need builder, calls or recipe", "bad_request")
            frames, durs, meta = eng.export_frames(doc_id)
        except EngineError as e:
            raise GenerationError(str(e), "engine_error") from None
        paths = []
        for i, f in enumerate(frames):
            p = out / f"frame_{i:03d}.png"
            f.save(p)
            paths.append(p)
        shutil.copyfile(eng.doc_dir(doc_id) / "doc.recipe", out / "doc.recipe")
        ctx.progress(1.0, "rendered")
        return GenerationResult(paths, {"doc_id": doc_id, "durations": durs, "recipe": str(out / "doc.recipe"), "calls": eng.calls,
                                        "engine_meta": meta.get("meta", {})})
