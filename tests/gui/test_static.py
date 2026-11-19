"""Contract tests for the offline static frontend."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC = REPO_ROOT / "src" / "seq_ext_gui" / "static"
STATIC_FILES = ["index.html", "styles.css", "app.js", "graph.js"]


def read(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    match = re.search(rf"function {name}\([^)]*\) \{{(.*?)\n\}}", source, re.DOTALL)
    assert match, f"{name} helper not found"
    return match.group(1)


@pytest.mark.parametrize("name", STATIC_FILES)
def test_static_file_exists_and_is_not_empty(name: str) -> None:
    path = STATIC / name
    assert path.is_file(), f"missing src/seq_ext_gui/static/{name}"
    assert path.stat().st_size > 0, f"empty static asset: {name}"


def test_index_html_is_fully_local() -> None:
    html = read("index.html")
    assert not re.search(r"https?://", html, re.IGNORECASE), "external URL in index.html"
    assert "//cdn" not in html.lower(), "CDN reference in index.html"
    assert not re.search(r"\bcdn\.", html, re.IGNORECASE), "CDN host in index.html"

    refs = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", html)
    assert refs, "index.html should reference its static assets"
    for ref in refs:
        assert ref.startswith("/static/"), f"non-local asset reference: {ref}"


def test_no_innerhtml_assignment() -> None:
    # Engine text is untrusted: the UI must build nodes with textContent only.
    for name in ("app.js", "graph.js"):
        source = read(name)
        assert not re.search(r"\.innerHTML\s*=", source), f"innerHTML assignment in {name}"
        assert not re.search(r"\.outerHTML\s*=", source), f"outerHTML assignment in {name}"


def test_app_js_references_http_api() -> None:
    source = read("app.js")
    for endpoint in ("/api/evaluate", "/api/execute", "/api/jobs/", "/api/file?path="):
        assert endpoint in source, f"app.js does not call {endpoint}"


@pytest.mark.parametrize("name", ["app.js", "graph.js"])
def test_javascript_parses_as_an_es_module(name: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    proc = subprocess.run(
        [node, "--check", str(STATIC / name)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"node --check failed for {name}:\n{proc.stderr}"


def test_app_js_dom_ids_exist_in_html() -> None:
    html = read("index.html")
    source = read("app.js")
    defined = set(re.findall(r"""\bid\s*=\s*["']([^"']+)["']""", html))
    referenced = set(re.findall(r"""\$\(\s*["']([^"']+)["']\s*\)""", source))
    referenced |= set(re.findall(r"""getElementById\(\s*["']([^"']+)["']\s*\)""", source))
    missing = sorted(referenced - defined)
    assert not missing, f"app.js references missing DOM ids: {missing}"


def test_no_inline_event_handlers_or_external_assets() -> None:
    html = read("index.html")
    assert not re.search(r"<[^>]+\son[a-z]+\s*=", html, re.IGNORECASE), "inline handler"
    for name in ("app.js", "graph.js"):
        source = read(name)
        urls = re.findall(r"https?://[^\s\"'`]+", source)
        external = [url for url in urls if not url.startswith("http://www.w3.org/")]
        assert not external, f"external URL in {name}: {external}"


def test_module_script_runs_after_dom() -> None:
    html = read("index.html")
    assert '<script type="module" src="/static/app.js"></script>' in html
    assert html.rindex("/static/app.js") > html.rindex("</main>")


def test_plan_document_emits_only_the_engine_fields() -> None:
    source = read("app.js")
    body = function_body(source, "planDocument")
    for field in ("schema", "parameters", "nodes", "edges", "options"):
        assert re.search(rf"\b{field}\b", body), f"planDocument omits {field}"
    assert "flow-plan/2" in source
    assert not re.search(r"\beditable\b", body), "planDocument leaks editable"
    assert not re.search(r"\bnote\b", body), "planDocument leaks note"
    assert re.search(r"\bpath:\s*Array\.isArray\(node\.path\)", body), "path identity lost"
    assert re.search(r"\binstance:\s*node\.instance\s*\?\?\s*1", body), "instance identity lost"
    assert re.search(r"\bfrom:\s*edge\.from\s*\?\?\s*edge\.source", body)
    assert re.search(r"\bto:\s*edge\.to\s*\?\?\s*edge\.target", body)


def test_build_payload_shape() -> None:
    body = function_body(read("app.js"), "buildPayload")
    for key in ("flow_file", "flow_name", "plan"):
        assert re.search(rf"\b{key}\b", body), f"buildPayload omits {key}"
    for removed in ("config_file", "config_text", "cwd", "overrides"):
        assert not re.search(rf"\b{removed}\b", body), f"buildPayload still sends {removed}"
    assert "planDocument(state.plan)" in body
    assert re.search(r"state\.plan\s*\?", body), "plan should be null when absent"


def test_execute_payload_and_endpoints() -> None:
    source = read("app.js")
    assert "new EventSource(" in source
    assert "/api/jobs/" in source and "/events" in source and "/cancel" in source
    assert "/api/tree?path=" in source
    assert 'method: "PUT"' not in source
    assert "content: state.configText" not in source


def test_plan_import_recovers_the_flow_root(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    source = read("app.js")
    body = function_body(source, "planFlowName")

    import_body = function_body(source, "importPlanText")
    assert "await inventoryReady" in import_body, "import must wait for discovery"
    assert "planFlowName(document)" in import_body, "import must recover the plan root"
    assert import_body.index("planFlowName(document)") < import_body.index("applyPlan(document)"), (
        "the root must be known before the plan is applied"
    )

    script = tmp_path / "plan_root.mjs"
    script.write_text(
        "const state = { nodes: [], flowName: null };\n"
        "function planFlowName(plan) {\n"
        + body
        + "\n}\n"
        + """
function check(actual, expected, message) {
  if (actual !== expected) throw new Error(`${message}: ${actual}`);
}
const plan = {
  nodes: [
    { name: "prepare_data", path: ["pipeline", "prepare_data"] },
    { name: "simulate", path: ["pipeline", "simulate"] },
  ],
};
state.nodes = [{ name: "pipeline" }, { name: "prepare_data" }, { name: "simulate" }];
check(planFlowName(plan), "pipeline", "root recovered from unused flow names");
state.nodes = [{ name: "simulate" }, { name: "postprocess" }];
check(planFlowName(plan), null, "foreign plan node rejected");
state.nodes = [{ name: "pipeline" }];
check(
  planFlowName({
    nodes: [
      { name: "pipeline", path: ["a", "x"] },
      { name: "pipeline", path: ["b", "y"] },
    ],
  }),
  null,
  "ambiguous roots rejected",
);
state.nodes = [{ name: "pipeline" }, { name: "other" }];
check(planFlowName({ nodes: [] }), null, "rootless plan stays ambiguous");

state.nodes = [
  { name: "campaign" },
  { name: "evaluate" },
  { name: "simulate" },
  { name: "summarize" },
];
const gather_plan = {
  nodes: [
    { name: "simulate", path: ["campaign", "simulate"] },
    { name: "evaluate", path: ["campaign", "evaluate"] },
    { name: "gather", kind: "gather", path: ["gather"] },
    { name: "summarize", path: ["campaign", "summarize"] },
  ],
};
check(planFlowName(gather_plan), "campaign", "engine gather node is not a root");
state.nodes = [
  { name: "campaign" },
  { name: "report" },
  { name: "evaluate" },
  { name: "simulate" },
  { name: "summarize" },
];
check(planFlowName(gather_plan), "campaign", "path fallback when two flows are unused");
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"plan root recovery test failed:\n{proc.stderr}"


def test_execute_requires_a_selected_flow(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    source = read("app.js")
    assert "flowSelectionError()" in function_body(source, "evaluate")
    assert "flowSelectionError()" in function_body(source, "execute"), (
        "execute must refuse a run without a flow instead of failing in the worker"
    )

    script = tmp_path / "flow_guard.mjs"
    script.write_text(
        "const state = { nodes: [], flowName: null };\n"
        "function flowSelectionError() {\n"
        + function_body(source, "flowSelectionError")
        + "\n}\n"
        + """
function check(actual, expected, message) {
  if (actual !== expected) throw new Error(`${message}: ${actual}`);
}
check(flowSelectionError() !== null, true, "no flow is rejected");
state.nodes = [{ name: "a" }, { name: "b" }];
check(flowSelectionError(), "Select a flow node first (2 available).", "count is reported");
state.flowName = "a";
check(flowSelectionError(), null, "selected flow passes");
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"flow selection guard test failed:\n{proc.stderr}"


def test_plan_import_export_controls() -> None:
    html = read("index.html")
    source = read("app.js")
    toolbar = html[html.index('id="dirty-hint"') : html.index('id="cancel"')]
    for element_id in ("import-plan", "export-plan", "plan-file", "plan-status"):
        assert f'id="{element_id}"' in toolbar, f"#{element_id} must sit in the graph toolbar"
    assert 'accept=".json,application/json"' in html
    assert 'type="file"' in html

    assert 'id="flow-file"' not in html
    assert "Flow file" not in html
    assert "<h2>Plan</h2>" not in html
    assert "plan-actions" not in html

    assert "function importPlanText" in source
    assert "document.schema !== PLAN_SCHEMA" in source
    assert "flow-plan/2" in source
    assert "function exportPlan" in source
    assert "JSON.stringify(planDocument(state.plan), null, 2)" in source
    assert '"plan.json"' in source
    assert "ui.importPlan.addEventListener" in source
    assert "ui.exportPlan.addEventListener" in source


def test_project_root_switch_controls() -> None:
    html = read("index.html")
    source = read("app.js")

    for element_id in ("project-root", "open-root", "root-status"):
        assert f'id="{element_id}"' in html, f"missing project root control #{element_id}"
    assert 'aria-label="Project root path"' in html
    assert re.search(
        r'<div id="root-status"[^>]*\brole="status"[^>]*\baria-live="polite"',
        html,
    ), "root status must be a polite live region"
    assert html.index('id="project-root"') < html.index('id="file-list"'), (
        "project root controls must sit above the file browser"
    )

    assert "/api/root" in source, "app.js does not call /api/root"
    assert 'putJson("/api/root", { path })' in source, "root switch must use PUT"
    assert "function switchRoot" in source
    assert 'ui.openRoot.addEventListener("click", switchRoot)' in source
    assert 'ui.projectRoot.addEventListener("keydown"' in source, "Enter wiring is missing"
    assert "health.project_root" in source

    for text in (html, source):
        assert not re.search(r"https?://", text, re.IGNORECASE), "external URL introduced"


def test_file_browser_routes_py_and_json() -> None:
    source = read("app.js")
    assert 'lower.endsWith(".py")' in source, "clicking .py must select the workflow"
    assert 'lower.endsWith(".json")' in source, "clicking .json must import a plan"
    assert "await importPlanText(" in source


def test_file_browser_is_a_lazy_tree() -> None:
    html = read("index.html")
    source = read("app.js")
    css = read("styles.css")

    assert 'id="file-list"' in html, "missing tree control #file-list"
    assert 'id="refresh-tree"' not in html, "tree refresh is merged into #open-root"
    assert "function syncRootButton" in source
    assert '"Refresh"' in source and '"Open"' in source
    assert 'id="crumbs"' not in html, "breadcrumb nav must be gone"
    assert "crumbs" not in source, "breadcrumb renderer must be gone"
    assert re.search(r'id="file-list"[^>]*role="tree"', html), "#file-list must be a tree"

    assert re.search(r'setAttribute\("role", "treeitem"\)', source)
    assert re.search(r"setAttribute\(\"aria-expanded\"", source)
    assert re.search(r"setAttribute\(\"aria-level\"", source)
    assert "state.expanded" in source
    assert "children: new Map()" in source
    assert "function fetchDir" in source
    assert "function toggleDir" in source
    assert "function renderTree" in source
    assert "function refreshTree" in source
    assert "function appendEntries" in source
    assert "loadTree(" not in source, "the flat loader must be replaced"
    assert "No .py or .json files here." in source

    toggle = function_body(source, "toggleDir")
    assert "state.expanded.has(path)" in toggle
    assert "fetchDir(" in toggle
    assert "renderTree()" in toggle

    refresh = function_body(source, "refreshTree")
    assert "state.expanded" in refresh, "refresh must keep the expanded set"
    assert "Promise.all" in refresh
    assert "renderTree()" in refresh

    click = source[source.index('ui.fileList.addEventListener("click"') :]
    assert "toggleDir(path)" in click
    assert "loadTree(" not in click

    assert re.search(r"\.file-list\s*\{[^}]*max-height:\s*320px", css, re.DOTALL)
    assert ".crumbs" not in css


def test_node_inventory_discovery() -> None:
    html = read("index.html")
    source = read("app.js")

    assert 'id="node-inventory"' in html
    assert 'class="node-inventory"' in html
    assert 'aria-label="Node inventory"' in html
    assert 'role="listbox"' in html

    assert "/api/discover" in source
    assert "function loadNodeInventory" in source
    assert "function renderNodeCards" in source
    assert "data-node-name" in source
    assert 'postJson("/api/discover", { flow_file: path })' in source
    assert "function selectFlow" in source
    assert "Select a .py file to list nodes." in source
    assert "Loading nodes…" in source
    assert "No nodes found." in source
    assert 'card.className = "node-card"' in source
    assert 'label.textContent = "preview"' in source


def test_root_preview_and_required_inputs() -> None:
    html = read("index.html")
    source = read("app.js")

    assert 'id="flow-select"' not in html
    for removed in ("flow-params", "flow-params-status", "flow-params-error"):
        assert f'id="{removed}"' not in html

    assert "function buildRootPreview" in source
    assert "function applyPreviewPlan" in source
    assert "state.preview" in source
    assert '"preview"' in source
    assert "function validateRequiredInputs" in source
    assert "Missing required flow parameter(s): " in source
    assert "Fill required inputs, then Evaluate." in source


def test_run_options_mutate_the_plan() -> None:
    source = read("app.js")
    body = function_body(source, "readOptions")
    assert "state.plan.options" in body
    assert "markDirty()" in body
    for key in (
        "max_workers",
        "summary",
        "fixed_clock",
        "retries",
        "retry_delay_seconds",
        "timeout",
    ):
        assert key in source, f"run option {key} is missing"

    layout = read("index.html")
    editor = layout[layout.index('class="panel editor-panel"') :]
    assert editor.index('id="run-options"') < editor.index("</aside>"), (
        "run options belong in the right-hand editor column"
    )
    left = layout[layout.index('id="left-panel"') : layout.index('class="right"')]
    assert 'id="run-options"' not in left, "run options must not stay in the left panel"
    editor_body = function_body(source, "renderNodeEditor")
    assert 'ui.runOptions.classList.toggle("hidden", nodeSelected)' in editor_body
    assert "state.selectedId !== ROOT_NODE_ID" in editor_body


def test_parameter_edits_use_the_plan_not_overrides() -> None:
    source = read("app.js")
    assert "param.editable !== false" in source
    assert "input.disabled = !editable" in source
    assert "function buildParam(param, commit)" in source
    for removed in ("reconcileOverrides", "deleteOverride", "state.overrides", "emptyOverrides"):
        assert removed not in source, f"stale override helper remains: {removed}"
    assert "param.value = value" in source


def test_node_edits_target_one_occurrence() -> None:
    source = read("app.js")
    assert "edits apply to all of them" not in source
    assert "candidate.name !== node.name" not in source
    assert "setNodeParamValue(node, param.name, value)" in source
    assert "setNodePolicyValue(node, key, parsed.value)" in source


def test_edit_one_instance_leaves_sibling_unchanged(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    source = read("app.js")
    script = tmp_path / "instance_edit.mjs"
    script.write_text(
        "function setNodeParamValue(node, name, value) {\n"
        + function_body(source, "setNodeParamValue")
        + "\n}\nfunction setNodePolicyValue(node, key, value) {\n"
        + function_body(source, "setNodePolicyValue")
        + "\n}\n"
        + """
const first = {
  id: 1,
  name: "scale",
  instance: 1,
  params: [{ name: "factor", value: 1 }],
  policy: { retries: 0 },
};
const second = {
  id: 2,
  name: "scale",
  instance: 2,
  params: [{ name: "factor", value: 1 }],
  policy: { retries: 0 },
};
const plan = { nodes: [first, second] };
setNodeParamValue(plan.nodes[0], "factor", 10);
setNodePolicyValue(plan.nodes[0], "retries", 2);
if (first.params[0].value !== 10) throw new Error("selected param not updated");
if (first.policy.retries !== 2) throw new Error("selected policy not updated");
if (second.params[0].value !== 1) throw new Error("sibling param changed");
if (second.policy.retries !== 0) throw new Error("sibling policy changed");
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"single-instance edit test failed:\n{proc.stderr}"


def test_synthetic_root_is_gui_only() -> None:
    html = read("index.html")
    app = read("app.js")
    graph = read("graph.js")

    # The root is synthesized in the view layer; the plan schema has no root.
    assert "export const ROOT_NODE_ID" in graph
    assert "export function withRootNode" in graph
    assert 'kind: "root"' in graph
    assert "rootEdges" in graph
    assert "to: ROOT_NODE_ID" in graph
    assert "plan.root" not in app
    assert "plan.root" not in graph

    # Apply selects the root and passes the flow label to the renderer.
    assert "ROOT_NODE_ID" in app
    assert "state.selectedId = ROOT_NODE_ID" in app
    assert "rootLabel: state.flowName" in app

    # The standalone flow-inputs panel is replaced by the root node editor.
    for dead in ("root-editor", "root-node"):
        assert dead not in html
        assert dead not in app


@pytest.mark.parametrize("name", STATIC_FILES)
def test_no_toml_config_surface(name: str) -> None:
    source = read(name).lower()
    assert "toml" not in source, f"TOML surface remains in {name}"
    assert "save-config" not in source, f"save-config control remains in {name}"
    assert "config_file" not in source, f"config_file remains in {name}"
    assert "config_text" not in source, f"config_text remains in {name}"


def test_graph_layout_edge_cases(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    module = tmp_path / "graph.mjs"
    module.write_text(read("graph.js"), encoding="utf-8")
    script = tmp_path / "layout.mjs"
    script.write_text(
        f"""
import {{ computeLayout, withRootNode }} from {module.as_uri()!r};

function check(value, message) {{
  if (!value) throw new Error(message);
}}

const empty = computeLayout(null);
check(empty.nodes.length === 0 && empty.positions.size === 0, "empty plan");

const raw = {{
  parameters: [{{ name: "alpha", type: "int", value: 3 }}],
  nodes: [
    {{ id: 1, name: "entry" }},
    {{ id: 2, name: "dependent" }},
  ],
  edges: [{{ from: 2, to: 1 }}],
}};
const view = withRootNode(raw, "demo");
check(view !== raw && raw.nodes.length === 2, "withRootNode is non-destructive");
check(view.nodes.length === 3, "root appended");
const root = view.nodes.find((node) => node.id === "root");
check(root && root.kind === "root" && root.name === "demo", "root node shape");
check(root.params === raw.parameters, "root reuses plan parameters");
check(view.edges.some((edge) => edge.from === 1 && edge.to === "root"), "entry to root");
check(!view.edges.some((edge) => edge.from === 2 && edge.to === "root"), "only entry nodes");
const rooted = computeLayout(view);
check(rooted.positions.get("root").y < rooted.positions.get("1").y, "root above entry");
check(rooted.positions.get("1").y < rooted.positions.get("2").y, "entry above dependent");

const bare = withRootNode({{ parameters: [], nodes: [], edges: [] }}, "");
check(bare.nodes.length === 1 && bare.nodes[0].name === "Flow parameters", "bare root");

const one = computeLayout({{ nodes: [{{ id: 7, name: "solo" }}], edges: [] }});
const single = one.positions.get("7");
check(single && single.x === 0 && single.y === 0, "single node");

const plan = {{
  nodes: [
    {{ id: 3, name: "same" }},
    {{ id: 10, name: "same" }},
    {{ id: 42, name: "other" }},
  ],
  edges: [
    {{ from: 10, to: 3 }},
    {{ from: 42, to: 10 }},
  ],
}};
const laid = computeLayout(plan);
check(laid.positions.size === 3, "non-contiguous ids");
check(laid.positions.get("3").y < laid.positions.get("10").y, "dependency above dependent");
check(laid.positions.get("10").y < laid.positions.get("42").y, "transitive rank");

const alias = computeLayout({{
  nodes: [{{ id: 1, name: "a" }}, {{ id: 2, name: "b" }}],
  edges: [{{ source: 1, target: 2 }}],
}});
check(alias.links.length === 1, "source/target alias");
check(alias.links[0].source === "1" && alias.links[0].target === "2", "alias direction");
""",
        encoding="utf-8",
    )
    proc = subprocess.run([node, str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"graph layout test failed:\n{proc.stderr}"
