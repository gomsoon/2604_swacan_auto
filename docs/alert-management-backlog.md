# Alert Management Backlog

## Current Sequencing Note

Current recommended order after compound publish enablement:

1. Alert lifecycle / archive hardening
2. Event / stale / no-data rule MVP scope
3. Preview/runtime explainability
4. Family-level alert identity review
5. Monitoring alert operations follow-up

This note is intentionally short so the next implementation discussion can
resume from the same order without re-deriving priorities.

Current MVP decision for item 2:

- `stale` should not open as a separate rule engine first.
- MVP `stale` should be expressed as a threshold-style rule over derived metrics such as `heartbeat_age_seconds`.
- `event` should be the first genuinely new rule type after threshold/compound threshold.
- `no-data` should stay on the deferred backlog until lifecycle and baseline timing rules are clearer.

Current implementation note for item 2:

- `grouped_event_repeat` event rule is now enabled as the first post-threshold rule family.
- event rules currently reuse `alert_rules.signal_type + signal_key` and store `metric_key = signal_key` as a compatibility shadow.
- event MVP is limited to process events with scalar `gte` repeat-count thresholds.
- `stale` and `no-data` are still deferred from separate rule-family implementation.

버전: Draft 0.3  
작성일: 2026-04-18

목적: 현재까지 구현된 alert 관리 기능을 기준으로, 남은 기능을 backlog 형태로 정리한다.

## 1. 현재까지 확보된 기준점

- `alert_instances` 기반 current alert 관리
- `open / in_progress / suppressed / resolved` 상태
- ACK / ACK 해제
- 수동 resolve
- `alert_history_archive` 기반 종료 이력 요약
- `grouped_events`와 alert fan-out 연계
- rule preview
- Monitoring View에서의 최소 운영 액션

즉 alert는 “운영자가 실제로 사용할 수 있는 1차 수준”까지는 올라온 상태로 본다.

## 2. 지금 남아 있는 큰 축

### 2.1 Backend alert 조건 유연화

현재 가장 중요한 축이다.

중점 항목:
- threshold rule의 한계 정리
- threshold MVP 범위와 validation 기준 고정
- `monitored_object > object_type` 우선순위 / suppression 정책 정리
- 단방향 scalar threshold 이후 `compound threshold(and/or + 양방향 범위)` 확장 검토
- compound threshold는 저장 모델보다 `preview shape + evaluator + validation` 정규화부터 우선 검토
- `rule_key / display_name` 분리와 naming 정책 정리
- `rule_key` format과 draft/published 이후 변경 정책 고정
- `rule_key` 직접 입력 + 자동 제안 + 운영 이후 clone 흐름 정책 정리
- `display_name` rename 허용 기준과 `rule_key` 전역 unique / 재사용 금지 정책 정리
- `rule_key` 자동 제안 slug 규칙과 충돌 suffix 정책 정리
- `rule_key` validation에서 `_` 허용 여부와 segment 규칙 고정
- `selector / signal / condition / aggregation / lifecycle policy` 모델 검토
- 단순 metric threshold 외에 event, stale, no-data rule을 어떻게 단계적으로 도입할지 정리
- rule preview / dry-run / validation 방향 정리

참고 문서:
- [alert-condition-flexibility-draft.md](C:/2604_swacan_auto/docs/alert-condition-flexibility-draft.md)

### 2.2 Alert lifecycle / archive 구조 정교화

중점 항목:
- `alert_instances(current)`와 `alert_history(archive)` 역할 분리 정리
- `resolution_source / resolution_reason` 정교화
- manual resolve / auto recovery / policy timeout / cleanup 기반 종료 구분
- 필요 시 `alert_action_log` 검토
- archive/history에서 `source_rule_display_name_snapshot` 유지 여부 검토
- product 단계에서 `alert occurrence ledger` 분리 검토
  - 현재는 `repeat_count` 기반 한 줄 집계가 실용적
  - 이후 occurrence 통계 / noise 분석 / burst 분석 요구가 생기면 재검토

### 2.3 운영 UX 고도화

중점 항목:
- Monitoring View 운영 액션 2차 고도화
- 운영 메모
- 상태 변경 이력 노출
- 관련 admin 화면 deep link

## 3. 후속 backlog

### 3.1 suppression / escalation 고도화

- suppression 기간
- auto escalation
- auto resolve 정책
- policy 조건과 lifecycle의 연결 정리

### 3.2 rule 영향도 / diff

- rule 변경 전후 영향도 비교
- threshold 변경 dry-run
- preview 고도화
- product 단계에서 `reason_code` 기반 발화 원인 통계/분석 검토

### 3.3 alert correlation

- parent/child alert
- correlated alert group
- root cause 후보 표현

### 3.4 fan-out 가시성

- 특정 alert가 현재 어떤 active view들에 fan-out 되는지 표시
- active view count / active node count 표시 강화

## 4. 현재 결론

지금은 alert 기능을 계속 빠르게 넓히기보다,

1. backend alert 조건을 어떻게 유연하게 설계할지 먼저 정리하고
2. lifecycle / archive 구조를 다시 점검한 뒤
3. 구현은 작은 slice로 나누어 천천히 들어가는 것이 적절하다.
