"""Regenerate the bundled ComfyUI workflow templates in workflows/comfyui/.

Bundled templates use only core ComfyUI node classes (except background removal, which needs a
custom node). They contain NO model names: every model file is a required parameter that the user
supplies for their own server. All are 'unverified' until Stage B production testing passes.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "workflows" / "comfyui"
CKPT = "SET_CHECKPOINT_PARAMETER"


def base_sd(i2i=False, latent_from="5"):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 28, "cfg": 6.5, "sampler_name": "euler", "scheduler": "normal",
                                                    "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                                                    "latent_image": [latent_from, 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "artstudio", "images": ["8", 0]}},
    }
    if i2i:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": "reference.png"}}
        wf["11"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}}
        wf["3"]["inputs"]["latent_image"] = ["11", 0]
        wf["3"]["inputs"]["denoise"] = 0.55
    else:
        wf["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}}
    return wf


COMMON_INPUTS = {
    "checkpoint": {"type": "model", "required": True, "model_folder": "checkpoints", "description": "Checkpoint filename on YOUR server (see /object_info CheckpointLoaderSimple)."},
    "prompt": {"type": "text", "required": True, "description": "Positive prompt (built from the locked character master)."},
    "negative_prompt": {"type": "text", "required": False},
    "seed": {"type": "seed", "required": False, "description": "-1 = random"},
    "steps": {"type": "int", "required": False, "minimum": 1, "maximum": 200},
    "cfg": {"type": "float", "required": False, "minimum": 0, "maximum": 30},
    "sampler_name": {"type": "string", "required": False},
    "scheduler": {"type": "string", "required": False},
}
COMMON_MAP = {
    "checkpoint": [{"node": "4", "input": "ckpt_name"}], "prompt": [{"node": "6", "input": "text"}],
    "negative_prompt": [{"node": "7", "input": "text"}], "seed": [{"node": "3", "input": "seed"}],
    "steps": [{"node": "3", "input": "steps"}], "cfg": [{"node": "3", "input": "cfg"}],
    "sampler_name": [{"node": "3", "input": "sampler_name"}], "scheduler": [{"node": "3", "input": "scheduler"}],
}


def tpl(id_, name, cat, wf, inputs, mappings, outputs, models, desc, notes=""):
    return {"schema": "artstudio.comfy-workflow/1", "id": id_, "name": name, "category": cat, "verification": "unverified",
            "description": desc, "workflow": wf, "inputs": inputs, "mappings": mappings, "outputs": outputs,
            "required_nodes": sorted({n["class_type"] for n in wf.values()}), "required_models": models, "notes": notes}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = []
    wf = base_sd()
    t.append(tpl("sd-text-to-image", "Text to image (core SD nodes)", "text_to_image", wf,
                 {**COMMON_INPUTS, "width": {"type": "int", "required": False}, "height": {"type": "int", "required": False},
                  "batch_size": {"type": "int", "required": False, "minimum": 1, "maximum": 8}},
                 {**COMMON_MAP, "width": [{"node": "5", "input": "width"}], "height": [{"node": "5", "input": "height"}],
                  "batch_size": [{"node": "5", "input": "batch_size"}]},
                 [{"node": "9", "kind": "image"}], [{"node": "4", "input": "ckpt_name", "param": "checkpoint"}],
                 "Concept art / character candidates from text. Model-agnostic: supply your own checkpoint."))
    wf = base_sd(i2i=True)
    i2i_inputs = {**COMMON_INPUTS, "reference_image": {"type": "image", "required": True}, "denoise": {"type": "float", "required": False, "minimum": 0, "maximum": 1}}
    i2i_map = {**COMMON_MAP, "reference_image": [{"node": "10", "input": "image"}], "denoise": [{"node": "3", "input": "denoise"}]}
    t.append(tpl("sd-image-to-image", "Image to image (core SD nodes)", "image_to_image", wf, i2i_inputs, i2i_map,
                 [{"node": "9", "kind": "image"}], [{"node": "4", "input": "ckpt_name", "param": "checkpoint"}],
                 "Restyle or refine an image while keeping its composition."))
    wf2 = json.loads(json.dumps(wf))
    wf2["3"]["inputs"]["denoise"] = 0.35
    t.append(tpl("sd-character-reference", "Character reference variation (img2img, low denoise)", "character_reference", wf2, i2i_inputs, i2i_map,
                 [{"node": "9", "kind": "image"}], [{"node": "4", "input": "ckpt_name", "param": "checkpoint"}],
                 "Directional master candidates from an approved master. Low denoise keeps identity; review every candidate.",
                 "Identity preservation with plain img2img is limited; production setups usually add IPAdapter/reference nodes — import such a workflow via the Import dialog."))
    wf3 = json.loads(json.dumps(wf))
    wf3["12"] = {"class_type": "LoadImage", "inputs": {"image": "pose.png"}}
    wf3["13"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "SET_CONTROLNET_PARAMETER"}}
    wf3["14"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "control_net": ["13", 0],
                                                                       "image": ["12", 0], "strength": 0.9, "start_percent": 0.0, "end_percent": 0.85}}
    wf3["3"]["inputs"]["positive"] = ["14", 0]
    wf3["3"]["inputs"]["negative"] = ["14", 1]
    t.append(tpl("sd-pose-keyframe", "Pose-controlled keyframe (ControlNet, core nodes)", "pose_keyframe", wf3,
                 {**i2i_inputs, "pose_image": {"type": "image", "required": True, "description": "Pose/control image (e.g. OpenPose skeleton)"},
                  "controlnet": {"type": "model", "required": True, "model_folder": "controlnet"},
                  "control_strength": {"type": "float", "required": False, "minimum": 0, "maximum": 2}},
                 {**i2i_map, "pose_image": [{"node": "12", "input": "image"}], "controlnet": [{"node": "13", "input": "control_net_name"}],
                  "control_strength": [{"node": "14", "input": "strength"}]},
                 [{"node": "9", "kind": "image"}],
                 [{"node": "4", "input": "ckpt_name", "param": "checkpoint"}, {"node": "13", "input": "control_net_name", "param": "controlnet"}],
                 "Keyframe for one animation pose: character reference (img2img) + pose control image."))
    wf4 = json.loads(json.dumps(base_sd(i2i=True)))
    wf4["15"] = {"class_type": "LoadImageMask", "inputs": {"image": "mask.png", "channel": "alpha"}}
    wf4["11"] = {"class_type": "VAEEncodeForInpaint", "inputs": {"pixels": ["10", 0], "vae": ["4", 2], "mask": ["15", 0], "grow_mask_by": 6}}
    wf4["3"]["inputs"]["denoise"] = 1.0
    t.append(tpl("sd-inpaint", "Inpaint region (core nodes)", "inpainting", wf4,
                 {**i2i_inputs, "mask_image": {"type": "mask", "required": True, "description": "PNG whose alpha marks the region to repaint"}},
                 {**i2i_map, "mask_image": [{"node": "15", "input": "image"}]},
                 [{"node": "9", "kind": "image"}], [{"node": "4", "input": "ckpt_name", "param": "checkpoint"}],
                 "Fix one region of a frame (hand, weapon, face) without regenerating the whole pose."))
    wf5 = {
        "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {"ckpt_name": "SET_VIDEO_CHECKPOINT_PARAMETER"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": "keyframe.png"}},
        "3": {"class_type": "SVD_img2vid_Conditioning", "inputs": {"clip_vision": ["1", 1], "init_image": ["2", 0], "vae": ["1", 2], "width": 576,
                                                                   "height": 576, "video_frames": 14, "motion_bucket_id": 60, "fps": 8, "augmentation_level": 0.0}},
        "4": {"class_type": "VideoLinearCFGGuidance", "inputs": {"model": ["1", 0], "min_cfg": 1.0}},
        "5": {"class_type": "KSampler", "inputs": {"seed": 0, "steps": 20, "cfg": 2.5, "sampler_name": "euler", "scheduler": "karras", "denoise": 1.0,
                                                    "model": ["4", 0], "positive": ["3", 0], "negative": ["3", 1], "latent_image": ["3", 2]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveAnimatedWEBP", "inputs": {"images": ["6", 0], "filename_prefix": "artstudio_video", "fps": 8.0, "lossless": True,
                                                            "quality": 90, "method": "default"}},
    }
    t.append(tpl("svd-image-to-video", "Image to video (Stable Video Diffusion core nodes)", "image_to_video", wf5,
                 {"video_checkpoint": {"type": "model", "required": True, "model_folder": "checkpoints"},
                  "reference_image": {"type": "image", "required": True}, "seed": {"type": "seed", "required": False},
                  "video_frames": {"type": "int", "required": False, "minimum": 2, "maximum": 64}},
                 {"video_checkpoint": [{"node": "1", "input": "ckpt_name"}], "reference_image": [{"node": "2", "input": "image"}],
                  "seed": [{"node": "5", "input": "seed"}], "video_frames": [{"node": "3", "input": "video_frames"}]},
                 [{"node": "7", "kind": "video"}], [{"node": "1", "input": "ckpt_name", "param": "video_checkpoint"}],
                 "Motion from a single keyframe. Output is an animated WebP; import it in the Import Studio for frame extraction.",
                 "Experimental: video models drift identity; use for effects/secondary motion, review frame by frame."))
    wf6 = {"1": {"class_type": "LoadImage", "inputs": {"image": "input.png"}},
           "2": {"class_type": "InspyrenetRembg", "inputs": {"image": ["1", 0], "torchscript_jit": "default"}},
           "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "artstudio_rembg"}}}
    t.append(tpl("rembg-inspyrenet", "Background removal (custom node: ComfyUI-Inspyrenet-Rembg)", "background_removal", wf6,
                 {"reference_image": {"type": "image", "required": True}}, {"reference_image": [{"node": "1", "input": "image"}]},
                 [{"node": "3", "kind": "image"}], [],
                 "Matting for complex backgrounds. Requires the custom node pack; the app checks /object_info before running.",
                 "Custom node class name 'InspyrenetRembg' is taken from the ComfyUI-Inspyrenet-Rembg pack and is UNVERIFIED here. "
                 "The built-in colour-key remover (Import Studio) works offline for solid/checker backgrounds."))
    for x in t:
        (OUT / f"{x['id']}.json").write_text(json.dumps(x, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(t)} templates to {OUT}")


if __name__ == "__main__":
    main()
