---
name: gif-video-frame-extraction
description: Extract frames from GIF/APNG/WebP animations and MP4/WebM videos, key the background and align.
---

# Gif Video Frame Extraction

Extract frames from GIF/APNG/WebP animations and MP4/WebM videos, key the background and align.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Atelier tools are reached through the `atelier` provider — never re-implement drawing in Python image code.

## Required inputs
File; target fps (video); max frames; key colour/tolerance; art mode; optional de-pixelation.

## Recommended workflow
1. GIF/APNG: `import anim.gif` — frames are fully composited (disposal honoured) with original durations.
2. Video: requires ffmpeg (`status` shows it). `import clip.mp4 --opts '{"video":{"fps":12,"max_frames":48},"background":{"method":"solid","color":[0,177,64],"tolerance":60}}'`.
3. Pixel-art captures: add `depixelate_block` (auto or explicit) to return to native pixels.
4. Review onion skin + ground line; trim with `frames delete`; set loop; export.

## Tool-selection rules
ffmpeg via fixed argument lists (no shell); Pillow ImageSequence; Import Studio.

## Prompt templates
n/a.

## Quality criteria
Frame count/timing match the source; clean key (no fringe); preserved interior colours (connected keying); stable registration.

## Common failure modes
Compression fringes around the key colour; interior colours close to the key removed; variable frame rate.

## Recovery strategies
Raise tolerance a little or use HD soft keying; keep connected=true; resample to a fixed fps.

## Output specification
Animation asset with per-frame durations; import record (kind, fps, background info).
