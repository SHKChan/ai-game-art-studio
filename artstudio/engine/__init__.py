"""Pixel Forge — the studio's own layered pixel-art engine (pure Python, Pillow + numpy).

Originally the studio drove the external Atelier editor (Rust, MIT © 2026 Marmik Shah). This package
replaces it with an in-process engine that keeps Atelier's *call format* — a JSON object
{"name": <tool>, "arguments": {...}} per step — and the subset of tools the studio and its agents use,
so recipes stay readable and agents familiar with Atelier can author drawings unchanged.

Documents persist under <home>/documents/<doc_id>/ as doc.json + cels/L{layer}_F{frame}.png and keep
a replayable recipe (doc.recipe, one JSON call per line). Same calls → same pixels.
"""
from .document import Document, EngineError, Store
from .tools import TOOLS, Engine

__all__ = ["Document", "Engine", "EngineError", "Store", "TOOLS"]
