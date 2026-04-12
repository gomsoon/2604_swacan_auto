# Software Architecture Runtime Monitoring System

## 최소 E2E 테스트 전략

버전: Draft 0.1
작성일: 2026-04-12
목적: 본 문서는 최소 E2E 구현 단계에서 적용할 자동화 테스트 전략을 정의한다. 최소 E2E 게이트는 `pytest + Playwright` 조합을 기준으로 설계한다.

## 1. 기본 원칙

- [필수] backend, worker, agent 의 로직 테스트는 `pytest` 를 기본으로 한다.
- [필수] 로그인, editor, monitoring 흐름의 브라우저 테스트는 `Playwright` 를 기본으로 한다.
- [필수] 최소 E2E 게이트는 `pytest` 와 `Playwright` 가 모두 통과되어야 한다.
- [필수] 테스트는 기능 추가 직후가 아니라 milestone 진행 중 지속적으로 추가되어야 한다.
- [필수] 구조 refactoring 이 발생하더라도 핵심 회귀 테스트 세트는 유지되어야 한다.

## 2. 도구 선택 기준

### 2.1 pytest

- 적용 대상: Flask API, worker 후처리, SQLite 접근, agent selector, outbox, transport, debug mode 저장 여부
- 장점: 빠른 실행, 독립 SQLite fixture, 세밀한 로직 검증, CI 적용 용이
- 역할: 최소 E2E 의 내부 계약과 안정성 검증

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

### 3.2 Playwright 범위

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

### 4.2 Playwright 최소 세트

- `login-smoke`
- `editor-save-smoke`
- `monitoring-view-smoke`
- `monitoring-polling-update`
- `event-panel-smoke`

## 5. 테스트 데이터와 환경

- [필수] 테스트용 seed 사용자와 최소 view seed 를 준비해야 한다.
- [필수] 테스트용 dummy target process 를 제공해 process alive/dead 시나리오를 반복 가능하게 해야 한다.
- [필수] pytest 는 독립 SQLite DB 를 사용해야 한다.
- [필수] Playwright 실행 시 backend 와 frontend 는 테스트용 설정으로 기동되어야 한다.

## 6. 실행 순서

1. `pytest` 단위/통합 테스트 실행
2. Flask 앱 및 필요한 프로세스 기동
3. `Playwright` 브라우저 테스트 실행
4. 실패 시 로그, debug payload, outbox 상태 확인

## 7. 게이트 기준

- [필수] `pytest` 최소 세트 전부 통과
- [필수] `Playwright` 최소 세트 전부 통과
- [필수] 수동 통합 테스트 1회 이상 성공
- [필수] 주요 실패 원인에 대해 debug 정보 수집 가능

## 8. 후속 확장

- grouped event 등장 이후 event panel 테스트 확장
- SSE 도입 이후 reconnect/fallback 테스트 추가
- admin UI 등장 이후 권한/로그 조회 테스트 추가
- agent 자동 업데이트 도입 이후 version check, download, restart, rollback 테스트 추가

## 9. 요약

- 최소 E2E 테스트 전략의 기본 조합은 `pytest + Playwright` 다.
- `pytest` 는 내부 계약과 내구성 검증, `Playwright` 는 사용자 흐름 검증을 담당한다.
- 최소 E2E 게이트는 두 계층 테스트가 함께 통과할 때만 완료로 본다.
