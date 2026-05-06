# Agent Current State And Backlog

Version: Draft 0.1  
Updated: 2026-05-06

References:
- [agent-detailed-requirements.md](C:/2604_swacan_auto/docs/agent-detailed-requirements.md)
- [agent-linux-runbook.md](C:/2604_swacan_auto/docs/agent-linux-runbook.md)
- [linux-agent-l01-evidence.md](C:/2604_swacan_auto/docs/linux-agent-l01-evidence.md)
- [testing-coverage-sprint-plan.md](C:/2604_swacan_auto/docs/testing-coverage-sprint-plan.md)

## Current Baseline

- The project already has a usable Linux-first Python agent baseline.
- The current implementation covers selector-driven process discovery, host and process snapshot collection, agent self-state reporting, SQLite outbox persistence, and HTTPS batch transport.
- The end-to-end path from `agent -> backend ingest -> worker -> latest_states -> Monitoring View` has been verified with real Linux SSH integration evidence.
- The recent coverage sprints also improved confidence around the agent configuration, selector, runner, and service branches.

## What Is Good Enough For Now

- Linux server monitoring is no longer in a mock-only stage.
- The agent can collect monitored host and process data without application code injection.
- Offline-safe transport through the SQLite outbox is already part of the design baseline.
- The current agent is good enough to support the MVP while the main product focus moves to alert modeling and lifecycle design.

## Remaining Gaps

- Productization and deployment polish:
  - systemd/service packaging
  - configuration ergonomics
  - operational runbook refinement
- Richer collection model:
  - deeper process/thread grouping
  - broader host metrics
  - more advanced selector behavior
- Long-running operational hardening:
  - failure-mode observation
  - prolonged recovery verification
  - backlog cleanup and retention policy polish

## Recommended Priority

- The agent should currently be treated as a stable MVP baseline with a follow-up backlog.
- The next primary implementation focus should not move back to Agent before the Alert condition and lifecycle work becomes clearer.
- Agent work should continue as small follow-up slices when required by alert, monitoring, or deployment needs.

## Suggested Agent Backlog

1. Deployment and service hardening
- systemd/service unit polish
- startup/restart behavior checks
- operator-facing install/update guidance

2. Operational resilience polish
- longer retry/recovery scenarios
- outbox growth and retention behavior
- more explicit failure diagnostics

3. Richer runtime model
- process grouping refinement
- additional host/process metrics
- future data model expansion only when backend consumers are ready

4. Productization follow-up
- packaging/distribution approach
- operator defaults and safer configuration UX
- environment-specific rollout guidelines

## Current Conclusion

- The agent is not the largest architectural gap in the project right now.
- It has already crossed the line from prototype support code to a usable baseline.
- The healthiest overall direction is to keep the agent on a measured follow-up backlog and return the main implementation focus to Alert.
