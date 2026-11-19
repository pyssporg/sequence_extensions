---
id: IMP-031
type: imp
title: Show nested composite nodes
summary: Surface fan-out created inside a node body in the preview
date: 2026-11-12
status: suggested
---

# Show nested composite nodes

- **Question:** Should the preview show fan-out that a node body creates at runtime?
- **Evidence:** nested composite nodes are absent from the plan, so the graph understates the run (`TEST-004`).
- **Change:** preview nested composites, or mark the expansion as incomplete.
- **Risk:** expanded graphs can be large; a partial preview can mislead.
- **Acceptance:** a nested-composite flow shows its inner nodes or an explicit incomplete marker.
