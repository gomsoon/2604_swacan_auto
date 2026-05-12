# Alert Explainability Draft

Version: Draft 0.1
Updated: 2026-05-13

## Goal

Use the same explanation contract across:

1. preview responses
2. current alert payloads
3. archive/detail payloads

The immediate goal is not a full trace tree. The goal is to make the same alert
readable with the same language no matter where the operator sees it.

## Explanation Contract

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
- `suppressed_rule_keys`
- `resolution_reason`

Notes:

- `value_key` means `metric_key` for threshold-style rules and `signal_key` for
  event rules.
- `reason` is human-readable.
- `winning_condition_trace` is the structured machine-readable reason.
- `resolution_reason` is only meaningful for resolved/archive payloads.

## Phase 1 Scope

This phase keeps the slice narrow.

- add `explanation` to preview items
- add `explanation` to current alert payloads
- add `explanation` to archive payloads
- normalize runtime metadata so threshold/event paths carry the same fields

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

## Deferred Backlog

These stay out of the current slice and should remain backlog items:

1. full candidate/winner/suppressed catalog UI
2. clause-level deep trace drill-down for suppressed rules
3. family-level current alert identity
4. suppressed current-row retention
5. `reason_code + reason_message + reason_params`
