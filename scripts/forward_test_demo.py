#!/usr/bin/env python3
"""Short-chain forward test for pAI-Econ-codex.

This is a deterministic smoke test, not a full research run. It checks that a
demo hypothesis can enter the intake path, that core resources resolve from
both the repository skill and the packaged plugin skill, and that the workflow
reaches the first human-in-the-loop stop without requiring web citation work.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SKILL_ROOT = ROOT / "plugins" / "pai-econ-codex" / "skills" / "pai-econ-codex"

REQUIRED_STAGE_PROMPTS = [
    "00-intake.md",
    "01-puzzle-refinement.md",
    "02-literature-positioning.md",
    "02a-empirical-reality-check.md",
    "03-persona-council.md",
    "03b-canonical-model-match.md",
    "04-model-primitives.md",
    "07b-numerical-simulation.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(skill_md: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required for the forward test")
    content = read_text(skill_md)
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise AssertionError(f"Missing YAML frontmatter: {skill_md}")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise AssertionError(f"Frontmatter is not a mapping: {skill_md}")
    return data


def derive_model_abbrev(hypothesis: str) -> str:
    lowered = hypothesis.lower()
    if "principal" in lowered and "agent" in lowered:
        return "PrincipalAgent"
    if "search" in lowered:
        return "SearchModel"
    if "human capital" in lowered:
        return "HumanCapital"
    return "EconModel"


def check_skill_root(skill_root: Path, hypothesis: str) -> dict:
    if not skill_root.is_dir():
        raise AssertionError(f"Skill root missing: {skill_root}")

    frontmatter = parse_frontmatter(skill_root / "SKILL.md")
    if frontmatter.get("name") != "pai-econ-codex":
        raise AssertionError(f"Unexpected skill name in {skill_root}: {frontmatter.get('name')}")

    skill_text = read_text(skill_root / "SKILL.md")
    required_markers = [
        "HiL-1",
        "Stage 7b never runs by default",
        "REFERENCE VERIFICATION GATE",
        "Exploration/Project_NNN_<ModelAbbrev>",
    ]
    missing_markers = [marker for marker in required_markers if marker not in skill_text]
    if missing_markers:
        raise AssertionError(f"Missing workflow markers in {skill_root}: {missing_markers}")

    for prompt in REQUIRED_STAGE_PROMPTS:
        path = skill_root / "prompts" / prompt
        if not path.is_file():
            raise AssertionError(f"Missing prompt in {skill_root}: prompts/{prompt}")

    state = json.loads(read_text(skill_root / "templates" / "state.json"))
    for key in ["campaign_id", "workspace", "hypothesis", "gate_results", "human_decisions"]:
        if key not in state:
            raise AssertionError(f"State template missing {key} in {skill_root}")

    abbrev = derive_model_abbrev(hypothesis)
    return {
        "skill_root": str(skill_root),
        "skill_name": frontmatter["name"],
        "hypothesis_chars": len(hypothesis),
        "derived_model_abbrev": abbrev,
        "synthetic_workspace": f"Exploration/Project_001_{abbrev}",
        "first_prompts": ["prompts/00-intake.md", "prompts/01-puzzle-refinement.md"],
        "expected_first_hil_stop": "HiL-1 after Stage 1",
        "stage_7b_default": "not run without explicit user opt-in",
    }


def main() -> int:
    hypothesis_path = ROOT / "examples" / "quickstart-task.txt"
    hypothesis = read_text(hypothesis_path).strip()
    if not hypothesis:
        raise AssertionError("Demo hypothesis is empty")

    roots = [ROOT, PLUGIN_SKILL_ROOT]
    results = [check_skill_root(root, hypothesis) for root in roots]

    print("Short-chain forward test passed.")
    print(json.dumps({"demo_hypothesis": str(hypothesis_path), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
