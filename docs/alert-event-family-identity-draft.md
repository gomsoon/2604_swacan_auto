# Alert Event Family Identity Draft

Version: Draft 0.1
Updated: 2026-05-13

## Goal

Extend family-level current alert identity from threshold-style families to the
`grouped_event_repeat` event family.

This removes close/open churn when the winning published event rule changes
inside the same monitored object and event family.

## Scope

Phase 2 is intentionally narrow.

- `signal_type = grouped_event_repeat`
- `state_type = process`
- `signal_key = process_started | process_stopped | process_restarted`
- scalar `gte` repeat-count thresholds only
- runtime worker current-alert identity only

Out of scope:

- raw-event identity
- custom event windows
- multi-signal event rules
- event-family transition timeline UI
- opener-rule archive snapshot separate from final winner snapshot

## Identity Contract

Event families reuse the same storage fields introduced for threshold families:

- `identity_kind`
- `identity_key`

For event families:

- `identity_kind = 'family'`
- `identity_key = 'event:<monitored_object_id>:<state_type>:<signal_key>:<comparison>'`

Example:

- `event:1302:process:process_restarted:gte`

## Runtime Semantics

For the same monitored object and the same event family:

1. if no winner exists and no current row exists, do nothing
2. if a winner exists and no current row exists, create one current row
3. if the winner stays the same, update the same current row
4. if the winner changes but the family still fires, keep the same current row
   and update winner-specific fields
5. if the family clears, resolve/archive the current row

Winner ordering stays the same:

1. `monitored_object` beats `object_type`
2. `critical` beats `warning`
3. newer rule wins
4. larger `rule_id`

## Resolution Contract

Phase 2 keeps the current event-family closure vocabulary.

- family cleared because the grouped event window elapsed:
  - `resolution_source = auto_recovery`
  - `resolution_reason = event_window_elapsed`
- losing fired event rules remain suppressed through precedence semantics

## Suggested Implementation Order

1. extend identity helper/backfill to event-family keys
2. switch runtime event path to family-based current row lookup/update
3. keep preview/archive explainability contract unchanged
4. add regression coverage for:
   - warning -> critical same-row update
   - object-type -> monitored-object winner switch on same row
   - archive only when the family fully clears

## Deferred Backlog

- event-family transition counters/timeline
- raw-event family identity
- multi-signal event-family identity
- dedicated archive analytics for winner changes
