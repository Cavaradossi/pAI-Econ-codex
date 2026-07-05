#!/usr/bin/env python3
"""Release checks for the pAI-Econ-codex skill repository."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency hint for local machines
    yaml = None


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "SKILL.md",
    "CODEX.md",
    "README.md",
    "README_EN.md",
    "LICENSE",
    "CHANGELOG.md",
    "THEORETICAL_ECON_MIGRATION_PLAN.md",
    "agents/openai.yaml",
    "templates/state.json",
    ".gitignore",
    ".gitattributes",
]

REQUIRED_DIRS = [
    "prompts",
    "model_library",
    "templates",
    "docs",
    "examples",
    "agents",
]

REQUIRED_PROMPTS = [
    "00-intake.md",
    "01-puzzle-refinement.md",
    "02-literature-positioning.md",
    "02a-empirical-reality-check.md",
    "03-persona-council.md",
    "03b-canonical-model-match.md",
    "04-model-primitives.md",
    "05-assumption-audit.md",
    "06-proposition-generator.md",
    "07-proof-sketch.md",
    "07b-numerical-simulation.md",
    "08-counterexample-finder.md",
    "09-economic-interpretation.md",
    "10-manuscript-skeleton.md",
    "gate-01-novelty-risk.md",
    "gate-02b-canonical-fit.md",
    "gate-02c-theory-lineage.md",
    "gate-02-model-coherence.md",
    "gate-03-non-triviality.md",
    "gate-04-proof-integrity.md",
    "gate-04b-numerical-integrity.md",
    "gate-05-economic-meaning.md",
]

PROHIBITED_PATHS = [
    ".claude/commands",
    "settings.json",
]

PROHIBITED_TREE_PATHS = [
    "Exploration",
]

ALLOWED_CLAUDE_REFERENCES = {
    "LICENSE",
    "CHANGELOG.md",
    "THEORETICAL_ECON_MIGRATION_PLAN.md",
    ".gitignore",
    "scripts/release_check.py",
}

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".latex",
    ".tex",
    ".py",
    ".gitignore",
    ".gitattributes",
}


class CheckRun:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def ok(self, message: str) -> None:
        print(f"[OK] {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"[FAIL] {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"[WARN] {message}")

    def require(self, condition: bool, message: str) -> None:
        if condition:
            self.ok(message)
        else:
            self.fail(message)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_yaml(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required for release checks")
    data = yaml.safe_load(read_text(path))
    return data if isinstance(data, dict) else {}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            if path.name in {".git", "__pycache__", ".pytest_cache"}:
                continue
            continue
        if ".git" in path.parts:
            continue
        if path.name in TEXT_EXTENSIONS or path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return files


def check_required_layout(run: CheckRun) -> None:
    for item in REQUIRED_FILES:
        run.require((ROOT / item).is_file(), f"required file exists: {item}")
    for item in REQUIRED_DIRS:
        run.require((ROOT / item).is_dir(), f"required directory exists: {item}")
    for item in REQUIRED_PROMPTS:
        run.require((ROOT / "prompts" / item).is_file(), f"required prompt exists: prompts/{item}")
    for item in PROHIBITED_PATHS:
        run.require(not (ROOT / item).exists(), f"Claude-only path absent: {item}")
    for item in PROHIBITED_TREE_PATHS:
        path = ROOT / item
        run.require(not path.exists(), f"generated workspace tree absent from release: {item}/")


def check_skill_metadata(run: CheckRun) -> None:
    skill_path = ROOT / "SKILL.md"
    content = read_text(skill_path)
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        run.fail("SKILL.md has YAML frontmatter")
        return
    run.ok("SKILL.md has YAML frontmatter")
    if yaml is None:
        run.fail("PyYAML is available")
        return
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        run.fail("SKILL.md frontmatter is a YAML mapping")
        return
    run.require(frontmatter.get("name") == "pai-econ-codex", "skill name is pai-econ-codex")
    description = frontmatter.get("description")
    run.require(isinstance(description, str) and "Codex" in description, "skill description targets Codex")
    run.require("user-invocable" not in frontmatter, "Claude user-invocable field absent")


def check_openai_yaml(run: CheckRun) -> None:
    path = ROOT / "agents" / "openai.yaml"
    data = read_yaml(path)
    interface = data.get("interface") if isinstance(data.get("interface"), dict) else data
    run.require(interface.get("display_name") == "pAI-Econ-codex", "openai.yaml display name is pAI-Econ-codex")
    short = interface.get("short_description", "")
    run.require(isinstance(short, str) and 25 <= len(short) <= 80, "openai.yaml has concise short_description")
    default_prompt = interface.get("default_prompt", "")
    run.require(isinstance(default_prompt, str) and "$pai-econ-codex" in default_prompt, "openai.yaml default prompt invokes $pai-econ-codex")


def check_docs_and_residue(run: CheckRun) -> None:
    readme = read_text(ROOT / "README.md")
    readme_en = read_text(ROOT / "README_EN.md")
    skill = read_text(ROOT / "SKILL.md")
    run.require("$pai-econ-codex" in readme and "$pai-econ-codex" in readme_en, "README files use Codex skill invocation")
    run.require("/theoretical-economics-claude-skill" not in readme + readme_en + skill, "Claude slash command removed from active docs")
    run.require("pAI-Econ-codex" in readme and "pAI-Econ-codex" in readme_en, "README files use Codex project name")

    for path in iter_text_files():
        text = read_text(path)
        if any(token in text for token in ["theoretical-economics-claude-skill", "Claude Code", "CLAUDE.md"]):
            if rel(path) not in ALLOWED_CLAUDE_REFERENCES:
                run.fail(f"unexpected Claude-era reference in {rel(path)}")


def check_state_template(run: CheckRun) -> None:
    state = json.loads(read_text(ROOT / "templates" / "state.json"))
    gates = ["gate_1", "gate_1b", "gate_2b", "gate_2c", "gate_2", "gate_3", "gate_4", "gate_4b", "gate_5"]
    human = ["hil_1", "hil_2", "hil_3", "hil_4", "hil_5", "hil_n1", "hil_n2", "hil_n3", "hil_6"]
    run.require(all(key in state.get("gate_results", {}) for key in gates), "state template contains all gate result keys")
    run.require(all(key in state.get("gate_retry_counts", {}) for key in gates), "state template contains all gate retry keys")
    run.require(all(key in state.get("human_decisions", {}) for key in human), "state template contains all HiL decision keys")
    numerical = state.get("numerical_simulation", {})
    run.require("blocked_propositions" in numerical, "state template tracks numerical blocked propositions")


def check_utf8(run: CheckRun) -> None:
    for path in iter_text_files():
        try:
            read_text(path)
        except UnicodeDecodeError as exc:
            run.fail(f"not valid UTF-8: {rel(path)} ({exc})")
    if not run.failures:
        run.ok("all checked text files decode as UTF-8")


def check_git(run: CheckRun) -> None:
    git_dir = ROOT / ".git"
    run.require(git_dir.is_dir(), "local Git repository exists")
    if not git_dir.is_dir():
        return
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode == 0:
        if status.stdout.strip():
            run.warn("working tree has uncommitted changes")
        else:
            run.ok("working tree is clean")
    else:
        run.fail("git status runs successfully")

    remote = subprocess.run(
        ["git", "remote", "-v"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if remote.returncode == 0 and remote.stdout.strip():
        run.ok("Git remote is configured")
    else:
        run.warn("Git remote is not configured yet")


def main() -> int:
    run = CheckRun()
    print(f"Release check root: {ROOT}")
    check_required_layout(run)
    check_skill_metadata(run)
    check_openai_yaml(run)
    check_docs_and_residue(run)
    check_state_template(run)
    check_utf8(run)
    check_git(run)

    print()
    if run.failures:
        print(f"Release check failed: {len(run.failures)} failure(s), {len(run.warnings)} warning(s).")
        return 1
    print(f"Release check passed with {len(run.warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
