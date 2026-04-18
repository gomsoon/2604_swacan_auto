# Monitoring View Backlog

버전: Draft 0.1  
작성일: 2026-04-18

목적: `Monitoring View`에서 남아 있는 주요 구현을 영향도와 중요도 기준으로 정리한다.

## 1. 현재까지 구현된 핵심

- `active View Version` 기준 렌더링
- `latest state / alert / grouped event / raw event drill-down`
- `Selection Summary`
  - node / edge 선택 요약
  - runtime binding
  - latest state
  - open alert
  - grouped event
  - fan-out
- monitored object 기반 fan-out 표시
- polling 기반 near-real-time 갱신

## 2. 최우선 backlog

### 2.1 Alert / Event 컨텍스트 통합 강화

- 선택한 node / edge에서 `open alert -> grouped event -> raw event` 흐름을 더 짧게 연결
- alert와 event 사이의 원인/결과 관계를 더 명확하게 표현
- 선택 패널과 우측 이벤트 패널 사이의 이동 비용 축소

### 2.2 Canvas 상태 시각화 고도화

- `warning / down / stale / open alert` overlay를 더 직접적으로 표시
- node 뿐 아니라 edge에도 상태 영향을 더 명확하게 투영
- 동일 monitored object가 여러 곳에 fan-out될 때 일관된 상태 표시 유지

### 2.3 대형 Monitoring View 탐색 UX

- 검색
- severity / object type 필터
- 문제 있는 node만 보기
- outline / canvas / selection summary 연동 강화

## 3. 실시간 갱신 backlog

### 3.1 목표 방향

- 현재 구조는 polling 기반 near-real-time이다.
- 다음 실시간 갱신 기본선은 `SSE + monitored_object 단위 partial refresh + 느린 full reconcile`이다.

### 3.2 구현 원칙

- backend가 alert / latest state / grouped event 변경을 감지하면 `monitored_object_id` 중심의 작은 이벤트를 발행한다.
- frontend는 `refreshAll()` 대신 해당 monitored object를 참조하는 node / edge / selection summary만 우선 갱신한다.
- polling은 완전히 제거하지 않고, drift 방지를 위한 느린 full reconcile fallback으로 유지한다.

### 3.3 현재 반영된 기반

- `GET /api/views/{view_id}/runtime-objects/{monitored_object_id}/slice`
- `Monitoring View`에서 선택한 node / edge에 대해 monitored object slice를 부분 갱신하는 helper

## 4. 후속 backlog

- 운영 액션 최소 연결
  - ACK 상태 확인
  - 관련 alert 열기
  - 운영자 처리 흐름 이동
- 실시간 SSE 채널 구현
- partial refresh 이후 full reconcile 주기 최적화
- grouped event / alert correlation 추가 고도화

## 5. 현재 결론

지금은 `Selection Summary`와 monitored object 기반 구조가 자리 잡았으므로, 다음 `Monitoring View` 구현은

1. `alert / event 컨텍스트 통합`
2. `canvas 상태 시각화 고도화`
3. `대형 view 탐색 UX`

순서로 가는 것이 가장 적절하다.
