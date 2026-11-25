"""Versioned, engine-independent manifest schemas with a dependency-free validator.

The schemas are standard JSON Schema (draft 2020-12 subset) stored beside this file so
external tools can validate workspaces too. The validator below implements the subset we use:
type, required, properties, additionalProperties(bool|schema), items, enum, const,
minimum, maximum, minItems, maxItems, minLength, maxLength, pattern, $ref (local #/$defs), oneOf/anyOf.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..util import StudioError

HERE = Path(__file__).resolve().parent
_CACHE: dict[str, dict] = {}

TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def load_schema(name: str) -> dict:
    if name not in _CACHE:
        _CACHE[name] = json.loads((HERE / f"{name}.schema.json").read_text(encoding="utf-8"))
    return _CACHE[name]


def _is_type(v, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


def _validate(v, s: dict, root: dict, path: str, errors: list) -> None:
    if "$ref" in s:
        ref = s["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError("Only local $defs refs are supported")
        s = root["$defs"][ref.split("/")[-1]]
    if "oneOf" in s or "anyOf" in s:
        opts = s.get("oneOf") or s.get("anyOf")
        ok = sum(1 for o in opts if not _errs(v, o, root))
        if (s.get("oneOf") and ok != 1) or (s.get("anyOf") and ok < 1):
            errors.append(f"{path}: does not match {'oneOf' if 'oneOf' in s else 'anyOf'}")
        return
    t = s.get("type")
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(v, x) for x in ts):
            errors.append(f"{path}: expected {t}, got {type(v).__name__}")
            return
    if "const" in s and v != s["const"]:
        errors.append(f"{path}: must equal {s['const']!r}")
    if "enum" in s and v not in s["enum"]:
        errors.append(f"{path}: {v!r} not in {s['enum']}")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            errors.append(f"{path}: below minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errors.append(f"{path}: above maximum {s['maximum']}")
    if isinstance(v, str):
        if "minLength" in s and len(v) < s["minLength"]:
            errors.append(f"{path}: too short")
        if "maxLength" in s and len(v) > s["maxLength"]:
            errors.append(f"{path}: too long")
        if "pattern" in s and not re.search(s["pattern"], v):
            errors.append(f"{path}: does not match {s['pattern']}")
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errors.append(f"{path}: needs at least {s['minItems']} items")
        if "maxItems" in s and len(v) > s["maxItems"]:
            errors.append(f"{path}: at most {s['maxItems']} items")
        if "items" in s:
            for i, item in enumerate(v):
                _validate(item, s["items"], root, f"{path}[{i}]", errors)
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                errors.append(f"{path}: missing '{r}'")
        props = s.get("properties", {})
        addl = s.get("additionalProperties", True)
        for k, item in v.items():
            if k in props:
                _validate(item, props[k], root, f"{path}.{k}", errors)
            elif addl is False:
                errors.append(f"{path}: unexpected property '{k}'")
            elif isinstance(addl, dict):
                _validate(item, addl, root, f"{path}.{k}", errors)


def _errs(v, s, root) -> list:
    e: list = []
    _validate(v, s, root, "$", e)
    return e


def validate(data, schema_name: str) -> list[str]:
    root = load_schema(schema_name)
    return _errs(data, root, root)


def require_valid(data, schema_name: str) -> None:
    errors = validate(data, schema_name)
    if errors:
        raise StudioError(f"{schema_name} validation failed: " + "; ".join(errors[:8]))
