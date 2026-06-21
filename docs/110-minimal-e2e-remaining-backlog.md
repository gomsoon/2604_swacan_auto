# Software Architecture Runtime Monitoring System

## Minimal E2E 남은 구현 백로그
버전: Draft 0.3  
작성일: 2026-04-14

목적: 현재까지 완료된 minimal end-to-end 구현을 기준으로, 남은 구현 항목을 `agent`, `backend`, `frontend`, `운영 증적` 관점에서 우선순위 순으로 정리한다.

## 1. 현재 상태 요약

- `frontend -> backend -> DB -> monitoring` 흐름은 기본 동작이 닫혀 있다.
- `agent payload -> backend ingest -> worker -> latest state/raw event` 흐름도 기본 동작이 닫혀 있다.
- 실제 Linux 서버를 사용하는 SSH 기반 agent 통합 테스트와 monitoring UI 확인까지 완료했다.
- agent는 설정 로딩, runner, selector, host/process snapshot, 상태 전이 event, SQLite outbox, batch transport, ack 반영, acked row cleanup까지 구현된 상태다.
- backend는 batch receipt 중복 방지, worker item idempotency, batch rollback, stale 파생 상태, retention cleanup 1차까지 반영된 상태다.
- frontend는 MonitoringAgent self-state, 실제 agent 데이터 기반 monitoring, 기본 관리자 화면까지 연결된 상태다.

## 2. 최근 완료 항목

### Agent

- `A-01 agent main 실제 runtime 연결` 완료
- `A-02 process 상태 전이 event 생성` 완료
- `A-03 retry/backoff 실동작 보강` 완료
- `A-04 실행 운영 보조` 완료
  - Linux 실행 가이드 문서 추가
  - sample config 및 systemd 예시 추가
- `A-05 SSH 기반 Linux agent 테스트 실행 골격` 완료
- `A-06 대규모 process 환경 discovery 최적화 1차` 완료

### Backend

- `B-01 worker loop/service 1차` 완료
- `B-02 duplicate/idempotency 보강` 완료
- `B-03 batch transaction/rollback 1차` 완료
- `B-04 agent heartbeat timeout/stale 처리 1차` 완료
  - latest-state API에서 MonitoringAgent의 heartbeat age를 계산해 `warning/down` 상태를 파생한다.
  - monitoring UI에서 timeout 결과가 즉시 보이도록 연결했다.
- `B-05 retention/cleanup 1차` 완료
  - raw event 1주, debug payload 24시간, processed/failed ingest inbox 1주 보존 정책 반영
  - cleanup CLI와 관련 테스트 추가
- `B-04 후속 보강` 완료
  - stale agent를 관리자 화면 운영 요약으로 노출
  - 관리자 화면에서 stale agent를 빠르게 식별할 수 있도록 반영
- `B-05 후속 보강` 완료
  - worker loop에서 주기적 cleanup 실행을 지원
  - 관리자 화면에서 최근 cleanup 실행 결과를 확인할 수 있도록 반영

### Frontend

- `F-01 실제 agent 결과 기반 monitoring 최종 점검` 완료
- `F-02 MonitoringAgent/self-state 시각화 보강` 완료
- `F-03 관리자 화면 운영성 보강` 완료
  - latest state 패널 추가
  - stale agent 요약 표시 추가
  - retention 정책 요약 추가
  - ingest/debug/latest state를 운영자가 더 빠르게 추적할 수 있도록 정리

### Linux 실제 통합 테스트

- `L-01 dummy process 기반 실제 통합 시나리오` 완료
  - SSH 기반 smoke test 성공
  - 동일 시나리오 3회 반복 성공
  - monitoring UI에서 실제 Linux agent 결과 확인 완료
- `L-02 운영 증적 정리` 완료
  - Linux agent 검증 증적 문서 정리
  - 실행 가이드와 관련 테스트 문서 연결

## 3. 남은 우선순위

1. `운영 마감 점검 및 Minimal E2E 완료 선언`
2. `최종 증적 정리와 회귀 기준 고정`
3. `MVP 다음 단계 설계 착수`

## 4. 마감 점검 항목

- 실제 Linux agent 기준으로 최소 1회 더 수동 운영 점검을 수행한다.
- 최신 문서, runbook, sample config가 현재 구현 상태와 일치하는지 확인한다.
- 전체 회귀 테스트와 Playwright 테스트 결과를 다시 증적으로 남긴다.
- branch coverage 리포트를 현재 기준으로 다시 보관한다.

## 5. 요약

- minimal end-to-end 핵심 기능 구현은 사실상 닫힌 상태다.
- 현재 남은 핵심은 `최종 운영 점검`, `증적 정리`, `완료 선언 기준 확정`이다.
- 다음 단계에서는 구현 확장보다 마감 점검과 MVP 다음 단계 연결이 중심이 된다.
