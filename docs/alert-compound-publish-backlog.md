# Alert Compound Publish Backlog

Version: Draft 0.1
Updated: 2026-05-11

## Near-Term Sequence

1. regression and coverage follow-up
2. richer preview/runtime explainability
3. lifecycle/archive follow-up
4. deferred identity architecture review

## Backlog After Initial Publish Enablement

### Publish Endpoint

- keep preview validation as the publish gate
- keep warnings-only publish behavior stable
- expand compound publish regression coverage as new rule types arrive

### UI Messaging

- keep validation-driven publish readiness consistent in list, detail, and preview views
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
