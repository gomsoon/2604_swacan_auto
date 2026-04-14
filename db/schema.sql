PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS views (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id INTEGER NOT NULL,
    metamodel_version TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS view_nodes (
    id INTEGER PRIMARY KEY,
    view_id INTEGER NOT NULL,
    parent_node_id INTEGER,
    node_type TEXT NOT NULL CHECK (node_type IN ('PhysicalServer', 'SoftwareProcess', 'MonitoringAgent')),
    display_name TEXT NOT NULL,
    target_id TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    style_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_id) REFERENCES views(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_node_id) REFERENCES view_nodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS view_edges (
    id INTEGER PRIMARY KEY,
    view_id INTEGER NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN ('CommunicationLink')),
    source_node_id INTEGER NOT NULL,
    target_node_id INTEGER NOT NULL,
    source_anchor TEXT,
    target_anchor TEXT,
    control_points_json TEXT,
    label TEXT,
    style_json TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_id) REFERENCES views(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES view_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES view_nodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ingest_inbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    seq_start INTEGER NOT NULL,
    seq_end INTEGER NOT NULL,
    received_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'processed', 'failed')),
    processed_at TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS latest_states (
    id INTEGER PRIMARY KEY,
    view_node_id INTEGER,
    target_id TEXT NOT NULL,
    state_type TEXT NOT NULL CHECK (state_type IN ('process', 'agent', 'host')),
    status TEXT NOT NULL,
    severity TEXT,
    state_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_node_id) REFERENCES view_nodes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('process_started', 'process_stopped', 'process_restarted', 'agent_heartbeat_lost')),
    severity TEXT NOT NULL,
    message TEXT,
    event_json TEXT,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS debug_payload_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('request', 'response')),
    endpoint_or_topic TEXT NOT NULL,
    agent_id TEXT,
    user_id INTEGER,
    session_id TEXT,
    trace_id TEXT,
    status_code INTEGER,
    payload_json TEXT NOT NULL,
    payload_size INTEGER NOT NULL,
    is_redacted INTEGER NOT NULL DEFAULT 1 CHECK (is_redacted IN (0, 1)),
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_views_owner_updated
    ON views(owner_user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_view_nodes_view_id
    ON view_nodes(view_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_parent_node_id
    ON view_nodes(parent_node_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_target_id
    ON view_nodes(target_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_view_id
    ON view_edges(view_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_source_node_id
    ON view_edges(source_node_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_target_node_id
    ON view_edges(target_node_id);

CREATE INDEX IF NOT EXISTS idx_ingest_inbox_status_received
    ON ingest_inbox(status, received_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ingest_inbox_agent_boot_seq_range
    ON ingest_inbox(agent_id, boot_id, seq_start, seq_end);

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
