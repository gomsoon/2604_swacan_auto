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

CREATE TABLE IF NOT EXISTS metamodel_namespaces (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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
    FOREIGN KEY (metamodel_version_id) REFERENCES metamodel_versions(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by_user_id) REFERENCES users(id),
    FOREIGN KEY (activated_by_user_id) REFERENCES users(id),
    FOREIGN KEY (lock_owner_user_id) REFERENCES users(id),
    UNIQUE (view_id, version_no)
);

CREATE TABLE IF NOT EXISTS view_nodes (
    id INTEGER PRIMARY KEY,
    view_id INTEGER NOT NULL,
    parent_node_id INTEGER,
    node_type TEXT NOT NULL CHECK (node_type IN ('PhysicalServer', 'SoftwareProcess', 'MonitoringAgent')),
    semantic_type_code TEXT NOT NULL,
    notation_code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    target_id TEXT,
    layer_order INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS view_version_nodes (
    id INTEGER PRIMARY KEY,
    view_version_id INTEGER NOT NULL,
    element_key TEXT NOT NULL,
    parent_node_id INTEGER,
    node_type TEXT NOT NULL CHECK (node_type IN ('PhysicalServer', 'SoftwareProcess', 'MonitoringAgent')),
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

CREATE TABLE IF NOT EXISTS view_edges (
    id INTEGER PRIMARY KEY,
    view_id INTEGER NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN ('CommunicationLink')),
    semantic_type_code TEXT NOT NULL,
    notation_code TEXT NOT NULL,
    source_node_id INTEGER NOT NULL,
    target_node_id INTEGER NOT NULL,
    layer_order INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS view_version_edges (
    id INTEGER PRIMARY KEY,
    view_version_id INTEGER NOT NULL,
    element_key TEXT NOT NULL,
    edge_type TEXT NOT NULL CHECK (edge_type IN ('CommunicationLink')),
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

CREATE TABLE IF NOT EXISTS alert_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitored_object_id INTEGER NOT NULL,
    alert_code TEXT NOT NULL,
    source_rule_id INTEGER,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    acknowledged_at TEXT,
    acknowledged_by_user_id INTEGER,
    ack_note TEXT,
    first_occurred_at TEXT NOT NULL,
    last_occurred_at TEXT NOT NULL,
    repeat_count INTEGER NOT NULL DEFAULT 1,
    latest_message TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE CASCADE,
    FOREIGN KEY (source_rule_id) REFERENCES alert_rules(id) ON DELETE SET NULL,
    FOREIGN KEY (acknowledged_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('object_type', 'monitored_object')),
    object_type TEXT,
    monitored_object_id INTEGER,
    state_type TEXT NOT NULL CHECK (state_type IN ('process', 'agent', 'host')),
    metric_key TEXT NOT NULL,
    comparison TEXT NOT NULL CHECK (comparison IN ('gte', 'lte')),
    warning_threshold REAL,
    critical_threshold REAL,
    is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE CASCADE
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

CREATE TABLE IF NOT EXISTS processed_item_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    item_seq INTEGER NOT NULL,
    payload_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    inbox_id INTEGER NOT NULL,
    processed_at TEXT NOT NULL,
    FOREIGN KEY (inbox_id) REFERENCES ingest_inbox(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS latest_states (
    id INTEGER PRIMARY KEY,
    view_node_id INTEGER,
    monitored_object_id INTEGER,
    target_id TEXT NOT NULL,
    state_type TEXT NOT NULL CHECK (state_type IN ('process', 'agent', 'host')),
    status TEXT NOT NULL,
    severity TEXT,
    state_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (view_node_id) REFERENCES view_nodes(id) ON DELETE SET NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    monitored_object_id INTEGER,
    target_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('process_started', 'process_stopped', 'process_restarted', 'agent_heartbeat_lost')),
    severity TEXT NOT NULL,
    message TEXT,
    event_json TEXT,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS grouped_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitored_object_id INTEGER,
    target_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('process_started', 'process_stopped', 'process_restarted', 'agent_heartbeat_lost')),
    severity TEXT NOT NULL,
    first_occurred_at TEXT NOT NULL,
    last_occurred_at TEXT NOT NULL,
    repeat_count INTEGER NOT NULL DEFAULT 1,
    latest_message TEXT,
    latest_event_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (monitored_object_id) REFERENCES monitored_objects(id) ON DELETE SET NULL
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

CREATE TABLE IF NOT EXISTS cleanup_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    raw_events_deleted INTEGER NOT NULL,
    grouped_events_deleted INTEGER NOT NULL,
    debug_payload_logs_deleted INTEGER NOT NULL,
    ingest_inbox_deleted INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_views_owner_updated
    ON views(owner_user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_metamodel_versions_namespace_status
    ON metamodel_versions(namespace_id, status);

CREATE INDEX IF NOT EXISTS idx_semantic_types_version_code
    ON semantic_types(metamodel_version_id, code);

CREATE INDEX IF NOT EXISTS idx_property_definitions_type_sort
    ON property_definitions(semantic_type_id, sort_order, id);

CREATE INDEX IF NOT EXISTS idx_association_definitions_version_code
    ON association_definitions(metamodel_version_id, code);

CREATE INDEX IF NOT EXISTS idx_containment_rules_version_parent
    ON containment_rules(metamodel_version_id, parent_type_id, child_type_id);

CREATE INDEX IF NOT EXISTS idx_palette_groups_version_sort
    ON palette_groups(metamodel_version_id, sort_order, id);

CREATE INDEX IF NOT EXISTS idx_notation_definitions_version_type_sort
    ON notation_definitions(metamodel_version_id, semantic_type_id, sort_order, id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_view_id
    ON view_nodes(view_id);

CREATE INDEX IF NOT EXISTS idx_view_versions_view_status
    ON view_versions(view_id, status);

CREATE INDEX IF NOT EXISTS idx_view_versions_view_version_no
    ON view_versions(view_id, version_no);

CREATE INDEX IF NOT EXISTS idx_view_versions_based_on
    ON view_versions(based_on_version_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_parent_node_id
    ON view_nodes(parent_node_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_target_id
    ON view_nodes(target_id);

CREATE INDEX IF NOT EXISTS idx_view_nodes_view_layer
    ON view_nodes(view_id, layer_order, id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_parent
    ON view_version_nodes(view_version_id, parent_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_target
    ON view_version_nodes(view_version_id, target_id);

CREATE INDEX IF NOT EXISTS idx_view_version_nodes_version_layer
    ON view_version_nodes(view_version_id, layer_order, id);

CREATE INDEX IF NOT EXISTS idx_view_edges_view_id
    ON view_edges(view_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_source_node_id
    ON view_edges(source_node_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_target_node_id
    ON view_edges(target_node_id);

CREATE INDEX IF NOT EXISTS idx_view_edges_view_layer
    ON view_edges(view_id, layer_order, id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_source
    ON view_version_edges(view_version_id, source_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_target
    ON view_version_edges(view_version_id, target_node_id);

CREATE INDEX IF NOT EXISTS idx_view_version_edges_version_layer
    ON view_version_edges(view_version_id, layer_order, id);

CREATE INDEX IF NOT EXISTS idx_monitored_objects_object_key
    ON monitored_objects(object_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_monitored_objects_runtime_binding_key
    ON monitored_objects(runtime_binding_key)
    WHERE runtime_binding_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_node_bindings_view_version_node
    ON node_bindings(view_version_node_id);

CREATE INDEX IF NOT EXISTS idx_alert_rules_scope_state
    ON alert_rules(scope_type, state_type, is_enabled);

CREATE INDEX IF NOT EXISTS idx_alert_instances_source_rule_status
    ON alert_instances(source_rule_id, status);

CREATE INDEX IF NOT EXISTS idx_node_bindings_monitored_object
    ON node_bindings(monitored_object_id);

CREATE INDEX IF NOT EXISTS idx_ingest_inbox_status_received
    ON ingest_inbox(status, received_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ingest_inbox_agent_boot_seq_range
    ON ingest_inbox(agent_id, boot_id, seq_start, seq_end);

CREATE UNIQUE INDEX IF NOT EXISTS uq_processed_item_receipts_agent_boot_seq
    ON processed_item_receipts(agent_id, boot_id, item_seq);

CREATE INDEX IF NOT EXISTS idx_processed_item_receipts_inbox_id
    ON processed_item_receipts(inbox_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_latest_states_target_state_type
    ON latest_states(target_id, state_type);

CREATE INDEX IF NOT EXISTS idx_latest_states_monitored_object_state_type
    ON latest_states(monitored_object_id, state_type);

CREATE INDEX IF NOT EXISTS idx_raw_events_target_occurred
    ON raw_events(target_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_events_monitored_object_occurred
    ON raw_events(monitored_object_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_events_event_type_occurred
    ON raw_events(event_type, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_grouped_events_target_type_occurred
    ON grouped_events(target_id, event_type, severity, last_occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_grouped_events_monitored_object_occurred
    ON grouped_events(monitored_object_id, event_type, severity, last_occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_debug_payload_logs_channel_occurred
    ON debug_payload_logs(channel, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_debug_payload_logs_trace_id_occurred
    ON debug_payload_logs(trace_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_cleanup_runs_finished_at
    ON cleanup_runs(finished_at DESC);
