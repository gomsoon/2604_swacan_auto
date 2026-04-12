# Software Architecture Runtime Monitoring System

## 최소 ERD 초안

버전: Draft 0.1
작성일: 2026-04-10
목적: 본 문서는 최소 E2E 구현을 위해 필요한 최소 데이터베이스 엔터티와 관계를 정의한다. 본 초안은 MVP 전체 ERD가 아니라, `로그인 -> view 저장 -> agent ingest -> latest state 반영 -> monitoring 조회 -> raw event 확인 -> debug payload 저장` 흐름을 만족시키기 위한 최소 범위만 다룬다.

## 1. 설계 원칙

- [필수] ERD 는 최소 E2E 구현에 직접 필요한 테이블만 포함한다.
- [필수] `model/view 저장`, `agent ingest durable write`, `latest state`, `raw event`, `debug payload` 는 분리한다.
- [필수] grouped event, 동적 metamodel 편집, 관리자 콘솔용 전체 테이블은 이후 확장으로 미룬다.
- [필수] SQLite 기반 구현을 전제로 하므로, 읽기 최적화와 단순한 쓰기 흐름을 우선한다.

## 2. 최소 포함 테이블

- `users`
- `views`
- `view_nodes`
- `ingest_inbox`
- `latest_states`
- `raw_events`
- `debug_payload_logs`

## 3. 테이블 정의

### 3.1 users

목적:
- 로그인과 최소 권한 확인을 위한 사용자 계정 저장

주요 컬럼:
- `id` TEXT PK
- `username` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `role` TEXT NOT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- 최소 E2E 에서는 `admin` 또는 `user` 수준의 단순 role 만 있어도 된다.

### 3.2 views

목적:
- architecture view 메타데이터 저장

주요 컬럼:
- `id` TEXT PK
- `name` TEXT NOT NULL
- `description` TEXT NULL
- `owner_user_id` TEXT NOT NULL
- `metamodel_version` TEXT NOT NULL
- `revision` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

관계:
- `owner_user_id -> users.id`

비고:
- 최소 E2E 에서는 workspace 분리를 생략하고 단일 사용자 또는 단일 소유자 구조로 시작할 수 있다.

### 3.3 view_nodes

목적:
- editor 와 monitoring view 가 공유하는 최소 layout 및 노드 정의 저장

주요 컬럼:
- `id` TEXT PK
- `view_id` TEXT NOT NULL
- `parent_node_id` TEXT NULL
- `node_type` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `target_id` TEXT NULL
- `x` REAL NOT NULL
- `y` REAL NOT NULL
- `width` REAL NOT NULL
- `height` REAL NOT NULL
- `style_json` TEXT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

관계:
- `view_id -> views.id`
- `parent_node_id -> view_nodes.id`

비고:
- 최소 E2E 에서는 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent` 세 타입만 지원해도 된다.
- `target_id` 는 process node 와 agent node 를 runtime 상태와 연결하기 위한 최소 식별자다.

### 3.4 ingest_inbox

목적:
- agent ingest 요청을 durable 하게 먼저 저장하는 내부 work queue

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `agent_id` TEXT NOT NULL
- `boot_id` TEXT NOT NULL
- `seq_start` INTEGER NOT NULL
- `seq_end` INTEGER NOT NULL
- `received_at` TEXT NOT NULL
- `payload_json` TEXT NOT NULL
- `status` TEXT NOT NULL
- `processed_at` TEXT NULL
- `error_message` TEXT NULL

비고:
- request path 는 이 테이블까지 durable write 한 뒤 ack 를 반환한다.
- worker 가 `status=pending` 레코드를 읽어 후처리한다.

### 3.5 latest_states

목적:
- monitoring 화면 조회용 최신 상태 저장

주요 컬럼:
- `id` TEXT PK
- `view_node_id` TEXT NULL
- `target_id` TEXT NOT NULL
- `state_type` TEXT NOT NULL
- `status` TEXT NOT NULL
- `severity` TEXT NULL
- `state_json` TEXT NOT NULL
- `occurred_at` TEXT NOT NULL
- `received_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

관계:
- `view_node_id -> view_nodes.id`

비고:
- `state_type` 은 최소한 `process`, `agent` 를 지원한다.
- `state_json` 에는 cpu, memory, pid, heartbeat 등 최소 overlay 정보가 들어간다.
- 같은 `target_id + state_type` 조합에 대해 upsert 중심으로 관리한다.

### 3.6 raw_events

목적:
- 최소 event panel 에 표시할 원시 이벤트 저장

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `agent_id` TEXT NOT NULL
- `target_id` TEXT NOT NULL
- `event_type` TEXT NOT NULL
- `severity` TEXT NOT NULL
- `message` TEXT NULL
- `event_json` TEXT NULL
- `occurred_at` TEXT NOT NULL
- `received_at` TEXT NOT NULL

비고:
- 최소 E2E 에서는 `process_started`, `process_stopped`, `process_restarted`, `agent_heartbeat_lost` 정도면 충분하다.
- grouped event 는 이후 확장에서 별도 테이블 또는 파생 구조로 추가한다.

### 3.7 debug_payload_logs

목적:
- backend debug mode 에서만 저장되는 통신 payload 기록

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `channel` TEXT NOT NULL
- `direction` TEXT NOT NULL
- `endpoint_or_topic` TEXT NOT NULL
- `agent_id` TEXT NULL
- `user_id` TEXT NULL
- `session_id` TEXT NULL
- `trace_id` TEXT NULL
- `status_code` INTEGER NULL
- `payload_json` TEXT NOT NULL
- `payload_size` INTEGER NOT NULL
- `is_redacted` INTEGER NOT NULL DEFAULT 1
- `occurred_at` TEXT NOT NULL

관계:
- `user_id -> users.id`

비고:
- 최소 E2E 에서는 `agent <-> backend` payload 저장만 우선 지원해도 된다.
- 보존 기간은 최근 24시간 기준으로 정리한다.

## 4. 테이블 간 관계 요약

- `users 1:N views`
- `views 1:N view_nodes`
- `view_nodes 1:N view_nodes` self-reference for containment
- `view_nodes 1:N latest_states` optional by `view_node_id`
- `users 1:N debug_payload_logs` optional
- `ingest_inbox` 는 다른 테이블의 직접 FK 없이 ingest/work queue 역할을 수행
- `raw_events` 와 `latest_states` 는 `target_id` 중심으로 연결됨

## 5. 최소 인덱스 제안

- `users(username)` UNIQUE
- `views(owner_user_id, updated_at)`
- `view_nodes(view_id)`
- `view_nodes(parent_node_id)`
- `view_nodes(target_id)`
- `ingest_inbox(status, received_at)`
- `latest_states(target_id, state_type)` UNIQUE 또는 동등 인덱스
- `raw_events(target_id, occurred_at)`
- `raw_events(event_type, occurred_at)`
- `debug_payload_logs(channel, occurred_at)`
- `debug_payload_logs(trace_id, occurred_at)`

## 6. 최소 E2E 범위에서 일부러 뺀 것

- `metamodel tables`
- `notation registry tables`
- `runtime_bindings`
- `grouped_events`
- `admin_audit_logs`
- `viewer_sessions`
- `workspace_members`
- `view_edges` 별도 테이블

비고:
- 최소 E2E 에서는 edge 편집보다 node 배치와 runtime overlay 검증이 더 중요하므로, 선 연결 정보는 `style_json` 또는 후속 확장으로 미룰 수 있다.
- metamodel 과 notation 은 우선 seed 데이터와 enum 수준으로 처리하고, 정식 테이블화는 다음 단계에서 진행할 수 있다.

## 7. 최소 ERD에 대한 판단

- 이 초안은 최소 E2E 구현 속도를 높이기 위한 고의적 축소본이다.
- 가장 중요한 것은 `view_nodes`, `ingest_inbox`, `latest_states`, `raw_events` 의 책임이 섞이지 않는 것이다.
- 이후 grouped event, metamodel registry, admin 기능 확장 시 테이블은 늘어나더라도, 최소 E2E 에서 만든 `durable ingest -> latest state -> monitoring 조회` 흐름은 유지되어야 한다.

## 8. 다음 단계 입력

- 이 문서를 기준으로 SQLite `CREATE TABLE` 초안을 작성할 수 있어야 한다.
- 이 문서를 기준으로 최소 API 명세 초안의 request/response 구조를 정리할 수 있어야 한다.
- 이 문서를 기준으로 backend web/worker 코드 경계를 나눌 수 있어야 한다.
