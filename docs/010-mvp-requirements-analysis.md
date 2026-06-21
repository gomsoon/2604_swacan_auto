# Software Architecture Runtime Monitoring System

## 1. 요구사항 분석서 목적

- 본 문서는 MVP 구현에 직접 연결할 수 있는 요구사항을 파트별로 정리한다.
- 요구사항은 `공통/운영`, `Frontend`, `Backend`, `Agent` 네 영역으로 구분한다.
- 각 항목은 MVP 기준으로 `필수`, `선택`, `후속` 우선순위를 갖는다.

## 2. MVP 기술 전제

- Backend: Python, Flask, SQLite3
- Test: pytest
- Frontend UI: Bootstrap
- Canvas: Inline SVG + 경량 JavaScript 계층
- Canvas Interaction: interact.js 중심
- Agent: Python 기반 Linux daemon

## 3. 핵심 리스크

- Canvas 복잡도: containment, edge, overlay를 한 번에 너무 많이 넣으면 MVP 범위가 커진다.
- Runtime binding 흔들림: PID 변경, 재시작, 일시 미탐지 상황을 요구사항에서 명시해야 한다.
- Flask + SQLite 실시간 부하: latest state와 event log 분리, snapshot 보정 정책이 필수다.
- Agent 신뢰성: backend 장애 시 outbox 복구 없이는 데이터 유실 위험이 크다.

## 4. 공통/운영 요구사항

- C-001 `필수`: 시스템은 `관리자`, `일반 사용자` 권한을 구분해야 한다.
- C-002 `필수`: 각 view는 `metamodel_version_id`에 고정되어야 한다.
- C-003 `필수`: agent host와 backend host의 시간은 NTP로 동기화되어야 한다.
- C-004 `필수`: `occurred_at`, `received_at`, `updated_at` 등 주요 시간값은 1/1000초 정밀도로 저장되어야 한다.
- C-005 `필수`: 구조화된 운영 로그와 감사 로그는 최근 1주일만 유지한다.
- C-006 `필수`: frontend는 실시간 이벤트 수신과 주기적 snapshot 재동기화를 함께 사용한다.
- C-007 `필수`: pytest 기반 자동 테스트를 갖추고, 테스트는 독립 SQLite 환경에서 실행 가능해야 한다.

## 5. Frontend 요구사항

- FE-001 `필수`: 사용자는 로그인 후 접근 가능한 workspace와 view 목록을 보아야 한다.
- FE-002 `필수`: canvas palette는 backend notation registry를 기반으로 동적 구성되어야 한다.
- FE-003 `필수`: editor canvas는 containment 규칙을 위반하지 않는 범위에서만 요소 생성과 배치를 허용한다.
- FE-004 `필수`: node 이동, 크기, 부모 좌표계, edge routing 정보를 저장할 수 있어야 한다.
- FE-005 `필수`: view는 저장과 복제가 가능해야 한다.
- FE-006 `필수`: monitoring view는 latest runtime state를 overlay하고 event panel을 함께 표시해야 한다.
- FE-007 `필수`: `MonitoringAgent`는 canvas와 monitoring view에서 별도 요소로 표시되어야 한다.
- FE-008 `필수`: `MonitoringAgent`의 heartbeat, backend connection status, queue depth를 시각화할 수 있어야 한다.
- FE-009 `필수`: 관리자 화면에서 메타모델, 접속 세션, 운영 로그, backend 상태를 보아야 한다.
- FE-010 `선택`: `MonitoringAgent`에 대한 전용 아이콘, 배지, 강조 표현을 추가할 수 있다.

## 6. Backend 요구사항

- BE-001 `필수`: semantic type, property definition, association definition, containment rule를 저장하고 조회해야 한다.
- BE-002 `필수`: notation registry는 고유 ID와 안정적 code를 갖고 palette 구성을 지원해야 한다.
- BE-003 `필수`: backend는 containment 위반 여부를 저장 전 최종 검증해야 한다.
- BE-004 `필수`: `PhysicalServer`/`VirtualMachine`은 `MonitoringAgent`를 포함할 수 있어야 한다.
- BE-005 `필수`: `MonitoringAgent`는 `monitors` 관계를 통해 process/group을 관측해야 한다.
- BE-006 `필수`: architecture model, view, layout, edge 정보를 저장하고 복원해야 한다.
- BE-007 `필수`: runtime binding은 `target_id` 중심으로 관리하고 `stale` 상태를 지원해야 한다.
- BE-008 `필수`: latest state와 event log를 분리해 관리해야 한다.
- BE-009 `필수`: backend는 `MonitoringAgent` 정의, agent runtime state, execution node, monitored target 관계를 함께 관리해야 한다.
- BE-010 `필수`: agent API는 batch push, ack, seq 처리, 시간값 처리를 지원해야 한다.
- BE-011 `필수`: 관리자 API는 접속 세션, 운영 로그, agent 상태, 감사 로그를 조회할 수 있어야 한다.
- BE-012 `필수`: SQLite는 WAL 전략과 쓰기 부하 완화 정책을 가졌야 한다.

## 7. Agent 요구사항

- AG-001 `필수`: agent는 Linux 상에서 단독 실행되는 비침습형 daemon이어야 한다.
- AG-002 `필수`: host/process 자원 정보를 수집해야 한다.
- AG-003 `필수`: thread 정보는 MVP에서 `thread_count` 중심으로 제한한다.
- AG-004 `필수`: agent는 자기 자신의 state를 runtime data로 보낼 수 있어야 한다.
- AG-005 `필수`: self-state에는 `agent pid`, `start time`, `heartbeat time`, `backend connection status`, `outbox queue depth`, `last_sent_seq`, `last_ack_seq`가 포함될 수 있어야 한다.
- AG-006 `필수`: 모니터링 대상은 `target_id` 기준으로 선택하고, selector로 `command line regex`, `executable path`, `process name`, `pid`를 지원한다.
- AG-007 `필수`: 하나의 target에 대해 여러 PID를 수집할 수 있고 group summary를 전송할 수 있어야 한다.
- AG-008 `필수`: backend 장애 시 SQLite outbox에 저장하고, 복구 후 seq 기준으로 재전송해야 한다.
- AG-009 `필수`: agent payload는 `agent_id`, `boot_id`, `seq`, `items`를 포함하고 HTTPS로 전송되어야 한다.

## 8. 후속 항목

- L-001 `후속`: 침습형 agent, application 내부 SDK, 개별 thread 상세 분석
- L-002 `후속`: Windows/macOS agent 지원
- L-003 `후속`: 고급 시각화 규칙 엔진과 복합 조건식
- L-004 `후속`: 실시간 동시 편집과 자동 병합
- L-005 `후속`: 장기 시계열 분석과 고급 로그 외부 연계

## 9. 다음 설계 단계 입력물

- 화면 목록 및 화면 흐름
- backend API 목록
- SQLite ERD 초안
- agent payload 구조
- runtime binding/stale 처리 규칙
- pytest 테스트 범위

## 10. 종합 의견

- MVP 구현 관점에서 가장 중요한 요구사항은 `containment`, `MonitoringAgent`, `runtime binding`, `1주 로그 보존`, `NTP + 밀리초 시간값`, `agent outbox`이다.
- 다음 단계에서는 본 문서를 바탕으로 화면, API, DB, agent 설계로 즉시 내려가는 것이 가장 효율적이다.
