-- Default login: admin / admin123!

INSERT INTO users (
    id,
    username,
    password_hash,
    role,
    is_active,
    created_at,
    updated_at
) VALUES (
    1,
    'admin',
    'scrypt:32768:8:1$1E9IY1SSOJA4WLLL$037b286549ea05d116f801c379e320b9922771e5987ae33aa3403c6ebfc1cfad487a58637f2661b1a5efb00065c5ef6876d3a8ae12bd8e6d8bd1cbe8b4cf589f',
    'admin',
    1,
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
);

INSERT INTO views (
    id,
    name,
    description,
    owner_user_id,
    metamodel_version,
    revision,
    created_at,
    updated_at
) VALUES (
    1,
    'Demo View',
    'Minimal E2E demo view',
    1,
    'seed-v1',
    1,
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
);

INSERT INTO view_nodes (
    id,
    view_id,
    parent_node_id,
    node_type,
    display_name,
    target_id,
    x,
    y,
    width,
    height,
    is_deleted,
    style_json,
    created_at,
    updated_at
) VALUES
(
    101,
    1,
    NULL,
    'PhysicalServer',
    'Host A',
    NULL,
    40,
    40,
    480,
    260,
    0,
    '{"shape":"rect"}',
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
),
(
    102,
    1,
    101,
    'SoftwareProcess',
    'App Process',
    'app_main',
    80,
    90,
    160,
    56,
    0,
    '{"shape":"rounded-rect"}',
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
),
(
    103,
    1,
    101,
    'MonitoringAgent',
    'Local Agent',
    'agent_local',
    280,
    90,
    150,
    56,
    0,
    '{"shape":"rounded-rect","variant":"double-border"}',
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
);

INSERT INTO view_edges (
    id,
    view_id,
    edge_type,
    source_node_id,
    target_node_id,
    source_anchor,
    target_anchor,
    control_points_json,
    label,
    style_json,
    is_deleted,
    created_at,
    updated_at
) VALUES (
    201,
    1,
    'CommunicationLink',
    102,
    103,
    'right',
    'left',
    '[]',
    'agent link',
    '{"strokeStyle":"solid"}',
    0,
    '2026-04-12T10:00:00.000+09:00',
    '2026-04-12T10:00:00.000+09:00'
);
