---
id: CP-038
type: capability
title: See the graph before anything runs
summary: Nodes, edges, fan-out, parameters, and policy before execution
date: 2026-11-12
status: current
---

# See the graph before anything runs

The operator sees every reachable node, its links, its fan-out width, its parameters, and its effective policy, while no submitted node body has run.

- **Request:** "show me what this flow will do before I spend a run."
- **Goal:** judge the shape and the inputs from the preview alone.
- **Observable outcome:** a top-to-bottom graph draws one box per node instance with links, parameters, and effective retry and timeout policy; the browser draws it offline (`INFO-035`).
- **Where it fits:** after a module and flow are chosen (`CP-037`), before Execute (`CP-040`).
- **Where it strains:** fan-out created inside a node body is invisible; only fan-out in the orchestration appears.
