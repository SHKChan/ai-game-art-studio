# Deliverables

`poc/` — proof-of-concept outputs from `python demo/build_poc.py` (SPECIFICATION §15). Regenerate any time; the
working project lives in `workspace/poc` (git-ignored).

| Path | Content |
|---|---|
| `poc/POC_REPORT.json` | machine-readable results of tests A–D and the mock pipeline |
| `poc/contact_sheets/` | contact sheets used for visual inspection |
| `poc/test_a_procedural/` | Engine A assets: frames, sheets, packed atlas + TexturePacker JSON, Cocos plist, GIF/APNG previews, metadata, ZIP; `engine_sources/` = editable engine documents + replayable recipes |
| `poc/test_b_knight/` | knight sample (genuine AI art from Pixel Atelier, demo-only) processed in pixel and HD modes, exported with direction map |
| `poc/test_b_prompt_pack_chibi_adventurer{,_zh-CN}.json` | English and Chinese prompts prepared for the blocked chibi-adventurer generation (Stage B) |
| `poc/test_c_external/`, `poc/test_c_input_cat_greenscreen.mp4` | GIF / sheet / MP4 processing results and the MP4 test input |
| `poc/test_d_hybrid/`, `poc/test_d_hybrid_composite_preview.gif` | character + Engine A effect layer export and composite preview |
| `poc/poc_workspace_backup.zip` | workspace backup (git-ignored) |

Sample art credits: knight — Pixel Atelier (demonstration only, samples/knight/NOTICE.md); torch/cat GIFs — Atelier showcase (MIT).
