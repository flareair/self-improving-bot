# Manifest regeneration has no platform-native trigger

The Manifest (aggregated frontmatter index) needs to stay in sync whenever Policy Files are added or edited. We confirmed against the Managed Agents docs that the Memory API has no webhook/event/subscription mechanism on memory create/update/delete — mutation is purely client-initiated, and the documented session event types cover agent/session activity, not memory store changes.

Because of this platform constraint (not a preference), Manifest regeneration is triggered by the Upsert Script itself — the same script that writes Policy Files into the memory store also regenerates the Manifest, in the same step. There is no separate watcher, poller, or server-side hook, and none is possible without building one ourselves.
