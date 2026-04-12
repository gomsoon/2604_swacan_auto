# Software Architecture Runtime Monitoring System

## 최소 E2E 구현 백로그

버전: Draft 0.1
작성일: 2026-04-10
목적: 본 문서는 `최소 E2E 버전 정의` 문서를 기준으로, 실제 구현을 위한 작업 단위를 우선순위와 완료 기준, 테스트 게이트와 함께 분해한다.

## 1. 문서의 목적

- 본 백로그는 최소 E2E 버전을 실제로 구현하기 위한 실행 계획 문서다.
- 각 작업은 기능 구현뿐 아니라 구조적 경계, 자동 테스트, 수동 통합 테스트를 함께 고려해야 한다.
- 본 문서는 "무엇을 먼저 만들 것인가" 뿐 아니라 "어디서 refactoring 을 먼저 해야 하는가"를 판단하는 기준으로 사용한다.

## 2. 백로그 운영 원칙

- [필수] 각 작업은 가능한 한 1~2일 안에 끝낼 수 있는 크기로 유지한다.
- [필수] 새 기능을 열기 전에 관련 회귀 테스트를 먼저 추가하거나 동시에 추가한다.
- [필수] 구조적 문제가 발견되면 새 기능을 이어붙이지 않고 refactoring 작업을 별도 backlog 항목으로 분리한다.
- [필수] 최소 E2E 수용 기준과 직접 연결되지 않는 작업은 후순위로 미룬다.
- [필수] 각 milestone 종료 시점에는 자동 테스트와 수동 통합 테스트 게이트를 함께 점검한다.
- [필수] 상세 요구사항 문서의 정리 순서와 별개로, 실제 구현 순서의 기준 문서는 본 backlog 로 본다.
- [필수] 최소 E2E 자동화 테스트 기본 조합은 `pytest + Playwright` 로 고정한다.
- [필수] backend 와 agent 테스트에는 branch coverage 측정 및 report 생성 작업이 포함되어야 한다.

## 3. 구현 순서 개요

- `Milestone 0`: 개발 골격과 seed 준비
- `Milestone 1`: 로그인과 최소 editor 저장 흐름
- `Milestone 2`: agent ingest 와 latest state 반영
- `Milestone 3`: monitoring 화면과 event 반영
- `Milestone 4`: debug mode 와 outbox 복구 게이트
- `Milestone Gate`: 최소 E2E 수용 기준 전체 검증

## 3.1 Agent 구현 권장 순서

- agent 구현은 `설정/runner -> selector -> snapshot collector -> SQLite outbox -> transport -> backend 계약 테스트 -> Linux 실제 통합 테스트` 순서를 기본으로 한다.
- backend ingest API 가 준비되어 있더라도, agent 는 별도 축으로 단계적 구현을 진행하고 각 단계마다 독립 `pytest` 테스트를 먼저 붙인다.
- backend 와의 연동 검증은 transport 구현 이후 별도 계약 테스트 세트로 유지한다.
- Linux 실제 통합 테스트는 마지막 게이트로 두되, dummy target process 와 실행 절차 준비는 너무 늦지 않게 시작한다.

## 4. Milestone 0 - 개발 골격과 seed 준비

### B-001 프로젝트 골격 생성

- 우선순위: `필수`
- 설명: Flask app factory, blueprint 구조, SQLite 초기화, pytest 기본 실행 구조를 만든다.
- 완료 기준:
- `app` 이 최소 실행 가능해야 한다.
- `pytest` 가 빈 상태 또는 최소 smoke test 상태로 실행 가능해야 한다.
- 선행 조건: 없음
- 연결 테스트: 앱 기동 smoke test

### B-002 최소 DB 스키마 초안 적용

- 우선순위: `필수`
- 설명: 최소 E2E에 필요한 users, views, view_nodes, view_edges, ingest inbox, latest state, raw event, debug payload 테이블을 준비한다.
- 완료 기준:
- SQLite DB 초기화 스크립트가 있어야 한다.
- 테스트 환경에서 독립 DB 생성이 가능해야 한다.
- 선행 조건: B-001
- 연결 테스트: DB 초기화 테스트

### B-003 최소 메타모델/notation seed 추가

- 우선순위: `필수`
- 설명: `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink` 에 대한 최소 seed 데이터를 넣는다.
- 완료 기준:
- seed 실행 후 editor palette 구성에 필요한 데이터가 조회 가능해야 한다.
- containment 규칙이 seed 에 포함되어야 한다.
- 선행 조건: B-002
- 연결 테스트: seed 조회 테스트

### B-004 공통 테스트 fixture 정리

- 우선순위: `필수`
- 설명: pytest 에서 독립 SQLite DB, seed 데이터, Flask test client 를 쉽게 쓸 수 있는 fixture 를 만든다.
- 완료 기준:
- backend API 테스트가 fixture 만으로 실행 가능해야 한다.
- 선행 조건: B-001, B-002, B-003
- 연결 테스트: pytest fixture smoke test

### B-004A pytest coverage 설정 추가

- 우선순위: `필수`
- 설명: backend 와 agent 테스트 실행 시 branch coverage 를 측정하고 report 를 남기는 설정을 추가한다.
- 완료 기준:
- `pytest` 실행 시 branch coverage report 가 생성되어야 한다.
- coverage 결과 파일이 증적 자료로 남아 추후 비교 가능해야 한다.
- 선행 조건: B-001, B-004
- 연결 테스트: pytest coverage smoke test

### B-005 Playwright 기본 실행 골격 준비

- 우선순위: `필수`
- 설명: 브라우저 기반 최소 E2E 테스트를 위한 Playwright 실행 환경과 기본 smoke 시나리오를 준비한다.
- 완료 기준:
- 로그인 화면 또는 최소 진입 화면까지 Playwright 로 열 수 있어야 한다.
- 테스트 실행 스크립트와 기본 설정이 저장소에 정리되어야 한다.
- 선행 조건: B-001
- 연결 테스트: Playwright smoke test

## 5. Milestone 1 - 로그인과 최소 editor 저장 흐름

### B-101 로그인 화면 및 인증 API 연동

- 우선순위: `필수`
- 설명: seed 된 계정으로 로그인하고 세션을 유지할 수 있게 한다.
- 완료 기준:
- 로그인 성공/실패 흐름이 동작해야 한다.
- 인증되지 않은 사용자는 editor 와 monitoring 에 접근할 수 없어야 한다.
- 선행 조건: B-001, B-002
- 연결 테스트: pytest 로그인 API 테스트, Playwright 로그인 smoke test

### B-102 workspace/view 목록 최소 화면

- 우선순위: `필수`
- 설명: 로그인 후 최소한의 view 목록 화면을 보여준다.
- 완료 기준:
- 사용자는 접근 가능한 view 목록을 볼 수 있어야 한다.
- 새 최소 view 생성 진입점이 있어야 한다.
- 선행 조건: B-101, B-003
- 연결 테스트: pytest view 목록 API 테스트

### B-103 최소 editor SVG canvas 구현

- 우선순위: `필수`
- 설명: inline SVG 기반 editor 에서 최소 node 생성, 이동, edge 생성이 가능하게 한다.
- 완료 기준:
- `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent` 를 화면에 배치할 수 있어야 한다.
- 두 node 사이에 단순 `CommunicationLink` line 을 생성할 수 있어야 한다.
- 선택과 이동이 가능해야 한다.
- 선행 조건: B-003, B-102
- 연결 테스트: Playwright editor smoke test

### B-104 containment 제약 1차 적용

- 우선순위: `필수`
- 설명: editor 에서 허용된 containment 조합과 최소 edge 연결 규칙만 생성 가능하게 한다.
- 완료 기준:
- `PhysicalServer` 내부에만 `SoftwareProcess`, `MonitoringAgent` 생성이 가능해야 한다.
- 잘못된 위치에는 생성되지 않아야 한다.
- 선행 조건: B-103
- 연결 테스트: containment 제약 테스트

### B-105 view 저장 API 및 layout 저장

- 우선순위: `필수`
- 설명: editor 에서 만든 최소 layout 과 edge 연결을 저장할 수 있게 한다.
- 완료 기준:
- node 좌표, edge source/target, 최소 속성이 DB 에 저장되어야 한다.
- 저장 후 다시 열었을 때 같은 배치와 line 연결이 보여야 한다.
- 선행 조건: B-103, B-104
- 연결 테스트: view 저장/재조회 테스트

### Refactor Checkpoint R-1

- 시점: Milestone 1 종료 직후
- 확인 항목:
- editor 상태 관리와 API 응답 구조가 뒤섞여 있지 않은가
- metamodel/notation seed 구조가 이후 확장을 막지 않는가
- 저장 모델과 view layout 모델이 명확히 분리되어 있는가
- 결과:
- 구조 문제가 크면 Milestone 2 전에 refactoring backlog 를 추가한다.

## 6. Milestone 2 - agent ingest 와 latest state 반영

### B-201 backend ingest 최소 API 구현

- 우선순위: `필수`
- 설명: agent 의 `HTTPS + JSON batch POST` 요청을 받을 수 있는 ingest endpoint 를 만든다.
- 완료 기준:
- 정상 payload 수신 후 durable write 가 가능해야 한다.
- 최소한 `ack_seq` 를 응답할 수 있어야 한다.
- 선행 조건: B-002, B-004
- 연결 테스트: ingest API 정상 수신 테스트

### B-202 backend inbox/work queue 처리 구조 구현

- 우선순위: `필수`
- 설명: ingest 요청은 DB 에 접수 후 worker 가 처리하도록 최소 구조를 만든다.
- 완료 기준:
- request 경로와 후처리 경로가 분리되어야 한다.
- worker 가 inbox 를 읽어 latest state 를 갱신할 수 있어야 한다.
- 선행 조건: B-201
- 연결 테스트: inbox -> worker 처리 테스트

### B-203 latest state 저장과 조회 API 구현

- 우선순위: `필수`
- 설명: process 상태와 MonitoringAgent 상태를 latest state 로 저장하고 조회 가능하게 한다.
- 완료 기준:
- process up/down 상태와 agent heartbeat 상태가 저장되어야 한다.
- monitoring 화면이 이를 읽어올 수 있는 API 가 있어야 한다.
- 선행 조건: B-202
- 연결 테스트: latest state 반영 테스트

### B-204 최소 raw event 생성

- 우선순위: `필수`
- 설명: process started, process stopped, agent heartbeat lost 수준의 raw event 를 생성한다.
- 완료 기준:
- 상태 전이 시 raw event 가 저장되어야 한다.
- 최근 event 조회 API 가 있어야 한다.
- 선행 조건: B-202
- 연결 테스트: raw event 생성 테스트

### B-205 Linux agent 최소 실행 골격 구현

- 우선순위: `필수`
- 설명: 단일 Python 프로세스 기반 agent 실행 골격과 설정 로딩 구조를 만든다.
- 완료 기준:
- agent 프로세스가 실행되고 종료될 수 있어야 한다.
- backend endpoint, token, target selector 를 읽을 수 있어야 한다.
- 선행 조건: 없음
- 연결 테스트: agent 설정 로딩 테스트

### B-205A agent runner 와 주기 스케줄 골격 구현

- 우선순위: `필수`
- 설명: 설정을 바탕으로 heartbeat, snapshot, flush 주기를 실행하는 최소 runner 골격을 만든다.
- 완료 기준:
- 단일 프로세스에서 scheduler 와 collector/transport 호출 경계가 분리되어야 한다.
- 주기 함수가 테스트에서 독립 호출 가능해야 한다.
- 선행 조건: B-205
- 연결 테스트: runner 주기 실행 테스트

### B-206 selector 와 process snapshot 수집 구현

- 우선순위: `필수`
- 설명: process name 또는 command line 기준으로 target 하나를 찾아 snapshot 을 만든다.
- 완료 기준:
- target process 를 찾고 최소 snapshot 을 생성할 수 있어야 한다.
- `target_id`, `pid`, `state`, `cpu_usage`, `memory_rss` 가 포함되어야 한다.
- 선행 조건: B-205
- 연결 테스트: selector 및 snapshot 테스트

### B-206A agent 단위 테스트 1차 세트 구축

- 우선순위: `필수`
- 설명: selector, snapshot, payload 직렬화, sequence 증가 로직에 대한 빠른 단위 테스트 세트를 고정한다.
- 완료 기준:
- backend 없이도 실행 가능한 agent 단위 테스트 세트가 분리되어 있어야 한다.
- branch coverage report 에 agent 핵심 분기 경로가 포함되어야 한다.
- 선행 조건: B-205, B-206
- 연결 테스트: agent unit test suite

### B-207 SQLite outbox 구현

- 우선순위: `필수`
- 설명: agent 가 전송 전 payload 를 outbox 에 기록하고 ack 이후 정리하도록 만든다.
- 완료 기준:
- backend 미연결 시 payload 가 outbox 에 저장되어야 한다.
- 연결 복구 후 순차 재전송이 가능해야 한다.
- 선행 조건: B-205, B-206
- 연결 테스트: outbox 저장/복구 테스트

### B-207A backend 계약 테스트 1차 세트 구축

- 우선순위: `필수`
- 설명: agent 가 만든 payload 를 실제 backend ingest API 에 보내고 ack 와 후처리 반영을 검증하는 계약 테스트를 구축한다.
- 완료 기준:
- `ack_seq`, latest state 반영, raw event 반영이 한 경로에서 검증되어야 한다.
- payload schema drift 가 생기면 빠르게 깨지는 테스트가 있어야 한다.
- 선행 조건: B-201, B-202, B-206, B-207
- 연결 테스트: agent-backend contract test

### B-208 agent transport 구현

- 우선순위: `필수`
- 설명: batch payload 를 backend ingest API 로 전송한다.
- 완료 기준:
- `seq`, `sent_at`, `items` 를 포함한 payload 전송이 가능해야 한다.
- `ack_seq` 기준으로 outbox 를 정리할 수 있어야 한다.
- 선행 조건: B-201, B-207
- 연결 테스트: transport/ack 테스트

### B-208A Linux 실제 통합 테스트 준비

- 우선순위: `필수`
- 설명: Linux 에서 실행 가능한 dummy target process 와 실행/종료 확인 절차를 정리한다.
- 완료 기준:
- 실제 Linux 환경에서 target process 를 띄우고 selector 로 찾을 수 있어야 한다.
- 종료/재시작 시나리오를 반복 가능한 체크리스트나 스크립트로 남겨야 한다.
- 선행 조건: B-206, B-208
- 연결 테스트: Linux integration smoke test

### Refactor Checkpoint R-2

- 시점: Milestone 2 종료 직후
- 확인 항목:
- backend web 과 worker 책임이 실제 코드에서 분리되어 있는가
- agent collector 와 transport 가 느슨하게 결합되어 있는가
- latest state 와 raw event 저장 구조가 이후 grouped event 확장을 막지 않는가
- 결과:
- 구조 혼합이 확인되면 Milestone 3 전에 refactoring backlog 를 우선 수행한다.

## 7. Milestone 3 - monitoring 화면과 event 반영

### B-301 monitoring 화면 최소 구성

- 우선순위: `필수`
- 설명: 저장된 view layout 위에 latest state 를 overlay 하는 화면을 만든다.
- 완료 기준:
- 저장된 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent` 와 `CommunicationLink` 가 표시되어야 한다.
- latest state 에 따라 node 색상 또는 배지가 바뀌어야 한다.
- 선행 조건: B-105, B-203
- 연결 테스트: monitoring 조회 테스트

### B-302 polling 기반 상태 갱신 구현

- 우선순위: `필수`
- 설명: monitoring 화면에서 주기적으로 latest state 를 다시 조회한다.
- 완료 기준:
- target process 상태 변화가 polling 주기 내 화면에 반영되어야 한다.
- stale 또는 마지막 갱신 시각을 표시할 수 있어야 한다.
- 선행 조건: B-301
- 연결 테스트: polling 갱신 테스트

### B-303 event panel 최소 구현

- 우선순위: `필수`
- 설명: 최근 raw event 몇 건을 표시하는 최소 event panel 을 구현한다.
- 완료 기준:
- process stopped/restarted 이벤트가 event panel 에 보일 수 있어야 한다.
- 시간과 event type 이 표시되어야 한다.
- 선행 조건: B-204, B-301
- 연결 테스트: event panel 조회 테스트

### B-304 MonitoringAgent 상태 표시 구현

- 우선순위: `필수`
- 설명: MonitoringAgent heartbeat 와 연결 상태를 monitoring 화면에 표시한다.
- 완료 기준:
- agent 정상/비정상 상태가 process 상태와 구분되어 보여야 한다.
- agent 중지 시 비정상 상태로 변해야 한다.
- 선행 조건: B-203, B-301
- 연결 테스트: agent 상태 표시 테스트

## 8. Milestone 4 - debug mode 와 복구 게이트

### B-401 backend debug mode payload 저장 구현

- 우선순위: `필수`
- 설명: debug mode 활성화 시 agent 요청/응답 payload 를 저장한다.
- 완료 기준:
- debug mode on/off 에 따라 저장 여부가 달라져야 한다.
- 민감 정보는 마스킹되어야 한다.
- 선행 조건: B-201
- 연결 테스트: debug payload 저장 테스트

### B-402 agent debug mode 메타데이터 추가

- 우선순위: `필수`
- 설명: trace_id, 요청/응답 시각, status code 등 최소 진단 메타데이터를 남긴다.
- 완료 기준:
- debug mode 에서 trace_id 가 payload 또는 헤더 수준에서 연결 가능해야 한다.
- backend 저장 로그와 상호 연계 가능해야 한다.
- 선행 조건: B-208, B-401
- 연결 테스트: trace_id 연계 테스트

### B-403 outbox 장애 복구 실전 시나리오 검증

- 우선순위: `필수`
- 설명: backend 중단 후 재기동 시 outbox 재전송이 실제로 동작하는지 검증한다.
- 완료 기준:
- backend 비가용 동안 수집 데이터가 outbox 에 쌓여야 한다.
- backend 복구 후 누락 없이 재전송되어야 한다.
- 선행 조건: B-207, B-208
- 연결 테스트: outbox 복구 통합 테스트

### Refactor Checkpoint R-3

- 시점: Milestone 4 종료 직후
- 확인 항목:
- debug mode 가 주 기능 경로를 오염시키지 않는가
- polling 기반 monitoring 구조가 이후 SSE 확장을 막지 않는가
- event 저장 구조가 grouped event 추가를 수용할 수 있는가
- 결과:
- 이상이 있으면 최소 E2E 게이트 통과 전 refactoring 을 먼저 수행한다.

## 9. 최소 E2E 게이트 검증 작업

### B-501 최소 E2E 자동 테스트 묶음 정리

- 우선순위: `필수`
- 설명: 최소 E2E 수용 기준에 대응하는 자동 테스트 묶음을 정리한다.
- 완료 기준:
- `pytest` 기반으로 로그인 API, view 저장 API, ingest, latest state, raw event, debug mode, outbox 복구 테스트가 한 세트로 실행 가능해야 한다.
- agent 쪽은 `단위 테스트 세트`와 `backend 계약 테스트 세트`가 분리되어 실행 가능해야 한다.
- `Playwright` 기반으로 로그인, editor 저장, monitoring 진입 흐름이 한 세트로 실행 가능해야 한다.
- backend 와 agent 의 branch coverage report 가 함께 생성되어야 한다.
- 선행 조건: B-101, B-105, B-201, B-203, B-204, B-401, B-403
- 연결 테스트: 최소 E2E test suite

### B-502 최소 E2E 수동 통합 시나리오 실행

- 우선순위: `필수`
- 설명: 실제 Linux process 를 대상으로 최소 E2E 시나리오를 반복 실행한다.
- 완료 기준:
- 로그인 -> editor 저장 -> agent 연결 -> monitoring 확인 -> process 종료 -> event 반영 흐름이 성공해야 한다.
- agent 수동 통합 테스트는 실제 Linux 환경에서 dummy process 를 사용해 최소 1회 이상 성공해야 한다.
- 동일 시나리오를 3회 이상 치명적 예외 없이 반복할 수 있어야 한다.
- 선행 조건: 전체 선행 milestone 완료
- 연결 테스트: 수동 통합 테스트 체크리스트

### B-503 최소 E2E 회고 및 다음 단계 backlog 조정

- 우선순위: `필수`
- 설명: 최소 E2E 완료 후 구조 문제, 테스트 공백, 다음 우선순위를 정리한다.
- 완료 기준:
- refactoring 필요 항목과 다음 확장 기능 후보가 분리된 backlog 로 정리되어야 한다.
- grouped event, SSE, admin UI 확장, agent 자동 업데이트 중 무엇을 다음으로 할지 결정 가능해야 한다.
- 선행 조건: B-501, B-502
- 연결 테스트: 없음

## 10. 기능 추가 전 반드시 확인할 리팩터링 후보

- `R-CAND-01`: backend web/worker 경계가 코드 수준에서 명확한가
- `R-CAND-02`: SQLite access 가 단일 책임 경로로 정리되어 있는가
- `R-CAND-03`: frontend editor 상태와 monitoring 상태가 분리되어 있는가
- `R-CAND-04`: agent collector, outbox, transport 가 테스트 가능한 단위로 분리되어 있는가
- `R-CAND-04A`: agent runner, selector, collector, outbox, transport, self-monitor 경계가 테스트 단위와 일치하는가
- `R-CAND-05`: 회귀 테스트가 새 기능 추가 전에 충분한 안전망 역할을 하는가

## 11. 구현 순서에 대한 의견

- 먼저 가장 작은 성공 경험을 만드는 것이 중요하므로, `Milestone 1` 과 `Milestone 2` 사이에 과도한 UI 고도화를 넣지 않는 것이 좋다.
- event panel 과 debug mode 는 최소 기능만 먼저 넣고, grouped event 나 debug 조회 UI 는 다음 단계로 넘기는 것이 맞다.
- agent 자동 업데이트는 중요하지만 최소 E2E 게이트 통과 전에는 backlog 범위에 넣지 않는 것이 좋다.
- 최소 E2E 단계의 핵심은 화려한 화면보다 `end-to-end 데이터 흐름의 반복 가능성`과 `회귀 테스트 기반`이다.
- 따라서 백로그 수행 중 구조적 냄새가 보이면 기능 추가 속도를 잠시 늦추더라도 refactoring 을 먼저 하는 편이 결과적으로 빠르다.

## 12. 주요 리스크

- [리스크] `Milestone 1` 에서 editor 기능이 커지면 최소 E2E 범위를 금방 넘길 수 있다.
- [리스크] `Milestone 2` 에서 ingest 경로와 worker 후처리 경계를 흐리게 구현하면 이후 refactoring 비용이 커진다.
- [리스크] `Milestone 2` 와 `Milestone 4` 에서 outbox 를 단순 버퍼처럼 구현하면 장애 복구 신뢰성이 떨어질 수 있다.
- [리스크] `Milestone 3` 에서 polling 기반 monitoring 만으로도 상태 갱신이 불안정하면 이후 SSE 확장 전에 구조 정리가 필요하다.
- [리스크] `Milestone 4` 의 debug mode 와 outbox 복구는 뒤로 미루기 쉽지만, 실제로는 최소 E2E 품질을 결정하는 핵심 게이트다.
- [리스크] seed 구조와 최소 메타모델을 임시 코드로만 처리하면 이후 metamodel/notation 확장 시 재작업이 발생할 수 있다.
- [리스크] 회귀 테스트가 milestone 끝에서만 추가되면 점진적 개발의 장점이 줄어들고, refactoring 비용이 커질 수 있다.
- [리스크] branch coverage 를 늦게 도입하면 backend 와 agent 내부 분기 경로의 테스트 공백을 초기에 파악하기 어렵다.
- [리스크] Playwright 기반 브라우저 테스트를 너무 늦게 붙이면 editor 와 monitoring 흐름의 UI 회귀를 초기에 잡기 어렵다.
- [리스크] agent 자동 업데이트를 현재 backlog 에 조기 편입하면 핵심 흐름 검증 전 운영 복잡도가 증가할 수 있다.
- [리스크] agent 단위 테스트와 backend 계약 테스트가 섞여 있으면 실패 원인 분리가 어려워질 수 있다.
- [리스크] Linux 실제 통합 테스트 준비를 너무 늦게 시작하면 agent 코드가 Windows 개발 환경 가정에 묶일 수 있다.
- [관찰] 최소 E2E 단계에서는 기능 수가 아니라 반복 가능한 성공 시나리오 확보 여부가 더 중요하다.

## 13. 요약

- 본 백로그는 최소 E2E 버전을 실제 구현 단위로 분해한 실행 계획이다.
- 우선순위는 `로그인/저장`, `ingest/latest state`, `monitoring/event`, `debug/outbox 복구`, `전체 게이트 검증` 순서다.
- 각 milestone 에는 refactoring checkpoint 를 두어 구조 문제를 조기에 정리할 수 있게 했다.
- 본 문서는 이후 실제 개발 작업 등록과 iteration planning 의 기준 문서로 사용한다.
