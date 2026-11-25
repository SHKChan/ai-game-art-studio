# AI Game Art Studio — Repository Integration and Implementation

## 1. Project Objective

Build a unified, extensible, local-first AI game art production studio by studying, integrating, and extending the following two open-source projects:

- Atelier: https://github.com/marmikshah/atelier
- Pixel Atelier: https://github.com/jinxingtaire/pixel-atelier

The final product must combine:

1. Agent-driven procedural pixel-art drawing.
2. AI-generated character artwork and keyframe animation.
3. Automated image and animation post-processing.
4. Visual asset editing, inspection, and quality assurance.
5. Reusable art-production skills and workflows.
6. Production-ready game asset export.

Do not simply combine the repositories into one directory. Build a genuinely integrated workflow with shared asset management, consistent project schemas, reusable tools, and a unified user interface.

The primary target is indie 2D game development, including top-down RPGs, side-scrolling RPGs, idle ARPGs, and casual games.

The application should support both pixel art and high-resolution hand-drawn game artwork.

## 2. Mandatory Repository Research

Before implementing anything:

- Clone both repositories.
- Inspect their complete source code, README files, architecture, dependencies, licenses, skills, examples, tests, tool schemas, production guidelines, and existing workflows.
- Run their existing demos and automated tests.
- Inspect actual generated artwork and animation quality.
- Identify reusable components, incompatible assumptions, duplicated functionality, and technical limitations.
- Study successful showcase recipes and reproduce representative examples.
- Record the upstream commit hashes.

Do not assume that a feature exists merely because it is mentioned in documentation.

Produce the following research documents:

- `docs/upstream-analysis.md`
- `docs/feature-mapping.md`
- `docs/integration-architecture.md`
- `docs/upstream-limitations.md`

After documenting the findings, proceed directly with implementation. Do not stop at the research or planning stage.

## 3. Integration Strategy

Use Pixel Atelier as the preferred foundation for the visual workspace, animation pipeline, project management, and asset inspection, subject to validation of its actual implementation.

Integrate Atelier as an independent procedural drawing engine through its supported CLI, MCP, or other verified interfaces.

Do not unnecessarily rewrite Atelier's Rust engine in Python or TypeScript.

Preserve upstream compatibility where practical.

Build adapters rather than tightly coupling the two codebases.

If an upstream feature is incomplete or unsuitable, implement a clearly documented replacement or extension.

Preserve all applicable upstream licenses and attribution.

## 4. Unified Art Production Engines

Implement three initial production workflows.

### Engine A — Procedural Art

Use Atelier for deterministic, Agent-controlled drawing.

Target assets:

- Pixel-art characters and monsters.
- Equipment and inventory icons.
- Weapons and armor.
- Potions and treasure chests.
- Tilesets and environmental objects.
- UI icons.
- Fire, ice, lightning, smoke, and magical effects.
- Procedurally animated sprites.

Expose reusable drawing operations, palette management, layer management, animation frame management, preview, export, and replay recipes.

Preserve editable source documents and reproducible drawing instructions.

### Engine B — AI Keyframe Generation

Use Pixel Atelier's existing generation workflow wherever practical.

Target assets:

- Character concept art.
- Character master references.
- Directional idle sprites.
- Walking and running animations.
- Attack and spellcasting animations.
- Monster animations.
- High-resolution chibi characters.
- Hand-drawn game sprites.

Support reference-image-driven generation with explicit constraints for character identity, proportions, clothing, hairstyle, weapon geometry, color palette, and camera direction.

Support multiple generation candidates, rejected versions, selective regeneration, and approved master references.

Do not require procedural redrawing of complex AI-generated character artwork.

### Engine C — External Asset Processing

Support artwork generated outside the application.

Accept:

- Individual PNG images.
- Transparent PNG sequences.
- Sprite sheets.
- GIF and APNG animations.
- MP4 and WebM videos.

Implement import, frame extraction, background removal, sprite segmentation, frame alignment, scaling, animation timing, and export.

This workflow must remain usable without access to a paid image-generation service.

## 5. Modular Provider Architecture

Implement a provider abstraction for different asset-generation technologies.

Initial providers:

- `AtelierProceduralProvider`
- `CodexImageProvider`
- `ExternalAssetProvider`

Prepare extension interfaces for:

- Local image-generation models.
- ComfyUI.
- External image-generation APIs.
- Image-to-video models.
- Skeleton-based animation tools.
- Additional MCP art tools.

Do not implement unsupported or undocumented APIs.

Verify actual provider availability and capabilities at runtime.

A provider that is not installed or authenticated must be displayed as unavailable, not silently replaced with another technology.

## 6. Character Master System

Create a centralized character identity system.

Each character must support:

- Unique character ID.
- Character name and description.
- Original concept artwork.
- Approved master reference.
- Directional master references.
- Character proportions.
- Color palette.
- Clothing and accessories.
- Weapon reference.
- Camera angle.
- Visual style.
- Reference constraints.
- Negative constraints.
- Generation history.
- Approved and rejected versions.

Support three directional configurations:

- Side-scrolling: left and right.
- Four-directional: north, east, south, west.
- Eight-directional: cardinal and diagonal directions.

Do not represent directional sprites by rotating a front-facing image.

Horizontal mirroring must be optional because asymmetric weapons, accessories, and costumes may require independently generated directions.

Once approved, master references must remain locked unless explicitly replaced.

## 7. Animation Production System

Support user-defined animation names, directions, frame counts, frame durations, and loop settings.

Provide default action templates:

- Idle
- Walk
- Run
- Attack
- Combo attack
- Cast
- Dodge
- Dash
- Jump
- Hit
- Death
- Interact

For each animation, support:

- Key pose planning.
- Reference-based frame generation.
- Full sprite-sheet generation.
- Imported video or GIF frame extraction.
- Procedural frame generation.
- Selective frame regeneration.
- Manual frame replacement.
- Frame reordering.
- Frame duplication.
- Frame deletion.
- Variable frame duration.
- Animation looping.
- Animation events.

Attack animations should support anticipation, action, impact, follow-through, and recovery phases.

Walking animations should support contact, down, passing, and up poses.

Preserve natural movement rather than forcing every frame into identical bounding boxes.

Allow separate body, weapon, and effect layers when appropriate.

## 8. Dual Art Processing Modes

Implement two independent processing modes.

### Pixel Art Mode

- Nearest-neighbor scaling.
- Optional fixed-palette quantization.
- Optional binary alpha.
- Integer pixel alignment.
- Pixel-grid inspection.
- Crisp pixel edges.
- Pixel-art-friendly export.

### HD Illustration Mode

- Preserve original colors.
- Preserve partial alpha transparency.
- Preserve anti-aliased edges.
- High-quality image resampling.
- No mandatory palette quantization.
- No mandatory binary alpha conversion.
- Preserve hand-painted textures and soft shading.

Both modes must share the same animation management, alignment, quality inspection, and export systems.

Never automatically convert high-resolution hand-drawn characters into pixel art unless explicitly requested.

## 9. Frame Normalization and Alignment

Implement a shared frame-processing pipeline.

Required capabilities:

- Background removal.
- Alpha-channel validation.
- Sprite boundary detection.
- Transparent padding.
- Consistent animation-group scaling.
- Logical root anchor.
- Ground-contact anchor.
- Configurable reference points.
- Support-foot alignment.
- Optional torso alignment.
- Weapon and effect boundary preservation.
- Canvas expansion.
- Sprite-sheet segmentation.
- Frame trimming.
- Restoration of original frame offsets.

Critical rules:

- Do not independently scale every frame to fit its own bounding box.
- Do not independently center every frame without considering motion.
- Do not eliminate intentional vertical motion during jumping, walking, or attacks.
- Do not crop weapons or effects.
- Do not force all animations to use identical visible sprite dimensions.

Preserve both original source frames and processed frames.

All transformations should be reversible or reproducible.

## 10. Visual Animation Laboratory

Build a unified local web-based workspace.

Prefer extending the existing Pixel Atelier interface when its architecture is suitable.

The UI must contain the following functional workspaces:

### Project Library

Manage games, characters, monsters, effects, icons, environment assets, and shared resources.

### Character Studio

Display concept artwork, locked references, directional sprites, equipment, palettes, and generation history.

### Animation Studio

Provide:

- Frame timeline.
- Animation playback.
- Adjustable FPS.
- Variable frame duration.
- Loop toggle.
- Single-frame stepping.
- Zoom.
- Background switching.
- Checkerboard transparency.
- Onion-skin preview.
- Ground reference line.
- Anchor editing.
- Frame comparison.
- Frame replacement.
- Selective regeneration.
- Animation event markers.

### Procedural Drawing Studio

Provide:

- Atelier document selection.
- Tool and recipe execution.
- Layer and frame inspection.
- Drawing previews.
- Palette inspection.
- Recipe replay.
- Editable source preservation.

### Import and Processing Studio

Provide:

- Drag-and-drop image import.
- Sprite-sheet slicing.
- GIF and video frame extraction.
- Background removal.
- Batch normalization.
- Before-and-after comparison.

### Export Studio

Provide individual PNG frames, sprite sheets, packed atlases, GIF previews, JSON metadata, and engine-specific export options.

The UI should be responsive, support dark mode, and use a consistent professional design.

All controls must be functional. Do not create a cosmetic dashboard with dummy controls.

## 11. Shared Asset Schema

Define a versioned, engine-independent asset manifest.

Each asset should support:

- Asset ID.
- Asset type.
- Character reference.
- Art style.
- Generation provider.
- Source files.
- Processed files.
- Generation prompt.
- Reference images.
- Processing parameters.
- Version history.
- Quality inspection results.
- Export configurations.

Animation metadata should contain:

- Animation name.
- Direction.
- Frame list.
- Frame duration.
- Source dimensions.
- Trimmed dimensions.
- Frame offsets.
- Pivot and anchor.
- Loop configuration.
- Animation events.
- Atlas coordinates.

Use a documented schema with validation.

Ensure that project data can be backed up and migrated between versions.

## 12. Agent Skills and Automation

Extract, study, and adapt useful skills and production guidelines from both repositories.

Create reusable Agent skills for:

- Procedural pixel-art generation.
- Game icon generation.
- Tileset generation.
- Character master creation.
- Four-directional character generation.
- Eight-directional character generation.
- Idle animation.
- Walking animation.
- Attack animation.
- Skill-effect animation.
- Sprite-sheet processing.
- GIF and video frame extraction.
- Animation consistency inspection.
- Game-engine export.

Each skill must define:

- Required inputs.
- Recommended workflow.
- Tool-selection rules.
- Prompt templates.
- Quality criteria.
- Common failure modes.
- Recovery strategies.
- Output specification.

Create an Agent-facing CLI or MCP interface for managing projects, invoking workflows, inspecting outputs, approving assets, and exporting assets.

Implement asynchronous local job execution with progress, cancellation, retry, and resumable generation where supported.

Avoid unnecessary paid generation calls.

Require an explicit configurable generation budget for unattended batch jobs.

## 13. Automated Quality Assurance

Implement deterministic checks for:

- Empty frames.
- Invalid transparency.
- Unexpected backgrounds.
- Clipped sprites.
- Inconsistent canvas dimensions.
- Duplicate frames.
- Unexpected scale changes.
- Anchor discontinuities.
- Excessive unintended positional jitter.
- Invalid frame durations.
- Missing directions.
- Invalid atlas coordinates.
- Missing export files.

Add optional visual-model-assisted checks for:

- Character identity drift.
- Clothing changes.
- Weapon deformation.
- Extra or missing limbs.
- Inconsistent proportions.
- Art-style drift.
- Unnatural motion.
- Poor animation transitions.

Clearly distinguish deterministic validation from probabilistic visual assessment.

Do not claim visual consistency merely because technical validation passes.

Support manual approval and rejection.

## 14. Game Engine Export

Prioritize Cocos Creator 3.x compatibility.

Also provide generic PNG and JSON exports that can be adapted to:

- Godot.
- Phaser.
- PixiJS.
- Unity.

Export animation frames, sprite sheets, texture atlases, anchor metadata, animation timing, directional mappings, and gameplay event markers.

Provide a TypeScript integration example for directional movement and animation playback in Cocos Creator.

Verify the exported resource format instead of inventing unsupported engine-specific formats.

## 15. Mandatory Proof-of-Concept Assets

Create an isolated demonstration project containing the following real assets.

### Test A — Procedural Asset Production

Using Atelier:

- 64×64 fantasy health potion.
- 64×64 treasure chest.
- Eight-frame treasure chest opening animation.
- Eight-frame fireball animation.
- Eight-frame sword-slash effect.

### Test B — AI Character Production

Use a provided character reference image when available.

Otherwise create a chibi fantasy adventurer with:

- Red hood.
- Blonde hair.
- Red cape.
- Brown adventurer outfit.
- Brown boots.
- Sword.

Produce:

- Four directional idle sprites.
- Four directional walking animations.
- Four directional attack animations.

Use 4–8 frames per walking direction and 6–10 frames per attack direction.

Allow a reduced initial test of one walking direction and one attack direction before consuming additional generation resources.

Test both pixel-art and HD illustration workflows without unnecessarily regenerating artwork.

### Test C — External Animation Processing

Import a real GIF, video, or sprite sheet.

Demonstrate:

- Frame extraction.
- Background processing.
- Alignment.
- Animation preview.
- Export.

### Test D — Hybrid Animation

Combine an AI-generated character attack animation with an Atelier-generated sword-slash or magical effect.

Maintain independent character and effect timing and export both layers with aligned metadata.

Do not use placeholder drawings to conceal failed generation.

If a required generation provider is unavailable, complete the offline parts using genuine supplied or upstream demonstration assets and document the blocker.

## 16. Engineering Requirements

Target Windows-first local development while retaining cross-platform compatibility.

Prefer the existing upstream technology stack unless there is a compelling reason to change it.

Requirements:

- Modular architecture.
- Typed and validated interfaces.
- Reliable local persistence.
- Secure subprocess execution.
- No arbitrary shell execution from untrusted UI inputs.
- Safe file-path validation.
- Configurable workspace directory.
- No hardcoded secrets.
- No unnecessary external network access.
- No mandatory cloud database.
- No mandatory paid API.
- Structured logging.
- Error handling.
- Unit and integration tests.
- Reproducible dependency installation.
- Clear setup instructions.

Provide an easy Windows startup mechanism, preferably `start.ps1`, and an equivalent Linux/macOS startup script.

Docker support is optional, not mandatory.

Keep generated assets outside the application source directory.

Do not modify unrelated existing game projects.

## 17. Testing and Acceptance

Before declaring the implementation complete:

1. Run upstream tests.
2. Run all newly implemented tests.
3. Verify application startup.
4. Verify Atelier integration.
5. Verify Pixel Atelier workflow integration.
6. Verify actual asset import and processing.
7. Verify animation playback.
8. Verify project persistence after restart.
9. Verify frame editing and regeneration interfaces.
10. Verify real exported PNG, GIF, atlas, and JSON files.
11. Inspect generated visuals and animation playback.
12. Test failure handling when generation providers are unavailable.
13. Verify that existing upstream functionality has not been unintentionally removed.

Perform browser-based UI testing using Playwright or equivalent when available.

Do not report a test as passed unless it was actually executed.

Record test results, visual defects, remaining limitations, and integration decisions.

## 18. Implementation Priorities

### Phase 1 — Functional MVP

- Repository integration.
- Shared project and asset schemas.
- Unified workspace.
- Atelier procedural provider.
- Existing Pixel Atelier generation and processing pipeline.
- PNG, GIF, and sprite-sheet import.
- Animation preview and export.

### Phase 2 — RPG Production

- Four-directional character masters.
- Custom animation-direction matrix.
- HD illustration mode.
- Improved alignment and normalization.
- Hybrid character and effect animation.
- Cocos Creator export.

### Phase 3 — Agent Automation

- Unified CLI or MCP interface.
- Reusable production skills.
- Generation job queue.
- Quality inspection.
- Selective regeneration.
- Batch asset production.

Complete and verify each phase before expanding its scope.

Do not spend excessive time building infrastructure before demonstrating actual art production.

## 19. Deliverables

Provide:

- Complete working source code.
- Unified local web application.
- Installation and startup scripts.
- Upstream license attribution.
- Architecture documentation.
- Agent skills and prompt templates.
- Real demonstration assets.
- Editable procedural art documents.
- Reproducible drawing recipes.
- Animation previews.
- Exported game assets.
- Cocos Creator integration example.
- Automated tests.
- Test and quality evaluation report.
- Known limitations and future improvements.

The final README must explain how to install, launch, configure, and use the studio.

The final implementation report must distinguish:

- Features reused from Atelier.
- Features reused from Pixel Atelier.
- Newly implemented features.
- Successfully verified features.
- Features blocked by unavailable dependencies or generation services.
- Features that remain experimental.

## 20. Execution Instruction

You are responsible for implementation, not just architecture design.

Begin by inspecting and running both repositories.

Then implement the smallest working end-to-end integration, validate it with real assets, and incrementally expand it.

Make reasonable technical decisions independently.

Do not repeatedly request confirmation for ordinary implementation decisions.

Do not fabricate API capabilities, generated artwork, test results, or successful integrations.

Prioritize actual visual quality, working functionality, maintainability, and reproducibility over the number of features implemented.

The final result should be a practical AI game art production tool that an independent game developer can install and use locally.
