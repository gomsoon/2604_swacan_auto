# Software Architecture Runtime Monitoring System

## SQLite CREATE TABLE 초안

버전: Draft 0.2  
작성일: 2026-04-15

목적: 본 문서는 현재 `db/schema.sql` 기준의 SQLite 테이블 구성을 설명하는 초안이다. 초기 minimal E2E 범위를 출발점으로 했지만, 현재는 metamodel registry 테이블과 운영 보조 테이블까지 포함한 상태를 반영한다.

## 1. 기본 원칙

- SQLite는 backend의 현재 기본 저장소다.
- 시간은 ISO 8601 문자열과 밀리초 정밀도를 사용한다.
- foreign key를 켜고 WAL 모드로 동작한다.
- `view` 구조와 `runtime` 데이터, `metamodel registry`를 한 저장소에서 관리하되 책임은 구분한다.

## 2. PRAGMA

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

## 3. 현재 주요 테이블

### 3.1 사용자/인증
- `users`

### 3.2 metamodel registry
- `metamodel_namespaces`
- `metamodel_versions`
- `semantic_types`
- `property_definitions`
- `association_definitions`
- `containment_rules`
- `palette_groups`
- `notation_definitions`

### 3.3 view/editor
- `views`
- `view_versions`
- `view_nodes`
- `view_edges`
- `view_version_nodes`
- `view_version_edges`

### 3.4 ingest/runtime
- `ingest_inbox`
- `processed_item_receipts`
- `latest_states`
- `raw_events`
- `debug_payload_logs`
- `cleanup_runs`

## 4. 핵심 DDL 포인트

### 4.1 view_nodes

현재 `view_nodes`는 단순 layout 테이블이 아니라, metamodel registry와 연결되는 persisted node 인스턴스다.

핵심 컬럼:
- `node_type`
- `semantic_type_code`
- `notation_code`
- `layer_order`
- `target_id`
- `style_json`

의미:
- `node_type`는 현재 코드의 기존 분기와 호환된다.
- `semantic_type_code`, `notation_code`는 metamodel registry 기반 표현과 연결된다.
- `layer_order`는 화면 렌더 순서를 backend가 관리하기 위한 값이다.

### 4.1.1 view_versions

핵심 컬럼:
- `view_id`
- `version_no`
- `version_code`
- `status`
- `based_on_version_id`
- `metamodel_version_id`
- `published_at`
- `activated_at`
- `revision`

의미:
- `views`는 logical root 로 유지하고, 실제 편집/운영 대상은 `view_versions` 로 분리한다.
- `status`는 `draft`, `published`, `active`, `deprecated` 를 가진다.
- `published`는 승인 대기/배포 후보 고정본, `active`는 실제 운영 중 버전이다.

### 4.1.2 view_version_nodes

핵심 컬럼:
- `view_version_id`
- `element_key`
- `parent_node_id`
- `semantic_type_code`
- `notation_code`
- `target_id`
- `layer_order`
- `properties_json`

의미:
- 특정 version snapshot 에 속한 node 구조와 layout 을 저장한다.
- `element_key`는 버전 간 동일 논리 객체를 잇는 안정 키다.

### 4.2 view_edges

핵심 컬럼:
- `edge_type`
- `semantic_type_code`
- `notation_code`
- `source_node_id`
- `target_node_id`
- `layer_order`
- `control_points_json`

의미:
- edge도 node와 동일하게 metamodel 식별자를 함께 저장한다.
- `x`, `y`보다 `anchor + control_points_json` 구조를 사용한다.

### 4.2.1 view_version_edges

핵심 컬럼:
- `view_version_id`
- `element_key`
- `association_code`
- `source_node_id`
- `target_node_id`
- `source_element_key`
- `target_element_key`
- `layer_order`

의미:
- 특정 version snapshot 에 속한 edge 를 저장한다.
- 현재 row id 와 별개로 `source_element_key`, `target_element_key` 를 두면 version 간 안정 참조에 유리하다.

### 4.3 ingest_inbox

핵심 컬럼:
- `agent_id`
- `boot_id`
- `seq_start`
- `seq_end`
- `payload_json`
- `status`
- `processed_at`
- `error_message`

의미:
- agent가 보낸 batch payload의 durable receipt queue다.
- `ack_seq`는 이 inbox 저장 완료를 기준으로 반환된다.

### 4.4 processed_item_receipts

의미:
- worker item-level idempotency 테이블
- `(agent_id, boot_id, item_seq)` unique로 중복 반영을 막는다.

### 4.5 latest_states

의미:
- monitoring overlay용 최신 상태 스냅샷
- `target_id + state_type` unique 기반 upsert

### 4.6 raw_events

의미:
- low-level event append-only 저장
- grouped event는 현재 후속 단계다.

### 4.7 debug_payload_logs

의미:
- debug mode에서만 저장되는 통신 payload 로그
- `agent <-> backend`, `backend <-> frontend` 흐름 디버깅용

### 4.8 cleanup_runs

의미:
- retention cleanup 실행 결과 기록
- 관리자 화면에서 최근 cleanup 결과를 조회할 수 있다.

## 5. 현재 스키마에서 중요한 제약

- `metamodel_versions.status`는 `draft`, `published`, `deprecated`만 허용한다.
- `semantic_types.kind`는 `node`, `edge`, `container`, `runtime-only`만 허용한다.
- `notation_definitions.render_primitive`는 현재 whitelist primitive만 허용한다.
- `view_nodes.node_type`와 `view_edges.edge_type`는 더 이상 하드코딩 집합으로 제한하지 않고, metamodel registry의 `semantic_type_code`와 함께 해석한다.
- `ingest_inbox.status`는 `pending`, `processing`, `processed`, `failed`만 허용한다.
- `latest_states.state_type`는 `process`, `agent`, `host`만 허용한다.
- `raw_events.event_type`는 현재 minimal/MVP 핵심 이벤트 집합만 허용한다.

## 6. 주요 인덱스 방향

- `views(owner_user_id, updated_at DESC)`
- `metamodel_versions(namespace_id, status)`
- `semantic_types(metamodel_version_id, code)`
- `property_definitions(semantic_type_id, sort_order, id)`
- `association_definitions(metamodel_version_id, code)`
- `containment_rules(metamodel_version_id, parent_type_id, child_type_id)`
- `palette_groups(metamodel_version_id, sort_order, id)`
- `notation_definitions(metamodel_version_id, semantic_type_id, sort_order, id)`
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
- `ingest_inbox(agent_id, boot_id, seq_start, seq_end)` UNIQUE
- `processed_item_receipts(agent_id, boot_id, item_seq)` UNIQUE
- `latest_states(target_id, state_type)` UNIQUE
- `raw_events(target_id, occurred_at DESC)`
- `raw_events(event_type, occurred_at DESC)`
- `debug_payload_logs(channel, occurred_at DESC)`
- `debug_payload_logs(trace_id, occurred_at DESC)`
- `cleanup_runs(finished_at DESC)`

## 7. seed 방향

- 기본 로그인은 `admin / admin123!`
- 기본 published metamodel version은 `seed-v1`
- demo view 1개를 seed한다.
- demo view용 `active` version snapshot 1개도 seed한다.
- demo view에는 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink`를 포함한다.
- seed node/edge도 `semantic_type_code`, `notation_code`를 함께 저장한다.
- `layer_order`는 seed 단계부터 명시해 초기 렌더 순서를 고정한다.
- `view_version_nodes`, `view_version_edges` 는 `element_key` 와 함께 seed해 이후 migration 입력으로 사용한다.

## 8. 구현 시 주의사항

- SQLite에도 transaction은 있다. 핵심은 어떤 단위로 commit/rollback 하느냐다.
- ingest ack는 `receipt ack`로 정의하고, worker 처리 성공과 분리해야 한다.
- agent 로컬 저장소도 SQLite를 계속 사용한다.
- backend cleanup은 `raw_events`, `debug_payload_logs`, `processed/failed ingest_inbox`에 대해 보존 정책을 적용한다.
- metamodel registry는 backend가 관리하고, frontend는 선언형 schema를 해석한다.

## 9. 현재 문서의 역할

- 이 문서는 지금 구현된 `db/schema.sql`을 사람이 읽기 쉬운 설계 문서로 요약한다.
- 이후 PostgreSQL 전환 시에도 도메인 구조를 유지하면서 저장소만 바꾸는 기준 문서로 쓸 수 있다.
