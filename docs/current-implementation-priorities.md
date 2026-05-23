# Current Implementation Priorities

## Current Alert Sequence

Current recommended alert-focused sequence:

1. Winner transition timeline UI / archive analytics follow-up
2. Preview/runtime explainability product follow-up
3. Monitoring alert operations follow-up

This sequence should be treated as the default follow-up order unless a new
operational blocker changes priorities.

Current scope decision for item 2:

- `stale` first reuses the threshold evaluator over derived runtime metrics.
- `event` becomes the first new post-threshold rule family.
- `no-data` also first reuses the threshold evaluator over derived runtime metrics, while never-seen/grace/reset policy remains deferred.

Current implementation note for item 2:

- `grouped_event_repeat` event rules are now available in draft/save/preview/publish/runtime.
- event MVP is intentionally narrow:
  - `state_type = process`
  - `signal_key = process_started | process_stopped | process_restarted`
  - scalar `gte` repeat-count thresholds only
- `stale` threshold-style reuse is now available for published `agent.heartbeat_age_seconds` rules, including periodic runtime re-evaluation without new agent payloads.
- `no-data` threshold-style reuse is now available for published `process/host.latest_state_age_seconds` rules, including periodic runtime re-evaluation without new payloads.
- the next priority after this MVP remains lifecycle/archive clarity and later explainability expansion.

Current scope note for item 3:

- start with a shared explanation contract across preview/current/archive
- keep the phase narrow and contract-oriented before larger UI work
- leave deep candidate traces, family-level identity, and structured reason
  codes on the deferred backlog

Current implementation note for item 3:

- preview/current/archive now share a common `explanation` object
- current alert and archive cards can read `winner_display_name` and `suppressed_rule_display_names`
- current explainability polish should now focus on:
  - stable reason vocabulary
  - shared labels across preview/current/archive/timeline
  - winner transition reason readability
- full candidate catalogs and `reason_code` remain deferred

Current scope note for the next review step:

- keep family-level identity as the incident foundation
- add opener snapshots, winner-transition summaries, and a dedicated transition
  table next
- treat winner changes as incident updates rather than close/open churn

Current implementation note for the next review step:

- threshold-style family-level identity is now implemented in runtime storage
- event-family identity is now implemented for `grouped_event_repeat`
- runtime/archive now persist durable `identity_kind + identity_key` fields
- winner changes now preserve the same current row and therefore preserve
  ACK/in-progress state
- opener snapshots and winner-transition analytics are now implemented through:
  - summary columns on current/archive rows
  - the append-only `alert_winner_transitions` table
  - admin detail APIs for current/archive winner transitions
- the next follow-up slice is timeline UI / archive analytics polish

## Agent Addendum

- See [agent-current-state-backlog.md](C:/2604_swacan_auto/docs/agent-current-state-backlog.md).
- Agent is currently a usable Linux baseline rather than the main architectural gap.
- The existing baseline already includes selector-driven discovery, snapshot collection, SQLite outbox transport, backend ingest integration, and Monitoring View verification.
- Agent should remain on a measured follow-up backlog while the main implementation focus returns to Alert condition flexibility and Alert lifecycle design.

버전: Draft 0.4  
작성일: 2026-04-18

목적: 현재 구현 상태를 기준으로, 다음 구현 축과 설계 검토 축을 다시 정리한다.

참고 문서:
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)
- [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)
- [monitoring-view-backlog.md](C:/2604_swacan_auto/docs/monitoring-view-backlog.md)
- [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)
- [alert-condition-flexibility-draft.md](C:/2604_swacan_auto/docs/alert-condition-flexibility-draft.md)
- [testing-coverage-sprint-plan.md](C:/2604_swacan_auto/docs/testing-coverage-sprint-plan.md)

## 1. 현재 상태 요약

- `Metamodel Editor`는 draft 편집, diff, validation, 권한/감사 로그, canvas 기반 직접 편집까지 1차 기준점에 도달했다.
- `Architecture Editor`는 metamodel snapshot 기반 palette, containment tree, runtime binding 검색/미리보기, containment drag-drop, relation direct edit까지 1차 기준점에 도달했다.
- `Monitoring View`는 selection summary, alert/event drill-down, SSE partial refresh, 최소 운영 액션, 객체 이력 요약까지 1차 운영 사용 수준에 도달했다.
- `Alert`는 운영 가능한 1차 기능을 확보했고, 이제부터는 기능을 급히 더 늘리기보다 조건 설계와 lifecycle 정리 방향을 다시 보는 단계로 넘어간다.

## 2. 현재 최우선 3개

### Priority 1. Backend Alert Condition Flexibility 설계

지금 다음으로 가장 중요한 축은 backend가 alert을 어떤 조건으로, 얼마나 유연하게 생성할 수 있어야 하는지 다시 정의하는 것이다.

중점 항목:
- 현재 threshold rule 모델의 한계 정리
- `selector / signal / condition / aggregation / lifecycle policy` 관점으로 분리 설계
- 단순 threshold, event rule, stale/no-data rule, windowed rule을 어떤 단계로 도입할지 정의
- runtime identity(`monitored_object`)와 alert fan-out 구조를 유지하면서 rule만 더 유연하게 만드는 방향 검토

### Priority 2. Alert Lifecycle / Archive 구조 정교화

중점 항목:
- `alert_instances(current)`와 `alert_history/archive` 역할 분리 재정의
- `resolution_source / resolution_reason` 모델 정교화
- manual resolve, auto recovery, policy timeout, cleanup 기반 종료의 의미 차이 명확화
- 향후 `alert_action_log` 필요성 검토

### Priority 3. Monitoring / Alert 운영 모델 정리

중점 항목:
- Monitoring View에서 어디까지 운영 액션을 수행할지 경계 정의
- Admin 화면과 Monitoring View의 역할 구분
- backlog로 남겨둘 Monitoring View 고도화 항목 정리

## 3. 2차 우선순위

### 3.1 Architecture Editor backlog

- 대형 view 편집 UX 강화
- outline tree 고도화
- runtime binding UX 후속 polish
- 제약 기반 직접 편집 2차 고도화

자세한 항목은 [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)를 따른다.

### 3.2 Monitoring View backlog

- 대형 view 탐색 UX
- alert/event 컨텍스트 고도화
- 운영 액션 2차 고도화
- 상태 시각화 2차 고도화
- 객체 이력 / 트렌드 확장

자세한 항목은 [monitoring-view-backlog.md](C:/2604_swacan_auto/docs/monitoring-view-backlog.md)를 따른다.

### 3.3 Metamodel / Architecture / Monitoring 후속 연동

- publish된 metamodel 변경이 editor / monitor에 주는 영향 점검
- compatibility fallback 정리
- 권한/감사 로그의 후속 polish

## 4. 지금 바로 무겁게 들어가지 않아도 되는 항목

- Monitoring View의 고급 시각 효과 확장
- Architecture Editor의 대형 view 편집 기능 전체 확장
- Alert correlation / root-cause grouping 고도화
- Agent productization 후속 작업

## 5. 권장 진행 방식

1. 기능 구현 전에 설계 문서로 먼저 방향을 고정한다.
2. alert 조건 설계는 schema를 바로 바꾸기보다 개념 모델부터 정리한다.
3. 다음 단계 구현은 설계 문서가 어느 정도 합의된 뒤 작은 slice로 나눈다.
4. 구현이 시작되면 기존 원칙대로 boundary value analysis 기준 테스트를 유지한다.

## 6. 현재 결론

지금은 `Monitoring View`를 급하게 더 넓히기보다, 남은 작업을 backlog로 관리하면서 `backend alert 조건을 얼마나 유연하게 만들 것인가`를 다시 설계하는 것이 가장 적절하다.
