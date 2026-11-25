"""Stage B — production integration smoke test. Run on the computer that has a working ComfyUI.

  python scripts/production_smoke_test.py --comfy http://127.0.0.1:8188 --checkpoint <your_ckpt.safetensors> \
      [--controlnet <openpose.safetensors>] [--reference path/to/character.png] [--budget 4] [--steps 20] [--size 768]

What it verifies (each step PASS / FAIL / SKIP, written to smoke_report.json + smoke_report.md):
  1  ComfyUI reachable, version, GPU devices (fails on the mock server unless --allow-mock)
  2  /object_info node discovery; the checkpoint (and ControlNet) exist on this server
  3  bundled workflow templates validated against this server (missing nodes/models listed)
  4  text-to-image generation (1 budgeted call) -> PNG decodes, non-empty
  5  image-to-image with reference -> studio import, background removal, normalisation, QA, export
  6  pose-keyframe workflow (only if --controlnet given)
  7  cancellation of a running prompt (interrupt) -> job ends 'cancelled'
  8  studio still works with ComfyUI unreachable (bad URL) -> provider reported unavailable

It does NOT judge artistic quality or identity consistency: it writes contact sheets for a human review.
Never run against the mock and report Stage B as passed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--controlnet")
    ap.add_argument("--reference", default=str(ROOT / "samples" / "knight" / "idle" / "poster.png"))
    ap.add_argument("--pose", default=str(ROOT / "samples" / "knight" / "run" / "poster.png"))
    ap.add_argument("--budget", type=int, default=4, help="max generation calls this test may spend")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--workspace", default=str(ROOT / "workspace" / "stage-b-smoke"))
    ap.add_argument("--out", default=str(ROOT / "workspace" / "stage-b-smoke-report"))
    ap.add_argument("--allow-mock", action="store_true", help="for rehearsing the script only; the report will say MOCK")
    a = ap.parse_args()

    os.environ["ARTSTUDIO_WORKSPACE"] = a.workspace
    os.environ["COMFYUI_URL"] = a.comfy
    from artstudio.config import load_config
    from artstudio.jobs import Budget
    from artstudio.service import Studio
    cfg = load_config()
    cfg.comfyui.job_timeout_s = a.timeout
    s = Studio(cfg, workers=1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    steps, budget = [], Budget(a.budget)
    prov = s.registry.get("comfyui")
    base = {"checkpoint": a.checkpoint, "steps": a.steps}

    def step(name, fn):
        t0 = time.time()
        try:
            r = fn()
            status = "SKIP" if r == "SKIP" else "PASS"
            steps.append({"step": name, "status": status, "seconds": round(time.time() - t0, 1), "detail": r if r != "SKIP" else None})
        except Exception as e:  # noqa: BLE001
            steps.append({"step": name, "status": "FAIL", "seconds": round(time.time() - t0, 1), "error": str(e),
                          "details": getattr(e, "details", None), "trace": traceback.format_exc()[-1500:]})
        print(f"{steps[-1]['status']:4}  {name}", flush=True)

    def s1():
        st = prov.status()
        if not st.available:
            raise RuntimeError(st.reason)
        if st.details.get("is_mock") and not a.allow_mock:
            raise RuntimeError("Connected to the MOCK ComfyUI. Stage B requires a real server.")
        return st.details

    def s2():
        info = prov.object_info(refresh=True)
        ck = info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        if a.checkpoint not in ck:
            raise RuntimeError(f"checkpoint not on server; available: {ck[:20]}")
        res = {"nodes": len(info), "checkpoints": len(ck)}
        if a.controlnet:
            cn = info.get("ControlNetLoader", {}).get("input", {}).get("required", {}).get("control_net_name", [[]])[0]
            if a.controlnet not in cn:
                raise RuntimeError(f"controlnet not on server; available: {cn[:20]}")
        return res

    def s3():
        rep = {}
        for w in s.registry.workflows.list():
            params = {**base, "controlnet": a.controlnet, "video_checkpoint": a.checkpoint}
            try:
                rep[w["id"]] = prov.check_workflow(w["id"], {k: v for k, v in params.items() if v})
            except Exception as e:  # noqa: BLE001
                rep[w["id"]] = {"ok": False, "error": str(e)}
        (out / "workflow_compatibility.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        return {k: v.get("ok") for k, v in rep.items()}

    p = s.ws.create_project("Stage B smoke", pid=f"stage-b-{int(time.time())}")
    c = s.ws.create_character(p["id"], "Smoke Adventurer", "four", "pixel", cid="smoke",
                              description="chibi fantasy adventurer, red hood, blonde hair, red cape, brown outfit, brown boots, sword")

    def s4():
        r = s.generate(p["id"], "comfyui", kind="master_candidate", character_id="smoke", direction="south", workflow_id="sd-text-to-image",
                       params={**base, "width": a.size, "height": a.size}, budget=budget)
        cand = r["character"]["candidates"][-1]
        if cand["is_test_fixture"] and not a.allow_mock:
            raise RuntimeError("result flagged as fixture")
        return {"candidate": cand["file"]}

    def s5():
        asset = s.generate(p["id"], "comfyui", character_id="smoke", template="idle", direction="south", workflow_id="sd-image-to-image",
                           reference=a.reference, params={**base, "denoise": 0.6}, layout={"method": "auto"}, budget=budget)
        s.contact_sheet_png(p["id"], asset["id"], 2).save(out / "i2i_contact_sheet_FOR_HUMAN_REVIEW.png")
        m = s.export(p["id"], [asset["id"]], name="smoke_i2i")
        return {"asset": asset["id"], "frames": len(asset["animation"]["frames"]), "qa": asset["qa"]["deterministic"]["status"],
                "export_qa": m["qa"]["status"], "export": m["path"]}

    def s6():
        if not a.controlnet:
            return "SKIP"
        asset = s.generate(p["id"], "comfyui", character_id="smoke", template="walk", direction="east", workflow_id="sd-pose-keyframe",
                           reference=a.reference, params={**base, "controlnet": a.controlnet, "pose_image": a.pose}, budget=budget)
        s.contact_sheet_png(p["id"], asset["id"], 2).save(out / "pose_contact_sheet_FOR_HUMAN_REVIEW.png")
        return {"asset": asset["id"]}

    def s7():
        budget.spend(1)
        job = s.jobs.submit("generate", dict(provider_id="comfyui", workflow_id="sd-text-to-image", character_id="smoke",
                                             params={**base, "steps": max(a.steps, 40), "width": a.size, "height": a.size}), project_id=p["id"])
        for _ in range(300):  # cancel as soon as the prompt is on the server
            j = s.jobs.get(job["id"])
            if j.get("state", {}).get("prompt_id") or j["status"] not in ("queued", "running"):
                break
            time.sleep(0.1)
        s.jobs.cancel(job["id"])
        j = s.jobs.wait(job["id"], 120)
        if j["status"] != "cancelled":
            raise RuntimeError(f"job ended {j['status']} (it may have finished before cancel; rerun with more steps)")
        return {"job": job["id"]}

    def s8():
        from artstudio.config import ComfyConfig
        from artstudio.providers.comfyui import ComfyUIProvider
        st = ComfyUIProvider(ComfyConfig(url="http://127.0.0.1:9", connect_timeout_s=1), s.registry.workflows).status()
        if st.available:
            raise RuntimeError("unreachable server reported available")
        return {"reason": st.reason}

    for name, fn in [("1 server reachable (not mock)", s1), ("2 node & model discovery", s2), ("3 workflow compatibility", s3),
                     ("4 text-to-image master candidate", s4), ("5 image-to-image -> import -> QA -> export", s5),
                     ("6 pose keyframe (ControlNet)", s6), ("7 cancellation", s7), ("8 offline fallback", s8)]:
        step(name, fn)
    ok = all(x["status"] in ("PASS", "SKIP") for x in steps)
    report = {"stage": "B", "mock": bool(prov.status().details.get("is_mock")) if prov.status().available else None,
              "server": a.comfy, "checkpoint": a.checkpoint, "budget_used": budget.used, "overall": "PASS" if ok else "FAIL",
              "steps": steps, "human_review_required": ["identity consistency vs reference", "art quality", "pose/anatomy", "GPU time acceptable"]}
    (out / "smoke_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md = [f"# Stage B smoke test — {report['overall']}", "", f"Server {a.comfy} · checkpoint `{a.checkpoint}` · budget used {budget.used}", "",
          "| step | status | s |", "|---|---|---|"] + [f"| {x['step']} | {x['status']} | {x['seconds']} |" for x in steps] + \
         ["", "Technical PASS does not mean visual consistency. Review the *_FOR_HUMAN_REVIEW.png contact sheets."]
    (out / "smoke_report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nOverall: {report['overall']}  -> {out / 'smoke_report.md'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
