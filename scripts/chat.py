#!/usr/bin/env python3
"""Local interactive CLI to chat with the deployed Support Agent.

    python scripts/chat.py

Type a message and press enter. Type /exit (or Ctrl-D) to end the session.
Prints a Console URL you can open alongside to watch tool calls stream in
live. Every tool call the agent makes is echoed with its name and inputs
(e.g. which file it read, which command it ran), so you can follow along
without switching to the Console.
"""
from __future__ import annotations

import os
import sys

from common import Deployment, get_client, session_console_url

MEMORY_RESOURCE_INSTRUCTIONS = (
    "Policy Files (markdown, frontmatter: title/topics/summary) plus "
    "_manifest.json, the aggregated frontmatter index."
)

# ---- color output -----------------------------------------------------
# Plain ANSI escapes — no extra dependency needed for a handful of colors.
# Disabled automatically when stdout isn't a terminal or NO_COLOR is set
# (see https://no-color.org).
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def _dim(text: str) -> str:
    return _paint("2", text)


def _bold(text: str) -> str:
    return _paint("1", text)


def _cyan(text: str) -> str:
    return _paint("36", text)


def _yellow(text: str) -> str:
    return _paint("33", text)


def _green(text: str) -> str:
    return _paint("32", text)


def _red(text: str) -> str:
    return _paint("31", text)


def _magenta(text: str) -> str:
    return _paint("35", text)


# Which input field best describes "what this tool touched", per built-in
# tool name (agent_toolset_20260401: bash, read, write, edit, glob, grep,
# web_fetch, ...). Falls back to dumping the whole input dict.
_TOOL_HEADLINE_FIELD = {
    "bash": "command",
    "read": "file_path",
    "write": "file_path",
    "edit": "file_path",
    "glob": "pattern",
    "grep": "pattern",
    "web_fetch": "url",
}


def _format_tool_use(name: str, tool_input: dict, prefix: str = "tool") -> str:
    field = _TOOL_HEADLINE_FIELD.get(name)
    if field and field in tool_input:
        headline = f"{tool_input[field]!r}"
        extra = {k: v for k, v in tool_input.items() if k != field}
        detail = f" {extra}" if extra else ""
        return f"  {_yellow(f'[{prefix}: {name}]')} {headline}{_dim(detail)}"
    return f"  {_yellow(f'[{prefix}: {name}]')} {_dim(str(tool_input))}"


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
                        print(f"\n{_bold(_green('Agent:'))} {block.text}")
            elif event.type == "agent.tool_use":
                print(_format_tool_use(event.name, event.input))
            elif event.type == "agent.mcp_tool_use":
                print(_format_tool_use(event.name, event.input, prefix=f"mcp:{event.mcp_server_name}"))
            elif event.type == "agent.custom_tool_use":
                print(_format_tool_use(event.name, event.input, prefix="custom"))
            elif event.type in ("agent.tool_result", "agent.mcp_tool_result"):
                if event.is_error:
                    print(f"    {_red('result: error')}")
            elif event.type == "session.error":
                print(f"  {_red('[error]')} {event.error.message}")
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
    print(f"Session: {_dim(session.id)}")
    print(f"Watch live: {_dim(session_console_url(session.id))}")
    print("Type your message (/exit to quit)\n")

    try:
        while True:
            try:
                text = input(_bold(_cyan("You: "))).strip()
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
            print(f"\n{_dim(f'Session archived: {session.id}')}")
        except Exception as exc:  # session may still be settling — harmless
            print(f"\n{_magenta(f'(Could not archive session {session.id} yet: {exc})')}")


if __name__ == "__main__":
    main()
