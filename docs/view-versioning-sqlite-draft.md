# Software Architecture Runtime Monitoring System

## View Versioning SQLite 확장 초안
버전: Draft 0.2  
작성일: 2026-04-16

목적: `draft / published / active / deprecated` 상태 모델과 이후 runtime identity 분리 계층을 SQLite 관점에서 어떻게 확장할지 정리한다.

참고 문서:
- [view-versioning-erd-draft.md](C:/2604_swacan_auto/docs/view-versioning-erd-draft.md)
- [view-versioning-api-draft.md](C:/2604_swacan_auto/docs/view-versioning-api-draft.md)
- [runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/runtime-identity-binding-design-draft.md)

## 1. 설계 목표

- 현재 `views`, `view_nodes`, `view_edges`를 즉시 제거하지 않고 점진 migration이 가능해야 한다.
- editor는 `draft`, monitoring은 `active` 기준으로 점진 전환한다.
- `published`는 승인 대기/배포 후보 고정본으로 유지한다.
- `target_id` 기반 compatibility를 유지하되, 장기적으로는 `monitored_objects`와 `node_bindings` 계층으로 전환한다.

## 2. 신규 테이블 초안

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
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_id) REFERENCES views(id) ON DELETE CASCADE,
    FOREIGN KEY (based_on_version_id) REFERENCES view_versions(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by_user_id) REFERENCES users(id),
    FOREIGN KEY (activated_by_user_id) REFERENCES users(id),
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id),
    UNIQUE (view_id, version_no)
);
```

운영 규칙:
- `view_id`별 `active`는 최대 1개
- MVP에서는 `view_id`별 `draft`도 최대 1개로 두는 편이 단순하다

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

메모:
- `target_id`는 compatibility용 binding key로 유지한다.
- 장기적으로는 `node_bindings`를 통해 monitored object와 연결한다.

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

## 3. runtime identity 분리용 후속 테이블 초안

이 테이블들은 MVP 후속 또는 점진 migration 단계에서 도입할 수 있다.

### 3.1 monitored_objects

```sql
CREATE TABLE IF NOT EXISTS monitored_objects (
    id INTEGER PRIMARY KEY,
    object_key TEXT NOT NULL UNIQUE,
    object_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    runtime_binding_key TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 3.2 node_bindings

```sql
CREATE TABLE IF NOT EXISTS node_bindings (
    id INTEGER PRIMARY KEY,
    view_version_node_id INTEGER NOT NULL,
    monitored_object_id INTEGER NOT NULL,
    binding_role TEXT NOT NULL DEFAULT 'primary',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_version_node_id) REFERENCES view_version_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE CASCADE,
    UNIQUE (view_version_node_id, monitored_object_id)
);
```

### 3.3 alert_instances

```sql
CREATE TABLE IF NOT EXISTS alert_instances (
    id INTEGER PRIMARY KEY,
    monitored_object_id INTEGER NOT NULL,
    alert_code TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    first_occurred_at TEXT NOT NULL,
    last_occurred_at TEXT NOT NULL,
    repeat_count INTEGER NOT NULL DEFAULT 1,
    latest_message TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE CASCADE
);
```

## 4. 기존 테이블과의 관계

### 4.1 views
- logical root로 계속 유지
- 사용자에게 보이는 화면 단위는 여전히 `views`

### 4.2 latest_states / raw_events
- 현재는 `target_id` 기반으로도 충분히 fan-out 가능하다
- 하지만 장기적으로는 `monitored_object_id` 기준으로 옮기는 편이 더 안정적이다

권장 전환 방향:
- 초기: `target_id` 유지
- 중간: `monitored_object_id` nullable 추가
- 후속: `monitored_object_id` 기준 주 경로 전환

## 5. 권장 인덱스

```sql
CREATE INDEX IF NOT EXISTS idx_view_versions_view_status
    ON view_versions(view_id, status);

CREATE INDEX IF NOT EXISTS idx_view_versions_view_version_no
    ON view_versions(view_id, version_no);

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

CREATE INDEX IF NOT EXISTS idx_monitored_objects_object_key
    ON monitored_objects(object_key);

CREATE INDEX IF NOT EXISTS idx_node_bindings_node
    ON node_bindings(view_version_node_id);

CREATE INDEX IF NOT EXISTS idx_node_bindings_object
    ON node_bindings(monitored_object_id);

CREATE INDEX IF NOT EXISTS idx_alert_instances_object_status
    ON alert_instances(monitored_object_id, status);
```

## 6. migration 순서 권장

### 6.1 1단계
- `view_versions`, `view_version_nodes`, `view_version_edges` 추가
- 기존 view를 initial active version으로 이관

### 6.2 2단계
- editor를 draft version 기준으로 전환
- monitoring을 active version 기준으로 전환

### 6.3 3단계
- `monitored_objects`, `node_bindings` 추가
- 새 view version node 생성 시 monitored object binding 생성 가능하도록 준비

### 6.4 4단계
- `latest_states`, `raw_events`, `alert_instances`를 monitored object 중심 구조로 점진 전환

## 7. 중요한 운영 원칙

- `published -> draft` 직접 상태 변경은 만들지 않는다
- 수정이 필요하면 `published 기반 새 draft 생성`
- alert/event/latest state는 장기적으로 node가 아니라 monitored object에 귀속한다
- 하나의 runtime 문제는 여러 active view에 fan-out되어 보여질 수 있지만, 저장과 생성은 한 번만 일어나야 한다

## 8. 요약

- `view_versions` 계층은 운영/편집 분리를 위한 핵심이다.
- `monitored_objects / node_bindings / alert_instances` 계층은 runtime identity 분리를 위한 핵심이다.
- 현재 SQLite 구조는 `target_id` compatibility를 유지하면서도, 이후 monitored object 기반 구조로 점진 이동할 수 있다.
