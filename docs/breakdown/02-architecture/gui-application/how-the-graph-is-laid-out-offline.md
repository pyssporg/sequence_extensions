---
id: INFO-035
type: info
title: How the graph is laid out offline
summary: Layered SVG computed in the browser, no CDN
date: 2026-11-12
status: current
---

# How the graph is laid out offline

The browser computes a layered SVG layout itself, with no third-party layout library and no network access.

- **Layering:** a node's layer is its longest dependency chain; dependencies sit at the top and dependents below.
- **Rows:** each layer is one row, sorted by numeric id and centred.
- **Pan and zoom:** pointer drag and wheel transform one `.viewport` group.
- **Selection:** each node group carries `data-node-id`, used to highlight and select it.
- **Sparse ids:** nodes are keyed by plan id, so gaps in the id sequence are harmless.
- **Empty plan:** a flow with no nodes renders a plain-root note.
