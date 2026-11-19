# 04-verification/gui-application — GUI Verification

How the GUI is proven — the suite levels, CI, the end-to-end acceptance run, and the gaps left open.

## Ask

"How do we know the GUI works?" — the levels (`TEST-001`), the end-to-end acceptance run (`TEST-002`), CI (`TEST-003`), and what is deliberately not verified (`TEST-004`).

## When to Read

- Before claiming a GUI change is done.
- When adding a test and choosing its level.

## Boundary

- Holds evidence only.
- The design under test is `02-architecture/gui-application/`.
- The engine's test strategy and stress findings stay in the parent layer, `04-verification/`.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **TEST-001** [What the test suite proves](what-the-test-suite-proves.md) — Static, engine, schema, API, integration, and browser checks
- **TEST-002** [How a change is accepted end to end](how-a-change-is-accepted-end-to-end.md) — Campaign example: plan shape, then a successful run
- **TEST-003** [What runs in CI](what-runs-in-ci.md) — One tests workflow, engine and GUI jobs, Python 3.11 and 3.12, split coverage
- **TEST-004** [What is not verified](what-is-not-verified.md) — Browser automation, opaque values, nested composites
<!-- pb:index:end -->
