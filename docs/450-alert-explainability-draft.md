# Alert Explainability Draft

Version: Draft 0.2
Updated: 2026-05-24

## Goal

Use the same explanation contract across:

1. preview responses
2. current alert payloads
3. archive/detail payloads

The immediate goal is not a full trace tree. The goal is to make the same alert
readable with the same language no matter where the operator sees it.

The operator-facing questions stay fixed:

1. Why did this fire?
2. Which rule became the winner?
3. Which rules were suppressed?
4. Why did this close?

## Explanation Contract V2

The shared `explanation` object should stay small and stable.

- `rule_key`
- `display_name`
- `signal_type`
- `value_key`
- `threshold_level`
- `reason`
- `winning_condition_trace`
- `family_key`
- `winner_rule_key`
- `winner_display_name`
- `suppressed_rule_keys`
- `suppressed_rule_display_names`
- `resolution_reason`

Notes:

- `value_key` means `metric_key` for threshold-style rules and `signal_key` for
  event rules.
- `reason` is human-readable.
- `winning_condition_trace` is the structured machine-readable reason.
- `resolution_reason` is only meaningful for resolved/archive payloads.

## Reason Vocabulary

Reason text should stay short, stable, and category-specific.

Recommended templates:

- threshold scalar upper-bound:
  - `{metric_key}={value} met {level} threshold {threshold}`
- threshold scalar lower-bound:
  - `{metric_key}={value} met {level} lower threshold {threshold}`
- threshold compound:
  - `{metric_key}={value} matched {level} condition ({logical_operator}, clause {n})`
- event grouped repeat:
  - `{signal_key} repeat count {count} met {level} threshold {threshold}`
- stale threshold reuse:
  - `heartbeat_age_seconds={value} met {level} threshold {threshold}`
- no-data threshold reuse:
  - `latest_state_age_seconds={value} met {level} threshold {threshold}`

Resolution vocabulary remains code-oriented in storage and user-readable in UI.

## UI Reading Order

Preview/current/archive/timeline should reuse the same reading order:

1. Rule
2. Why it fired
3. Winner / suppressed
4. Why it closed

Preview may group this into:

1. Current rule evaluation
2. Final winner
3. Suppressed rules
4. Decision trace

## Current Scope

This phase keeps the slice narrow.

- keep `explanation` stable across preview items, current alert payloads, and archive payloads
- normalize threshold/event/stale/no-data reason vocabulary
- make preview/current/archive/timeline use the same operator-facing labels
- avoid introducing a larger trace tree before the wording is stable

This phase does not add:

- full candidate trace trees
- family-level alert identity
- suppressed current rows
- `reason_code` / i18n

## Preview Rules

Preview explanation is winner-centric.

- if a winner exists, `rule_key` and `display_name` describe the winner
- `winner_rule_key` equals the final winner
- `suppressed_rule_keys` lists the losing rules in the same family/object
- `reason` explains why the winning rule fired

If there is no winner, preview may still expose a partial explanation with:

- current rule identity
- `reason = null`
- `winner_rule_key = null`

## Runtime / Archive Rules

Runtime metadata should carry the same explanation ingredients so current alert
and archive serializers do not need separate rule-family-specific logic.

Recommended runtime metadata fields:

- `rule_key`
- `display_name`
- `signal_type`
- `metric_key` or `signal_key`
- `threshold_level`
- `reason`
- `winning_condition_trace`
- `family_key`
- `winner_rule_key`
- `suppressed_rule_keys`
- nested `explanation`

Archive serializers may rebuild the top-level `explanation` object from runtime
metadata plus archive-only fields such as `resolution_reason`.

Current/archive cards should explicitly show:

- `Opened by`
- `Current winner` or `Final winner`
- `Why it fired`
- `Why it closed`
- `Winner transitions` when family identity is active

Winner transition timeline rows should show:

- `previous rule -> new rule`
- severity change
- occurred time
- transition reason note when available

## Deferred Backlog

These stay out of the current slice and should remain backlog items:

1. full candidate/winner/suppressed catalog UI
2. clause-level deep trace drill-down for suppressed rules
3. full transition analytics dashboard
4. suppressed current-row retention
5. `reason_code + reason_message + reason_params`
6. debug-oriented raw explanation dump view
