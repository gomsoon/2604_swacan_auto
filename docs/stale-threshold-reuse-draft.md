# Stale Threshold-Style Reuse

## Scope

MVP `stale` does not open as a separate rule family. Instead, it reuses the
existing `latest_state_metric` threshold evaluator over derived runtime metrics.

The first enabled stale path is:

- `state_type = agent`
- `signal_type = latest_state_metric`
- `metric_key = heartbeat_age_seconds`
- `comparison = gte`

This means stale alerting now works through ordinary published threshold rules.

## Runtime contract

- Preview and runtime both evaluate the same derived `heartbeat_age_seconds`
  metric.
- The ingest worker periodically re-evaluates published
  `heartbeat_age_seconds` rules even when no new agent payload arrives.
- A stale alert can therefore open after time passes and later resolve when a
  fresh heartbeat arrives.

## Current limits

- This slice only enables stale reuse for `agent.heartbeat_age_seconds`.
- It does not introduce a separate `stale` rule family.
- `no-data` still remains deferred until baseline timing, first-seen grace
  period, and rematch/reset policy are clarified.
