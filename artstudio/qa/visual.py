"""Optional visual-model-assisted (PROBABILISTIC) checks.

No vision model is bundled or required. A `VisualAssessor` can be plugged in (e.g. a local
VLM behind an HTTP endpoint, or an agent that looks at the contact sheet). Without one, the
status is 'unavailable' — never 'passed'. Results are stored separately from deterministic QA.
"""
from __future__ import annotations

from ..util import now

CRITERIA = [
    "character_identity_drift", "clothing_changes", "weapon_deformation", "extra_or_missing_limbs",
    "inconsistent_proportions", "art_style_drift", "unnatural_motion", "poor_transitions",
]


class VisualAssessor:
    name = "none"

    def available(self) -> bool:
        return False

    def assess(self, contact_sheet_png: bytes, reference_png: bytes | None, criteria: list[str]) -> dict:
        raise NotImplementedError


class ManualAssessor(VisualAssessor):
    """Records a human/agent judgement per criterion (the honest default)."""
    name = "manual"

    def available(self) -> bool:
        return True


def record_visual_review(ws, a: dict, findings: dict, reviewer: str, notes: str = "") -> dict:
    unknown = set(findings) - set(CRITERIA)
    if unknown:
        from ..util import StudioError
        raise StudioError(f"Unknown criteria {sorted(unknown)}")
    failed = [k for k, v in findings.items() if v == "fail"]
    a["qa"]["visual"] = {"status": "failed" if failed else ("passed" if findings else "pending"), "kind": "probabilistic",
                         "notes": notes, "reviewer": reviewer, "findings": findings, "at": now()}
    return ws.save_asset(a)


def unavailable_result() -> dict:
    return {"status": "unavailable", "kind": "probabilistic", "criteria": CRITERIA,
            "notes": "No visual model configured. Review the contact sheet manually; deterministic checks do not imply visual consistency."}
