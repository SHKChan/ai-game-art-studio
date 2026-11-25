"""Engine A provider — runs procedural builders, agent-authored call lists and recipes on the studio's own
pixel engine (artstudio.engine). In-process, no external binary; always available."""
from __future__ import annotations

import shutil
from pathlib import Path

from ..engine import Engine, EngineError
from .base import GenerationError, GenerationRequest, GenerationResult, JobContext, Provider, ProviderStatus


class ProceduralProvider(Provider):
    id = "procedural"
    name = "Pixel engine (Engine A)"
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
        from ..procedural import BUILDERS
        home = Path(req.params["home"])
        out = Path(req.out_dir or home / "out")
        out.mkdir(parents=True, exist_ok=True)
        eng = Engine(home)
        try:
            if req.params.get("builder"):
                b = BUILDERS.get(req.params["builder"])
                if not b:
                    raise GenerationError(f"Unknown builder {req.params['builder']}", "bad_request")
                doc_id = eng.run(b.build(**(req.params.get("builder_params") or {})), progress=lambda p, m: ctx.progress(p * 0.9, m), cancel=ctx.check_cancel)
            elif req.params.get("calls"):
                doc_id = eng.run(req.params["calls"], progress=lambda p, m: ctx.progress(p * 0.9, m), cancel=ctx.check_cancel)
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
