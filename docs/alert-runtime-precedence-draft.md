# Alert Runtime Precedence Draft

Version: Draft 0.1
Updated: 2026-05-10

## Goal

Align alert preview winner/suppressed hints with the runtime worker so that
published scalar threshold rules follow the same precedence decision for the
same monitored object and threshold family.

## Phase 1 Scope

Phase 1 is intentionally narrow.

- published rules only
- scalar threshold rules only
- same monitored object only
- same threshold family only
- winner-only current alert policy

Out of scope for phase 1:

- compound publish/runtime enablement
- family-level alert identity
- suppressed current alert rows
- full candidate catalog runtime explainability

## Threshold Family

Phase 1 threshold competition happens inside the following family key:

- rule type: `threshold`
- `state_type`
- `metric_key`
- `comparison`

This keeps runtime parity aligned with the current preview behavior and avoids
mixing opposite-direction threshold semantics in the same competition group.

## Competition Boundary

Precedence and suppression apply only inside the same `monitored_object_id`.

This means:

- a monitored-object-specific rule can suppress an object-type rule for that
  same monitored object
- the object-type rule must still remain eligible for other monitored objects
  of the same object type

## Winner Order

When multiple rules in the same family fire for the same monitored object, the
runtime winner is chosen in this order:

1. higher specificity
   - `monitored_object` beats `object_type`
2. higher severity
   - `critical` beats `warning`
3. newer rule revision
   - phase 1 uses `updated_at` as the practical recency signal until a
     dedicated `published_at` field exists
4. larger `rule_id`

Preview keeps the same ordering logic. Draft preview may still present the
current preview rule as the effective newest candidate when it participates in
the decision.

## Current Alert Policy

Phase 1 keeps exactly one current threshold alert per:

- `monitored_object_id`
- threshold family

If a winner exists:

- only the winner remains open/current
- firing loser rules are resolved with precedence-related resolution payload
- non-firing rules in the same family are resolved as threshold-cleared

If no winner exists:

- all open current alerts in that family are resolved as threshold-cleared

## Shared Evaluator

Preview and runtime should use a shared evaluator module for:

- metric value extraction
- scalar threshold normalization/evaluation
- candidate ranking
- winner selection
- suppressed/losing rule calculation

This shared module is the main phase 1 implementation target because it reduces
future drift between `admin_api.py` and `ingest_worker.py`.

## Runtime Resolution Semantics

Phase 1 runtime resolution reasons:

- `threshold_cleared`
  - the rule no longer fires
- `suppressed_by_precedence`
  - the rule still fires, but another rule wins the same family for the same
    monitored object

The alert archive/history schema may continue to use existing current/archive
storage. A richer family-level archive model remains backlog work.

## Deferred Backlog

- compound threshold publish/runtime enablement
- explicit `published_at` and stronger recency semantics
- family-level alert identity instead of rule-level current alert identity
- runtime candidate catalog / explainability
- separate suppressed current state instead of winner-only enforcement
