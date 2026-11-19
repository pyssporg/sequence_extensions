---
id: IMP-032
type: imp
title: Save and restore a session
summary: Keep the flow, imported plan, and plan edits across reloads
date: 2026-11-12
status: suggested
---

# Save and restore a session

- **Question:** Can the GUI keep the selected flow, imported plan, and plan edits across a reload?
- **Evidence:** a reload loses the flow selection and plan edits because no persistence exists today.
- **Change:** save and restore one session.
- **Risk:** stale state can outlive the plan it came from.
- **Acceptance:** reload restores the flow and the edited plan document.
