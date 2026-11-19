// Browser UI for the sequence_extensions flow engine. Vanilla ES module.
// All engine-provided text is inserted with textContent; there is no innerHTML.

import {
  fitGraph,
  ROOT_NODE_ID,
  renderGraph,
  selectGraphNode,
  setGraphNodeStates,
} from "./graph.js";

const $ = (id) => document.getElementById(id);

const ui = {
  health: $("health"),
  projectRoot: $("project-root"),
  openRoot: $("open-root"),
  rootStatus: $("root-status"),
  fileList: $("file-list"),
  nodeInventory: $("node-inventory"),

  planStatus: $("plan-status"),
  importPlan: $("import-plan"),
  exportPlan: $("export-plan"),
  planFile: $("plan-file"),
  evaluate: $("evaluate"),
  evalError: $("eval-error"),
  warnings: $("warnings"),
  graph: $("graph"),
  graphEmpty: $("graph-empty"),
  fitGraph: $("fit-graph"),
  execute: $("execute"),
  cancel: $("cancel"),
  dirtyHint: $("dirty-hint"),
  selectedNode: $("selected-node"),
  nodeEditor: $("node-editor"),
  runOptions: $("run-options"),
  jobStatus: $("job-status"),
  resultBanner: $("result-banner"),
  log: $("log-console"),
  clearLog: $("clear-log"),
  optMaxWorkers: $("opt-max-workers"),
  optRetries: $("opt-retries"),
  optRetryDelay: $("opt-retry-delay"),
  optTimeout: $("opt-timeout"),
  optSummary: $("opt-summary"),
  optFixedClock: $("opt-fixed-clock"),
};

const PLAN_SCHEMA = "flow-plan/2";
const PUT_METHOD = "PUT";

const OPTION_DEFAULTS = {
  max_workers: 16,
  summary: false,
  fixed_clock: false,
  retries: 0,
  retry_delay_seconds: 0.0,
  timeout: null,
};

const state = {
  projectRoot: "",
  children: new Map(),
  expanded: new Set(),
  pending: new Set(),
  errors: new Map(),
  flowFile: null,
  flowName: null,
  nodes: [],
  plan: null,
  preview: false,
  selectedId: null,
  dirty: false,
  jobId: null,
  source: null,
  run: null,
};

let widgetSeq = 0;
let nodeInventoryToken = 0;
let inventoryReady = Promise.resolve();
let treeToken = 0;

function nextId(prefix) {
  widgetSeq += 1;
  return `${prefix}-${widgetSeq}`;
}

async function api(path, init = {}) {
  const response = await fetch(path, init);
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!response.ok) {
    const detail =
      typeof data === "string" ? data : data?.detail != null ? JSON.stringify(data.detail) : text;
    const error = new Error(
      `${response.status} ${response.statusText}${detail ? `: ${detail}` : ""}`,
    );
    error.status = response.status;
    throw error;
  }
  return data;
}

function postJson(path, payload) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function putJson(path, payload) {
  return api(path, {
    method: PUT_METHOD,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------- startup ----

async function boot() {
  try {
    const health = await api("/api/health");
    state.projectRoot = health.project_root || "";
    ui.projectRoot.value = state.projectRoot;
    ui.health.textContent = `ok · v${health.version ?? "?"} · ${state.projectRoot}`;
    ui.health.classList.remove("bad");
  } catch (error) {
    ui.health.textContent = `backend unreachable: ${error.message}`;
    ui.health.classList.add("bad");
  }
  syncRootButton();
  await refreshTree();
}

// ---------------------------------------------------------- project files ----

async function readDir(path) {
  const data = await api(`/api/tree?path=${encodeURIComponent(path)}`);
  return Array.isArray(data?.entries) ? data.entries : [];
}

async function fetchDir(path, token) {
  if (state.children.has(path)) return state.children.get(path);
  const entries = await readDir(path);
  if (token !== treeToken) return null;
  state.children.set(path, entries);
  return entries;
}

async function toggleDir(path) {
  if (state.expanded.has(path)) {
    state.expanded.delete(path);
    renderTree();
    focusPath(path);
    return;
  }
  state.expanded.add(path);
  state.errors.delete(path);
  if (!state.children.has(path)) {
    const token = treeToken;
    state.pending.add(path);
    renderTree();
    try {
      await fetchDir(path, token);
    } catch (error) {
      if (token === treeToken) {
        state.errors.set(path, error.message);
      }
    } finally {
      if (token === treeToken) state.pending.delete(path);
    }
    if (token !== treeToken) return;
  }
  renderTree();
  focusPath(path);
}

async function refreshTree() {
  const token = ++treeToken;
  const dirs = ["", ...state.expanded];
  const results = await Promise.all(
    dirs.map(async (path) => {
      try {
        return { path, entries: await readDir(path) };
      } catch (error) {
        return { path, error };
      }
    }),
  );
  if (token !== treeToken) return;
  for (const result of results) {
    state.pending.delete(result.path);
    if (result.error) {
      state.errors.set(result.path, result.error.message);
      if (!result.path) state.children.delete("");
    } else {
      state.errors.delete(result.path);
      state.children.set(result.path, result.entries);
    }
  }
  renderTree();
}

function resetTree() {
  treeToken += 1;
  state.children.clear();
  state.expanded.clear();
  state.pending.clear();
  state.errors.clear();
  ui.fileList.replaceChildren();
}

function renderTree() {
  ui.fileList.replaceChildren();
  const entries = state.children.get("");
  if (entries === undefined) {
    const error = state.errors.get("");
    ui.fileList.append(message(`Cannot list files: ${error || "unknown error"}`, "error"));
    return;
  }
  if (!entries.length) {
    ui.fileList.append(message("No .py or .json files here.", "empty"));
    return;
  }
  appendEntries(entries, 0);
}

function appendEntries(entries, depth) {
  for (const entry of entries) {
    const isDir = entry.kind === "dir";
    const selected = !isDir && entry.path === state.flowFile;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "file-entry";
    button.dataset.path = entry.path;
    button.dataset.kind = entry.kind;
    button.setAttribute("role", "treeitem");
    button.setAttribute("aria-level", String(depth + 1));
    button.style.paddingLeft = `${6 + 12 * depth}px`;
    if (isDir) {
      const open = state.expanded.has(entry.path);
      button.setAttribute("aria-expanded", open ? "true" : "false");
    } else {
      button.setAttribute("aria-selected", selected ? "true" : "false");
      if (selected) button.classList.add("selected");
    }
    const glyph = document.createElement("span");
    glyph.className = "glyph";
    glyph.textContent = isDir ? (state.expanded.has(entry.path) ? "▾" : "▸") : "·";
    const name = document.createElement("span");
    name.textContent = entry.name;
    button.append(glyph, name);
    ui.fileList.append(button);

    if (!isDir || !state.expanded.has(entry.path)) continue;
    if (state.pending.has(entry.path)) {
      ui.fileList.append(treeNote("loading…", depth + 1, "tree-note muted"));
      continue;
    }
    const error = state.errors.get(entry.path);
    if (error) {
      ui.fileList.append(treeNote(`Cannot list: ${error}`, depth + 1, "tree-error"));
      continue;
    }
    const children = state.children.get(entry.path);
    if (children === undefined) {
      ui.fileList.append(treeNote("Not loaded.", depth + 1, "tree-note muted"));
    } else if (!children.length) {
      ui.fileList.append(treeNote("No .py or .json files here.", depth + 1, "tree-note empty"));
    } else {
      appendEntries(children, depth + 1);
    }
  }
}

function treeNote(text, depth, className) {
  const node = message(text, className);
  node.style.paddingLeft = `${24 + 12 * depth}px`;
  return node;
}

function focusPath(path) {
  for (const button of ui.fileList.querySelectorAll("button[data-path]")) {
    if (button.dataset.path === path) {
      button.focus();
      return;
    }
  }
}

// -------------------------------------------------------------- project root ----

function setRootStatus(text, tone) {
  ui.rootStatus.textContent = text || "";
  ui.rootStatus.classList.toggle("ok", tone === "ok");
  ui.rootStatus.classList.toggle("bad", tone === "error");
}

function runActive() {
  return (
    state.source !== null ||
    state.jobId !== null ||
    !ui.cancel.classList.contains("hidden")
  );
}

function setRootBusy(busy) {
  ui.openRoot.disabled = busy;
}

function lockRootForRun() {
  setRootBusy(true);
  setRootStatus("cancel or wait for the run to finish", "error");
}

function unlockRootAfterRun() {
  setRootBusy(runActive());
  if (ui.rootStatus.textContent.includes("wait for the run to finish")) {
    setRootStatus("");
  }
}

function normalizedRoot(value) {
  return String(value ?? "").trim().replace(/\/+$/, "");
}

// One button opens a typed root and reloads the tree when the path is unchanged.
function syncRootButton() {
  const same =
    normalizedRoot(state.projectRoot) !== "" &&
    normalizedRoot(ui.projectRoot.value) === normalizedRoot(state.projectRoot);
  ui.openRoot.textContent = same ? "Refresh" : "Open";
  ui.openRoot.title = same
    ? "Reload the project file tree"
    : "Open this project root";
}

async function switchRoot() {
  if (runActive()) {
    setRootStatus("cancel or wait for the run to finish", "error");
    return;
  }
  const path = ui.projectRoot.value.trim();
  if (!path) {
    setRootStatus("enter an absolute path", "error");
    return;
  }
  if (normalizedRoot(path) === normalizedRoot(state.projectRoot)) {
    setRootStatus("refreshing…");
    await refreshTree();
    setRootStatus("project files refreshed", "ok");
    return;
  }

  setRootBusy(true);
  setRootStatus("switching…");
  try {
    const health = await putJson("/api/root", { path });
    const root = health?.project_root || path;
    state.projectRoot = root;
    ui.projectRoot.value = root;
    syncRootButton();
    ui.health.textContent = `ok · v${health?.version ?? "?"} · ${root}`;
    ui.health.classList.remove("bad");
    resetForRoot();
    setRootStatus("project root updated", "ok");
    await refreshTree();
  } catch (error) {
    setRootStatus(`switch failed: ${error.message}`, "error");
  } finally {
    setRootBusy(runActive());
  }
}

function resetForRoot() {
  resetTree();
  state.flowFile = null;
  state.flowName = null;
  state.selectedId = null;
  state.nodes = [];
  nodeInventoryToken += 1;
  renderNodeCards("Select a .py file to list nodes.");
  ui.planFile.value = "";
  clearPlan();
  ui.log.replaceChildren();
  ui.resultBanner.classList.add("hidden");
  ui.resultBanner.replaceChildren();
  setJobStatus("idle");
  hideEvalError();
  renderWarnings([]);
}

function message(text, className) {
  const node = document.createElement("p");
  node.className = className || "muted";
  node.textContent = text;
  return node;
}

// --------------------------------------------------------------- selection ----

async function selectFile(path) {
  const lower = path.toLowerCase();
  if (lower.endsWith(".py")) {
    if (state.flowFile !== path) {
      state.flowFile = path;
      state.flowName = null;
      hideEvalError();
      renderWarnings([]);
      clearPlan();
    }
    renderTree();
    await loadNodeInventory(path);
    return;
  }
  if (lower.endsWith(".json")) {
    try {
      const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
      await importPlanText(data?.content ?? "", path);
    } catch (error) {
      showEvalError(`Cannot load ${path}: ${error.message}`);
    }
  }
}

function clearPlan() {
  state.plan = null;
  state.preview = false;
  state.selectedId = null;
  state.dirty = false;
  ui.execute.disabled = true;
  ui.exportPlan.disabled = true;
  ui.dirtyHint.classList.add("hidden");
  ui.graphEmpty.classList.remove("hidden");
  ui.graphEmpty.textContent = "Evaluate a flow to see its graph";
  ui.selectedNode.textContent = "none";
  ui.nodeEditor.replaceChildren(message("Select a node in the graph.", "muted"));
  ui.planStatus.textContent = "none";
  renderGraph(ui.graph, null);
  syncOptions();
  setOptionsEnabled(false);
}

function selectFlow(name) {
  const value = name || "";
  if (value === (state.flowName || "")) return;
  state.flowName = value || null;
  syncNodeSelection();
  const card = state.nodes.find((node) => String(node?.name ?? "") === value);
  if (card) applyPreviewPlan(card);
  else clearPlan();
}

function syncNodeSelection() {
  for (const card of ui.nodeInventory.querySelectorAll(".node-card")) {
    const selected = card.dataset.nodeName === state.flowName;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-selected", selected ? "true" : "false");
  }
}

// A plan never lists the root as a child, so the flow it was built from is
// normally the one discovered node the plan does not mention. Fall back to
// the first segment of the node paths (which is the root name too) when the
// module leaves more than one flow unused. Both guesses are accepted only
// when they name exactly one flow the selected module declares.
function planFlowName(plan) {
  const known = new Set(
    (Array.isArray(state.nodes) ? state.nodes : []).map((node) => String(node?.name ?? "")),
  );
  const entries = Array.isArray(plan?.nodes) ? plan.nodes : [];
  const used = new Set();
  for (const node of entries) {
    const name = String(node?.name ?? "");
    if (!name || (node?.kind ?? "node") === "gather") continue;
    if (!known.has(name)) return null;
    used.add(name);
  }
  const unused = [...known].filter((name) => name && !used.has(name));
  if (unused.length === 1) return unused[0];

  const roots = new Set();
  for (const node of entries) {
    const path = Array.isArray(node?.path) ? node.path : [];
    const root = path.length ? String(path[0] ?? "") : "";
    if (root && known.has(root)) roots.add(root);
  }
  if (roots.size !== 1) return null;
  const [root] = roots;
  return root;
}

function flowSelectionError() {
  if (state.flowName) return null;
  const count = Array.isArray(state.nodes) ? state.nodes.length : 0;
  return count > 1 ? `Select a flow node first (${count} available).` : "Select a flow node first.";
}

// ---------------------------------------------------------- node inventory ----

async function loadNodeInventory(path) {
  const token = ++nodeInventoryToken;
  state.nodes = [];
  renderNodeCards("Loading nodes…");
  inventoryReady = discoverNodes(path, token);
  await inventoryReady;
}

async function discoverNodes(path, token) {
  try {
    const data = await postJson("/api/discover", { flow_file: path });
    if (token !== nodeInventoryToken) return;
    if (!data || data.ok === false || data.error) {
      const error = data?.error ? String(data.error) : "No nodes found.";
      state.nodes = [];
      renderNodeCards(error, "error");
      return;
    }
    state.nodes = Array.isArray(data.nodes) ? data.nodes : [];
    renderNodeCards();
    if (state.nodes.length === 1 && !state.flowName) {
      selectFlow(state.nodes[0].name);
    }
  } catch (error) {
    if (token !== nodeInventoryToken) return;
    state.nodes = [];
    renderNodeCards(`Cannot discover nodes: ${error.message}`, "error");
  }
}

function renderNodeCards(emptyText, emptyClass) {
  ui.nodeInventory.replaceChildren();
  const nodes = Array.isArray(state.nodes) ? state.nodes : [];
  if (!nodes.length) {
    ui.nodeInventory.append(message(emptyText || "No nodes found.", emptyClass || "muted"));
    return;
  }
  for (const node of nodes) {
    ui.nodeInventory.append(buildNodeCard(node));
  }
}

function buildNodeCard(node) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "node-card";
  card.setAttribute("role", "option");
  const name = String(node?.name ?? "");
  card.setAttribute("data-node-name", name);

  const nameNode = document.createElement("span");
  nameNode.className = "node-card-name";
  nameNode.textContent = name;
  card.append(nameNode);

  const summary = String(node?.summary ?? "").trim();
  if (summary) {
    const doc = document.createElement("span");
    doc.className = "node-card-doc";
    doc.textContent = summary;
    card.append(doc);
  }

  const signature = document.createElement("span");
  signature.className = "node-card-sig";
  const label = document.createElement("span");
  label.className = "node-card-label";
  label.textContent = "preview";
  const code = document.createElement("code");
  code.textContent = String(node?.signature ?? "");
  signature.append(label, code);
  card.append(signature);

  const selected = name === state.flowName;
  if (selected) card.classList.add("selected");
  card.setAttribute("aria-selected", selected ? "true" : "false");
  card.addEventListener("click", () => selectFlow(name));
  return card;
}

// ------------------------------------------------------------------- plan ----

function markDirty() {
  if (!state.plan || state.preview) return;
  state.dirty = true;
  ui.dirtyHint.classList.remove("hidden");
}

function buildRootPreview(card) {
  const params = Array.isArray(card?.params) ? card.params : [];
  return {
    schema: PLAN_SCHEMA,
    parameters: params.map((param) => ({
      name: param.name,
      type: param.type ?? "",
      required: Boolean(param.required),
      default: param.default ?? null,
      value: param.default ?? null,
    })),
    nodes: [],
    edges: [],
    options: { ...OPTION_DEFAULTS },
  };
}

function showPlanView(plan, { preview, status, emptyText }) {
  state.plan = plan;
  state.preview = preview;
  state.selectedId = ROOT_NODE_ID;
  state.dirty = false;
  ui.dirtyHint.classList.add("hidden");
  ui.execute.disabled = preview;
  ui.exportPlan.disabled = preview;
  ui.planStatus.textContent = status;
  ui.graphEmpty.classList.add("hidden");
  syncOptions();
  setOptionsEnabled(true);
  renderGraph(ui.graph, plan, {
    onSelect: selectNode,
    selectedId: ROOT_NODE_ID,
    rootLabel: state.flowName || "",
    emptyText,
  });
  renderNodeEditor();
}

function applyPreviewPlan(card) {
  showPlanView(buildRootPreview(card), {
    preview: true,
    status: "preview",
    emptyText: "Fill required inputs, then Evaluate.",
  });
}

// Convert a wire/imported plan into the pure engine document. Display-only
// fields (`editable`, `note`) and wire aliases are stripped.
function planDocument(plan) {
  if (!plan) return null;
  const cleanParams = (params) =>
    (Array.isArray(params) ? params : []).map((param) => ({
      name: param.name,
      type: param.type ?? "",
      required: Boolean(param.required),
      default: param.default ?? null,
      value: param.value ?? null,
    }));
  const parameters = cleanParams(plan.parameters);
  const nodes = (Array.isArray(plan.nodes) ? plan.nodes : []).map((node) => ({
    id: node.id,
    name: node.name,
    kind: node.kind ?? "node",
    path: Array.isArray(node.path) ? node.path : [],
    instance: node.instance ?? 1,
    policy: {
      retries: node.policy?.retries ?? 0,
      retry_delay_seconds: node.policy?.retry_delay_seconds ?? 0.0,
      timeout: node.policy?.timeout ?? null,
    },
    params: cleanParams(node.params),
  }));
  const edges = (Array.isArray(plan.edges) ? plan.edges : []).map((edge) => ({
    from: edge.from ?? edge.source,
    to: edge.to ?? edge.target,
  }));
  const source = plan.options || {};
  const options = {};
  for (const [key, fallback] of Object.entries(OPTION_DEFAULTS)) {
    options[key] = Object.prototype.hasOwnProperty.call(source, key) ? source[key] : fallback;
  }
  return { schema: PLAN_SCHEMA, parameters, nodes, edges, options };
}

function buildPayload() {
  return {
    flow_file: state.flowFile,
    flow_name: state.flowName || null,
    plan: state.plan ? planDocument(state.plan) : null,
  };
}

function applyPlan(plan) {
  showPlanView(plan, {
    preview: false,
    status: PLAN_SCHEMA,
    emptyText: "Root flow — no child nodes.",
  });
}

async function importPlanText(text, label) {
  let document;
  try {
    document = JSON.parse(text);
  } catch (error) {
    showEvalError(`Cannot import ${label}: invalid JSON (${error.message})`);
    return;
  }
  if (!document || document.schema !== PLAN_SCHEMA) {
    showEvalError(`Cannot import ${label}: schema must be "${PLAN_SCHEMA}".`);
    return;
  }
  // Discovery may still be running; wait so the plan's root can be matched
  // against the module's node names before the plan replaces the view.
  await inventoryReady;
  if (!state.flowName) {
    const inferred = planFlowName(document);
    if (inferred) {
      state.flowName = inferred;
      syncNodeSelection();
    }
  }
  applyPlan(document);
  markDirty();
  if (!state.flowFile) {
    showEvalError("Plan imported. Select a .py flow file, then press Evaluate.");
    return;
  }
  await evaluate();
}

function exportPlan() {
  if (state.preview) {
    showEvalError("Evaluate first: preview is not a plan.");
    return;
  }
  if (!state.plan) {
    showEvalError("Nothing to export: evaluate or import a plan first.");
    return;
  }
  const text = JSON.stringify(planDocument(state.plan), null, 2);
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "plan.json";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function validateRequiredInputs() {
  const missing = [];
  for (const param of state.plan?.parameters || []) {
    if (!param.required) continue;
    const value = param.value;
    if (value === undefined || value === null) {
      missing.push(param.name);
      continue;
    }
    if (typeof value === "string" && value.trim() === "") {
      missing.push(param.name);
      continue;
    }
    const path = pathValue(value);
    if (path !== null && path.trim() === "") {
      missing.push(param.name);
    }
  }
  return missing;
}

async function evaluate() {
  if (!state.flowFile) {
    showEvalError("Select a .py flow file first.");
    return;
  }
  const selectionError = flowSelectionError();
  if (selectionError) {
    showEvalError(selectionError);
    return;
  }
  hideEvalError();
  const missing = validateRequiredInputs();
  if (missing.length) {
    showEvalError(`Missing required flow parameter(s): ${missing.join(", ")}`);
    return;
  }
  ui.evaluate.disabled = true;
  ui.evaluate.textContent = "Evaluating…";
  try {
    const result = await postJson("/api/evaluate", buildPayload());
    handleEvaluateResult(result);
  } catch (error) {
    showEvalError(`Evaluate failed: ${error.message}`);
  } finally {
    ui.evaluate.disabled = false;
    ui.evaluate.textContent = "Evaluate";
  }
}

function handleEvaluateResult(result) {
  if (!result || typeof result !== "object") {
    showEvalError("Evaluate returned an unexpected response.");
    return;
  }
  renderWarnings(result.warnings);

  if (!result.ok) {
    showEvalError(result.error || "Evaluate failed.", result.traceback);
    markDirty();
    return;
  }
  if (!result.plan) {
    showEvalError("Evaluate succeeded but returned no plan.");
    markDirty();
    return;
  }

  hideEvalError();
  if (result.flow_name && result.flow_name !== state.flowName) {
    state.flowName = result.flow_name;
    syncNodeSelection();
  }
  applyPlan(result.plan);
}

function selectNode(id) {
  state.selectedId = id;
  selectGraphNode(ui.graph, id);
  renderNodeEditor();
}

// -------------------------------------------------------- parameter editor ----

function widgetKind(type) {
  const text = String(type || "").toLowerCase();
  if (text.includes("list") || text.includes("dict") || text.includes("tuple") || text.includes("set")) {
    return "json";
  }
  if (text.includes("bool")) return "bool";
  if (text.includes("float") || text.includes("decimal")) return "float";
  if (text.includes("int")) return "int";
  return "text";
}

// Numeric coercion shared by the parameter, policy, and option fields.
function toNumber(text, integer) {
  const value = Number(text);
  if (!Number.isFinite(value)) return null;
  if (integer && !Number.isInteger(value)) return null;
  return value;
}

function buildParam(param, commit) {
  const editable = param.editable !== false;
  const kind = widgetKind(param.type);
  const value = param.value;

  const row = document.createElement("div");
  row.className = `param${editable ? "" : " readonly"}`;
  if (!editable && param.note) row.title = param.note;

  const inputId = nextId("param");
  const head = document.createElement("label");
  head.className = "param-head";
  head.htmlFor = inputId;
  const name = document.createElement("span");
  name.className = "param-name";
  name.textContent = param.name;
  const type = document.createElement("span");
  type.className = "param-type";
  type.textContent = param.type || "value";
  head.append(name, type);
  if (param.required) {
    const required = document.createElement("span");
    required.className = "param-required";
    required.textContent = "required";
    head.append(required);
  }
  row.append(head);

  let input;
  let error = null;

  const setError = (text) => {
    if (!error) return;
    error.textContent = text || "";
    error.classList.toggle("hidden", !text);
  };

  if (kind === "bool") {
    input = document.createElement("input");
    input.type = "checkbox";
    input.id = inputId;
    input.checked = Boolean(value);
    input.disabled = !editable;
    input.addEventListener("change", () => {
      commit(input.checked);
    });
  } else if (kind === "int" || kind === "float") {
    input = document.createElement("input");
    input.type = "number";
    input.id = inputId;
    input.step = kind === "int" ? "1" : "any";
    input.value = value === null || value === undefined ? "" : String(value);
    input.disabled = !editable;
    input.addEventListener("input", () => {
      const text = input.value.trim();
      if (text === "") {
        setError("enter a number");
        return;
      }
      const number = toNumber(text, kind === "int");
      if (number === null) {
        setError(kind === "int" ? "not an integer" : "not a number");
        return;
      }
      setError(null);
      commit(number);
    });
  } else if (kind === "json") {
    input = document.createElement("textarea");
    input.id = inputId;
    input.spellcheck = false;
    input.rows = 3;
    input.value = JSON.stringify(value ?? null, null, 2);
    input.disabled = !editable;
    input.addEventListener("input", () => {
      try {
        const parsed = JSON.parse(input.value);
        setError(null);
        commit(parsed);
      } catch (parseError) {
        setError(`invalid JSON: ${parseError.message}`);
      }
    });
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.id = inputId;
    input.value = value === null || value === undefined ? "" : String(value);
    input.disabled = !editable;
    input.addEventListener("input", () => {
      commit(input.value);
    });
  }

  if (!editable) {
    input.title = param.note || "read-only";
    row.title = param.note || "read-only";
  }
  row.append(input);

  if (!editable && param.note) {
    const note = document.createElement("div");
    note.className = "muted";
    note.textContent = param.note;
    row.append(note);
  }

  if (editable) {
    error = document.createElement("div");
    error.className = "field-error hidden";
    error.setAttribute("role", "alert");
    row.append(error);
  }

  return row;
}

// A Path parameter travels as {path, sha256}; its path string, else null.
function pathValue(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return typeof value.path === "string" ? value.path : null;
}

function displayParamValue(value, type) {
  if (String(type || "").toLowerCase().includes("path")) {
    const path = pathValue(value);
    if (path !== null) return path;
  }
  return value;
}

function setNodeParamValue(node, name, value) {
  for (const param of node.params || []) {
    if (param.name === name) param.value = value;
  }
}

function setNodePolicyValue(node, key, value) {
  node.policy = { ...(node.policy || {}), [key]: value };
}

function renderNodeEditor() {
  // Run options share the right column with node parameters: a concrete node
  // replaces them, the flow root (or an empty view) shows them.
  const nodeSelected = Boolean(state.plan) && state.selectedId !== ROOT_NODE_ID;
  ui.runOptions.classList.toggle("hidden", nodeSelected);
  ui.nodeEditor.replaceChildren();
  if (!state.plan) {
    ui.selectedNode.textContent = "none";
    ui.nodeEditor.append(message("Select a node in the graph.", "muted"));
    return;
  }
  if (state.selectedId === ROOT_NODE_ID) {
    ui.selectedNode.textContent = state.flowName || "Flow parameters";
    const params = state.plan.parameters || [];
    if (!params.length) {
      ui.nodeEditor.append(message("No flow inputs.", "muted"));
      return;
    }
    for (const param of params) {
      ui.nodeEditor.append(
        buildParam({ ...param, value: displayParamValue(param.value, param.type) }, (value) => {
          param.value = value;
          markDirty();
        }),
      );
    }
    return;
  }
  const node = (state.plan.nodes || []).find(
    (candidate) => String(candidate.id) === String(state.selectedId),
  );
  if (!node) {
    ui.selectedNode.textContent = "none";
    ui.nodeEditor.append(message("Select a node in the graph.", "muted"));
    return;
  }

  ui.selectedNode.textContent = `${node.name} #${node.instance}`;

  const params = node.params || [];
  if (!params.length) {
    ui.nodeEditor.append(message("No parameters on this node.", "muted"));
  } else {
    for (const param of params) {
      ui.nodeEditor.append(
        buildParam({ ...param, value: displayParamValue(param.value, param.type) }, (value) => {
          setNodeParamValue(node, param.name, value);
          markDirty();
        }),
      );
    }
  }
  ui.nodeEditor.append(buildPolicyEditor(node));
}

function parsePolicyField(text, kind, allowEmpty) {
  if (text.trim() === "") {
    return allowEmpty ? { value: null } : { error: "enter a number" };
  }
  const number = toNumber(text, kind === "int");
  if (number === null || number < 0) {
    return { error: kind === "int" ? "not a non-negative integer" : "not a non-negative number" };
  }
  return { value: number };
}

function buildPolicyEditor(node) {
  const box = document.createElement("div");
  box.className = "policy";
  const heading = document.createElement("h3");
  heading.textContent = `Policy — ${node.name}`;
  box.append(heading);

  const grid = document.createElement("div");
  grid.className = "policy-grid";
  const policy = node.policy || {};
  const fields = [
    ["retries", "int", false],
    ["retry_delay_seconds", "float", false],
    ["timeout", "float", true],
  ];

  for (const [key, kind, allowEmpty] of fields) {
    const label = document.createElement("label");
    const inputId = nextId("policy");
    label.htmlFor = inputId;
    label.textContent = key;
    const input = document.createElement("input");
    input.type = "number";
    input.id = inputId;
    input.step = kind === "int" ? "1" : "any";
    input.min = "0";
    input.placeholder = allowEmpty ? "none" : "0";
    input.value =
      policy[key] === null || policy[key] === undefined ? "" : String(policy[key]);

    const error = document.createElement("div");
    error.className = "field-error hidden";
    error.setAttribute("role", "alert");

    input.addEventListener("input", () => {
      const parsed = parsePolicyField(input.value, kind, allowEmpty);
      if (parsed.error) {
        error.textContent = parsed.error;
        error.classList.remove("hidden");
        return;
      }
      error.classList.add("hidden");
      setNodePolicyValue(node, key, parsed.value);
      markDirty();
    });

    const cell = document.createElement("div");
    cell.className = "policy-cell";
    cell.append(input, error);
    grid.append(label, cell);
  }

  box.append(grid);
  return box;
}

// --------------------------------------------------------------- messages ----

function showEvalError(messageText, traceback) {
  ui.evalError.replaceChildren();
  const headline = document.createElement("div");
  headline.textContent = messageText;
  ui.evalError.append(headline);
  if (traceback) {
    const details = document.createElement("details");
    details.className = "details";
    const summary = document.createElement("summary");
    summary.textContent = "traceback";
    const pre = document.createElement("pre");
    pre.textContent = traceback;
    details.append(summary, pre);
    ui.evalError.append(details);
  }
  ui.evalError.classList.remove("hidden");
}

function hideEvalError() {
  ui.evalError.classList.add("hidden");
  ui.evalError.replaceChildren();
}

function renderWarnings(warnings) {
  ui.warnings.replaceChildren();
  const list = Array.isArray(warnings) ? warnings : [];
  if (!list.length) {
    ui.warnings.classList.add("hidden");
    return;
  }
  for (const warning of list) {
    const item = document.createElement("li");
    item.textContent = String(warning);
    ui.warnings.append(item);
  }
  ui.warnings.classList.remove("hidden");
}

// ----------------------------------------------------------------- run view ----

function pathKey(path) {
  return JSON.stringify(Array.isArray(path) ? path : []);
}

function startRunGraph() {
  const plan = state.plan;
  const nodes = Array.isArray(plan?.nodes) ? plan.nodes : [];
  const nodesByPath = new Map();
  for (const node of nodes) {
    const key = pathKey(node.path);
    if (!nodesByPath.has(key)) nodesByPath.set(key, []);
    nodesByPath.get(key).push(node);
  }
  for (const list of nodesByPath.values()) {
    list.sort((a, b) => Number(a.id) - Number(b.id));
  }

  const deps = new Map();
  for (const node of nodes) deps.set(String(node.id), []);
  for (const edge of Array.isArray(plan?.edges) ? plan.edges : []) {
    const from = edge.from ?? edge.source;
    const to = edge.to ?? edge.target;
    if (from === undefined || to === undefined) continue;
    const id = String(from);
    if (!deps.has(id) || !deps.has(String(to))) continue;
    deps.get(id).push(String(to));
  }

  state.run = {
    nodesById: new Map(nodes.map((node) => [String(node.id), node])),
    nodesByPath,
    deps,
    outcomes: new Map(),
    retrying: new Set(),
    assigned: new Set(),
  };
  refreshRunGraph();
}

// Match a run-log record to a plan occurrence. Records carry the call path but
// not the instance; bound argument values are compared with the plan's
// parameter values, then instances of one path consume plan ids in order.
function recordValues(record) {
  const values = Array.isArray(record.args) ? [...record.args] : [];
  if (record.kwargs && typeof record.kwargs === "object") {
    values.push(...Object.values(record.kwargs));
  }
  return values;
}

function bindingScore(node, values) {
  const planValues = (Array.isArray(node.params) ? node.params : [])
    .map((param) => param.value)
    .filter((value) => value !== null && value !== undefined)
    .map((value) => JSON.stringify(value));
  let score = 0;
  for (const value of values) {
    if (planValues.includes(JSON.stringify(value))) score += 1;
  }
  return score;
}

function bestScored(pool, values) {
  let best = null;
  let bestScore = -Infinity;
  for (const node of pool) {
    const score = bindingScore(node, values);
    if (score > bestScore) {
      best = node;
      bestScore = score;
    }
  }
  return best;
}

function matchRunNode(run, record) {
  const key = pathKey(record.path);
  const candidates = run.nodesByPath.get(key) || [];
  const named = candidates.filter((node) => !record.node || node.name === record.node);
  const pool = named.length ? named : candidates;
  if (pool.length === 0) return null;

  const values = recordValues(record);
  let chosen = null;
  if (Number(record.attempt ?? 0) > 1) {
    const retrying = pool.filter((node) => run.retrying.has(String(node.id)));
    chosen = bestScored(retrying.length ? retrying : pool, values);
  } else {
    const fresh = pool.filter((node) => {
      const id = String(node.id);
      return !run.outcomes.has(id) && !run.assigned.has(id);
    });
    chosen = bestScored(fresh, values);
  }
  if (!chosen) return null;

  const id = String(chosen.id);
  run.assigned.add(id);
  return id;
}

function applyRunRecord(record) {
  const run = state.run;
  if (!run || !record || typeof record !== "object" || record.record !== "node") return;
  const id = matchRunNode(run, record);
  if (id === null) return;

  const status = String(record.status ?? "");
  if (status === "ok") {
    run.outcomes.set(id, "ok");
    run.retrying.delete(id);
  } else if (status === "skipped") {
    run.outcomes.set(id, "skipped");
    run.retrying.delete(id);
  } else {
    const retries = Number(run.nodesById.get(id)?.policy?.retries ?? 0);
    const attempt = Number(record.attempt ?? 0);
    if (attempt > 0 && attempt <= retries) {
      run.retrying.add(id);
    } else {
      run.outcomes.set(id, "error");
      run.retrying.delete(id);
    }
  }
  refreshRunGraph();
}

function refreshRunGraph() {
  const run = state.run;
  if (!run) return;
  const states = new Map();
  for (const id of run.nodesById.keys()) {
    const outcome = run.outcomes.get(id);
    if (outcome) {
      states.set(id, outcome);
      continue;
    }
    const deps = run.deps.get(id) || [];
    if (run.retrying.has(id) || deps.every((dep) => run.outcomes.get(dep) === "ok")) {
      states.set(id, "running");
    }
  }
  setGraphNodeStates(ui.graph, states);
}

function finishRunGraph() {
  const run = state.run;
  if (!run) return;
  setGraphNodeStates(ui.graph, new Map(run.outcomes));
  state.run = null;
}

// ----------------------------------------------------------------- execute ----

async function execute() {
  if (!state.flowFile) {
    showEvalError("Select a .py flow file first.");
    return;
  }
  if (!state.plan) {
    showEvalError("Evaluate the flow before executing.");
    return;
  }
  const selectionError = flowSelectionError();
  if (selectionError) {
    showEvalError(selectionError);
    return;
  }
  hideEvalError();
  ui.execute.disabled = true;
  ui.cancel.disabled = false;
  ui.cancel.classList.remove("hidden");
  ui.resultBanner.classList.add("hidden");
  ui.resultBanner.replaceChildren();
  ui.log.replaceChildren();
  setJobStatus("starting…");
  lockRootForRun();
  startRunGraph();

  try {
    const data = await postJson("/api/execute", buildPayload());
    if (!data?.job_id) throw new Error("response did not include a job_id");
    state.jobId = data.job_id;
    openStream(data.job_id);
  } catch (error) {
    setJobStatus("failed to start");
    showEvalError(`Execute failed: ${error.message}`);
    ui.cancel.classList.add("hidden");
    ui.execute.disabled = !state.plan;
    state.jobId = null;
    finishRunGraph();
    unlockRootAfterRun();
  }
}

function openStream(jobId) {
  if (state.source) {
    state.source.close();
    state.source = null;
  }
  const source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
  state.source = source;

  source.addEventListener("status", (event) => {
    const data = parseEvent(event);
    setJobStatus(data?.state || "status");
  });
  source.addEventListener("log", (event) => {
    const data = parseEvent(event);
    const record = data?.record ?? data;
    applyRunRecord(record);
    appendLog(record);
  });
  source.addEventListener("done", (event) => {
    const data = parseEvent(event);
    source.close();
    if (state.source === source) state.source = null;
    state.jobId = null;
    finishRun(data);
  });
  source.onerror = () => {
    if (state.source === source) setJobStatus("stream disconnected — retrying");
  };
}

function parseEvent(event) {
  try {
    return JSON.parse(event.data);
  } catch {
    return { text: event.data };
  }
}

function finishRun(data) {
  setJobStatus(data?.state || "done");
  finishRunGraph();
  showResult(data?.result, data?.state, data?.error);
  if (data?.result && Array.isArray(data.result.warnings)) {
    renderWarnings(data.result.warnings);
  }
  ui.cancel.classList.add("hidden");
  ui.cancel.disabled = false;
  ui.execute.disabled = !state.plan;
  unlockRootAfterRun();
}

function setJobStatus(text) {
  ui.jobStatus.textContent = String(text);
}

function logSummary(record) {
  if (record === null || record === undefined) return "log";
  if (typeof record !== "object") return String(record);
  const node = record.node ?? record.name ?? record.flow ?? "?";
  const status = record.status ?? record.event ?? record.state ?? record.level ?? "log";
  const duration = record.duration_ms ?? record.durationMs ?? record.elapsed_ms;
  const attempt = record.attempt != null ? ` #${record.attempt}` : "";
  const timing =
    duration === null || duration === undefined || Number.isNaN(Number(duration))
      ? ""
      : ` · ${Number(duration)} ms`;
  return `${node}${attempt} · ${status}${timing}`;
}

function appendLog(record) {
  const item = document.createElement("li");
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = logSummary(record);
  const body = document.createElement("pre");
  body.textContent = JSON.stringify(record ?? null, null, 2);
  details.append(summary, body);
  item.append(details);

  const nearBottom = ui.log.scrollHeight - ui.log.scrollTop - ui.log.clientHeight < 48;
  ui.log.append(item);
  if (nearBottom) ui.log.scrollTop = ui.log.scrollHeight;
}

function showResult(result, finalState, topError) {
  const banner = ui.resultBanner;
  banner.replaceChildren();
  banner.classList.remove("hidden", "bad");

  const run = result?.run || null;
  const failed =
    finalState !== "succeeded" ||
    result?.ok === false ||
    Boolean(topError) ||
    Boolean(result?.error);
  if (failed) banner.classList.add("bad");

  const parts = [
    ["status", run?.status ?? finalState ?? "unknown"],
    ["result", run?.result ?? null],
    ["duration", run?.duration_ms != null ? `${run.duration_ms} ms` : result?.duration_ms != null ? `${result.duration_ms} ms` : null],
    ["node", run?.node || null],
    ["attempt", run?.attempt != null ? String(run.attempt) : null],
    ["error", run?.error ?? result?.error ?? topError ?? null],
    [
      "failed nodes",
      Array.isArray(run?.failed_nodes) && run.failed_nodes.length
        ? run.failed_nodes.map((path) => (Array.isArray(path) ? path.join(" › ") : String(path))).join("; ")
        : null,
    ],
    ["log", run?.log || null],
    ["run id", run?.run_id || null],
  ];

  let shown = 0;
  for (const [key, value] of parts) {
    if (value === null || value === undefined || value === "") continue;
    const keyNode = document.createElement("span");
    keyNode.className = "key";
    keyNode.textContent = `${key}:`;
    const valueNode = document.createElement("span");
    valueNode.className = "val";
    const text = typeof value === "object" ? JSON.stringify(value) : String(value);
    valueNode.textContent = text.length > 600 ? `${text.slice(0, 597)}…` : text;
    valueNode.title = text;
    banner.append(keyNode, valueNode);
    shown += 1;
  }
  if (!shown) {
    const plain = document.createElement("span");
    plain.textContent = finalState || "done";
    banner.append(plain);
  }
}

async function cancelRun() {
  if (!state.jobId) return;
  ui.cancel.disabled = true;
  try {
    const status = await api(`/api/jobs/${encodeURIComponent(state.jobId)}/cancel`, {
      method: "POST",
    });
    setJobStatus(status?.state || "cancelling…");
  } catch (error) {
    if (error.status === 404) {
      // The job is gone (server restarted or the record was already dropped).
      if (state.source) {
        state.source.close();
        state.source = null;
      }
      state.jobId = null;
      ui.cancel.classList.add("hidden");
      setJobStatus("job already finished");
      ui.execute.disabled = !state.plan;
      unlockRootAfterRun();
    } else {
      setJobStatus("cancel failed");
      showEvalError(`Cancel failed: ${error.message}`);
    }
  } finally {
    ui.cancel.disabled = false;
  }
}

// ------------------------------------------------------------ run options ----

const OPTION_INPUTS = [
  ui.optMaxWorkers,
  ui.optRetries,
  ui.optRetryDelay,
  ui.optTimeout,
  ui.optSummary,
  ui.optFixedClock,
];

function setOptionsEnabled(enabled) {
  for (const input of OPTION_INPUTS) input.disabled = !enabled;
}

function syncOptions() {
  const options = { ...OPTION_DEFAULTS, ...(state.plan?.options || {}) };
  ui.optMaxWorkers.value = String(options.max_workers);
  ui.optRetries.value = String(options.retries);
  ui.optRetryDelay.value = String(options.retry_delay_seconds);
  ui.optTimeout.value =
    options.timeout === null || options.timeout === undefined ? "" : String(options.timeout);
  ui.optSummary.value = options.summary ? "true" : "false";
  ui.optFixedClock.value = options.fixed_clock ? "true" : "false";
}

function readOptions() {
  if (!state.plan) return;
  if (!state.plan.options) state.plan.options = { ...OPTION_DEFAULTS };
  const options = state.plan.options;
  const number = (input, integer, minimum) => {
    const text = input.value.trim();
    if (text === "") return null;
    const value = toNumber(text, integer);
    if (value === null || value < minimum) return null;
    return value;
  };
  const maxWorkers = number(ui.optMaxWorkers, true, 1);
  if (maxWorkers !== null) options.max_workers = maxWorkers;
  const retries = number(ui.optRetries, true, 0);
  if (retries !== null) options.retries = retries;
  const retryDelay = number(ui.optRetryDelay, false, 0);
  if (retryDelay !== null) options.retry_delay_seconds = retryDelay;
  if (ui.optTimeout.value.trim() === "") {
    options.timeout = null;
  } else {
    const timeout = number(ui.optTimeout, false, 0);
    if (timeout !== null) options.timeout = timeout;
  }
  options.summary = ui.optSummary.value === "true";
  options.fixed_clock = ui.optFixedClock.value === "true";
  markDirty();
}

// ----------------------------------------------------------------- wiring ----

ui.fileList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-path]");
  if (!button) return;
  const path = button.dataset.path;
  if (button.dataset.kind === "dir") {
    toggleDir(path).catch((error) =>
      showEvalError(`Cannot list ${path}: ${error.message}`),
    );
  } else {
    selectFile(path).catch((error) =>
      showEvalError(`Cannot open ${path}: ${error.message}`),
    );
  }
});

ui.openRoot.addEventListener("click", switchRoot);
ui.projectRoot.addEventListener("input", syncRootButton);
ui.projectRoot.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    switchRoot();
  }
});
ui.evaluate.addEventListener("click", evaluate);
ui.execute.addEventListener("click", execute);
ui.cancel.addEventListener("click", cancelRun);
ui.fitGraph.addEventListener("click", () => fitGraph(ui.graph));
ui.clearLog.addEventListener("click", () => ui.log.replaceChildren());
ui.importPlan.addEventListener("click", () => ui.planFile.click());
ui.exportPlan.addEventListener("click", exportPlan);

ui.planFile.addEventListener("change", () => {
  const file = ui.planFile.files?.[0];
  ui.planFile.value = "";
  if (!file) return;
  file
    .text()
    .then((text) => importPlanText(text, file.name))
    .catch((error) => showEvalError(`Cannot read ${file.name}: ${error.message}`));
});

for (const input of OPTION_INPUTS) {
  input.addEventListener("input", readOptions);
  input.addEventListener("change", readOptions);
}

renderNodeCards("Select a .py file to list nodes.");
syncOptions();
setOptionsEnabled(false);

boot().catch((error) => {
  ui.health.textContent = `startup failed: ${error.message}`;
  ui.health.classList.add("bad");
});
