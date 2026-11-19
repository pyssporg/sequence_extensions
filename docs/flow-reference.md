# Flow and sequence reference

Narrative reference for the sequence helpers, graph futures, and the flow
engine. [docs/API.md](API.md) is the canonical per-method API reference; the
engine's current-state semantics are owned by the
[flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md).
Use this page for worked examples and API.md for signatures, parameters, and
return values.

## list_ext

```python
from sequence_extensions import list_ext

l = list_ext([1, 2, 3, 4])

l.map(lambda x: x * 2)
[2, 4, 6, 8]

l.filter(lambda x: x % 2 == 0)
[2, 4]

l.for_each(lambda x: print(x))
1
2
3
4

l.first(lambda x: x % 2 == 0)
2

l.last(lambda x: x % 2 == 0)
4

l.to_strings()
["1", "2", "3", "4"]

l.to_string()
"1, 2, 3, 4"

l.to_string(prefix="[", suffix="]")
"[1, 2, 3, 4]"
```

`list_ext.to_string` defaults to `", "` (while `dict_ext.to_string` defaults to `"\n"`).

### More list_ext helpers

```python
l.window(2)  # [[1, 2], [2, 3], [3, 4]]  (inner windows are list_ext)
l.window(5)  # []
l.window_select(lambda a, b: a + b)  # [3, 5, 7]
list_ext.execute_or_default(
    lambda: [1, 2][5], default="D"
)  # 'D'  (catches IndexError, KeyError by default)
list_ext.execute_or_default(
    lambda: 1 / 0, default="D"
)  # raises ZeroDivisionError (not caught by default)
list_ext.execute_or_default(lambda: 1 / 0, default="D", exception=ZeroDivisionError)  # 'D'
l.get_item_or_default(10, "D")  # 'D'
l.first_or_default(lambda x: x > 10, "D")  # 'D'
l.last_or_default(lambda x: x > 10, "D")  # 'D'
l.to_type(str)  # ['1', '2', '3', '4']
l.to_set()  # {1, 2, 3, 4}
l.to_tuple()  # (1, 2, 3, 4)
list_ext([1, 2]).to_dict_key(["a", "b"])  # {'a': 1, 'b': 2}
list_ext([1, 2]).to_dict_value(["a", "b"])  # {1: 'a', 2: 'b'}
list_ext([1, 2, 3]).to_dict_key(["a", "b"])  # raises ValueError (length mismatch)
l.to_dict_fn(lambda x: "k" + str(x), lambda x: x * 10)  # {'k1': 10, 'k2': 20, 'k3': 30, 'k4': 40}
list_ext([1, "a", 2, "b"]).of_type(int)  # [1, 2]
list_ext([True, 1]).of_type(int)  # [True, 1]  (isinstance)
l.contains(3)  # True
l.is_empty()  # False
l.is_single()  # False
list_ext([5]).single()  # 5
list_ext([1, 2]).single()  # raises ValueError "Expected exactly one item, got 2"
l.intersect([3, 4, 5])  # [3, 4]
l.union([5, 6])  # [1, 2, 3, 4, 5, 6]
list_ext([{"a": 1}, {"a": 2, "b": 3}]).chainmap()  # {'a': 1, 'b': 3}  (first dict wins)
l.average()  # 2.5
list_ext([]).average()  # raises statistics.StatisticsError
l.max()  # 4
l.min()  # 1
l.reduce(lambda a, b: a + b)  # 10
l.zip()  # []  (no args)
l.zip(["a", "b", "c", "d"])  # [(1, 'a'), (2, 'b'), (3, 'c'), (4, 'd')]
```

## dict_ext

`dict_ext` extends `dict` with functional helpers that operate on `(key, value)` pairs:

```python
from sequence_extensions import dict_ext

d = dict_ext({"a": 1, "b": 2, "c": 3, "d": 4})

d.map(lambda k, v: (k * 2, v * 2))  # dict_ext({'aa': 2, 'bb': 4, 'cc': 6, 'dd': 8})
d.map(lambda k, v: (k * 2, v * 2), cast=dict)  # {'aa': 2, 'bb': 4, 'cc': 6, 'dd': 8}  (plain dict)
d.map(lambda k, v: v * 2, cast=list)  # [2, 4, 6, 8]  (plain list)
d.filter(lambda k, v: v % 2 == 0)  # {'b': 2, 'd': 4}
d.filter()  # same dict (no func keeps all entries)
d.for_each(lambda k, v: print(k, v))  # prints each pair
d.to_list()  # [['a', 1], ['b', 2], ['c', 3], ['d', 4]]
d.to_strings()  # {'a': '1', 'b': '2', 'c': '3', 'd': '4'}
d.to_strings(key=False)  # {'a': '1', 'b': '2', 'c': '3', 'd': '4'}  (keys kept as-is, values str)
d.to_strings(value=False)  # {'a': 1, 'b': 2, 'c': 3, 'd': 4}  (keys str, values kept as-is)
d.to_string()  # 'a : 1\nb : 2\nc : 3\nd : 4'  (default separator "\n")
d.to_string(separator=";")  # 'a : 1;b : 2;c : 3;d : 4'
d.get_keys()  # ['a', 'b', 'c', 'd']
d.get_values()  # [1, 2, 3, 4]
d.to_tuple()  # (('a', 1), ('b', 2), ('c', 3), ('d', 4))
d.to_named_tuple()  # (KeyValueTuple(key='a', value=1), ...)
d.get_key_from_value(3)  # ['c']
d.reduce(lambda a, b: (a.key + b.key, a.value + b.value))  # {'abcd': 10}
dict_ext().reduce(lambda a, b: (a.key + b.key, a.value + b.value))  # {}  (empty dict_ext)
d.extend({"e": 5})  # merged dict (other wins on conflicts)
d.union({"e": 5})  # dict union (other wins on conflicts)
dict_ext({"a": 1}).extend({"a": 9, "b": 2})  # {'a': 9, 'b': 2}  (other wins)
d.inverse()  # {1: 'a', 2: 'b', 3: 'c', 4: 'd'}
d.first()  # KeyValueTuple(key='a', value=1)
d.first(lambda k, v: v == 2)  # KeyValueTuple(key='b', value=2)
d.last()  # KeyValueTuple(key='d', value=4)
d.last(lambda k, v: v == 2)  # KeyValueTuple(key='b', value=2)
d.all(lambda k, v: type(v) == int)  # True
d.all()  # True  (values-only)
d.any(lambda k, v: v == 1)  # True
dict_ext({"a": 0, "b": 0}).any()  # False  (values-only)
```

`KeyValueTuple` is a `NamedTuple` with `.key` and `.value` attributes, returned by `first`, `last`, `reduce`, and `to_named_tuple`. Import it with `from sequence_extensions import KeyValueTuple` (exported from the package root).

## gen_ext

Static helpers for generators and iterables:

```python
from sequence_extensions import gen_ext

gen_ext.to_list(iter([1, 2, 3]))  # [1, 2, 3]
list(gen_ext.recursive_gen(5, lambda x: x - 1, stop_f=lambda x: x > 0))  # [4, 3, 2, 1]
```

`recursive_gen` yields each next item produced by `iter_f`; `stop_f` is called on the *next* item — when it returns `False` the walk stops before yielding that item. The starting item is never yielded. If `iter_f` raises `StopIteration`, the walk stops cleanly.

> **Warning:** if `stop_f` is `None` the walk never terminates — use `itertools.islice` or always pass a `stop_f`.

## graph_future

Dependency-graph futures evaluated with a bounded thread pool:

```python
from sequence_extensions import GraphFuture, GraphPool


def add(x, y):
    return x + y


with GraphPool(max_workers=4) as pool:
    a = GraphFuture(lambda: 1)
    b = GraphFuture(lambda: 2)
    c = GraphFuture(add, a, b)  # waits for a and b
    result = pool.result(c)  # 3
```

`GraphFuture` nodes may depend on other nodes; results are resolved automatically. `GraphPool` can also be used without the context manager (the executor is created lazily on first use).

### graph_future — advanced usage

```python
from sequence_extensions import GraphFuture, GraphPool


# Chaining: a function returning another GraphFuture forwards its result.
# Plain concurrent.futures.Future values are dependencies too, and are
# forwarded when returned.
def outer():
    return GraphFuture(lambda: 20)


with GraphPool(max_workers=4) as pool:
    chained = GraphFuture(outer)
    pool.result(chained)  # 20

    # Cycle detection: a cyclic dependency graph raises ValueError("dependency cycle detected")

    # Exceptions raised by a node's function propagate from pool.result()
    bad = GraphFuture(lambda: 1 / 0)
    pool.result(bad)  # raises ZeroDivisionError

    # Timeout: GraphPool.result(gf, timeout=...) raises TimeoutError if not ready in time
    fast = GraphFuture(lambda: 42)
    pool.result(fast, timeout=5)  # 42
```

Pool lifecycle, cancellation scope, and re-entry are owned by
[components](breakdown/02-architecture/components.md); [API.md](API.md) lists
the errors each method raises.

## flow

The mini flow engine — parallel, deterministic, audited. A **node** is a function with retry/backoff/timeout policy; `execute_flow` opens a **run**: run identity, a bounded pool, and one JSON-lines audit log. The execution model is owned by the [flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md).

```python
from pathlib import Path

from sequence_extensions.flow import RunOptions, execute_flow, gather, node


@node(retries=2, retry_delay_seconds=0.1, timeout=60.0)
def simulate(case: Path) -> dict: ...  # one case; flakes are retried, hangs are bounded


@node
def evaluate(sim: dict, tolerance: float) -> dict: ...


@node
def merge(evaluations: list) -> dict:
    return {
        "count": len(evaluations),
        "mean_score": sum(e["score"] for e in evaluations) / len(evaluations),
        "passed": sum(1 for e in evaluations if e["passed"]),
        "all_passed": all(e["passed"] for e in evaluations),
    }


@node
def campaign(cases_dir: Path, tolerance: float = 0.5) -> dict:
    cases = sorted(cases_dir.glob("*.csv"))  # plain call: sequential
    sims = [simulate.submit(c) for c in cases]  # concurrent map
    evals = [evaluate.submit(s, tolerance) for s in sims]  # futures = edges
    return merge.submit(gather(evals))  # no .result() wait


run = execute_flow(campaign, Path("cases"), options=RunOptions(max_workers=16, log="runs"))
run.result, run.run_id, run.status, run.log, run.duration_ms, run.failed_nodes
```

Run semantics — the run boundary, plain versus `.submit()` calls, retry/timeout
policy, dependency edges, future consumption and `gather` shapes, drain and
failure behaviour, nested nodes, log records, and process-pool limits — are
owned by the [flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md)
and the [node-body contract](breakdown/02-architecture/node-body-and-future-consumption.md).
The `Run`/`RunOptions` surface is in [API.md](API.md).

CPU-bound campaigns swap threads for processes:

```python
from sequence_extensions.flow import ProcessGraphPool, RunOptions, execute_flow

with ProcessGraphPool() as pool:  # worker processes instead of threads
    run = execute_flow(campaign, cases_dir, options=RunOptions(pool=pool))
```

Two examples of the log's shape (from the acceptance test's campaign — six cases, one flaky):

```json
{"seq": 3, "schema": 2, "record": "node", "run_id": "campaign-20261013T101500-1a2b3c4d", "node": "simulate", "path": ["campaign", "simulate"], "attempt": 1, "parent_attempt": 1, "status": "error", "args": [{"path": "cases/case_3.csv", "sha256": "…"}], "error": {"type": "RuntimeError", "message": "transient simulator crash on case_3"}, "worker": "graph-worker_2"}
{"seq": 4, "schema": 2, "record": "node", "run_id": "campaign-20261013T101500-1a2b3c4d", "node": "simulate", "path": ["campaign", "simulate"], "attempt": 2, "parent_attempt": 1, "status": "ok", "args": [{"path": "cases/case_3.csv", "sha256": "…"}], "result": {"case": "case_3", "score": 0.3}, "worker": "graph-worker_2"}
```

For wrapping real simulators (subprocess timeouts, `sbatch`-and-poll for HPC), see the recipes in [docs/hpc-recipes.md](hpc-recipes.md).

## Run options

There is no global configuration: everything a run needs travels with the `execute_flow` call. Field defaults and precedence are owned by the [flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md); [API.md](API.md) has the per-field table.

```python
from sequence_extensions.flow import NodePolicy, RunOptions, execute_flow

run = execute_flow(
    campaign,
    Path("cases"),
    options=RunOptions(
        max_workers=8,  # default 16
        log="output/runs",  # default "runs"; None disables
        summary=False,  # log item counts for long containers
        fixed_clock=False,  # reference mode (see below)
        retries=0,  # run-level retries (one log per attempt)
        timeout=None,  # run-level wall budget
        node_defaults=NodePolicy(  # defaults for nodes that left a value unset
            retries=2,
            retry_delay_seconds=0.5,
            timeout=30.0,
        ),
        node_policies={"simulate": NodePolicy(timeout=60.0)},  # plan overrides
    ),
)
```

Resolution precedence (exact-identity plan policy over name-wide plan policy,
then the `@node` keyword, `node_defaults`, and the built-in default) is owned by
the [flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md);
the per-occurrence rule is in [override an input for one node occurrence](breakdown/01-product/planning/override-an-input-for-one-node-occurrence.md).

`fixed_clock = true` opts a run into **reference mode**: an identical run
produces a byte-identical log, with the run id pinned to `<node>-fixed`. The
pinned fields, canonical order, retry rejection, and path exclusivity are owned
by the [flow engine](breakdown/02-architecture/flow-engine-decorators-over-the-graph-substrate.md).

## Plan document

A `flow-plan/2` JSON document is the whole run configuration: the root parameters with bound values, every node (id, name, kind, path, instance, effective policy, parameters), the edges, and the run `options`. It never selects the flow — that stays outside the document (GUI dropdown, `flow-runner --flow`).

```python
import json
from pathlib import Path

from sequence_extensions.flow import (
    NodeIdentity,
    RunOptions,
    apply_override,
    diff_plans,
    execute_plan,
    jsonable,
    plan_document,
    plan_manifest,
)

document = plan_document(campaign, Path("cases"), options=RunOptions(max_workers=8))
manifest = plan_manifest(document)  # same shape, every value stripped
edited = apply_override(
    document,
    {
        "nodes": [
            # Name-wide: every evaluate occurrence.
            {"name": "evaluate", "params": [{"name": "tolerance", "value": 0.7}]},
            # Exact identity: only the second evaluate occurrence.
            {
                "name": "evaluate",
                "path": ["campaign", "evaluate"],
                "instance": 2,
                "params": [{"name": "tolerance", "value": 0.9}],
            },
        ]
    },
)
diff_plans(document, edited)  # {"equal": False, "changes": [...]}

Path("plan.json").write_text(json.dumps(jsonable(edited)))
run = execute_plan(campaign, json.loads(Path("plan.json").read_text()), log="runs")
```

The capabilities — preview the graph, extract settable inputs, override one
occurrence, see an override's effect, and diff two plans — are owned by
[see a flow](breakdown/01-product/planning/see-a-flow-before-it-runs.md),
[extract](breakdown/01-product/planning/extract-what-a-flow-can-be-tuned-with.md),
[override](breakdown/01-product/planning/override-an-input-for-one-node-occurrence.md),
[see an override's effect](breakdown/01-product/planning/see-an-override-s-effect-before-the-run.md),
and [diff](breakdown/01-product/planning/diff-two-flow-plans.md). The function
contracts and wire shape are in [API.md](API.md).
