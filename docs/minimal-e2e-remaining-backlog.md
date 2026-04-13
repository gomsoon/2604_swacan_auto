# Software Architecture Runtime Monitoring System

## Minimal E2E 남은 구현 백로그

버전: Draft 0.1
작성일: 2026-04-13
목적: 현재까지 완료된 minimal end-to-end 구현 상태를 기준으로, 남은 구현 항목을 `frontend`, `backend`, `agent` 관점에서 우선순위 중심으로 정리한다.

## 1. 현재 상태 요약

- 현재 시스템은 `frontend -> backend -> DB -> monitoring` 흐름과 `agent payload -> backend ingest -> worker -> latest state/raw event` 흐름의 기본 골격이 구현되어 있다.
- editor, monitoring, admin 기본 화면과 backend API, ingest pipeline, SQLite schema, pytest/Playwright 기반 자동화 테스트가 준비되어 있다.
- agent 는 설정 로딩, runner, selector, host/process snapshot, SQLite outbox, batch transport, ack 반영, acked row cleanup 정책까지 최소 골격이 구현되어 있다.
- 현재 가장 큰 남은 공백은 `실제 Linux agent 실행 흐름 완성`, `worker 안정성 보강`, `실제 Linux 통합 테스트` 이다.

## 2. 우선순위 개요

1. `Agent 실제 실행 흐름 완성`
2. `Backend ingest/worker 안정성 보강`
3. `Linux 실제 통합 테스트 완료`
4. `Frontend 운영성 보강`

## 3. Agent 남은 구현

### A-01 agent main 실제 runtime 연결

- 우선순위: `최우선`
- 설명: 현재 `agent.main` 은 logging 중심 실행 골격이므로, 실제 `AgentStorage`, `AgentRuntimeServices`, `AgentTransport` 를 연결해 진짜 수집/전송 경로가 동작하도록 바꾼다.
- 완료 기준:
- `--once` 실행 시 heartbeat, host snapshot, process snapshot, flush 가 실제 outbox/transport 경로를 사용해야 한다.
- 설정 파일 기준으로 SQLite outbox 가 생성되고 재사용되어야 한다.
- 테스트 기준: main/runner 연동 테스트

### A-02 process 상태 전이 event 생성

- 우선순위: `최우선`
- 설명: snapshot 수집만으로는 운영 의미가 부족하므로, target 발견/미탐지/재시작을 비교해 `process_started`, `process_stopped`, `process_restarted`, `not_found` 계열 event 를 만든다.
- 완료 기준:
- 이전 cycle 대비 상태 전이 판단이 가능해야 한다.
- event 가 outbox 에 즉시 기록되어 backend 로 전달될 수 있어야 한다.
- 테스트 기준: agent unit test, backend contract test

### A-03 retry/backoff 실동작 보강

- 우선순위: `높음`
- 설명: flush 실패 시 다음 cycle 에서 backoff 를 반영하고, queue pressure 와 connection status 가 self-state 에 자연스럽게 반영되도록 보강한다.
- 완료 기준:
- 일시 실패와 반복 실패가 구분되어야 한다.
- backoff 정책이 transport 재시도에 반영되어야 한다.
- 테스트 기준: transport failure/backoff 테스트

### A-04 실행 운영 보조

- 우선순위: `중간`
- 설명: 샘플 설정 파일, 실행 방법, systemd 예시, 최소 운영 체크리스트를 제공한다.
- 완료 기준:
- Linux 환경에서 agent 실행 절차가 문서만으로 재현 가능해야 한다.
- 테스트 기준: 수동 운영 점검

## 4. Backend 남은 구현

### B-01 worker loop/service화

- 우선순위: `최우선`
- 설명: 현재 CLI 기반 worker 처리 함수를 실제 loop/service 실행 구조로 연결한다.
- 완료 기준:
- `pending -> processing -> processed/failed` 흐름이 지속적으로 동작해야 한다.
- polling sleep/backoff 가 포함되어야 한다.
- 테스트 기준: worker loop 통합 테스트

### B-02 duplicate/idempotency 보강

- 우선순위: `최우선`
- 설명: agent 재전송이 발생해도 `(agent_id, boot_id, seq)` 기준으로 중복 반영을 방지해야 한다.
- 완료 기준:
- 동일 batch 재전송 시 latest state/raw event 가 중복 반영되지 않아야 한다.
- 테스트 기준: duplicate ingest 테스트

### B-03 batch 처리 원자성/rollback 정책

- 우선순위: `높음`
- 설명: 현재 ack 의미는 receipt ack 로 정리됐으므로, worker 쪽에서는 batch 처리 중 실패 시 어느 범위까지 rollback 할지 정책을 더 명확히 해야 한다.
- 완료 기준:
- batch 단위 commit/rollback 정책이 문서와 코드에서 일치해야 한다.
- 운영자가 failed batch 와 partial effect 가능성을 구분할 수 있어야 한다.
- 테스트 기준: batch failure/rollback 테스트

### B-04 agent heartbeat timeout/stale 처리

- 우선순위: `높음`
- 설명: agent self-state 가 끊겼을 때 backend 가 `heartbeat lost`, stale 상태를 판단할 수 있어야 한다.
- 완료 기준:
- 일정 시간 동안 heartbeat 가 없으면 agent 상태가 warning/down 으로 바뀌어야 한다.
- 테스트 기준: timeout/stale 테스트

### B-05 retention/cleanup 보강

- 우선순위: `중간`
- 설명: ingest inbox, debug payload, raw event, latest state 정리 정책을 worker 또는 관리 작업으로 연결한다.
- 완료 기준:
- 1주 보존 정책과 debug payload 24시간 정책이 실제 cleanup 작업으로 동작해야 한다.
- 테스트 기준: retention cleanup 테스트

## 5. Frontend 남은 구현

### F-01 실제 agent 결과 기반 monitoring 최종 점검

- 우선순위: `높음`
- 설명: simulated payload 가 아니라 실제 Linux agent 가 보낸 결과가 monitoring 화면에 자연스럽게 보이는지 점검하고 필요시 보정한다.
- 완료 기준:
- process 상태 변화, event, MonitoringAgent 상태가 실제 agent 기준으로 보이는지 확인되어야 한다.
- 테스트 기준: Linux 통합 시나리오, Playwright 보조 확인

### F-02 MonitoringAgent/self-state 시각화 보강

- 우선순위: `중간`
- 설명: queue pressure, last_ack_seq, backend connection status 같은 agent 운영 정보가 더 쉽게 보이도록 개선한다.
- 완료 기준:
- monitoring 또는 admin 화면에서 agent 전송 상태를 빠르게 파악할 수 있어야 한다.
- 테스트 기준: UI smoke test

### F-03 관리자 화면 운영성 보강

- 우선순위: `중간`
- 설명: ingest 실패 batch, debug payload, latest state 추적을 더 쉽게 하는 read-only 보강을 진행한다.
- 완료 기준:
- 운영자가 문제 batch 와 최근 payload 흐름을 빠르게 따라갈 수 있어야 한다.
- 테스트 기준: admin UI/API 테스트

## 6. Linux 실제 통합 테스트 남은 항목

### L-01 dummy process 기반 실제 통합 시나리오

- 우선순위: `최우선`
- 설명: Linux 에서 dummy target process 를 띄우고, `발견 -> snapshot -> 전송 -> 종료 감지 -> event -> 재시작` 흐름을 실제로 검증한다.
- 완료 기준:
- 최소 1회 이상 end-to-end 성공 증적이 있어야 한다.
- 가능하면 동일 시나리오를 3회 반복해도 안정적으로 성공해야 한다.

### L-02 운영 증적 정리

- 우선순위: `높음`
- 설명: 테스트 로그, coverage report, 수동 실행 절차, 확인 결과를 문서로 남긴다.
- 완료 기준:
- minimal E2E 완료 선언 시 근거 자료로 사용할 수 있어야 한다.

## 7. 지금 바로 이어서 할 작업

1. `A-01 agent main 실제 runtime 연결`
2. `A-02 process 상태 전이 event 생성`
3. `B-01 worker loop/service화`
4. `L-01 Linux 실제 통합 시나리오`

## 8. 요약

- frontend 는 minimal E2E 관점에서 큰 뼈대가 거의 닫혔다.
- backend 는 안정성 보강 항목이 남아 있고, 특히 duplicate 처리와 worker 정책이 중요하다.
- agent 는 현재 가장 중요한 남은 축이며, 실제 실행 흐름 완성과 Linux 통합 검증이 minimal E2E 완료의 핵심이다.
