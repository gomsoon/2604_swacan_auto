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

### A-04 실행 운영 보조

- 우선순위: `높음`
- 설명: 샘플 설정 파일, 실행 방법, systemd 서비스 예시, 원격 테스트 서버 배치/정리 절차를 운영 가능한 형태로 정리한다.
- 완료 기준:
  - Linux 서버에서 agent를 수동 배치하고 실행하는 절차가 문서만으로 재현 가능해야 한다.
  - systemd 기반 실행 예시와 로그 확인 방법이 문서에 포함되어야 한다.
  - 테스트용 설정과 운영용 설정을 구분하는 예시가 있어야 한다.
- 테스트 기준: 수동 운영 점검

## 4. Backend 남은 구현

### 최근 완료된 항목

- `B-01 worker loop/service 1차` 완료
- `B-02 duplicate/idempotency 보강` 완료
- `B-03 batch transaction/rollback 1차` 완료
- `B-04 agent heartbeat timeout/stale 처리 1차` 완료
  - latest-state API가 agent heartbeat age를 계산해 `warning/down` 상태를 파생시킨다.
  - monitoring UI에서 MonitoringAgent self-state에 timeout 결과가 바로 반영된다.

### B-04 후속 보강

- 우선순위: `중간`
- 설명: 현재는 read-time stale 파생만 구현되어 있으므로, 후속으로 `agent_heartbeat_lost` event 생성과 admin 화면 반영을 보강한다.
- 완료 기준:
  - stale 감지 결과를 raw event 또는 운영 요약으로 남길 수 있어야 한다.
  - admin 화면에서도 stale agent를 빠르게 확인할 수 있어야 한다.
- 테스트 기준: timeout/stale 보강 테스트

### B-05 retention/cleanup 보강

- 우선순위: `높음`
- 설명: ingest inbox, raw events, debug payload, latest state 정리 정책을 worker 또는 관리 작업으로 연결한다.
- 완료 기준:
  - 최근 1주 보존 정책이 raw event/debug payload에 적용되어야 한다.
  - 오래된 ingest inbox와 debug payload를 정리하는 cleanup 경로가 있어야 한다.
  - cleanup 이후에도 최신 상태 조회는 깨지지 않아야 한다.
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

### L-02 운영 증적 정리

- 우선순위: `높음`
- 설명: SSH 통합 테스트 로그, coverage report, 수동 실행 절차, 확인 결과를 운영 증적 문서로 정리한다.
- 완료 기준:
  - minimal E2E 완료 선언의 근거 자료로 사용할 수 있어야 한다.
  - Linux agent 테스트 서버, 실행 조건, 확인 항목, 성공 결과가 문서에 정리되어야 한다.
  - pytest/Playwright/SSH 통합 테스트 결과를 함께 연결할 수 있어야 한다.

## 7. 지금 바로 이어서 할 작업

1. `A-04 실행 운영 보조`
2. `L-02 운영 증적 정리`
3. `B-05 retention/cleanup 보강`
4. `F-03 관리자 화면 운영성 보강`
5. `B-04 후속 보강`

## 8. 요약

- minimal E2E는 실제 Linux agent와 monitoring UI 확인까지 완료된 상태다.
- 현재 남은 핵심은 “운영 안정성”과 “운영 문서화” 쪽이다.
- 다음 단계는 agent 실행 운영 보조, 운영 증적 정리, heartbeat/stale, retention/cleanup을 먼저 닫는 것이 가장 자연스럽다.
