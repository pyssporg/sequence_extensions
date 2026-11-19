# 06-evolution/selected — Selected Candidates

Change candidates selected for implementation, recorded ahead of any code change.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **IMP-018** [Pickle payload tier for run-log values](pickle-payload-tier-for-run-log-values.md) — jsonable falls back to str() for values JSON cannot express; an optional deferred pickle sidecar would preserve full structure
- **IMP-020** [Split ext from flow at a future release](split-ext-from-flow-at-a-future-release.md) — One distribution ships two unrelated products; kept together for 1.0.0, revisit when either half grows a dependency
- **IMP-026** [Reject unknown node parameter names](reject-unknown-node-parameter-names.md) — A parameter name the node signature does not accept fails at injection time instead of reaching the body or being swallowed by **kwargs
- **IMP-027** [Fill node parameters for inline calls](fill-node-parameters-for-inline-calls.md) — A name-wide parameter entry reaches nodes called directly, not only nodes submitted to the pool
- **IMP-028** [One null rule for parameter values](one-null-rule-for-parameter-values.md) — null is the value None for an optional parameter, missing for a required one, and absence is the only unset signal
<!-- pb:index:end -->
