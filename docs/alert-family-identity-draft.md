# Alert Family Identity Draft

Version: Draft 0.2
Updated: 2026-05-23

## Goal

Reduce close/open churn when the winning published rule changes inside the same
alert family for the same monitored object.

The main design change is:

- current alert identity becomes family-based
- winner rule becomes mutable state on that current row

This lets ACK/in-progress state stay attached to the same active incident while
precedence still decides which rule is currently winning.

## Current Status

Phase 1 is now implemented for threshold-style runtime families.

- current threshold incidents use `identity_kind = 'family'`
- the same current row survives winner changes inside the same family
- event-family identity is now implemented separately; see
  [alert-event-family-identity-draft.md](C:/2604_swacan_auto/docs/alert-event-family-identity-draft.md)
- the next shared follow-up is opener snapshots plus winner-transition
  analytics

## Phase 1 Scope

Phase 1 is intentionally narrow.

- threshold-style families only
- published rules only
- runtime worker path only
- current alert identity only

Threshold-style families include:

- scalar threshold
- compound threshold
- stale reuse over `heartbeat_age_seconds`
- no-data reuse over `latest_state_age_seconds`

Out of scope for phase 1:

- winner transition timeline UI
- opener-rule snapshot separate from final winner snapshot
- suppressed current alert rows
- family-level archive analytics

## Identity Contract

Two explicit identity fields are added to current/archive storage.

- `identity_kind`
- `identity_key`

Phase 1 values:

- legacy/event rule identity
  - `identity_kind = 'rule'`
  - `identity_key = 'rule:<source_rule_id>'` when a source rule exists
  - otherwise `identity_key = 'code:<alert_code>'`
- threshold family identity
  - `identity_kind = 'family'`
  - `identity_key = 'threshold:<monitored_object_id>:<state_type>:<metric_key>:<comparison>'`

`identity_key` is the durable incident identity. `alert_code` may still change
when the winning rule changes.

## Phase 1 Runtime Semantics

For the same monitored object and the same threshold family:

1. If no winner exists and no current row exists, do nothing.
2. If a winner exists and no current row exists, create one current row.
3. If the winner stays the same, update the same current row.
4. If the winner changes but the family still fires, keep the same current row
   and update:
   - `source_rule_id`
   - `alert_code`
   - `severity`
   - `latest_message`
   - `metadata_json`
   - `last_occurred_at`
   - `updated_at`
5. If the family clears, resolve/archive the current row.

Phase 1 keeps the existing winner ordering:

1. `monitored_object` beats `object_type`
2. `critical` beats `warning`
3. newer rule wins
4. larger `rule_id`

The design changes identity semantics, not winner ranking semantics.

## ACK / Status Semantics

Because the current row is reused:

- ACK stays attached when the winner changes
- in-progress state stays attached when the winner changes
- the incident resolves only when the whole family clears

This is the main operator-facing benefit of family identity.

## Archive Semantics

Phase 1 archive rows also carry:

- `identity_kind`
- `identity_key`

The archive row still records the final winning rule snapshot through:

- `source_rule_id`
- `source_rule_key`
- `source_rule_display_name_snapshot`

Phase 1 does not yet add a separate opener snapshot or winner-transition count.

## Suggested Implementation Order

1. add identity columns to current/archive tables
2. backfill legacy rows with rule/family identity keys where possible
3. switch threshold runtime path to family-based current row lookup/update
4. keep event runtime path rule-based for now
5. add regression coverage for winner change without current-row churn

## Deferred Backlog

- family-level archive analytics
- winner transition timeline / counts
- opener rule snapshot separate from final winner snapshot
- separate suppressed current rows
- preview UI showing family identity directly
