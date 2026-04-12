# Software Architecture Runtime Monitoring System

## SQLite CREATE TABLE 초안

버전: Draft 0.1
작성일: 2026-04-12
목적: 본 문서는 최소 E2E 구현을 위한 SQLite DDL 초안을 정의한다. 이 문서는 `minimal-erd-draft.md` 를 실제 테이블 생성 SQL 수준으로 구체화한 것이다.

## 1. 기본 원칙

- 본 초안은 최소 E2E 범위에 필요한 테이블만 포함한다.
- SQLite 를 사용하므로 타입은 실용적인 TEXT/INTEGER/REAL 중심으로 단순화한다.
- 시간 값은 밀리초(1/1000초) 단위 ISO 8601 문자열 저장을 기본으로 한다.
- `PRAGMA foreign_keys = ON;` 을 전제로 한다.

## 2. PRAGMA 초안

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
```

## 3. DDL 초안

### 3.1 users

```sql
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 3.2 views

```sql
CREATE TABLE IF NOT EXISTS views (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id TEXT NOT NULL,
    metamodel_version TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);
```

### 3.3 view_nodes

```sql
CREATE TABLE IF NOT EXISTS view_nodes (
    id TEXT PRIMARY KEY,
    view_id TEXT NOT NULL,
    parent_node_id TEXT,
    node_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    target_id TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    style_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_id) REFERENCES views(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_node_id) REFERENCES view_nodes(id) ON DELETE CASCADE,
    CHECK (node_type IN ('PhysicalServer', 'SoftwareProcess', 'MonitoringAgent', 'CommunicationLink'))
);
```

### 3.4 ingest_inbox

```sql
CREATE TABLE IF NOT EXISTS ingest_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    seq_start INTEGER NOT NULL,
    seq_end INTEGER NOT NULL,
    received_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    processed_at TEXT,
    error_message TEXT,
    CHECK (status IN ('pending', 'processing', 'processed', 'failed'))
);
```

### 3.5 latest_states

```sql
CREATE TABLE IF NOT EXISTS latest_states (
    id TEXT PRIMARY KEY,
    view_node_id TEXT,
    target_id TEXT NOT NULL,
    state_type TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT,
    state_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_node_id) REFERENCES view_nodes(id) ON DELETE SET NULL,
    CHECK (state_type IN ('process', 'agent'))
);
```

### 3.6 raw_events

```sql
CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    event_json TEXT,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    CHECK (event_type IN ('process_started', 'process_stopped', 'process_restarted', 'agent_heartbeat_lost'))
);
```

### 3.7 debug_payload_logs

```sql
CREATE TABLE IF NOT EXISTS debug_payload_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    direction TEXT NOT NULL,
    endpoint_or_topic TEXT NOT NULL,
    agent_id TEXT,
    user_id TEXT,
    session_id TEXT,
    trace_id TEXT,
    status_code INTEGER,
    payload_json TEXT NOT NULL,
    payload_size INTEGER NOT NULL,
    is_redacted INTEGER NOT NULL DEFAULT 1,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CHECK (direction IN ('request', 'response'))
);
```

## 4. 인덱스 초안

```sql
CREATE INDEX IF NOT EXISTS idx_views_owner_updated
    ON views(owner_user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_view_nodes_view_id
    ON view_nodes(view_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_parent_node_id
    ON view_nodes(parent_node_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_target_id
    ON view_nodes(target_id);

CREATE INDEX IF NOT EXISTS idx_ingest_inbox_status_received
    ON ingest_inbox(status, received_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_latest_states_target_state_type
    ON latest_states(target_id, state_type);

CREATE INDEX IF NOT EXISTS idx_raw_events_target_occurred
    ON raw_events(target_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_events_event_type_occurred
    ON raw_events(event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_debug_payload_logs_channel_occurred
    ON debug_payload_logs(channel, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_debug_payload_logs_trace_id_occurred
    ON debug_payload_logs(trace_id, occurred_at DESC);
```

## 5. Seed 데이터 초안 방향

- `users` 에는 최소 `admin` 계정 1개를 seed 한다.
- `views` 와 `view_nodes` 는 demo view 1개와 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent` 노드 3개를 seed 할 수 있다.
- `latest_states`, `raw_events`, `ingest_inbox`, `debug_payload_logs` 는 기본적으로 빈 상태로 시작한다.

## 6. 구현 시 주의사항

- `latest_states.id` 는 단순 PK 용 내부 식별자이지만, 실제 upsert 키는 `target_id + state_type` 를 사용한다.
- `payload_json`, `state_json`, `event_json`, `style_json` 은 최소 E2E 단계에서는 JSON TEXT 로 저장한다.
- `view_nodes` 에서 `CommunicationLink` 를 넣어두었지만, 최소 E2E 에서는 실제 사용하지 않아도 된다.
- grouped event 도입 시에는 `raw_events` 와 별도의 요약 테이블을 추가하는 것이 좋다.

## 7. 다음 단계 입력

- 이 문서를 기준으로 Flask 초기 DB 생성 스크립트를 작성할 수 있어야 한다.
- 이 문서를 기준으로 pytest fixture 에서 테스트용 DB 를 초기화할 수 있어야 한다.
- 이 문서를 기준으로 seed 스크립트 초안을 만들 수 있어야 한다.
