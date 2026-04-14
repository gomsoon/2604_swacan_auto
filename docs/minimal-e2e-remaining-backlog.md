# Software Architecture Runtime Monitoring System

## Minimal E2E 남은 구현 백로그

버전: Draft 0.2  
작성일: 2026-04-14

목적: 현재까지 완료된 minimal end-to-end 구현을 기준으로, 남은 구현 항목을 `agent`, `backend`, `frontend`, `운영 증적` 관점에서 우선순위 중심으로 정리한다.

## 1. 현재 상태 요약

- `frontend -> backend -> DB -> monitoring` 흐름은 기본 동작이 닫혀 있다.
- `agent payload -> backend ingest -> worker -> latest state/raw event` 흐름도 기본 동작이 닫혀 있다.
- 실제 Linux 서버를 사용하는 SSH 기반 agent 통합 테스트와 monitoring UI 확인까지 완료했다.
- agent는 설정 로딩, runner, selector, host/process snapshot, process 상태 전이 event, SQLite outbox, batch transport, ack 반영, acked row cleanup까지 구현되어 있다.
- backend는 receipt-level duplicate 방지, worker-level item idempotency, batch rollback까지 1차 보강이 끝난 상태다.
- monitoring UI는 MonitoringAgent self-state를 별도 요약 카드와 canvas 배지로 표시할 수 있는 상태다.

## 2. 우선순위 개요

1. `A-04 실행 운영 보조`
2. `L-02 운영 증적 정리`
3. `B-04 agent heartbeat timeout/stale 처리`
4. `B-05 retention/cleanup 보강`
5. `F-03 관리자 화면 운영성 보강`

## 3. Agent 남은 구현

### 최근 완료된 항목

- `A-01 agent main 실제 runtime 연결` 완료
- `A-02 process 상태 전이 event 생성` 완료
- `A-03 retry/backoff 실동작 보강` 완료
- `A-05 SSH 기반 Linux agent 테스트 실행 골격` 완료
- `A-06 대규모 process 환경 discovery 최적화 1차` 완료
- `A-04 실행 운영 보조` 완료
  - Linux 실행 가이드 문서 추가
  - sample config 및 systemd 예시 추가

## 4. Backend 남은 구현

### 최근 완료된 항목

- `B-01 worker loop/service 1차` 완료
- `B-02 duplicate/idempotency 보강` 완료
- `B-03 batch transaction/rollback 1차` 완료
- `B-04 agent heartbeat timeout/stale 처리 1차` 완료
  - latest-state API가 agent heartbeat age를 계산해 `warning/down` 상태를 파생시킨다.
  - monitoring UI에서 MonitoringAgent self-state에 timeout 결과가 바로 반영된다.
- `B-05 retention/cleanup 1차` 완료
  - raw event 1주, debug payload 24시간, processed/failed ingest inbox 1주 정리 함수와 CLI를 추가했다.
  - processed inbox 삭제 시 item receipt도 함께 정리된다.

### B-04 후속 보강

- 우선순위: `중간`
- 설명: 현재는 read-time stale 파생만 구현되어 있으므로, 후속으로 `agent_heartbeat_lost` event 생성과 admin 화면 반영을 보강한다.
- 완료 기준:
  - stale 감지 결과를 raw event 또는 운영 요약으로 남길 수 있어야 한다.
  - admin 화면에서도 stale agent를 빠르게 확인할 수 있어야 한다.
- 테스트 기준: timeout/stale 보강 테스트

### B-05 후속 보강

- 우선순위: `중간`
- 설명: 현재는 CLI 기반 cleanup 1차만 있으므로, 후속으로 worker 주기 작업 또는 관리 화면에서의 운영 연결을 보강한다.
- 완료 기준:
  - cleanup이 worker 주기 작업 또는 관리 작업 흐름에 자연스럽게 연결되어야 한다.
  - 필요 시 cleanup 실행 결과를 관리자 화면에서 확인할 수 있어야 한다.
- 테스트 기준: retention cleanup 테스트

## 5. Frontend 남은 구현

### 최근 완료된 항목

- `F-01 실제 agent 결과 기반 monitoring 최종 점검` 완료
- `F-02 MonitoringAgent/self-state 시각화 보강` 완료
  - monitoring 화면에서 MonitoringAgent 상태를 별도 요약 카드로 표시
  - MonitoringAgent 노드에 canvas 상태 배지 표시
  - selection summary에서 queue depth, last ack seq, backend connection status 확인 가능

### F-03 관리자 화면 운영성 보강

- 우선순위: `중간`
- 설명: ingest 실패 batch, debug payload, latest state 추적을 관리자 입장에서 더 빠르게 볼 수 있도록 read-only 화면을 보강한다.
- 완료 기준:
  - 문제 batch와 최근 payload 흐름을 더 쉽게 따라갈 수 있어야 한다.
  - 필요 시 latest state 또는 agent 상태 요약이 admin 화면에 추가되어야 한다.
  - 운영자가 최소 클릭으로 실패 원인을 좁혀갈 수 있어야 한다.
- 테스트 기준: admin UI/API 테스트

## 6. Linux 실제 통합 테스트 남은 항목

### 최근 완료된 항목

- `L-01 dummy process 기반 실제 통합 시나리오` 완료
  - SSH 기반 smoke test 성공
  - 동일 시나리오 3회 반복 성공
  - monitoring UI에서 실제 Linux agent 결과 확인 완료
- `L-02 운영 증적 정리` 완료
  - Linux agent 검증 증적 문서 정리
  - 실행 가이드와 관련 테스트 문서 연결

## 7. 지금 바로 이어서 할 작업

1. `F-03 관리자 화면 운영성 보강`
2. `B-04 후속 보강`
3. `B-05 후속 보강`

## 8. 요약

- minimal E2E는 실제 Linux agent와 monitoring UI 확인까지 완료된 상태다.
- 현재 남은 핵심은 “운영 가시성”과 “stale/cleanup 후속 연결” 쪽이다.
- 다음 단계는 관리자 화면 운영성 보강과 stale/cleanup 후속 연결을 닫는 것이 가장 자연스럽다.
