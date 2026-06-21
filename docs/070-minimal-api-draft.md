# Software Architecture Runtime Monitoring System

## 최소 API 명세 초안

버전: Draft 0.2  
작성일: 2026-04-15

목적: 본 문서는 현재 구현된 minimal end-to-end와 metamodel registry 조회 기능을 기준으로, 핵심 backend API 계약을 간결하게 정리한 초안이다. 전체 MVP API가 아니라, 지금 코드에서 이미 동작하거나 바로 이어서 확장될 수 있는 최소 계약을 대상으로 한다.

## 1. 설계 원칙

- API는 JSON 기반으로 단순하게 유지한다.
- ingest ack는 item 처리 완료가 아니라 `ingest_inbox` 영속 저장 완료를 뜻한다.
- editor와 monitoring은 같은 `view` 구조를 공유한다.
- metamodel registry는 backend가 제공하고 frontend가 해석하는 선언형 구조를 따른다.

## 2. 인증 API

### 2.1 로그인

- Method: `POST`
- Path: `/api/auth/login`

Request JSON:
```json
{
  "username": "admin",
  "password": "admin123!"
}
```

Response JSON 200:
```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### 2.2 로그아웃

- Method: `POST`
- Path: `/api/auth/logout`

Response JSON 200:
```json
{
  "ok": true
}
```

## 3. View API

### 3.1 view 목록 조회

- Method: `GET`
- Path: `/api/views`

Response JSON 200:
```json
{
  "items": [
    {
      "id": 1,
      "name": "Demo View",
      "description": "Minimal E2E demo view",
      "revision": 1,
      "updated_at": "2026-04-12T10:00:00.000+09:00"
    }
  ]
}
```

### 3.2 view 상세 조회

- Method: `GET`
- Path: `/api/views/{view_id}`

Response JSON 200:
```json
{
  "view": {
    "id": 1,
    "name": "Demo View",
    "revision": 1,
    "metamodel_version": "seed-v1"
  },
  "nodes": [
    {
      "id": 101,
      "parent_node_id": null,
      "node_type": "PhysicalServer",
      "semantic_type_code": "PhysicalServer",
      "notation_code": "server.physical.rect",
      "display_name": "Host A",
      "target_id": null,
      "layer_order": 10,
      "x": 40,
      "y": 40,
      "width": 480,
      "height": 260,
      "style": {
        "shape": "rect"
      }
    }
  ],
  "edges": [
    {
      "id": 201,
      "edge_type": "CommunicationLink",
      "semantic_type_code": "CommunicationLink",
      "notation_code": "communication.line",
      "source_node_id": 102,
      "target_node_id": 103,
      "layer_order": 10,
      "source_anchor": "right",
      "target_anchor": "left",
      "control_points": [],
      "label": "agent link"
    }
  ]
}
```

### 3.3 view 생성

- Method: `POST`
- Path: `/api/views`

Request JSON:
```json
{
  "name": "New View",
  "description": "Created in API test"
}
```

Response JSON 201:
```json
{
  "view": {
    "id": 2,
    "name": "New View",
    "revision": 1
  }
}
```

### 3.4 view 전체 저장

- Method: `PUT`
- Path: `/api/views/{view_id}`

Request JSON:
```json
{
  "revision": 1,
  "nodes": [
    {
      "id": 101,
      "parent_node_id": null,
      "node_type": "PhysicalServer",
      "semantic_type_code": "PhysicalServer",
      "notation_code": "server.physical.rect",
      "display_name": "Host A",
      "target_id": null,
      "layer_order": 10,
      "x": 40,
      "y": 40,
      "width": 480,
      "height": 260
    }
  ],
  "edges": []
}
```

Response JSON 200:
```json
{
  "ok": true,
  "revision": 2,
  "updated_at": "2026-04-15T09:30:00.000+09:00"
}
```

비고:
- `revision` mismatch 시 `409`를 반환한다.
- `node_type`와 `semantic_type_code`, `notation_code` 조합이 맞지 않으면 validation error를 반환한다.

## 4. Editor Unit API

### 4.1 node 생성

- Method: `POST`
- Path: `/api/views/{view_id}/nodes`

Request JSON 예:
```json
{
  "revision": 1,
  "node_type": "SoftwareProcess",
  "semantic_type_code": "SoftwareProcess",
  "notation_code": "process.rounded_rect",
  "parent_node_id": 101,
  "display_name": "Worker Process",
  "target_id": "worker_1",
  "x": 90,
  "y": 170,
  "width": 160,
  "height": 56,
  "style": {
    "shape": "rounded-rect"
  }
}
```

Response JSON 201:
```json
{
  "node": {
    "id": 104,
    "node_type": "SoftwareProcess",
    "semantic_type_code": "SoftwareProcess",
    "notation_code": "process.rounded_rect",
    "display_name": "Worker Process",
    "target_id": "worker_1",
    "layer_order": 40,
    "x": 90,
    "y": 170,
    "width": 160,
    "height": 56,
    "style": {
      "shape": "rounded-rect"
    }
  },
  "revision": 2,
  "updated_at": "2026-04-15T09:31:00.000+09:00"
}
```

### 4.2 node 수정

- Method: `PATCH`
- Path: `/api/views/{view_id}/nodes/{node_id}`

### 4.3 node 삭제

- Method: `DELETE`
- Path: `/api/views/{view_id}/nodes/{node_id}`

### 4.4 edge 생성

- Method: `POST`
- Path: `/api/views/{view_id}/edges`

Request JSON 예:
```json
{
  "revision": 2,
  "edge_type": "CommunicationLink",
  "semantic_type_code": "CommunicationLink",
  "notation_code": "communication.line",
  "source_node_id": 102,
  "target_node_id": 104,
  "source_anchor": "right",
  "target_anchor": "left",
  "control_points": [],
  "label": "new edge"
}
```

Response JSON 201:
```json
{
  "edge": {
    "id": 202,
    "edge_type": "CommunicationLink",
    "semantic_type_code": "CommunicationLink",
    "notation_code": "communication.line",
    "source_node_id": 102,
    "target_node_id": 104,
    "layer_order": 20,
    "source_anchor": "right",
    "target_anchor": "left",
    "control_points": [],
    "label": "new edge"
  },
  "revision": 3,
  "updated_at": "2026-04-15T09:32:00.000+09:00"
}
```

### 4.5 edge 수정

- Method: `PATCH`
- Path: `/api/views/{view_id}/edges/{edge_id}`

### 4.6 edge 삭제

- Method: `DELETE`
- Path: `/api/views/{view_id}/edges/{edge_id}`

## 5. Monitoring 조회 API

### 5.1 latest state 조회

- Method: `GET`
- Path: `/api/views/{view_id}/latest-state`

Response JSON 200:
```json
{
  "items": [
    {
      "target_id": "app_main",
      "state_type": "process",
      "status": "up",
      "severity": "normal",
      "occurred_at": "2026-04-10T10:20:00.100+09:00",
      "received_at": "2026-04-10T10:20:00.220+09:00",
      "state": {
        "pid": 1234,
        "cpu_usage": 3.2,
        "memory_rss": 10485760
      }
    }
  ]
}
```

### 5.2 recent event 조회

- Method: `GET`
- Path: `/api/views/{view_id}/events?limit=20`

Response JSON 200:
```json
{
  "items": [
    {
      "id": 101,
      "target_id": "app_main",
      "event_type": "process_stopped",
      "severity": "warning",
      "message": "process not found",
      "occurred_at": "2026-04-10T10:21:10.100+09:00",
      "received_at": "2026-04-10T10:21:10.230+09:00"
    }
  ]
}
```

## 6. Agent ingest API

### 6.1 batch ingest

- Method: `POST`
- Path: `/api/agents/ingest`

Request JSON:
```json
{
  "agent_id": "agent_local",
  "boot_id": "boot_001",
  "seq_start": 10,
  "seq_end": 12,
  "sent_at": "2026-04-10T10:20:00.150+09:00",
  "items": [
    {
      "seq": 10,
      "payload_type": "agent_state",
      "occurred_at": "2026-04-10T10:20:00.100+09:00",
      "target_id": "agent_local",
      "payload": {
        "heartbeat_time": "2026-04-10T10:20:00.100+09:00",
        "outbox_queue_depth": 0,
        "backend_connection_status": "connected"
      }
    }
  ]
}
```

Response JSON 202:
```json
{
  "ack_seq": 12,
  "accepted_count": 3,
  "server_time": "2026-04-10T10:20:00.220+09:00"
}
```

중요한 의미:
- `ack_seq`는 item 처리 성공 ack가 아니다.
- `ack_seq`는 batch가 `ingest_inbox`에 영속 저장되었다는 receipt ack다.
- 이후 `latest_states`, `raw_events` 반영은 worker가 처리한다.

## 7. Metamodel Registry 조회 API

### 7.1 published versions

- Method: `GET`
- Path: `/api/metamodel/versions/published`

### 7.2 version detail

- Method: `GET`
- Path: `/api/metamodel/versions/{id}`

### 7.3 palette

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/palette`

### 7.4 semantic types

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/semantic-types`

### 7.5 properties

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/semantic-types/{type_code}/properties`

### 7.6 containment rules

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/containment-rules`

### 7.7 associations

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/associations`

### 7.8 notations

- Method: `GET`
- Path: `/api/metamodel/versions/{id}/notations`

## 8. Admin API

현재 구현된 핵심 read-only API:
- `GET /api/admin/summary`
- `GET /api/admin/ingest-inbox`
- `GET /api/admin/latest-states`
- `GET /api/admin/raw-events`
- `GET /api/admin/debug-payloads`
- `GET /api/admin/cleanup-runs`

## 9. 공통 오류 응답

Error JSON:
```json
{
  "error": {
    "code": "validation_error",
    "message": "containment rule violated"
  }
}
```

공통 규칙:
- 시간값은 ISO 8601 문자열로 반환한다.
- 밀리초(1/1000초) 단위까지 유지한다.
- 인증 실패는 `401`, 권한 실패는 `403`, revision 충돌은 `409`, 입력 오류는 `400`을 사용한다.
