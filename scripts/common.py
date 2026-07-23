"""Shared helpers for the Self-Improving Support Bot scripts.

Every other script in this directory imports from here: client construction,
the on-disk deployment config (environment/memory-store/agent IDs), and the
Policy File frontmatter parser.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = REPO_ROOT / "policies"
CONFIG_PATH = REPO_ROOT / ".managed_agents_config.json"
SYSTEM_PROMPT_PATH = REPO_ROOT / "agents" / "support_agent" / "system_prompt.md"

MEMORY_STORE_NAME = "policies"
MANIFEST_PATH = "/_manifest.json"
AGENT_NAME = "Support Agent"
ENVIRONMENT_NAME = "support-agent-env"
MODEL = "claude-opus-4-8"


def get_client() -> anthropic.Anthropic:
    """A bare client — resolves ANTHROPIC_API_KEY from the environment (.env is
    loaded automatically at import time)."""
    return anthropic.Anthropic()


@dataclass
class Deployment:
    """The IDs of the live Managed Agents resources this project uses.

    Persisted to .managed_agents_config.json (gitignored — these IDs are
    specific to whichever workspace ran the setup script, not source of
    truth; the repo files under policies/ and agents/ are the source of
    truth per ADR-0003).
    """

    environment_id: str | None = None
    memory_store_id: str | None = None
    agent_id: str | None = None
    agent_version: int | None = None

    @classmethod
    def load(cls) -> "Deployment":
        if not CONFIG_PATH.exists():
            return cls()
        return cls(**json.loads(CONFIG_PATH.read_text()))

    def save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2) + "\n")

    def require_ready(self) -> None:
        missing = [
            field
            for field in ("environment_id", "memory_store_id", "agent_id")
            if getattr(self, field) is None
        ]
        if missing:
            raise SystemExit(
                "Missing deployment config: "
                + ", ".join(missing)
                + ".\nRun `python scripts/deploy_support_agent.py` first."
            )


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_policy_file(path: Path) -> dict[str, Any]:
    """Parse one Policy File: YAML frontmatter (title/topics/summary) plus the
    full original text, which is what actually gets written to the memory
    store — the Support Agent reads the real file, frontmatter and all."""
    text = path.read_text()
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path} is missing YAML frontmatter (a leading ---...--- block)")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    for field in ("title", "topics", "summary"):
        if field not in frontmatter:
            raise ValueError(f"{path} frontmatter is missing required field '{field}'")
    return {
        "path": f"/{path.name}",
        "title": frontmatter["title"],
        "topics": frontmatter["topics"],
        "summary": frontmatter["summary"],
        "content": text,
    }


def iter_policy_files():
    for path in sorted(POLICIES_DIR.glob("*.md")):
        yield parse_policy_file(path)


def session_console_url(session_id: str, workspace: str = "default") -> str:
    """Swap 'default' for your workspace ID if the API key isn't in the
    Default workspace."""
    return f"https://platform.claude.com/workspaces/{workspace}/sessions/{session_id}"
