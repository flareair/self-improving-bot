# Self-Improving Support Bot

Two Managed Agents deployment: a **Support Agent** that answers employee queries from a memory store of policy files via progressive disclosure, and an **Improvement Agent** that analyzes the Support Agent's past sessions and proposes changes to policy files or the Support Agent's system prompt.

## Language

**Policy File**:
A markdown file in the shared memory store representing one or more related policies. May bundle multiple sub-topics as separate sections.
_Avoid_: Doc, document

**Frontmatter**:
The YAML metadata block at the top of a Policy File: `title`, `topics[]` (one label per section/sub-topic in the file), and `summary` (one or two sentences for the whole file). Used by the Support Agent to judge relevance without reading the full file body.
_Avoid_: Metadata, header

**Manifest**:
A single aggregated file (`_manifest.json`) containing every Policy File's frontmatter plus its path. Lets the Support Agent scan all frontmatters in one read instead of opening every Policy File individually.
_Avoid_: Index, catalog

**Upsert Script**:
A Python script, run manually (by a human or by Claude Code) whenever Policy Files are added or edited, that writes the files into the memory store and regenerates the Manifest in the same step. The only sanctioned write path to the memory store — for this prototype there is no server-side hook that regenerates the Manifest automatically.
_Avoid_: Sync script, upload script

**Relevance Cap**:
The hard limit (3–5 files) on how many Policy Files the Support Agent will fully open per query, regardless of how many clear the relevance bar against the Manifest. If the query is still unanswerable after the cap, the agent asks a clarifying question instead of reading more.
_Avoid_: Threshold (that's the per-file relevance judgment; the cap is the ceiling on the batch)

**Improvement Agent**:
A local Claude Code skill (not a Managed Agents deployment) that a human runs on demand. It lists and retrieves all past Support Agent sessions via the Sessions API, judges per-session root cause freely (Policy File content gap vs Support Agent system prompt behavior — no fixed classification rule), aggregates sessions that share a root cause into one Suggestion, and presents the Suggestion list for human approval before editing repo files and opening a PR.
_Avoid_: Improver, review agent, meta-agent

**Suggestion**:
One aggregated, evidenced recommendation produced by the Improvement Agent — targets either a Policy File or the Support Agent's system prompt, and cites the session(s) that support it. Multiple sessions sharing the same root cause collapse into a single Suggestion.
_Avoid_: Finding, recommendation (finding is used elsewhere for code review; keep Suggestion specific to this domain)

## Facts (Managed Agents platform)

- A memory store is mounted as a real directory under `/mnt/memory/{store}/` inside the agent's sandbox; the agent's Bash tool can run arbitrary commands (`head`, `sed`, `awk`, `grep`) against it, so a tool call's output is only that command's stdout — not the whole file. This is what makes "read only the frontmatter" actually cheap.
- The Memory API itself only exposes `list` (path + type, no content) and `retrieve` (full content, all-or-nothing) — there is no metadata-only or partial-read endpoint. Frontmatter-only reads work *only* because of Bash-over-the-mounted-filesystem, not because of the Memory API.
- No native webhook/event mechanism fires on memory store create/update/delete — confirmed via docs. Regeneration of the Manifest must be triggered by whatever writes the store (the Upsert Script), not by the platform.
- Sessions API supports `list` and per-session `retrieve`, with no bulk/batch export — the Improvement Agent must list then retrieve sessions one at a time.
- This repo is the source of truth for Policy Files and the Support Agent's system prompt; the memory store is a deployment target the Upsert Script pushes to, never edited directly. See [ADR-0003](./docs/adr/0003-repo-is-source-of-truth.md).
