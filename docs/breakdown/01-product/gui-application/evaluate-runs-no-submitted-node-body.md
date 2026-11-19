---
id: REQ-003
type: requirement
title: Evaluate runs no submitted node body
summary: Planning executes orchestration only; node bodies wait for Execute
date: 2026-11-12
status: current
---

# Evaluate runs no submitted node body

Evaluate plans the flow once and starts no submitted node body; node work waits for Execute.

- **Promise:** a preview can be made at any time without side effects from submitted nodes.
- **Why it matters:** the operator inspects and edits inputs before anything costly or irreversible runs.
- **Violated by:** a node body starting during preview, or a preview reporting a run result that never happened.
- **Notice:** preview returns a graph and parameters only; log records appear only after Execute, which stays unavailable until a preview exists.
