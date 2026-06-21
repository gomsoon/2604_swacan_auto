# Software Architecture Runtime Monitoring System

## Linux Agent L-01 통합 검증 증적

버전: Draft 0.2  
작성일: 2026-04-14

## 1. 목적

- 실제 Linux 서버에서 agent를 실행하여 `발견 -> snapshot -> 전송 -> backend ingest -> worker 반영 -> latest state 확인` 흐름이 동작하는지 검증한다.
- 이 문서는 minimal end-to-end 완료의 핵심 증적 자료로 사용한다.

## 2. 테스트 환경

- 개발 환경: Windows
- backend 테스트 서버: Windows 로컬 Flask 테스트 서버
- agent 테스트 서버: `172.16.10.192`
- SSH 계정: `tprover`
- 원격 Python: helper가 `python3.11+`를 우선 탐지
- 원격 작업 디렉터리: `/tmp/swacan_agent_tests/<run_id>`

## 3. 사용된 테스트 축

### 3.1 SSH smoke / integration

- [test_linux_agent_ssh_integration.py](C:/2604_swacan_auto/tests/test_linux_agent_ssh_integration.py)
- 목적:
  - Linux 서버에서 agent 실제 실행
  - dummy process 감시
  - backend ingest 반영
  - latest state 확인

### 3.2 실제 agent 결과 기반 monitoring UI

- [test_linux_agent_monitor_ui.py](C:/2604_swacan_auto/tests/test_linux_agent_monitor_ui.py)
- 목적:
  - 실제 Linux agent가 보낸 결과가 monitoring UI에 보이는지 확인
  - `PhysicalServer`, `MonitoringAgent`, `SoftwareProcess` 상태 표시 확인

## 4. 검증 시나리오

1. Windows 테스트 러너가 SSH로 Linux 서버에 접속한다.
2. 원격 작업 디렉터리를 만든다.
3. local `agent/` 소스를 원격으로 업로드한다.
4. dummy target process 로 `sleep`를 실행한다.
5. agent를 제한 cycle 모드로 실행한다.
6. agent가 `agent_state`, `host_snapshot`, `process_snapshot` payload를 backend로 batch 전송한다.
7. Windows 쪽 backend worker가 inbox를 처리한다.
8. `latest_states`에서 agent, host, process 상태를 확인한다.
9. monitoring UI에서 같은 결과가 시각적으로 보이는지 확인한다.
10. 테스트 종료 시 agent, dummy process, 원격 디렉터리를 정리한다.

## 5. 확인 결과

- SSH 기반 smoke test: 성공
- 동일 시나리오 3회 반복 확인: 성공
- 실제 Linux agent 결과 기반 monitoring UI browser integration: 성공

확인된 대표 상태:
- `agent_ssh_smoke / agent / up`
- `agent_ssh_smoke:host / host / up`
- `ssh_smoke_target / process / up`

## 6. 중간 이슈와 반영 내용

### 6.1 원격 기본 Python 버전 문제

- 원격 서버의 기본 `python3`는 `3.6.8`이었다.
- 해결:
  - SSH helper가 `python3.11+`를 우선 탐지하도록 보강했다.

### 6.2 테스트용 agent 인증 토큰 문제

- backend 테스트 서버가 `agent_ssh_smoke` token을 기본 허용하지 않아 초기 실패가 있었다.
- 해결:
  - 테스트 서버 설정에서 `agent_ssh_smoke`용 token을 명시적으로 허용하도록 보강했다.

## 7. 현재 의미

- minimal end-to-end 관점에서 “실제 Linux agent -> backend -> worker -> monitoring UI” 흐름이 검증되었다.
- 즉, 이 프로젝트는 더 이상 mock-only 단계가 아니라 실제 Linux 서버 기반 검증을 통과한 상태다.

## 8. 함께 보는 증적

- 로컬/브라우저 E2E:
  - [test_playwright_e2e.py](C:/2604_swacan_auto/tests/test_playwright_e2e.py)
- SSH helper:
  - [linux_agent_ssh_support.py](C:/2604_swacan_auto/tests/linux_agent_ssh_support.py)
- 실행 가이드:
  - [130-agent-linux-runbook.md](C:/2604_swacan_auto/docs/130-agent-linux-runbook.md)

## 9. 현재 결론

- L-01은 완료된 것으로 본다.
- 이후 남은 증적 작업은 test report, coverage report, 운영 절차를 더 보기 좋게 정리하는 `L-02 운영 증적 정리` 수준이다.
