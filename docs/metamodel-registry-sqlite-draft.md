# Software Architecture Runtime Monitoring System

## 메타모델 Registry SQLite 테이블 초안
버전: Draft 0.1  
작성일: 2026-04-15

목적: 본 문서는 [metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/metamodel-notation-db-design-draft.md) 를 바탕으로, MVP 단계에서 추가될 메타모델 registry용 SQLite 테이블 구조를 초안 수준으로 정리한다.

참고 문서:

- [metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/metamodel-notation-db-design-draft.md)
- [sqlite-create-table-draft.md](C:/2604_swacan_auto/docs/sqlite-create-table-draft.md)
- [backend-detailed-requirements.md](C:/2604_swacan_auto/docs/backend-detailed-requirements.md)

## 1. 설계 범위

- 본 문서는 `metamodel` 과 `notation registry` 계층만 다룬다.
- `views`, `view_nodes`, `view_edges`, `latest_states`, `raw_events` 등 기존 minimal E2E runtime 테이블은 유지한다.
- MVP 전환 시에는 기존 architecture model 테이블과 메타모델 registry를 병행 운영하고, 이후 점진적으로 연결한다.

## 2. 기본 원칙

- SQLite에서는 JSON 전용 타입 대신 `TEXT` 컬럼에 JSON 문자열을 저장한다.
- 의미 규칙과 시각 표현 규칙은 서로 다른 테이블로 분리한다.
- 코드 기반 식별자와 정수 PK를 함께 사용한다.
- published 메타모델은 직접 수정하지 않고 새 draft 버전으로 파생한다.
- registry 테이블은 조회 중심으로 먼저 도입하고, 관리자 편집 기능은 후속 단계로 나눈다.

## 3. 신규 테이블 목록

권장 신규 테이블은 아래와 같다.

1. `metamodel_namespaces`
2. `metamodel_versions`
3. `semantic_types`
4. `property_definitions`
5. `association_definitions`
6. `containment_rules`
7. `palette_groups`
8. `notation_definitions`

## 4. 테이블 초안

### 4.1 metamodel_namespaces

역할:
- 메타모델의 논리적 구분 단위

```sql
CREATE TABLE IF NOT EXISTS metamodel_namespaces (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

예시 row:
- `core`
- `linux`
- `custom`

### 4.2 metamodel_versions

역할:
- namespace별 메타모델 버전 관리

```sql
CREATE TABLE IF NOT EXISTS metamodel_versions (
    id INTEGER PRIMARY KEY,
    namespace_id INTEGER NOT NULL,
    version_code TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'published', 'deprecated')),
    description TEXT,
    based_on_version_id INTEGER,
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (namespace_id) REFERENCES metamodel_namespaces(id) ON DELETE CASCADE,
    FOREIGN KEY (based_on_version_id) REFERENCES metamodel_versions(id),
    UNIQUE (namespace_id, version_code)
);
```

권장 인덱스:

```sql
CREATE INDEX IF NOT EXISTS idx_metamodel_versions_namespace_status
    ON metamodel_versions(namespace_id, status);
```

### 4.3 semantic_types

역할:
- node, edge, container 등 의미 타입 정의

```sql
CREATE TABLE IF NOT EXISTS semantic_types (
    id INTEGER PRIMARY KEY,
    metamodel_version_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('node', 'edge', 'container', 'runtime-only')),
    runtime_kind TEXT,
    is_groupable INTEGER NOT NULL DEFAULT 0 CHECK (is_groupable IN (0, 1)),
    allows_runtime_binding INTEGER NOT NULL DEFAULT 1 CHECK (allows_runtime_binding IN (0, 1)),
    default_notation_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id) ON DELETE CASCADE,
    UNIQUE (metamodel_version_id, code)
);
```

초기 seed 대상:
- `PhysicalServer`
- `VirtualMachine`
- `SoftwareProcess`
- `MonitoringAgent`
- `ExecutionThread`
- `CommunicationLink`
- `ProcessGroup`
- `ThreadPool`
- `ServerGroup`

### 4.4 property_definitions

역할:
- semantic type별 속성 정의

```sql
CREATE TABLE IF NOT EXISTS property_definitions (
    id INTEGER PRIMARY KEY,
    semantic_type_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    value_type TEXT NOT NULL CHECK (value_type IN ('string', 'integer', 'number', 'boolean', 'enum', 'json')),
    unit TEXT,
    default_value_json TEXT,
    is_required INTEGER NOT NULL DEFAULT 0 CHECK (is_required IN (0, 1)),
    is_runtime INTEGER NOT NULL DEFAULT 0 CHECK (is_runtime IN (0, 1)),
    is_user_editable INTEGER NOT NULL DEFAULT 1 CHECK (is_user_editable IN (0, 1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (semantic_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    UNIQUE (semantic_type_id, code)
);
```

### 4.5 association_definitions

역할:
- semantic type 간 관계 정의

```sql
CREATE TABLE IF NOT EXISTS association_definitions (
    id INTEGER PRIMARY KEY,
    metamodel_version_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    source_type_id INTEGER NOT NULL,
    target_type_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('directed', 'undirected')),
    multiplicity_source TEXT,
    multiplicity_target TEXT,
    semantics_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    FOREIGN KEY (target_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    UNIQUE (metamodel_version_id, code)
);
```

초기 seed 대상:
- `communicates_with`
- `monitors`
- `depends_on`

### 4.6 containment_rules

역할:
- 부모-자식 포함 관계 강제

```sql
CREATE TABLE IF NOT EXISTS containment_rules (
    id INTEGER PRIMARY KEY,
    metamodel_version_id INTEGER NOT NULL,
    parent_type_id INTEGER NOT NULL,
    child_type_id INTEGER NOT NULL,
    min_count INTEGER,
    max_count INTEGER,
    cardinality_scope TEXT NOT NULL DEFAULT 'group_total'
        CHECK (cardinality_scope IN ('group_total', 'per_member')),
    is_required INTEGER NOT NULL DEFAULT 0 CHECK (is_required IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    FOREIGN KEY (child_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    UNIQUE (metamodel_version_id, parent_type_id, child_type_id)
);
```

초기 seed 규칙 예시:
- `PhysicalServer -> VirtualMachine`
- `PhysicalServer -> SoftwareProcess`
- `PhysicalServer -> MonitoringAgent`
- `VirtualMachine -> SoftwareProcess`
- `VirtualMachine -> MonitoringAgent`
- `SoftwareProcess -> ExecutionThread`

### 4.7 palette_groups

역할:
- frontend palette 구분과 정렬

```sql
CREATE TABLE IF NOT EXISTS palette_groups (
    id INTEGER PRIMARY KEY,
    metamodel_version_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id) ON DELETE CASCADE,
    UNIQUE (metamodel_version_id, code)
);
```

예시:
- `servers`
- `processes`
- `monitoring`
- `communication`

### 4.8 notation_definitions

역할:
- semantic type의 기본 시각 표현 정의

```sql
CREATE TABLE IF NOT EXISTS notation_definitions (
    id INTEGER PRIMARY KEY,
    metamodel_version_id INTEGER NOT NULL,
    semantic_type_id INTEGER NOT NULL,
    palette_group_id INTEGER,
    code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('node', 'edge')),
    render_primitive TEXT NOT NULL CHECK (render_primitive IN ('rect', 'rounded_rect', 'line', 'badge', 'label')),
    render_schema_json TEXT NOT NULL,
    style_tokens_json TEXT,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    is_visible_in_palette INTEGER NOT NULL DEFAULT 1 CHECK (is_visible_in_palette IN (0, 1)),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (semantic_type_id) REFERENCES semantic_types(id) ON DELETE CASCADE,
    FOREIGN KEY (palette_group_id) REFERENCES palette_groups(id),
    UNIQUE (metamodel_version_id, code)
);
```

초기 notation 예시:
- `server.physical.rect`
- `vm.logical.rect`
- `process.rounded_rect`
- `agent.rounded_rect.double_border`
- `communication.line`

## 5. 기존 테이블과의 연결 방향

### 5.1 views

기존:
- `metamodel_version TEXT NOT NULL`

MVP 전환 권장:
- `metamodel_version_id INTEGER`
- 필요 시 기존 `metamodel_version`은 transition 기간 동안 유지

### 5.2 view_nodes

기존:
- `node_type TEXT`

MVP 전환 권장:
- `semantic_type_id INTEGER`
- `notation_definition_id INTEGER`

전환 전략:
- 1단계: `node_type` 유지 + 신규 FK 컬럼 병행
- 2단계: backend에서 dual-write
- 3단계: migration 완료 후 `node_type` 제거 검토

### 5.3 view_edges

기존:
- `edge_type TEXT`

MVP 전환 권장:
- `association_definition_id INTEGER`
- `notation_definition_id INTEGER`

## 6. Seed 데이터 방향

최초 published metamodel version은 `core / 1.0.0` 한 세트로 시작하는 것이 좋다.

기본 seed 예시:
- namespace: `core`
- version: `1.0.0`, `published`
- semantic types: `PhysicalServer`, `VirtualMachine`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink`
- palette groups: `servers`, `processes`, `monitoring`, `communication`
- notation definitions:
  - `PhysicalServer -> rect`
  - `VirtualMachine -> rect + dashed style`
  - `SoftwareProcess -> rounded_rect`
  - `MonitoringAgent -> rounded_rect + double_border`
  - `CommunicationLink -> line`

## 7. 권장 인덱스

다음 인덱스를 권장한다.

```sql
CREATE INDEX IF NOT EXISTS idx_semantic_types_version
    ON semantic_types(metamodel_version_id, code);

CREATE INDEX IF NOT EXISTS idx_property_definitions_type
    ON property_definitions(semantic_type_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_association_definitions_version
    ON association_definitions(metamodel_version_id, code);

CREATE INDEX IF NOT EXISTS idx_containment_rules_version_parent
    ON containment_rules(metamodel_version_id, parent_type_id);

CREATE INDEX IF NOT EXISTS idx_notation_definitions_version_type
    ON notation_definitions(metamodel_version_id, semantic_type_id, sort_order);
```

## 8. SQLite에서 주의할 점

- JSON 필드는 `TEXT` 이므로 backend validation이 중요하다.
- 메타모델 publish 시점에는 관련 레코드를 하나의 transaction으로 저장하는 것이 좋다.
- published 버전은 수정 금지 원칙을 애플리케이션 로직에서 강제해야 한다.
- SQLite에서는 partial unique constraint를 과도하게 쓰기보다, MVP에서는 애플리케이션 검증으로 보완하는 것이 더 단순할 수 있다.

## 9. PostgreSQL 전환을 고려한 포인트

- `render_schema_json`, `style_tokens_json`, `semantics_json`은 PostgreSQL에서 `JSONB`로 바로 옮길 수 있다.
- 정수 PK와 코드 기반 식별자를 함께 사용하는 구조는 PostgreSQL로도 그대로 유지 가능하다.
- 버전/namespace 분리 구조는 운영 환경에서 draft/published 관리에 유리하다.

## 10. 다음 단계

이 문서를 기준으로 다음을 이어서 진행하는 것이 좋다.

1. registry 조회 API 초안
2. `db/schema.sql`의 metamodel registry 확장 초안
3. 관리자 화면용 registry 조회 API
4. 현재 `views`, `view_nodes`, `view_edges`의 점진 migration 계획 구체화
