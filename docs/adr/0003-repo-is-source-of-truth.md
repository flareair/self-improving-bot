# This repo is the source of truth; the memory store is a deployment target

Policy Files and the Support Agent's system prompt live in this git repo under version control. The Upsert Script pushes repo → memory store; the memory store is never edited directly. When the Agent Improver (a local Claude Code skill) proposes changes, it edits repo files and opens a PR — merging the PR is what makes a change real, and the Upsert Script re-syncs to the memory store afterward.

We considered treating the memory store itself as authoritative (repo as a mirror/staging copy) — rejected because it would leave no natural place for the Agent Improver's suggestions to become reviewable, diffable PRs, and no clean way to track history of policy changes over time.
