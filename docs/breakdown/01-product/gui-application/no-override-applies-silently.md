---
id: REQ-001
type: requirement
title: No override applies silently
summary: Code-bound values are read-only, and every limitation is warned
date: 2026-11-12
status: current
---

# No override applies silently

Every value that flow code fixes stays read-only, and every limit of an edit is warned about.

- **Promise:** a preview never pretends an edit took effect; code-bound values stay disabled with a reason.
- **Why it matters:** the operator judges a run from the preview, so a hidden override makes the verdict untrustworthy.
- **Violated by:** an edit accepted in the UI that the engine discards, or an unsupported edit applied with no notice.
- **Notice:** read-only values show a short reason, unsupported policy edits raise a warning, and a stale or missing node identity skips that node's edits with a warning instead of applying name-wide.
