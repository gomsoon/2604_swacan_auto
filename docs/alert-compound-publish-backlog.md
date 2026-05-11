# Alert Compound Publish Backlog

Version: Draft 0.1
Updated: 2026-05-11

## Near-Term Sequence

1. runtime enablement for published compound rules
2. publish endpoint enablement for valid compound drafts
3. admin UI publish readiness/message updates
4. regression and coverage follow-up

## Backlog After Runtime Enablement

### Publish Endpoint

- remove the current compound publish hard block
- reuse preview validation as publish gate
- allow warnings-only publish
- add compound publish regression coverage

### UI Messaging

- replace `compound publish unavailable` copy with validation-driven readiness
- keep clear blocked reasons for invalid drafts
- keep scalar/compound status visibility consistent in list and detail views

### Runtime Explainability

- fuller candidate/winner/suppressed trace in preview and runtime
- better compound-specific alert message wording
- richer decision summaries for operator debugging

### Lifecycle / Archive

- evaluate whether compound condition snapshots need first-class archive fields
- decide whether precedence-based resolution reasons need stronger archive
  reporting

### Deferred Architecture

- family-level current alert identity
- suppressed current alert rows
- explicit `published_at` support for recency ordering
- full candidate rule catalog across preview and runtime
