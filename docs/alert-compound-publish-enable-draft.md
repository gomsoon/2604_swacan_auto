# Alert Compound Publish Enablement Draft

Version: Draft 0.1
Updated: 2026-05-11

## Goal

Enable `compound threshold` rules to move from draft-only storage into the
published/runtime path without breaking parity between:

- preview winner/suppressed hints
- runtime worker alert creation/resolution

## Preconditions

Compound publish should not be opened until all of the following are true:

1. preview and runtime use the same threshold evaluator
2. published compound rules can be evaluated by the worker
3. precedence and suppression still enforce a single current alert winner per
   monitored object and threshold family
4. invalid compound rules are blocked by validation before publish

## Publish Allow Conditions

A draft compound rule may be published only when:

- rule status is `draft`
- rule payload passes base alert rule validation
- `rule_key` remains unique
- compound shape validation passes
- compound condition satisfiability passes
- `critical_condition` is a subset of `warning_condition`
- preview validation has no `errors`

Warnings do not block publish.

Examples of publish warnings that remain allowed:

- single-severity rule
- redundant clause
- `(Copy)` suffix still present in `display_name`

## Phase Order

The implementation order stays narrow:

1. runtime enablement
   - worker can evaluate published compound rules
   - current alert parity is preserved
2. publish endpoint enablement
   - remove the hard block for valid compound drafts
3. admin UI enablement
   - publish readiness and success/error wording updated

## Runtime Enablement Scope

Runtime enablement must support:

- scalar and compound published rules in the same threshold family
- same precedence ordering already used by preview
- winner-only current alert policy
- compound runtime message generation
- compound condition snapshot in alert metadata

The threshold family remains:

- rule type = `threshold`
- `state_type`
- `metric_key`
- `comparison`

## Metadata Expectations

When a compound winner fires at runtime, metadata should preserve at least:

- `cond_mode`
- `warning_condition`
- `critical_condition`
- `winning_condition_trace`
- `family_key`

This avoids extra schema work in phase 1 while still leaving enough evidence
for alert review, archive inspection, and later explainability work.

## UI Expectations

After runtime enablement is complete and publish is opened:

- valid compound drafts should become publishable
- invalid compound drafts should still be blocked
- publish blocked messaging should reflect validation errors, not feature flags
- the editor and preview should stop saying compound publish is unavailable

## Explicit Non-Goals

This phase does not include:

- family-level current alert identity
- suppressed current alert rows
- full candidate catalog runtime explainability
- extra archive columns dedicated to compound clauses
