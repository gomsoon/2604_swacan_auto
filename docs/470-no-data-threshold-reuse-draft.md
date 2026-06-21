# No-Data Threshold-Style Reuse

## Scope

MVP `no-data` does not open as a separate rule family. Instead, it reuses the
existing `latest_state_metric` threshold evaluator over a derived metric:

- `metric_key = latest_state_age_seconds`
- meaning: `now - latest_states.received_at`

The first enabled no-data path is:

- `state_type = process | host`
- `signal_type = latest_state_metric`
- `metric_key = latest_state_age_seconds`
- `comparison = gte`
- `condition_mode = scalar`

## Runtime contract

- Preview and runtime both evaluate the same derived
  `latest_state_age_seconds` metric.
- The ingest worker periodically re-evaluates published
  `latest_state_age_seconds` rules even when no new payload arrives.
- A no-data alert can therefore open after time passes and later resolve when a
  fresh state payload arrives again.
- Resolution uses `resolution_reason = data_resumed`.

## Current limits

- This slice only enables no-data reuse for `process` and `host` state types.
- `agent` no-data/stale should continue to use
  `metric_key = heartbeat_age_seconds`.
- `never-seen` objects are not evaluated in this MVP.
- First-seen grace periods, publish-time grace periods, rematch/reset baseline
  handling, and custom per-rule windows remain deferred.
- This slice does not introduce a separate `no-data` rule family.
