#!/usr/bin/env python3
"""The Upsert Script (see CONTEXT.md).

The only sanctioned write path to the memory store — writes every Policy
File under policies/ into the memory store and regenerates the Manifest
(_manifest.json) in the same step. Run manually whenever Policy Files are
added or edited:

    python scripts/upsert_policies.py
"""
from __future__ import annotations

import json
import sys

from common import Deployment, MANIFEST_PATH, get_client, iter_policy_files


def _existing_paths(client, memory_store_id: str) -> dict[str, str]:
    """path -> memory_id for every memory currently in the store."""
    paths: dict[str, str] = {}
    for m in client.beta.memory_stores.memories.list(memory_store_id, path_prefix="/"):
        if m.type == "memory":
            paths[m.path] = m.id
    return paths


def _upsert(client, memory_store_id: str, existing: dict[str, str], path: str, content: str) -> str:
    if path in existing:
        client.beta.memory_stores.memories.update(
            existing[path], memory_store_id=memory_store_id, content=content
        )
        return "updated"
    client.beta.memory_stores.memories.create(memory_store_id, path=path, content=content)
    return "created"


def main() -> None:
    deployment = Deployment.load()
    deployment.require_ready()
    client = get_client()

    existing = _existing_paths(client, deployment.memory_store_id)
    local_paths: set[str] = set()

    manifest_files = []
    for policy in iter_policy_files():
        local_paths.add(policy["path"])
        action = _upsert(client, deployment.memory_store_id, existing, policy["path"], policy["content"])
        print(f"[{action}] {policy['path']}  ({policy['title']})")
        manifest_files.append(
            {
                "path": policy["path"],
                "title": policy["title"],
                "topics": policy["topics"],
                "summary": policy["summary"],
            }
        )

    if not manifest_files:
        print("No Policy Files found under policies/ — nothing to upsert.", file=sys.stderr)
        sys.exit(1)

    manifest = json.dumps({"files": manifest_files}, indent=2)
    action = _upsert(client, deployment.memory_store_id, existing, MANIFEST_PATH, manifest)
    print(f"[{action}] {MANIFEST_PATH}  ({len(manifest_files)} files indexed)")

    # Policy Files that exist in the store but no longer exist locally aren't
    # deleted automatically (the Upsert Script only writes and regenerates
    # the manifest) — surface the drift instead so a human decides.
    stale = sorted(p for p in existing if p != MANIFEST_PATH and p not in local_paths)
    if stale:
        print("\nWarning: memories present in the store with no matching local Policy File:")
        for path in stale:
            print(f"  {path}")


if __name__ == "__main__":
    main()
