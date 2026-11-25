"""AI Game Art Studio — unified local-first 2D game art production.

Integrates two upstream projects through adapters (see docs/integration-architecture.md):
  * Atelier (Rust, MIT) — procedural pixel drawing via its `atelier call` CLI.
  * Pixel Atelier (Python, MIT) — whole-character frame pipeline (spritepipe) and
    reference-driven generation workflow.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = 1
