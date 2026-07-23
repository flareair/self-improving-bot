---
name: improvement-agent
description: Reviews past Support Agent sessions via the Sessions API, judges the root cause behind each (Policy File content gap vs Support Agent system-prompt behavior), aggregates matching sessions into Suggestions, and — after human approval — edits Policy Files or the system prompt and opens a PR.
---

# Improvement Agent

Run this on demand — there is no scheduler and no incremental cursor (see
[ADR-0004](../../../docs/adr/0004-improvement-agent-is-a-local-skill.md)).
Every run analyzes every session currently available.

## 1. Pull session data

```bash
python scripts/fetch_sessions.py
```

This lists every session via the Sessions API and retrieves each one's full
event history one at a time (list + per-session retrieve — there's no bulk
export), writing a transcript per session to `analysis/sessions/<session_id>.json`.
Read those files directly — don't re-fetch through the API yourself.

## 2. Judge root cause per session — freely, no fixed rule

For each transcript, read the user's question(s), what the agent answered,
and which Policy Files it opened (the `agent_tool_use` entries). Decide,
using your own judgment, which of these better explains what happened:

- **Policy File content gap** — the agent's *process* was fine (it read the
  manifest, judged relevance reasonably, stayed within the Relevance Cap,
  asked a clarifying question when it should have) but the underlying
  *content* was missing, wrong, or contradicted another Policy File.
- **Support Agent system-prompt behavior** — the agent's *process* was off:
  it skipped the manifest, opened more than the Relevance Cap (3–5) files,
  failed to ask a clarifying question when it should have, misjudged
  relevance, or otherwise didn't follow the frontmatter-first approach in
  `agents/support_agent/system_prompt.md`.

A session can be fine — not every session needs a Suggestion. There is no
mechanical rule mapping a symptom to a category; reason from the transcript
as evidence.

## 3. Aggregate by root cause into Suggestions

Sessions that share the same underlying root cause collapse into **one
Suggestion** — don't produce a separate Suggestion per session. Each
Suggestion needs:

- **Target** — the specific Policy File(s) (by path under `policies/`) or
  the Support Agent system prompt (`agents/support_agent/system_prompt.md`).
- **What to change** — a concrete, specific edit, not "improve this file."
- **Evidence** — the session ID(s) that support it, with a one-line
  quote/paraphrase of what went wrong in each.

## 4. Present the Suggestion list and pause for approval

Show every Suggestion to the human before touching any file. Use
`AskUserQuestion` (plain numbered text if there are more Suggestions than
that tool's option limit) so each one can be approved, rejected, or edited
individually — never bulk-apply without per-Suggestion confirmation.

## 5. Apply only approved Suggestions

- **Policy File edits** — edit the file(s) under `policies/` directly. Keep
  the frontmatter (`title`/`topics`/`summary`) in sync with any body change.
- **System prompt edits** — edit `agents/support_agent/system_prompt.md`.

## 6. Re-sync

- If any Policy File changed:
  ```bash
  python scripts/upsert_policies.py
  ```
  This is the only sanctioned write path to the memory store (see
  [ADR-0003](../../../docs/adr/0003-repo-is-source-of-truth.md)) — it also
  regenerates `_manifest.json` in the same step.
- If the system prompt changed:
  ```bash
  python scripts/deploy_support_agent.py --update-agent
  ```
  This publishes a new Agent version; sessions already running keep their
  pinned version.

## 7. Open a PR

Commit the changes and open a PR (`gh pr create`) whose description lists
each applied Suggestion with the session IDs that motivated it, so a
reviewer can trace every change back to real evidence. Do not push directly
to main.
