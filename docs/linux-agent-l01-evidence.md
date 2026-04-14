# Software Architecture Runtime Monitoring System

## Linux Agent L-01 통합 검증 증적

버전: Draft 0.1  
작성일: 2026-04-14

## 1. 목적

- 실제 Linux 서버에서 agent 를 기동하여 `발견 -> snapshot -> 전송 -> backend ingest -> worker 반영 -> latest state 확인` 흐름이 end-to-end 로 동작하는지 검증한다.

## 2. 테스트 환경

- 개발 환경: Windows
- backend 테스트 서버: Windows 로컬 Flask 테스트 서버
- agent 테스트 서버: `172.16.10.192`
- SSH 계정: `tprover`
- 원격 Python: helper 가 `python3.11+` 를 우선 탐지하여 사용
- 원격 작업 디렉토리: `/tmp/swacan_agent_tests/<run_id>`

## 3. 검증 시나리오

1. Windows 테스트 러너가 SSH 로 Linux 서버에 접속한다.
2. 원격 작업 디렉토리를 만들고 local `agent/` 소스를 업로드한다.
3. dummy target process 로 `sleep` 프로세스를 원격 서버에서 실행한다.
4. agent 를 `--cycles` 옵션으로 제한 실행한다.
5. agent 는 `agent_state`, `host_snapshot`, `process_snapshot` payload 를 batch 로 backend ingest API 에 전송한다.
6. Windows 쪽 backend worker 가 inbox 를 처리한다.
7. `latest_states` 테이블에서 agent, host, target process 상태를 확인한다.
8. 테스트 종료 후 agent 종료, dummy process 종료, 원격 임시 디렉토리 정리를 수행한다.

## 4. 확인 결과

- 2026-04-14 기준 SSH 기반 smoke test 1회 성공
- 동일 시나리오 3회 반복 재실행 성공
- 확인된 핵심 상태:
- `agent_ssh_smoke / agent / up`
- `agent_ssh_smoke:host / host / up`
- `ssh_smoke_target / process / up`

## 5. 확인 중 발견하여 반영한 사항

- 원격 서버의 기본 `python3` 가 `3.6.8` 이라서, SSH helper 는 `python3.11+` 를 우선 탐지하도록 보강했다.
- backend 테스트 서버는 `agent_ssh_smoke` agent id 를 허용하도록 테스트 설정을 보강했다.

## 6. 현재 의미

- minimal end-to-end 관점에서 실제 Linux 서버 기반 agent -> backend -> worker -> latest state 흐름은 동작이 확인되었다.
- 남은 주요 과제는 duplicate/idempotency 보강, worker 원자성 정책, 실제 agent 결과 기반 frontend 최종 점검이다.
