#!/usr/bin/env python3
"""Local interactive CLI to chat with the deployed Support Agent.

    python scripts/chat.py

Type a message and press enter. Type /exit (or Ctrl-D) to end the session.
Prints a Console URL you can open alongside to watch tool calls stream in
live.
"""
from __future__ import annotations

from common import Deployment, get_client, session_console_url

MEMORY_RESOURCE_INSTRUCTIONS = (
    "Policy Files (markdown, frontmatter: title/topics/summary) plus "
    "_manifest.json, the aggregated frontmatter index."
)


def create_session(client, deployment: Deployment, title: str):
    return client.beta.sessions.create(
        agent=deployment.agent_id,
        environment_id=deployment.environment_id,
        title=title,
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": deployment.memory_store_id,
                "access": "read_only",
                "instructions": MEMORY_RESOURCE_INSTRUCTIONS,
            }
        ],
    )


def send_and_wait(client, session_id: str, text: str) -> None:
    """Stream-first: open the event stream, then send — so we don't miss
    anything the agent emits before we'd otherwise start reading (see
    shared/managed-agents-client-patterns.md Pattern 7)."""
    with client.beta.sessions.events.stream(session_id=session_id) as stream:
        client.beta.sessions.events.send(
            session_id=session_id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": text}]}],
        )
        for event in stream:
            if event.type == "agent.message":
                for block in event.content:
                    if block.type == "text":
                        print(f"\nAgent: {block.text}")
            elif event.type == "agent.tool_use":
                print(f"  [tool: {event.name}]")
            elif event.type == "session.error":
                print(f"  [error] {event.error.message}")
            elif event.type == "session.status_terminated":
                break
            elif event.type == "session.status_idle":
                # Idle can be transient (e.g. between parallel tool calls) —
                # only stop on a terminal idle, not one still awaiting a
                # client-side action.
                if event.stop_reason.type != "requires_action":
                    break


def main() -> None:
    deployment = Deployment.load()
    deployment.require_ready()
    client = get_client()

    session = create_session(client, deployment, title="Local chat session")
    print(f"Session: {session.id}")
    print(f"Watch live: {session_console_url(session.id)}")
    print("Type your message (/exit to quit)\n")

    try:
        while True:
            try:
                text = input("You: ").strip()
            except EOFError:
                print()
                break
            if not text:
                continue
            if text in ("/exit", "/quit"):
                break
            send_and_wait(client, session.id, text)
    finally:
        try:
            client.beta.sessions.archive(session.id)
            print(f"\nSession archived: {session.id}")
        except Exception as exc:  # session may still be settling — harmless
            print(f"\n(Could not archive session {session.id} yet: {exc})")


if __name__ == "__main__":
    main()
