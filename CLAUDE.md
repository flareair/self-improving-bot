# Self-Improving Support Bot

See CONTEXT.md for domain language and platform facts.

## Setup

```
uv sync
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

Run any script with `uv run scripts/<name>.py` (`uv sync` is only needed
again after `pyproject.toml` changes).

## Scripts (run in this order the first time)

- `uv run scripts/deploy_support_agent.py` — one-time control-plane setup:
  creates the Environment, memory store, and Agent, saving their IDs to
  `.managed_agents_config.json`. Idempotent, safe to re-run. Pass
  `--update-agent` to publish the current `agents/support_agent/system_prompt.md`
  as a new Agent version.
- `uv run scripts/upsert_policies.py` — the Upsert Script: pushes every file
  under `policies/` into the memory store and regenerates `_manifest.json`.
  Re-run whenever a Policy File is added or edited.
- `uv run scripts/seed_sessions.py` — runs a handful of scripted conversations
  against the deployed Support Agent so there's session history to analyze.
  Requires the two scripts above to have run first.
- `uv run scripts/chat.py` — interactive CLI to chat with the deployed
  Support Agent yourself.
- `uv run scripts/fetch_sessions.py` — pulls every Support Agent session and
  transcript to `analysis/sessions/` (gitignored scratch cache). This is the
  data-gathering step the `agent-improver` skill runs first.

## Agent Improver

Run the `agent-improver` Claude Code skill (`.claude/skills/agent-improver/`)
on demand to review past sessions and propose Policy File or system-prompt
fixes for human approval.
