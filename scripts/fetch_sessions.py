#!/usr/bin/env python3
"""Pull every Support Agent session and its full transcript to local disk.

This is the data-gathering step the Agent Improver skill runs first (see
.claude/skills/agent-improver/SKILL.md): the Sessions API only supports
list + per-session retrieve, with no bulk export, so this walks both and
writes one transcript per session for the skill to read directly.

    python scripts/fetch_sessions.py

Writes analysis/sessions/<session_id>.json plus an index.json summary.
This is a local scratch cache (gitignored) — regenerate any time by
re-running the script; it always re-fetches everything (no incremental
state, matching ADR-0004).
"""
from __future__ import annotations

import json

from common import REPO_ROOT, Deployment, get_client

OUTPUT_DIR = REPO_ROOT / "analysis" / "sessions"


def _text_of(content_blocks) -> str:
    parts = []
    for block in content_blocks or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts)


def transcript_for(client, session) -> dict:
    turns = []
    for event in client.beta.sessions.events.list(session_id=session.id):
        if event.type == "user.message":
            turns.append({"role": "user", "text": _text_of(event.content)})
        elif event.type == "agent.message":
            turns.append({"role": "agent", "text": _text_of(event.content)})
        elif event.type == "agent.tool_use":
            turns.append({"role": "agent_tool_use", "name": event.name, "input": event.input})
        elif event.type == "session.error":
            turns.append({"role": "session_error", "message": event.error.message})

    return {
        "session_id": session.id,
        "title": session.title,
        "status": session.status,
        "created_at": str(session.created_at),
        "turns": turns,
    }


def main() -> None:
    deployment = Deployment.load()
    deployment.require_ready()
    client = get_client()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = []
    for session in client.beta.sessions.list():
        transcript = transcript_for(client, session)
        out_path = OUTPUT_DIR / f"{session.id}.json"
        out_path.write_text(json.dumps(transcript, indent=2, default=str))
        index.append({"session_id": session.id, "title": session.title, "status": session.status})
        print(f"[fetched] {session.id}  {session.title!r} -> {out_path.relative_to(REPO_ROOT)}")

    (OUTPUT_DIR / "index.json").write_text(json.dumps(index, indent=2))
    print(f"\n{len(index)} sessions written to {OUTPUT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
