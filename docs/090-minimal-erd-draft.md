# Software Architecture Runtime Monitoring System

## 최소 ERD 초안

버전: Draft 0.2  
작성일: 2026-04-15

목적: 본 문서는 현재 구현된 minimal end-to-end와 MVP 전환 초입의 설계를 기준으로, 최소 데이터 모델을 사람이 읽기 쉬운 ERD 관점에서 정리한 초안이다. 이 문서는 전체 제품 ERD가 아니라, 현재 코드베이스에서 실제로 사용 중인 핵심 테이블과 관계를 설명한다.

## 1. 설계 원칙

- editor, monitoring, admin, agent ingest가 같은 저장소를 공유하되 책임은 분리한다.
- `view` 구조와 `runtime` 데이터는 분리 저장한다.
- agent 수신은 `ingest_inbox`에 durable write 한 뒤 worker가 후처리한다.
- `latest_states`는 현재 스냅샷, `raw_events`는 append-only 이벤트로 구분한다.
- metamodel/notation registry는 현재 seed 기반 published version을 조회하는 구조로 시작한다.
- `view_nodes`, `view_edges`는 기존 `node_type`, `edge_type`를 유지하면서도 `semantic_type_code`, `notation_code`를 함께 저장해 metamodel registry와 점진 연결한다.
- `node_type`, `edge_type` 자체는 더 이상 하드코딩된 소수 타입 집합으로 제한하지 않고, 현재 연결된 metamodel version의 semantic type을 따라간다.

## 2. 현재 핵심 테이블

- `users`
- `metamodel_namespaces`
- `metamodel_versions`
- `semantic_types`
- `property_definitions`
- `association_definitions`
- `containment_rules`
- `palette_groups`
- `notation_definitions`
- `views`
- `view_versions`
- `view_nodes`
- `view_edges`
- `view_version_nodes`
- `view_version_edges`
- `ingest_inbox`
- `processed_item_receipts`
- `latest_states`
- `raw_events`
- `debug_payload_logs`
- `cleanup_runs`

## 3. 테이블 정의 요약

### 3.1 users

목적:
- 로그인, 권한 확인, 관리자 여부 판단

주요 컬럼:
- `id` INTEGER PK
- `username` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `role` TEXT NOT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.2 metamodel_namespaces

목적:
- metamodel registry의 namespace 구분

주요 컬럼:
- `id` INTEGER PK
- `code` TEXT UNIQUE NOT NULL
- `name` TEXT NOT NULL
- `description` TEXT NULL
- `is_system` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.3 metamodel_versions

목적:
- metamodel 버전 관리

주요 컬럼:
- `id` INTEGER PK
- `namespace_id` INTEGER NOT NULL
- `version_code` TEXT NOT NULL
- `status` TEXT NOT NULL (`draft`, `published`, `deprecated`)
- `description` TEXT NULL
- `based_on_version_id` INTEGER NULL
- `published_at` TEXT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- 현재 minimal/MVP baseline은 `seed-v1` published version을 사용한다.

### 3.4 semantic_types

목적:
- backend가 이해하는 의미 타입 정의

주요 컬럼:
- `id` INTEGER PK
- `metamodel_version_id` INTEGER NOT NULL
- `code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `kind` TEXT NOT NULL (`node`, `edge`, `container`, `runtime-only`)
- `runtime_kind` TEXT NULL
- `is_groupable` INTEGER NOT NULL DEFAULT 0
- `allows_runtime_binding` INTEGER NOT NULL DEFAULT 1
- `default_notation_id` INTEGER NULL
- `is_active` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

현재 seed 예:
- `PhysicalServer`
- `VirtualMachine`
- `SoftwareProcess`
- `MonitoringAgent`
- `CommunicationLink`

### 3.5 property_definitions

목적:
- semantic type별 속성 정의

주요 컬럼:
- `id` INTEGER PK
- `semantic_type_id` INTEGER NOT NULL
- `code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `value_type` TEXT NOT NULL
- `unit` TEXT NULL
- `default_value_json` TEXT NULL
- `is_required` INTEGER NOT NULL DEFAULT 0
- `is_runtime` INTEGER NOT NULL DEFAULT 0
- `is_user_editable` INTEGER NOT NULL DEFAULT 1
- `sort_order` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.6 association_definitions

목적:
- edge 의미 정의

주요 컬럼:
- `id` INTEGER PK
- `metamodel_version_id` INTEGER NOT NULL
- `code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `source_type_id` INTEGER NOT NULL
- `target_type_id` INTEGER NOT NULL
- `direction` TEXT NOT NULL
- `multiplicity_source` TEXT NULL
- `multiplicity_target` TEXT NULL
- `semantics_json` TEXT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

현재 seed 예:
- `communicates_with`
- `monitors`

### 3.7 containment_rules

목적:
- parent-child containment 규칙 정의

주요 컬럼:
- `id` INTEGER PK
- `metamodel_version_id` INTEGER NOT NULL
- `parent_type_id` INTEGER NOT NULL
- `child_type_id` INTEGER NOT NULL
- `min_count` INTEGER NULL
- `max_count` INTEGER NULL
- `cardinality_scope` TEXT NOT NULL DEFAULT `group_total`
- `is_required` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.8 palette_groups

목적:
- frontend palette 그룹 정의

주요 컬럼:
- `id` INTEGER PK
- `metamodel_version_id` INTEGER NOT NULL
- `code` TEXT NOT NULL
- `label` TEXT NOT NULL
- `sort_order` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.9 notation_definitions

목적:
- semantic type의 시각 표현 정의

주요 컬럼:
- `id` INTEGER PK
- `metamodel_version_id` INTEGER NOT NULL
- `semantic_type_id` INTEGER NOT NULL
- `palette_group_id` INTEGER NULL
- `code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `kind` TEXT NOT NULL (`node`, `edge`)
- `render_primitive` TEXT NOT NULL
- `render_schema_json` TEXT NOT NULL
- `style_tokens_json` TEXT NULL
- `is_default` INTEGER NOT NULL DEFAULT 0
- `is_visible_in_palette` INTEGER NOT NULL DEFAULT 1
- `sort_order` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- frontend는 임의 SVG 코드를 받는 구조가 아니라, 제한된 primitive와 render schema를 해석한다.

### 3.10 views

목적:
- architecture view 메타데이터 저장

주요 컬럼:
- `id` INTEGER PK
- `name` TEXT NOT NULL
- `description` TEXT NULL
- `owner_user_id` INTEGER NOT NULL
- `metamodel_version` TEXT NOT NULL
- `revision` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- 현재 `views` 는 logical root 로 유지되고, 점진적으로 실제 편집/운영 대상은 `view_versions` 로 분리될 예정이다.

### 3.11 view_versions

목적:
- draft / published / active / deprecated 상태를 갖는 view snapshot 관리

주요 컬럼:
- `id` INTEGER PK
- `view_id` INTEGER NOT NULL
- `version_no` INTEGER NOT NULL
- `version_code` TEXT NULL
- `status` TEXT NOT NULL
- `based_on_version_id` INTEGER NULL
- `metamodel_version_id` INTEGER NULL
- `created_by_user_id` INTEGER NOT NULL
- `approved_by_user_id` INTEGER NULL
- `activated_by_user_id` INTEGER NULL
- `published_at` TEXT NULL
- `activated_at` TEXT NULL
- `revision` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- `published` 는 편집 완료된 고정본, `active` 는 실제 운영 중인 버전으로 해석한다.

### 3.12 view_nodes

목적:
- editor와 monitoring이 공유하는 node 인스턴스와 레이아웃 저장

주요 컬럼:
- `id` INTEGER PK
- `view_id` INTEGER NOT NULL
- `parent_node_id` INTEGER NULL
- `node_type` TEXT NOT NULL
- `semantic_type_code` TEXT NOT NULL
- `notation_code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `target_id` TEXT NULL
- `layer_order` INTEGER NOT NULL DEFAULT 0
- `x` REAL NOT NULL
- `y` REAL NOT NULL
- `width` REAL NOT NULL
- `height` REAL NOT NULL
- `is_deleted` INTEGER NOT NULL DEFAULT 0
- `style_json` TEXT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- 현재 허용 node type은 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`다.
- `semantic_type_code`, `notation_code`를 함께 저장해서 registry 기반 표현과 실제 persisted view를 연결한다.
- `layer_order`는 화면에서 보이는 순서를 backend가 일관되게 관리하기 위한 값이다.

### 3.13 view_version_nodes

목적:
- 특정 version snapshot 에 속한 node 구조와 layout 저장

주요 컬럼:
- `id` INTEGER PK
- `view_version_id` INTEGER NOT NULL
- `element_key` TEXT NOT NULL
- `parent_node_id` INTEGER NULL
- `node_type` TEXT NOT NULL
- `semantic_type_code` TEXT NOT NULL
- `notation_code` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `target_id` TEXT NULL
- `layer_order` INTEGER NOT NULL DEFAULT 0
- `x` REAL NOT NULL
- `y` REAL NOT NULL
- `width` REAL NOT NULL
- `height` REAL NOT NULL
- `properties_json` TEXT NULL
- `is_deleted` INTEGER NOT NULL DEFAULT 0

비고:
- `element_key` 는 버전 간 같은 논리 객체를 잇는 안정 키다.

### 3.14 view_edges

목적:
- editor와 monitoring이 공유하는 edge 인스턴스 저장

주요 컬럼:
- `id` INTEGER PK
- `view_id` INTEGER NOT NULL
- `edge_type` TEXT NOT NULL
- `semantic_type_code` TEXT NOT NULL
- `notation_code` TEXT NOT NULL
- `source_node_id` INTEGER NOT NULL
- `target_node_id` INTEGER NOT NULL
- `layer_order` INTEGER NOT NULL DEFAULT 0
- `source_anchor` TEXT NULL
- `target_anchor` TEXT NULL
- `control_points_json` TEXT NULL
- `label` TEXT NULL
- `style_json` TEXT NULL
- `is_deleted` INTEGER NOT NULL DEFAULT 0
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

비고:
- 현재 허용 edge type은 `CommunicationLink` 하나다.
- `x`, `y`를 직접 두기보다 `anchor + control_points_json`으로 line을 표현한다.

### 3.15 view_version_edges

목적:
- 특정 version snapshot 에 속한 edge 저장

주요 컬럼:
- `id` INTEGER PK
- `view_version_id` INTEGER NOT NULL
- `element_key` TEXT NOT NULL
- `association_code` TEXT NULL
- `edge_type` TEXT NOT NULL
- `semantic_type_code` TEXT NOT NULL
- `notation_code` TEXT NOT NULL
- `source_node_id` INTEGER NOT NULL
- `target_node_id` INTEGER NOT NULL
- `source_element_key` TEXT NULL
- `target_element_key` TEXT NULL
- `layer_order` INTEGER NOT NULL DEFAULT 0

비고:
- version 간 안정적인 참조를 위해 `source_element_key`, `target_element_key` 를 병행할 수 있다.

### 3.16 ingest_inbox

목적:
- agent batch payload의 durable receipt queue

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `agent_id` TEXT NOT NULL
- `boot_id` TEXT NOT NULL
- `seq_start` INTEGER NOT NULL
- `seq_end` INTEGER NOT NULL
- `received_at` TEXT NOT NULL
- `payload_json` TEXT NOT NULL
- `status` TEXT NOT NULL (`pending`, `processing`, `processed`, `failed`)
- `processed_at` TEXT NULL
- `error_message` TEXT NULL

비고:
- ingest ack는 item 처리 완료가 아니라 inbox 영속 저장 완료를 의미한다.

### 3.17 processed_item_receipts

목적:
- worker item-level idempotency 보장

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `agent_id` TEXT NOT NULL
- `boot_id` TEXT NOT NULL
- `item_seq` INTEGER NOT NULL
- `payload_type` TEXT NOT NULL
- `target_id` TEXT NOT NULL
- `inbox_id` INTEGER NOT NULL
- `processed_at` TEXT NOT NULL

비고:
- `(agent_id, boot_id, item_seq)` unique 기준으로 중복 side effect를 막는다.

### 3.18 latest_states

목적:
- monitoring overlay용 최신 상태 스냅샷

주요 컬럼:
- `id` INTEGER PK
- `view_node_id` INTEGER NULL
- `target_id` TEXT NOT NULL
- `state_type` TEXT NOT NULL (`process`, `agent`, `host`)
- `status` TEXT NOT NULL
- `severity` TEXT NULL
- `state_json` TEXT NOT NULL
- `occurred_at` TEXT NOT NULL
- `received_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 3.19 raw_events

목적:
- event panel과 운영 확인용 low-level event 저장

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

### 3.20 debug_payload_logs

목적:
- debug mode에서만 저장되는 통신 payload 로그

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `channel` TEXT NOT NULL
- `direction` TEXT NOT NULL
- `endpoint_or_topic` TEXT NOT NULL
- `agent_id` TEXT NULL
- `user_id` INTEGER NULL
- `session_id` TEXT NULL
- `trace_id` TEXT NULL
- `status_code` INTEGER NULL
- `payload_json` TEXT NOT NULL
- `payload_size` INTEGER NOT NULL
- `is_redacted` INTEGER NOT NULL DEFAULT 1
- `occurred_at` TEXT NOT NULL

### 3.21 cleanup_runs

목적:
- backend retention cleanup 실행 결과 기록

주요 컬럼:
- `id` INTEGER PK AUTOINCREMENT
- `started_at` TEXT NOT NULL
- `finished_at` TEXT NOT NULL
- `raw_events_deleted` INTEGER NOT NULL
- `debug_payload_logs_deleted` INTEGER NOT NULL
- `ingest_inbox_deleted` INTEGER NOT NULL

## 4. 관계 요약

- `users 1:N views`
- `metamodel_namespaces 1:N metamodel_versions`
- `metamodel_versions 1:N semantic_types`
- `metamodel_versions 1:N association_definitions`
- `metamodel_versions 1:N containment_rules`
- `metamodel_versions 1:N palette_groups`
- `metamodel_versions 1:N notation_definitions`
- `semantic_types 1:N property_definitions`
- `views 1:N view_nodes`
- `views 1:N view_edges`
- `views 1:N view_versions`
- `view_versions 1:N view_version_nodes`
- `view_versions 1:N view_version_edges`
- `view_nodes 1:N view_nodes` self-reference for containment
- `view_version_nodes 1:N view_version_nodes` self-reference for containment
- `view_nodes 1:N latest_states` optional by `view_node_id`
- `ingest_inbox 1:N processed_item_receipts`

## 5. 최소 인덱스 방향

- `views(owner_user_id, updated_at)`
- `semantic_types(metamodel_version_id, code)`
- `property_definitions(semantic_type_id, sort_order)`
- `association_definitions(metamodel_version_id, code)`
- `containment_rules(metamodel_version_id, parent_type_id, child_type_id)`
- `palette_groups(metamodel_version_id, sort_order)`
- `notation_definitions(metamodel_version_id, semantic_type_id, sort_order)`
- `view_nodes(view_id)`
- `view_versions(view_id, status)`
- `view_versions(view_id, version_no)`
- `view_nodes(parent_node_id)`
- `view_nodes(target_id)`
- `view_nodes(view_id, layer_order, id)`
- `view_version_nodes(view_version_id, parent_node_id)`
- `view_version_nodes(view_version_id, target_id)`
- `view_version_nodes(view_version_id, layer_order, id)`
- `view_edges(view_id)`
- `view_edges(source_node_id)`
- `view_edges(target_node_id)`
- `view_edges(view_id, layer_order, id)`
- `view_version_edges(view_version_id, source_node_id)`
- `view_version_edges(view_version_id, target_node_id)`
- `view_version_edges(view_version_id, layer_order, id)`
- `ingest_inbox(status, received_at)`
- `processed_item_receipts(agent_id, boot_id, item_seq)` UNIQUE
- `latest_states(target_id, state_type)` UNIQUE
- `raw_events(target_id, occurred_at)`
- `debug_payload_logs(channel, occurred_at)`
- `cleanup_runs(finished_at)`

## 6. 현재 문서의 위치

- 본 문서는 더 이상 purely minimal E2E만 설명하지 않는다.
- 현재 구현 기준으로 `metamodel registry + persisted view + runtime pipeline`이 연결된 상태를 반영한다.
- 이후에는 이 문서를 바탕으로 PostgreSQL용 정식 ERD로 확장하면 된다.
