"""ComfyUI workflow templates: import API-format JSON, declare inputs/mappings/outputs/requirements,
validate against a server's /object_info, and bind parameters. Nothing here hardcodes a checkpoint,
LoRA, custom node or model architecture: those come from the user's workflow and parameters."""
from __future__ import annotations

import copy
import json
import random
import re
from pathlib import Path

from ..schema import require_valid, validate
from ..util import StudioError, check_id, read_json, safe_join, slug, write_json

CATEGORIES = ["text_to_image", "image_to_image", "character_reference", "pose_keyframe", "inpainting",
              "image_to_video", "background_removal"]
OUTPUT_NODE_HINTS = {"SaveImage": "image", "PreviewImage": "image", "SaveAnimatedWEBP": "video", "SaveAnimatedPNG": "video",
                     "VHS_VideoCombine": "video", "SaveVideo": "video", "SaveWEBM": "video"}
# Input names that conventionally reference model files (validated through /object_info COMBO lists).
MODEL_INPUT_NAMES = {"ckpt_name", "lora_name", "vae_name", "control_net_name", "unet_name", "clip_name", "clip_name1",
                     "clip_name2", "model_name", "upscale_model", "ipadapter_file", "clip_vision", "style_model_name",
                     "gligen_name", "hypernetwork_name"}


def is_api_format(wf: dict) -> bool:
    """API format = {node_id: {"class_type": ..., "inputs": {...}}}. The UI/editor format has 'nodes' and 'links'."""
    if not isinstance(wf, dict) or not wf:
        return False
    if "nodes" in wf and "links" in wf:
        return False
    return all(isinstance(v, dict) and "class_type" in v and isinstance(v.get("inputs", {}), dict) for v in wf.values())


def derive_template(wf: dict, *, wid: str, name: str, category: str, description: str = "") -> dict:
    """Build a template from an API-format workflow, auto-suggesting mappings by node conventions.
    Suggestions are editable; ambiguous cases are left unmapped rather than guessed."""
    if not is_api_format(wf):
        raise StudioError("Not an API-format workflow. In ComfyUI enable dev mode and use 'Save (API Format)' / Export (API).")
    if category not in CATEGORIES:
        raise StudioError(f"category must be one of {CATEGORIES}")
    inputs, mappings, outputs, models = {}, {}, [], []
    # Prompt encoders: positive/negative determined by how KSampler-like nodes reference them.
    pos_refs, neg_refs = set(), set()
    for nid, node in wf.items():
        ins = node.get("inputs", {})
        if isinstance(ins.get("positive"), list):
            pos_refs.add(str(ins["positive"][0]))
        if isinstance(ins.get("negative"), list):
            neg_refs.add(str(ins["negative"][0]))
    for nid, node in sorted(wf.items(), key=lambda kv: kv[0]):
        ct, ins = node["class_type"], node.get("inputs", {})
        if "text" in ins and isinstance(ins["text"], str):
            if nid in pos_refs:
                mappings.setdefault("prompt", []).append({"node": nid, "input": "text"})
            elif nid in neg_refs:
                mappings.setdefault("negative_prompt", []).append({"node": nid, "input": "text"})
        for k in ("seed", "noise_seed"):
            if k in ins and isinstance(ins[k], int):
                mappings.setdefault("seed", []).append({"node": nid, "input": k})
        if ct in ("LoadImage",) and "image" in ins:
            key = "reference_image" if "reference_image" not in mappings else f"image_{nid}"
            mappings.setdefault(key, []).append({"node": nid, "input": "image"})
            inputs[key] = {"type": "image", "required": True, "description": f"Image for LoadImage node {nid}"}
        if ct in ("LoadImageMask",) and "image" in ins:
            mappings.setdefault("mask_image", []).append({"node": nid, "input": "image"})
            inputs["mask_image"] = {"type": "mask", "required": True}
        for k in ("width", "height", "steps", "batch_size"):
            if k in ins and isinstance(ins[k], int):
                mappings.setdefault(k, []).append({"node": nid, "input": k})
        if "cfg" in ins and isinstance(ins["cfg"], (int, float)):
            mappings.setdefault("cfg", []).append({"node": nid, "input": "cfg"})
        if "denoise" in ins and isinstance(ins["denoise"], (int, float)):
            mappings.setdefault("denoise", []).append({"node": nid, "input": "denoise"})
        for k, v in ins.items():
            if k in MODEL_INPUT_NAMES and isinstance(v, str):
                models.append({"node": nid, "input": k, "param": f"model_{k}_{nid}"})
                mappings.setdefault(f"model_{k}_{nid}", []).append({"node": nid, "input": k})
                inputs[f"model_{k}_{nid}"] = {"type": "model", "required": False,
                                              "description": f"{ct}.{k} (default from workflow: {v})"}
        if ct in OUTPUT_NODE_HINTS:
            outputs.append({"node": nid, "kind": OUTPUT_NODE_HINTS[ct]})
    for k, t, d in [("prompt", "text", "Positive prompt"), ("negative_prompt", "text", "Negative prompt"),
                    ("seed", "seed", "Seed (-1 = random)"), ("width", "int", ""), ("height", "int", ""),
                    ("steps", "int", ""), ("cfg", "float", ""), ("denoise", "float", ""), ("batch_size", "int", "")]:
        if k in mappings:
            inputs.setdefault(k, {"type": t, "required": k == "prompt", "description": d})
    if not outputs:
        raise StudioError("No output node found (SaveImage/PreviewImage/...). Add one or declare outputs manually.")
    tpl = {"schema": "artstudio.comfy-workflow/1", "id": wid, "name": name, "description": description,
           "category": category, "verification": "unverified", "workflow": wf, "inputs": inputs,
           "mappings": mappings, "outputs": outputs, "required_nodes": sorted({n["class_type"] for n in wf.values()}),
           "required_models": [{k: m[k] for k in ("node", "input", "param")} for m in models],
           "notes": "Auto-derived mappings — review before production use."}
    require_valid(tpl, "workflow")
    check_mappings(tpl)
    return tpl


def check_mappings(tpl: dict) -> None:
    wf = tpl["workflow"]
    for param, targets in tpl["mappings"].items():
        for t in targets:
            node = wf.get(t["node"])
            if node is None:
                raise StudioError(f"Mapping {param} -> node {t['node']} does not exist")
            if t["input"] not in node.get("inputs", {}):
                raise StudioError(f"Mapping {param} -> {t['node']}.{t['input']}: input not present on {node['class_type']}")
    for o in tpl["outputs"]:
        if o["node"] not in wf:
            raise StudioError(f"Output node {o['node']} not in workflow")


def bind(tpl: dict, params: dict, uploaded: dict | None = None) -> tuple[dict, dict]:
    """Return (api_prompt, bound_params). Images must already be uploaded: uploaded maps param -> server filename."""
    wf = copy.deepcopy(tpl["workflow"])
    bound = {}
    uploaded = uploaded or {}
    for name, spec in tpl["inputs"].items():
        if spec["type"] in ("image", "mask"):
            if name in uploaded:
                bound[name] = uploaded[name]
            elif spec.get("required"):
                raise StudioError(f"Workflow input '{name}' requires an image")
            continue
        if name in params and params[name] is not None:
            v = params[name]
            if spec["type"] in ("int", "seed"):
                v = int(v)
            elif spec["type"] == "float":
                v = float(v)
            elif spec["type"] == "bool":
                v = bool(v)
            else:
                v = str(v)
            if spec["type"] == "seed" and v < 0:
                v = random.randint(0, 2**48)
            if "minimum" in spec and v < spec["minimum"] or "maximum" in spec and v > spec["maximum"]:
                raise StudioError(f"{name} out of range")
            bound[name] = v
        elif spec.get("required"):
            raise StudioError(f"Missing required workflow input '{name}'")
    for name, v in bound.items():
        for t in tpl["mappings"].get(name, []):
            wf[t["node"]]["inputs"][t["input"]] = v
    return wf, bound


def validate_against_server(tpl: dict, object_info: dict, api_prompt: dict | None = None) -> dict:
    """Check node classes and model filenames (COMBO choices) against the server's /object_info."""
    wf = api_prompt or tpl["workflow"]
    missing_nodes = sorted({n["class_type"] for n in wf.values() if n["class_type"] not in object_info} |
                           {n for n in tpl.get("required_nodes", []) if n not in object_info})
    missing_models, bad_values = [], []
    for nid, node in wf.items():
        info = object_info.get(node["class_type"])
        if not info:
            continue
        spec_all = {**info.get("input", {}).get("required", {}), **info.get("input", {}).get("optional", {})}
        for k, v in node.get("inputs", {}).items():
            spec = spec_all.get(k)
            if not spec or isinstance(v, list):
                continue
            choices = spec[0] if isinstance(spec[0], list) else (spec[1].get("options") if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict) else None)
            if choices is not None and isinstance(v, str) and v not in choices and not v.startswith("__pending_upload__"):
                rec = {"node": nid, "class_type": node["class_type"], "input": k, "value": v, "available": choices[:50]}
                (missing_models if k in MODEL_INPUT_NAMES else bad_values).append(rec)
    ok = not (missing_nodes or missing_models or bad_values)
    return {"ok": ok, "missing_nodes": missing_nodes, "missing_models": missing_models, "invalid_values": bad_values}


class WorkflowLibrary:
    """Bundled templates (read-only, in repo `workflows/comfyui`) + user templates (workspace)."""

    def __init__(self, bundled_dir: Path, user_dir: Path):
        self.bundled_dir, self.user_dir = Path(bundled_dir), Path(user_dir)
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        out = {}
        for src, d in (("bundled", self.bundled_dir), ("user", self.user_dir)):
            for f in sorted(d.glob("*.json")):
                try:
                    t = read_json(f)
                    errs = validate(t, "workflow")
                    out[t["id"]] = {"id": t["id"], "name": t["name"], "category": t["category"], "source": src,
                                    "verification": t["verification"], "required_nodes": t["required_nodes"],
                                    "required_models": t["required_models"], "inputs": t["inputs"], "valid": not errs,
                                    "errors": errs[:5], "description": t.get("description", "")}
                except (ValueError, KeyError) as e:
                    out[f.stem] = {"id": f.stem, "valid": False, "errors": [str(e)], "source": src}
        return sorted(out.values(), key=lambda t: (t.get("category", ""), t["id"]))

    def get(self, wid: str) -> dict:
        check_id(wid, "workflow id")
        for d in (self.user_dir, self.bundled_dir):
            f = d / f"{wid}.json"
            if f.is_file():
                t = read_json(f)
                require_valid(t, "workflow")
                return t
        raise StudioError(f"Unknown workflow {wid}")

    def import_workflow(self, wf: dict | str, *, name: str, category: str, wid: str | None = None,
                        description: str = "", overrides: dict | None = None) -> dict:
        if isinstance(wf, str):
            wf = json.loads(wf)
        if isinstance(wf, dict) and wf.get("schema") == "artstudio.comfy-workflow/1":
            tpl = wf
            tpl["verification"] = "unverified" if tpl.get("verification") == "production-verified" and not overrides else tpl.get("verification", "unverified")
        else:
            tpl = derive_template(wf, wid=wid or slug(name), name=name, category=category, description=description)
        for k in ("inputs", "mappings", "outputs", "required_models", "required_nodes", "notes"):
            if overrides and k in overrides:
                tpl[k] = overrides[k]
        if wid:
            tpl["id"] = check_id(wid)
        require_valid(tpl, "workflow")
        check_mappings(tpl)
        write_json(safe_join(self.user_dir, f"{tpl['id']}.json"), tpl)
        return tpl

    def set_verification(self, wid: str, status: str) -> dict:
        t = self.get(wid)
        t["verification"] = status
        require_valid(t, "workflow")
        write_json(safe_join(self.user_dir, f"{wid}.json"), t)
        return t

    def delete(self, wid: str) -> None:
        f = safe_join(self.user_dir, f"{check_id(wid)}.json")
        if not f.is_file():
            raise StudioError("Only user-imported workflows can be deleted")
        f.unlink()
