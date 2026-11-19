---
id: INFO-034
type: info
title: How project paths are confined
summary: Every file path resolves inside the project root
date: 2026-11-12
status: current
---

# How project paths are confined

Every accepted path is resolved and then checked to sit inside the configured project root.

- **Root:** `--project-root`, else `SEQ_EXT_GUI_PROJECT_ROOT`, else the current directory.
- **Confinement:** the resolved path must equal the root or sit under it; traversal and symlink escapes fail.
- **Tree:** directories plus `.py`/`.json` files; hidden entries and `__pycache__`, `.git`, `.venv`, `runs`, `.seq_ext_gui` are skipped.
- **Read:** only UTF-8 `.py` and `.json` files.
- **Write:** none; the API exposes no project-file write endpoint, and the browser imports/exports plans instead.
- **Errors:** a confinement failure becomes HTTP 400 (`INFO-037`).
