---
id: TEST-002
type: test
title: How a change is accepted end to end
summary: Campaign example: plan shape, then a successful run
date: 2026-11-12
status: current
---

# How a change is accepted end to end

A UI or engine change is accepted when the campaign example plans, runs, and renders with the expected shape and result.

- **Plan:** evaluate returns schema `flow-plan/2` with no `root` key, concrete `options`, 10 nodes, 9 edges, and 3 root parameters.
- **Execute:** the shipped 4-case example returns `{"cases": 4, "passed": 2, "mean": 1.565}` with status ok.
- **Browser:** the same plan shows 10 graph nodes, the log streams to done, and the console has no JS errors.
- **Automated part:** `test_engine.py` and the integration API tests check the plan shape and a real-worker evaluate.
- **Manual part:** the browser side is a hand walkthrough, so this bar is only as repeatable as that check (`IMP-030`).
- **Bar:** a UI or engine change that breaks one of these numbers is not accepted.
