#!/usr/bin/env python3
"""One-time control-plane setup for the Support Agent Managed Agent deployment.

Creates (idempotently) the Environment, the memory store, and the Agent
itself, storing their IDs in .managed_agents_config.json for reuse by every
other script in this directory. Safe to re-run — existing resources are
reused, not recreated.

    python scripts/deploy_support_agent.py
    python scripts/deploy_support_agent.py --update-agent

--update-agent publishes the current agents/support_agent/system_prompt.md
as a new Agent version (existing sessions keep running on their pinned
version; new sessions pick up the update).
"""
from __future__ import annotations

import argparse
import json

from common import (
    AGENT_NAME,
    ENVIRONMENT_NAME,
    MEMORY_STORE_NAME,
    MODEL,
    SYSTEM_PROMPT_PATH,
    Deployment,
    get_client,
)

# Full built-in toolset (bash, read, write, edit, glob, grep, web_fetch,
# web_search). The memory store itself is attached read-only per session
# (see chat.py / seed_sessions.py), so write/edit can't touch Policy Files
# even though they're enabled here.
TOOLS = [{"type": "agent_toolset_20260401"}]


def ensure_environment(client, deployment: Deployment) -> None:
    if deployment.environment_id:
        print(f"environment: reusing {deployment.environment_id}")
        return
    env = client.beta.environments.create(
        name=ENVIRONMENT_NAME,
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    deployment.environment_id = env.id
    deployment.save()
    print(f"environment: created {env.id}")


def ensure_memory_store(client, deployment: Deployment) -> None:
    if deployment.memory_store_id:
        print(f"memory store: reusing {deployment.memory_store_id}")
        return
    store = client.beta.memory_stores.create(
        name=MEMORY_STORE_NAME,
        description=(
            "Policy Files (markdown with title/topics/summary frontmatter) plus "
            "_manifest.json, the aggregated frontmatter index. Read the manifest "
            "first via bash to judge relevance before opening full files."
        ),
    )
    deployment.memory_store_id = store.id
    deployment.save()
    print(f"memory store: created {store.id}")


def ensure_agent(client, deployment: Deployment, update: bool) -> None:
    system_prompt = SYSTEM_PROMPT_PATH.read_text()

    if deployment.agent_id and update:
        agent = client.beta.agents.update(
            deployment.agent_id,
            version=deployment.agent_version,
            system=system_prompt,
        )
        deployment.agent_version = agent.version
        deployment.save()
        print(f"agent: updated {agent.id} -> v{agent.version}")
        return

    if deployment.agent_id:
        print(f"agent: reusing {deployment.agent_id} (v{deployment.agent_version})")
        return

    agent = client.beta.agents.create(
        name=AGENT_NAME,
        model=MODEL,
        system=system_prompt,
        tools=TOOLS,
    )
    deployment.agent_id = agent.id
    deployment.agent_version = agent.version
    deployment.save()
    print(f"agent: created {agent.id} (v{agent.version})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--update-agent",
        action="store_true",
        help="Publish agents/support_agent/system_prompt.md as a new Agent version.",
    )
    args = parser.parse_args()

    client = get_client()
    deployment = Deployment.load()

    ensure_environment(client, deployment)
    ensure_memory_store(client, deployment)
    ensure_agent(client, deployment, update=args.update_agent)

    print("\nDeployment config (.managed_agents_config.json):")
    print(json.dumps(deployment.__dict__, indent=2))
    print("\nNext: python scripts/upsert_policies.py   (push Policy Files into the memory store)")


if __name__ == "__main__":
    main()
