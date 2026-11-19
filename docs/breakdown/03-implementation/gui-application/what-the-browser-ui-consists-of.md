---
id: INFO-040
type: info
title: What the browser UI consists of
summary: Four static files, plan import/export panel, SVG graph, no build step
date: 2026-11-12
status: current
---

# What the browser UI consists of

The UI is four static files of vanilla JavaScript and CSS, loaded directly with no build or network step.

- **Files:** `index.html`, `app.js`, `graph.js`, `styles.css`; `app.js` imports `graph.js` as an ES module.
- **Project root:** a text field and **Open** button call `PUT /api/root`, clear the old selection, and reload the tree (`CP-044`).
- **Project files:** a nested `role="tree"` list; directories expand in place, fetching one level lazily and caching children. The **Open** button doubles as **Refresh**: it re-fetches the root and every expanded directory when the typed path is unchanged, and the selected `.py` stays highlighted.
- **Graph toolbar:** **Import plan** reads a `.json` file, **Export plan** downloads the current document, and the plan status sits beside them. Options, root inputs, node parameters, and node policy are bound to `state.plan` (`INFO-037`).
- **Graph:** `graph.js` renders the SVG DAG and reports selection through `data-node-id`.
- **Parameters:** type-driven widgets — checkbox, number, text, JSON textarea; read-only ones are disabled with a note. A node list selects the root; the plan never stores it.
- **Run options:** the right-hand editor column below node parameters; visible while the flow root or nothing is selected, hidden when a concrete node fills the column.
- **Stream:** an `EventSource` appends `log` records and shows `status` and `done`.
- **Safety:** engine text reaches the DOM through `textContent`; no `innerHTML`, no CDN.
