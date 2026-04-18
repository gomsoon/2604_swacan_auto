# Monitoring View Backlog

버전: Draft 0.2  
작성일: 2026-04-18

목적: 현재까지 구현된 `Monitoring View`의 기준점을 정리하고, 남은 작업을 중요도와 영향도 기준으로 backlog로 관리한다.

## 1. 현재까지 구현된 기준점

- `active View Version` 기준 Monitoring View 렌더링
- `latest state`, `open alert`, `grouped event`, `raw event drill-down`
- `Selection Summary`
  - node / edge 선택 요약
  - runtime binding
  - latest state
  - open alert
  - grouped event
  - fan-out node
- `SSE + monitored_object 단위 partial refresh + polling fallback`
- 선택 객체 기준 `객체 이력 / 트렌드` 요약
  - 최근 해결 이력
  - 최근 raw event
- Monitoring View 안에서의 최소 운영 액션
  - ACK / ACK 해제
  - 처리중 전환
  - 수동 해결

## 2. 현재 판단

- `Monitoring View`는 1차 운영 사용이 가능한 수준까지 올라왔다.
- 지금부터는 Monitoring View를 계속 넓히기보다, 남은 기능을 backlog로 관리하면서 다음 큰 축으로 넘어가는 편이 더 건강하다.
- 남은 Monitoring View 작업은 “지금 없어서 못 쓰는 기능”보다 “대형 화면 운영성과 가시성을 더 높이는 고도화”에 가깝다.

## 3. 높은 우선순위 backlog

### 3.1 대형 Monitoring View 탐색 UX

- 검색
- severity / object type 필터
- 문제 있는 객체만 보기
- outline / canvas / selection summary 포커스 연동
- 대형 view에서의 빠른 탐색성 강화

이 항목은 view가 커질수록 운영 효율에 직접 영향을 준다.

### 3.2 Alert / Event 컨텍스트 고도화

- `alert -> grouped event -> raw event -> 관련 객체` 흐름을 더 매끄럽게 연결
- 여러 alert가 동시에 열린 상황에서 원인 파악 흐름 강화
- edge 선택 시 source / target 컨텍스트와 alert/event 연관성 더 명확히 표현

### 3.3 운영 액션 2차 고도화

- 운영 메모
- 상태 변경 이력 노출
- 관련 admin 화면 deep link
- 객체별 action log drill-down

현재의 ACK / 처리중 / 수동 해결은 최소 구현이고, 이후에는 운영자의 작업 맥락을 더 풍부하게 남기는 방향으로 확장할 수 있다.

## 4. 후속 backlog

### 4.1 상태 시각화 2차 고도화

- `suppressed`, `in_progress`, `acknowledged`, `stale` 시각 상태 강화
- node / edge overlay의 의미 구분 강화
- fan-out 객체가 많은 경우 상태 집계 표현 보강

### 4.2 객체 단위 히스토리 / 트렌드 확장

- 최근 상태 변화 시퀀스
- alert 변화 흐름
- 이벤트 추이 요약
- 필요 시 소형 sparkline / timeline 검토

### 4.3 실시간 갱신 고도화

- 현재는 `SSE + partial refresh + polling fallback`
- 이후 필요 시:
  - reconnect 전략 강화
  - 더 세밀한 delta payload
  - full reconcile 주기 최적화

## 5. 현재 결론

지금 시점에서 Monitoring View는 “계속 급하게 구현해야 하는 화면”이라기보다, 1차 기준점을 확보한 상태로 보는 것이 맞다.

따라서 다음 단계에서는:

1. Monitoring View 남은 기능은 backlog로 관리하고
2. backend alert 조건을 얼마나 유연하게 설계할지 다시 검토하고
3. 구현은 서두르지 않고 설계부터 차분히 정리하는 흐름

으로 가는 것이 적절하다.
