# Alert Winner Transition Analytics Draft

Version: Draft 0.1
Updated: 2026-05-23

## Goal

Now that threshold-style families and event families both keep one current
incident row per monitored object and alert family, the next gap is explaining
how that incident evolved over time.

The near-term goal is:

- keep one current incident row per family
- remember which rule opened that incident
- count and timestamp winner-rule changes on the current row
- preserve the same summary on the archive row after resolution
- record each winner transition in a dedicated append-only timeline table

This slice should improve archive analytics and operator understanding without
reopening the larger identity model.

## Current Status

Already implemented:

- threshold-style families use `identity_kind = 'family'`
- `grouped_event_repeat` event families use `identity_kind = 'family'`
- winner changes no longer force close/open churn
- archive rows already preserve the final winner snapshot through:
  - `source_rule_id`
  - `source_rule_key`
  - `source_rule_display_name_snapshot`
- current and archive rows now preserve opener/final winner summary through:
  - `opening_rule_*`
  - `winner_transition_count`
  - `last_winner_transition_at`
- runtime worker now writes append-only `alert_winner_transitions` rows on
  actual winner-rule changes
- current/admin/monitor/archive serializers now expose
  `winner_transition_summary`

Still missing:

- dedicated API/detail view for `alert_winner_transitions`
- winner-transition timeline UI
- richer timeline analytics beyond opener/final winner summary

## Phase 1 Scope

Phase 1 is intentionally narrow.

Included:

- threshold-style families
- event families
- winner-rule changes only
- archive/current summary columns
- dedicated append-only transition table

Excluded:

- severity-only timeline rows when the winner rule does not change
- full candidate tree history
- suppressed-rule timeline rows
- aggregate dashboard analytics
- transition timeline UI beyond basic API exposure

## Summary Column Contract

Add the following explicit summary columns to `alert_instances`:

- `opening_rule_id`
- `opening_rule_key`
- `opening_rule_display_name_snapshot`
- `winner_transition_count`
- `last_winner_transition_at`

Mirror the same fields onto `alert_history_archive` so resolved incidents keep
the same summary.

Semantic roles:

- `opening_rule_*`
  - snapshot of the rule that opened the current family incident
  - set once on incident creation
  - never overwritten by later winner changes
- `source_rule_*`
  - snapshot of the current winner while the incident is open
  - becomes the final winner snapshot in archive rows
- `winner_transition_count`
  - increments only when the winning rule changes to another rule
  - does not increment for repeat updates or severity changes on the same rule
- `last_winner_transition_at`
  - timestamp of the most recent winner-rule change
  - remains `NULL` when the incident never changed winner

## Transition Timeline Table

Add a dedicated append-only table:

- `alert_winner_transitions`

Recommended columns:

- `id`
- `alert_instance_id`
- `identity_kind`
- `identity_key`
- `monitored_object_id`
- `previous_rule_id`
- `previous_rule_key`
- `previous_rule_display_name_snapshot`
- `previous_severity`
- `new_rule_id`
- `new_rule_key`
- `new_rule_display_name_snapshot`
- `new_severity`
- `transition_reason`
- `occurred_at`
- `created_at`
- `metadata_json` optional

Phase 1 keeps `transition_reason` intentionally simple:

- `winner_rule_changed`

Richer reason categories such as specificity/recency/severity causality are
deferred until the timeline itself is stable.

## Runtime Semantics

### 1. Incident opens

When a family starts firing and no current row exists:

- create one current row
- set `opening_rule_*` from the opening winner
- set `source_rule_*` from the same winner
- set `winner_transition_count = 0`
- set `last_winner_transition_at = NULL`

### 2. Winner stays the same

When the same rule stays the winner:

- keep the same current row
- update repeat/message/severity metadata as usual
- do not insert a transition row
- do not increment `winner_transition_count`

### 3. Winner changes

When the family still fires but the winning rule changes:

- keep the same current row
- insert one row into `alert_winner_transitions`
- update:
  - `source_rule_id`
  - `source_rule_key`
  - `source_rule_display_name_snapshot`
  - `alert_code`
  - `severity`
  - `latest_message`
  - `metadata_json`
  - `winner_transition_count += 1`
  - `last_winner_transition_at = now`

The current row `id` remains stable.

### 4. Family resolves

When the whole family clears:

- resolve/archive the same current row
- copy `opening_rule_*`, `winner_transition_count`,
  `last_winner_transition_at` into the archive row
- keep `source_rule_*` as the final winner snapshot

## Archive Analytics Shape

With the Phase 1 summary fields, archive detail can immediately show:

- `Opened by`
- `Final winner`
- `Winner transitions`
- `Last winner change`

This is intentionally enough for operator understanding before adding a richer
timeline UI.

## Recommended Implementation Slice

### Slice 1A. Schema and migration

1. add summary columns to `alert_instances`
2. add summary columns to `alert_history_archive`
3. add `alert_winner_transitions`
4. backfill legacy/current rows conservatively:
   - `opening_rule_* = source_rule_*` when missing
   - `winner_transition_count = 0`
   - `last_winner_transition_at = NULL`

### Slice 1B. Runtime worker write path

1. initialize opener summary fields on incident creation
2. detect winner-rule changes for threshold/event family paths
3. insert a transition row on winner change
4. update current-row summary counters/timestamps
5. copy opener/transition summary into archive rows

### Slice 1C. API and serializer exposure

1. expose summary columns on current alert payloads
2. expose summary columns on archive payloads
3. optionally add a detail endpoint for transition rows

Status:

- summary columns are now exposed on admin current-alert payloads
- summary columns are now exposed on monitoring current-alert payloads
- summary columns are now exposed on archive payloads
- dedicated transition-row detail API remains deferred

UI timeline rendering can remain a later slice.

## Regression Expectations

Phase 1 should add regression coverage for at least:

- family incident opens with opener snapshot populated
- threshold winner change keeps the same current row and increments transition
  count
- event winner change keeps the same current row and increments transition count
- no transition row is written when only severity changes on the same winner
- archive row preserves opener snapshot and final winner snapshot separately
- archive row preserves `winner_transition_count` and
  `last_winner_transition_at`

## Deferred Backlog

- causality-specific transition reasons
- severity-only transition timeline rows
- suppressed-rule timeline rows
- opener-to-final candidate tree analytics
- dashboard-level aggregate transition analytics
- current/archive UI timeline panel
