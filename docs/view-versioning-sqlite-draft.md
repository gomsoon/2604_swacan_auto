# Software Architecture Runtime Monitoring System

## View Versioning SQLite 확장 초안

버전: Draft 0.1  
작성일: 2026-04-15

목적: `draft / published / active / deprecated` 상태 모델을 SQLite 스키마 관점으로 구체화한다. 이 문서는 향후 `db/schema.sql` 확장과 migration 작업의 기준 초안으로 사용한다.

참고 문서:
- [view-versioning-erd-draft.md](C:/2604_swacan_auto/docs/view-versioning-erd-draft.md)
- [view-versioning-api-draft.md](C:/2604_swacan_auto/docs/view-versioning-api-draft.md)
- [sqlite-create-table-draft.md](C:/2604_swacan_auto/docs/sqlite-create-table-draft.md)

## 1. 설계 목표

- 현재 `views`, `view_nodes`, `view_edges` 구조를 즉시 버리지 않고, 점진 migration 이 가능한 형태로 versioning 테이블을 추가한다.
- 운영 중 monitoring 은 `active` version 만 읽도록 만들고, editor 는 `draft` version 만 저장하도록 유도한다.
- `published` 는 편집 완료된 고정본으로 두고, `active` 는 승인 완료된 운영 버전으로 구분한다.
- row id 와 별개로 버전 간 논리 객체를 이어주는 `element_key` 를 도입한다.

## 2. 신규 권장 테이블

### 2.1 view_versions

```sql
CREATE TABLE IF NOT EXISTS view_versions (
    id INTEGER PRIMARY KEY,
    view_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    version_code TEXT,
    status TEXT NOT NULL CHECK (status IN ('draft', 'published', 'active', 'deprecated')),
    based_on_version_id INTEGER,
    metamodel_version_id INTEGER,
    created_by_user_id INTEGER NOT NULL,
    approved_by_user_id INTEGER,
    activated_by_user_id INTEGER,
    description TEXT,
    published_at TEXT,
    activated_at TEXT,
    is_edit_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_edit_locked IN (0, 1)),
    lock_owner_user_id INTEGER,
    lock_acquired_at TEXT,
    lock_expires_at TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_id) REFERENCES views(id) ON DELETE CASCADE,
    FOREIGN KEY (based_on_version_id) REFERENCES view_versions(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by_user_id) REFERENCES users(id),
    FOREIGN KEY (activated_by_user_id) REFERENCES users(id),
    FOREIGN KEY (lock_owner_user_id) REFERENCES users(id),
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id),
    UNIQUE (view_id, version_no)
);
```

설계 메모:
- MVP 에서는 `view_id` 당 active 1개만 허용하는 운영 정책을 애플리케이션 레벨에서 먼저 강제하는 것이 단순하다.
- SQLite partial unique index 사용 여부는 후속 구현 단계에서 판단할 수 있다.

### 2.2 view_version_nodes

```sql
CREATE TABLE IF NOT EXISTS view_version_nodes (
    id INTEGER PRIMARY KEY,
    view_version_id INTEGER NOT NULL,
    element_key TEXT NOT NULL,
    parent_node_id INTEGER,
    node_type TEXT NOT NULL,
    semantic_type_code TEXT NOT NULL,
    notation_code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    target_id TEXT,
    instance_mode TEXT,
    cardinality_scope TEXT,
    expected_min INTEGER,
    expected_max INTEGER,
    layer_order INTEGER NOT NULL DEFAULT 0,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    collapsed_state INTEGER NOT NULL DEFAULT 0 CHECK (collapsed_state IN (0, 1)),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    style_json TEXT,
    properties_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_version_id) REFERENCES view_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_node_id) REFERENCES view_version_nodes(id) ON DELETE CASCADE,
    UNIQUE (view_version_id, element_key)
);
```

### 2.3 view_version_edges

```sql
CREATE TABLE IF NOT EXISTS view_version_edges (
    id INTEGER PRIMARY KEY,
    view_version_id INTEGER NOT NULL,
    element_key TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    association_code TEXT,
    semantic_type_code TEXT NOT NULL,
    notation_code TEXT NOT NULL,
    source_node_id INTEGER NOT NULL,
    target_node_id INTEGER NOT NULL,
    source_element_key TEXT,
    target_element_key TEXT,
    layer_order INTEGER NOT NULL DEFAULT 0,
    source_anchor TEXT,
    target_anchor TEXT,
    control_points_json TEXT,
    label TEXT,
    style_json TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_version_id) REFERENCES view_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES view_version_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES view_version_nodes(id) ON DELETE CASCADE,
    UNIQUE (view_version_id, element_key)
);
```

## 3. 기존 테이블과의 관계

### 3.1 views
- 계속 logical root 로 유지
- 현재 `revision` 은 장기적으로 `view_versions.revision` 으로 이동 가능
- 현재 `metamodel_version` 문자열은 `view_versions.metamodel_version_id` 기준으로 대체 가능

### 3.2 view_nodes / view_edges
- 즉시 삭제하지 않음
- migration 전환 기간 동안 compatibility layer 로 유지 가능
- 초기에는 “현재 active snapshot”의 legacy 저장소처럼 볼 수 있음

## 4. 권장 인덱스

```sql
CREATE INDEX IF NOT EXISTS idx_view_versions_view_status
    ON view_versions(view_id, status);

CREATE INDEX IF NOT EXISTS idx_view_versions_view_version_no
    ON view_versions(view_id, version_no);

CREATE INDEX IF NOT EXISTS idx_view_versions_based_on
    ON view_versions(based_on_version_id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_parent
    ON view_version_nodes(view_version_id, parent_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_target
    ON view_version_nodes(view_version_id, target_id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_layer
    ON view_version_nodes(view_version_id, layer_order, id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_source
    ON view_version_edges(view_version_id, source_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_target
    ON view_version_edges(view_version_id, target_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_layer
    ON view_version_edges(view_version_id, layer_order, id);
```

## 5. 권장 migration 순서

### 5.1 1단계
- `view_versions` 추가
- 각 기존 `views` 마다 initial active version 생성

### 5.2 2단계
- `view_version_nodes`, `view_version_edges` 추가
- 기존 `view_nodes`, `view_edges` 를 initial active version 으로 이관

### 5.3 3단계
- editor API 는 draft version 저장으로 전환
- monitoring API 는 active version 조회로 전환

### 5.4 4단계
- publish / activate / clone-to-draft API 구현
- 필요 시 기존 `view_nodes`, `view_edges` 제거 또는 read-only compatibility 유지

## 6. runtime binding 연결 메모

- `latest_states.view_node_id` 같은 현재 구조는 version snapshot row 와 직접 결합될 수 있다
- 장기적으로는 `element_key + target_id` 기반 overlay 연결이 더 안정적이다
- 초기 migration 단계에서는 기존 `view_node_id` 경로와 `target_id` 경로를 병행하는 전략이 현실적이다

## 7. 구현 시 주의사항

- `published -> draft` 직접 상태 변경은 만들지 않는다
- 수정이 필요하면 `clone-to-draft` 로 새 draft 생성
- active 전환 시 기존 active 를 `deprecated` 로 내릴지 `published` 로 되돌릴지는 운영 정책으로 확정 필요
- MVP 초기에는 `deprecated` 로 내리는 쪽이 더 단순하다

## 8. 요약

- SQLite 에서는 `view_versions`, `view_version_nodes`, `view_version_edges` 추가만으로 운영/편집 분리의 핵심 구조를 잡을 수 있다
- 기존 `views`, `view_nodes`, `view_edges` 와의 compatibility 기간을 두는 것이 migration 리스크를 줄인다
- 이 문서는 다음 단계인 실제 `schema.sql` 변경 초안의 직접 입력으로 사용할 수 있다
