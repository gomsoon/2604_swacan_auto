# Software Architecture Runtime Monitoring System

## 최소 E2E 테스트 전략

버전: Draft 0.1
작성일: 2026-04-12
목적: 본 문서는 최소 E2E 구현 단계에서 적용할 자동화 테스트 전략을 정의한다. 최소 E2E 게이트는 `pytest + Playwright` 조합을 기준으로 설계한다.

## 1. 기본 원칙

- [필수] backend, worker, agent 의 로직 테스트는 `pytest` 를 기본으로 한다.
- [필수] backend 와 agent 에 대해서는 line coverage 뿐 아니라 branch coverage 측정을 포함해야 한다.
- [필수] 로그인, editor, monitoring 흐름의 브라우저 테스트는 `Playwright` 를 기본으로 한다.
- [필수] 최소 E2E 게이트는 `pytest` 와 `Playwright` 가 모두 통과되어야 한다.
- [필수] agent 테스트는 `단위 테스트`, `backend 계약 테스트`, `Linux 실제 통합 테스트`의 세 층으로 분리해 관리해야 한다.
- [필수] 테스트는 기능 추가 직후가 아니라 milestone 진행 중 지속적으로 추가되어야 한다.
- [필수] 구조 refactoring 이 발생하더라도 핵심 회귀 테스트 세트는 유지되어야 한다.
- [필수] coverage report 는 실행 시마다 남겨 증적 자료로 활용할 수 있어야 한다.
- [필수] coverage 는 제품 코드 기준으로 `app` 패키지에 대해 분리 측정하고, `tests` 와 Playwright 시나리오 코드는 coverage 계산에서 분리한다.
- [필수] Windows 개발 환경에서 실행하는 기본 테스트와, SSH 를 통해 Linux agent test server 에서 실행하는 실제 통합 테스트는 별도 실행 세트로 분리해야 한다.
- [필수] SSH 기반 Linux 테스트는 기본 `pytest` 세트에 섞지 않고 별도 marker 또는 별도 실행 단계로 운영해야 한다.

## 2. 도구 선택 기준

### 2.1 pytest

- 적용 대상: Flask API, worker 후처리, SQLite 접근, agent selector, outbox, transport, debug mode 저장 여부
- 장점: 빠른 실행, 독립 SQLite fixture, 세밀한 로직 검증, CI 적용 용이
- coverage 정책: backend 와 agent 의 branch coverage 를 `app` 기준으로 측정하고 report 를 남긴다. 테스트 코드와 Playwright 시나리오는 coverage 수치와 분리한다.

### 2.2 Playwright

- 적용 대상: 로그인, view 목록, editor 저장, monitoring 화면, event panel 표시
- 장점: 실제 브라우저 기반 사용자 흐름 검증, UI 회귀 탐지, polling 기반 상태 반영 확인
- 역할: 최소 E2E 의 외부 사용자 흐름 검증

## 3. 테스트 범위 분담

### 3.1 pytest 범위

- 로그인 API 성공/실패
- view 생성/저장/재조회 API
- ingest API 정상 수신과 ack 응답
- inbox -> worker -> latest state 갱신
- raw event 생성
- debug mode payload 저장 on/off
- agent selector 와 snapshot 생성
- agent SQLite outbox 저장/복구/재전송
- backend worker 분기 경로와 agent transport/outbox 분기 경로에 대한 branch coverage 측정

### 3.2 agent 단위 테스트 범위

- 설정 로딩과 기본 runner 초기화
- selector 매칭과 target_id 결정
- process snapshot 생성과 직렬화
- sequence 증가와 millisecond 시간 정밀도
- SQLite outbox enqueue, ack 정리, 재기동 복구
- self-state 생성

### 3.3 agent-backend 계약 테스트 범위

- agent batch payload 를 backend ingest API 가 정상 수용하는지 확인
- `ack_seq`, `accepted_count`, `server_time` 계약 확인
- ingest 후 worker 처리로 latest state 와 raw event 가 정상 반영되는지 확인
- payload schema drift 와 필수 필드 누락 시 실패를 빠르게 감지

### 3.4 Linux 실제 통합 테스트 범위

- dummy target process 를 실제 Linux 에서 실행
- selector 로 target 발견
- snapshot 전송 후 backend 반영 확인
- target 종료/재시작 감지
- backend 비가용 후 outbox 복구 전송

### 3.5 SSH 기반 Linux agent 테스트 운영 방식

- 테스트 시작 시 Windows 테스트 러너가 SSH 로 Linux agent test server 에 접속한다.
- 원격 작업 디렉토리와 테스트용 config, storage path, 로그 경로를 준비한다.
- 원격 서버에서 agent 를 백그라운드로 실행하거나 동등한 방식으로 기동한다.
- Windows 쪽 테스트는 backend/API/monitoring 상태를 검증하고, 필요 시 원격 dummy process 를 제어한다.
- 테스트 종료 시 agent 프로세스를 종료하고, 원격 로그, outbox SQLite, stdout/stderr 를 수집한 뒤 SSH 세션을 종료한다.
- 동일 서버를 반복 사용하더라도 테스트별로 고유 작업 디렉토리 또는 고유 config 를 사용해 상태 오염을 줄여야 한다.
- SSH 기반 테스트는 네트워크 문제와 코드 문제를 구분할 수 있도록 별도 로그와 종료 코드를 남겨야 한다.

### 3.6 Playwright 범위

- 로그인 성공 후 view 목록 진입
- 최소 editor 화면에서 node 배치 및 저장
- monitoring 화면 진입
- polling 후 상태 반영 확인
- event panel 에 최근 event 표시 확인
- MonitoringAgent 상태 표시 확인

## 4. 최소 자동화 테스트 세트

### 4.1 pytest 최소 세트

- `test_auth_login_success`
- `test_auth_login_failure`
- `test_view_create_and_save`
- `test_ingest_accepts_payload_and_returns_ack`
- `test_worker_updates_latest_state`
- `test_worker_creates_raw_event`
- `test_debug_mode_stores_payload`
- `test_debug_mode_off_does_not_store_payload`
- `test_agent_outbox_retries_after_backend_recovery`

### 4.2 agent 계약 테스트 최소 세트

- `test_agent_payload_contract_accepts_valid_batch`
- `test_agent_payload_contract_rejects_invalid_batch`
- `test_agent_transport_ack_updates_outbox`
- `test_agent_transport_batch_updates_latest_state_and_raw_event`

### 4.3 Playwright 최소 세트

- `login-smoke`
- `editor-save-smoke`
- `monitoring-view-smoke`
- `monitoring-polling-update`
- `event-panel-smoke`

### 4.4 Linux 실제 통합 최소 세트

- `linux-agent-selector-smoke`
- `linux-agent-process-stop-detect`
- `linux-agent-outbox-recovery-smoke`
- `linux-agent-ssh-launch-and-stop`

## 5. 테스트 데이터와 환경

- [필수] 테스트용 seed 사용자와 최소 view seed 를 준비해야 한다.
- [필수] 테스트용 dummy target process 를 제공해 process alive/dead 시나리오를 반복 가능하게 해야 한다.
- [필수] pytest 는 독립 SQLite DB 를 사용해야 한다.
- [필수] Playwright 실행 시 backend 와 frontend 는 테스트용 설정으로 기동되어야 한다.
- [필수] coverage 결과는 파일 또는 HTML/XML report 형태로 저장되어 나중에 증적 자료로 확인 가능해야 한다.
- [필수] Linux 실제 통합 테스트용 SSH 접속 정보, 원격 작업 디렉토리 정책, agent 로그 저장 위치는 테스트 환경 문서에 명시되어야 한다.
- [필수] SSH 기반 테스트는 테스트 종료 후 원격 agent 종료와 임시 파일 정리를 보장해야 한다.
- [필수] SSH 기반 테스트를 자동화할 때는 최소한 `LINUX_AGENT_SSH_HOST`, `LINUX_AGENT_SSH_USER`, `LINUX_AGENT_SSH_PASSWORD` 와 동등한 환경 설정값이 준비되어야 한다.
- [필수] 원격 호스트에서 기본 `python3` 가 구버전을 가리킬 수 있으므로, SSH 테스트 helper 는 가능하면 `python3.11+` 를 우선 탐지해 사용하거나 `LINUX_AGENT_REMOTE_PYTHON` 으로 명시적으로 지정할 수 있어야 한다.

## 6. 실행 순서

1. agent/backend `pytest` 단위 테스트 실행
2. agent-backend 계약 테스트 실행
3. Flask 앱 및 필요한 프로세스 기동
4. `Playwright` 브라우저 테스트 실행
5. SSH 기반 Linux 실제 통합 테스트 실행 또는 동등한 체크리스트 수행
6. 실패 시 로그, debug payload, outbox 상태 확인

## 7. 게이트 기준

- [필수] `pytest` 최소 세트 전부 통과
- [필수] agent-backend 계약 테스트 최소 세트가 통과해야 한다.
- [필수] `Playwright` 최소 세트 전부 통과
- [필수] Linux 실제 통합 테스트 또는 동등한 수동 통합 테스트가 1회 이상 성공해야 한다.
- [필수] backend 와 agent 의 branch coverage report 가 `app` 기준으로 생성되어야 한다.
- [필수] 초기 단계에서는 coverage 수치 자체를 강한 합격 기준으로 두기보다, 측정과 추적 자체를 필수 게이트로 본다.
- [필수] Linux 실제 통합 테스트를 자동화하는 경우, SSH 접속부터 agent 종료까지의 전 과정이 실패 시에도 cleanup 되도록 보장해야 한다.

## 8. 후속 확장

- grouped event 등장 이후 event panel 테스트 확장
- SSE 도입 이후 reconnect/fallback 테스트 추가
- admin UI 등장 이후 권한/로그 조회 테스트 추가
- agent 자동 업데이트 도입 이후 version check, download, restart, rollback 테스트 추가

## 9. 요약

- 최소 E2E 테스트 전략의 기본 조합은 `pytest + Playwright` 다.
- `pytest` 는 내부 로직 검증, agent-backend 계약 검증, 내구성 검증을 담당하고 `Playwright` 는 사용자 흐름 검증을 담당한다.
- agent 는 `단위 -> 계약 -> Linux 실제 통합`의 세 층 테스트를 가지며, 서로 다른 실패 원인을 분리할 수 있어야 한다.
- backend 와 agent 는 초기부터 branch coverage 측정과 report 축적을 시작하고, 이후 단계에서 coverage 게이트를 점진적으로 강화한다.
- Playwright 는 coverage 수치 계산 대상이 아니라 최소 E2E 사용자 흐름의 pass/fail 과 실행 증적을 담당한다.
- 최소 E2E 게이트는 두 계층 테스트가 함께 통과할 때만 완료로 본다.
- Linux 실제 통합 테스트는 SSH 기반 별도 stage 로 운영하는 것이 가장 안정적이며, 기본 로컬 테스트와 분리해야 한다.
