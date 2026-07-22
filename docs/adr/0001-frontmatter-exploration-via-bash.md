# Frontmatter-only exploration via Bash over the mounted memory store, not the Memory API

The Support Agent needs to judge relevance of Policy Files without loading their full bodies. The Managed Agents Memory API only exposes `list` (path + type, no content) and `retrieve` (full content, all-or-nothing) — there is no metadata-only or partial-read endpoint, so this can't be built on the Memory API alone.

It works anyway because each memory store is mounted as a real directory under `/mnt/memory/{store}/` inside the sandbox, and the agent's Bash tool can run arbitrary commands (`head`, `sed`, `awk`, `grep`) against that path — a tool call's output is only that command's stdout, not the whole file. The Support Agent therefore reads frontmatter (and the pre-built Manifest) via Bash over the filesystem mount, never via `Memory.retrieve`.

We considered relying on `Memory.retrieve` and just prompting the agent to "only attend to the top of the file" — rejected because the full file body would still land in the transcript/context, defeating the slim-context goal.
