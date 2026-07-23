#!/usr/bin/env python3
"""Seed the deployment with sample Support Agent sessions.

Runs a handful of scripted conversations against the live Support Agent so
the Agent Improver has real session history to analyze the first time
it's run. Requires the Support Agent to already be deployed
(scripts/deploy_support_agent.py) and the Policy Files already pushed
(scripts/upsert_policies.py).

    python scripts/seed_sessions.py
"""
from __future__ import annotations

import time

from common import Deployment, get_client, session_console_url

MEMORY_RESOURCE_INSTRUCTIONS = (
    "Policy Files (markdown, frontmatter: title/topics/summary) plus "
    "_manifest.json, the aggregated frontmatter index."
)

# Each entry is one simulated employee session. They're chosen to exercise
# different behaviors so the Agent Improver has a mix of root causes to
# find: a clean answer, a query spanning two policies, a genuine content gap
# (nothing in policies/ covers it), a cap-testing multi-part question, and a
# real cross-policy inconsistency (expense-reimbursement.md says 45 days,
# benefits-and-payroll.md says 30 days for a similar reimbursement).
SCRIPTED_SESSIONS = [
    {
        "title": "seed: vacation basics",
        "turns": [
            "How many vacation days do I accrue per year, and how do I actually request time off?",
        ],
    },
    {
        "title": "seed: home office purchase + expensing it",
        "turns": [
            "I bought a new monitor for my home office. Can I expense it, and does IT need to "
            "approve equipment purchases first?",
        ],
    },
    {
        "title": "seed: AI tools and browser extensions (expected gap)",
        "turns": [
            "What's the policy on using AI coding assistants with our company codebase, and do I "
            "need a security review before installing a new browser extension?",
        ],
    },
    {
        "title": "seed: expense cap-testing multi-part question",
        "turns": [
            "For an upcoming conference I need to expense a flight, a hotel, per-diem meals, a "
            "team dinner I'm hosting, and a small client gift. What are the deadlines for each "
            "and which ones need pre-approval before I book?",
        ],
    },
    {
        "title": "seed: conflicting reimbursement deadline",
        "turns": [
            "How many days do I have to submit an expense reimbursement after I incur the cost?",
        ],
    },
]


def run_session(client, deployment: Deployment, spec: dict) -> str:
    session = client.beta.sessions.create(
        agent=deployment.agent_id,
        environment_id=deployment.environment_id,
        title=spec["title"],
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": deployment.memory_store_id,
                "access": "read_only",
                "instructions": MEMORY_RESOURCE_INSTRUCTIONS,
            }
        ],
    )
    print(f"\n=== {spec['title']} ===")
    print(f"session: {session.id}  ({session_console_url(session.id)})")

    for turn in spec["turns"]:
        print(f"  user: {turn}")
        with client.beta.sessions.events.stream(session_id=session.id) as stream:
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{"type": "user.message", "content": [{"type": "text", "text": turn}]}],
            )
            for event in stream:
                if event.type == "agent.message":
                    for block in event.content:
                        if block.type == "text":
                            print(f"  agent: {block.text[:300]}")
                elif event.type == "agent.tool_use":
                    print(f"    [tool: {event.name}]")
                elif event.type == "session.error":
                    print(f"  [error] {event.error.message}")
                elif event.type == "session.status_terminated":
                    break
                elif event.type == "session.status_idle":
                    if event.stop_reason.type != "requires_action":
                        break

    client.beta.sessions.archive(session.id)
    return session.id


def main() -> None:
    deployment = Deployment.load()
    deployment.require_ready()
    client = get_client()

    session_ids = []
    for spec in SCRIPTED_SESSIONS:
        session_id = run_session(client, deployment, spec)
        session_ids.append(session_id)
        time.sleep(1)

    print(f"\nSeeded {len(session_ids)} sessions:")
    for sid in session_ids:
        print(f"  {sid}")
    print(
        "\nNext: python scripts/fetch_sessions.py   (pull transcripts locally),\n"
        "then run the Agent Improver skill (.claude/skills/agent-improver/)."
    )


if __name__ == "__main__":
    main()
