# Software Architecture Runtime Monitoring System

## 최소 API 명세 초안

버전: Draft 0.1
작성일: 2026-04-10
목적: 본 문서는 최소 E2E 구현에 필요한 backend API 계약을 정의한다. 본 문서는 전체 MVP API 가 아니라, `로그인 -> view 저장 -> agent ingest -> monitoring 조회 -> raw event 조회 -> debug payload 저장` 흐름에 필요한 최소 범위만 다룬다.

## 1. 설계 원칙

- [필수] API 는 최소 E2E 구현에 필요한 범위로만 제한한다.
- [필수] request/response 는 단순 JSON 구조를 우선한다.
- [필수] backend ingest ack 는 처리 완료가 아니라 durable receive 완료 의미로 정의한다.
- [필수] grouped event, 동적 metamodel 편집, 관리자 전체 API 는 이후 확장으로 미룬다.

## 2. 인증 API

### 2.1 로그인

- Method: `POST`
- Path: `/api/auth/login`
- 목적: 사용자 로그인과 세션 시작

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

오류:
- `401`: 잘못된 계정 정보
- `400`: 필수 필드 누락

### 2.2 로그아웃

- Method: `POST`
- Path: `/api/auth/logout`
- 목적: 세션 종료

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
- 목적: 로그인 사용자가 접근 가능한 최소 view 목록 조회

Response JSON 200:
```json
{
  "items": [
    {
      "id": 1,
      "name": "Demo View",
      "description": "Minimal E2E view",
      "revision": 1,
      "updated_at": "2026-04-10T10:00:00.123+09:00"
    }
  ]
}
```

### 3.2 view 상세 조회

- Method: `GET`
- Path: `/api/views/{view_id}`
- 목적: editor 와 monitoring 가 공유할 view 구조 조회

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
      "display_name": "Host A",
      "target_id": null,
      "x": 40,
      "y": 40,
      "width": 480,
      "height": 260
    },
    {
      "id": 102,
      "parent_node_id": 101,
      "node_type": "SoftwareProcess",
      "display_name": "App Process",
      "target_id": "app_main",
      "x": 80,
      "y": 90,
      "width": 160,
      "height": 56
    },
    {
      "id": 103,
      "parent_node_id": 101,
      "node_type": "MonitoringAgent",
      "display_name": "Local Agent",
      "target_id": "agent_local",
      "x": 280,
      "y": 90,
      "width": 150,
      "height": 56
    }
  ],
  "edges": [
    {
      "id": 201,
      "edge_type": "CommunicationLink",
      "source_node_id": 102,
      "target_node_id": 103,
      "source_anchor": "right",
      "target_anchor": "left",
      "control_points": []
    }
  ]
}
```

오류:
- `404`: view 없음
- `403`: 권한 없음

### 3.3 view 생성

- Method: `POST`
- Path: `/api/views`
- 목적: 최소 view 메타데이터 생성

Request JSON:
```json
{
  "name": "Demo View",
  "description": "Minimal E2E view"
}
```

Response JSON 201:
```json
{
  "view": {
    "id": 1,
    "name": "Demo View",
    "revision": 1
  }
}
```

### 3.4 view 저장

- Method: `PUT`
- Path: `/api/views/{view_id}`
- 목적: node layout, edge 연결, 최소 속성 저장
- 비고: 새 node 와 edge 는 frontend 임시 ID가 아니라 backend 가 생성한 정수 ID를 사용한다고 가정한다.

Request JSON:
```json
{
  "revision": 1,
  "nodes": [
    {
      "id": 101,
      "parent_node_id": null,
      "node_type": "PhysicalServer",
      "display_name": "Host A",
      "target_id": null,
      "x": 40,
      "y": 40,
      "width": 480,
      "height": 260
    },
    {
      "id": 102,
      "parent_node_id": 101,
      "node_type": "SoftwareProcess",
      "display_name": "App Process",
      "target_id": "app_main",
      "x": 80,
      "y": 90,
      "width": 160,
      "height": 56
    },
    {
      "id": 103,
      "parent_node_id": 101,
      "node_type": "MonitoringAgent",
      "display_name": "Local Agent",
      "target_id": "agent_local",
      "x": 280,
      "y": 90,
      "width": 150,
      "height": 56
    }
  ],
  "edges": [
    {
      "id": 201,
      "edge_type": "CommunicationLink",
      "source_node_id": 102,
      "target_node_id": 103,
      "source_anchor": "right",
      "target_anchor": "left",
      "control_points": []
    }
  ]
}
```

Response JSON 200:
```json
{
  "ok": true,
  "revision": 2,
  "updated_at": "2026-04-10T10:15:00.456+09:00"
}
```

오류:
- `409`: revision mismatch
- `400`: containment 위반, edge 연결 규칙 위반 또는 필수 필드 누락

## 4. Monitoring 조회 API

### 4.1 latest state 조회

- Method: `GET`
- Path: `/api/views/{view_id}/latest-state`
- 목적: monitoring overlay 에 필요한 최신 상태 조회

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
    },
    {
      "target_id": "agent_local",
      "state_type": "agent",
      "status": "up",
      "severity": "normal",
      "occurred_at": "2026-04-10T10:20:00.100+09:00",
      "received_at": "2026-04-10T10:20:00.220+09:00",
      "state": {
        "heartbeat_time": "2026-04-10T10:20:00.100+09:00",
        "outbox_queue_depth": 0,
        "backend_connection_status": "connected"
      }
    }
  ]
}
```

### 4.2 recent raw event 조회

- Method: `GET`
- Path: `/api/views/{view_id}/events`
- 목적: 최소 event panel 에 최근 raw event 조회

Query:
- `limit` optional, default `20`

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

## 5. Agent ingest API

### 5.1 batch ingest

- Method: `POST`
- Path: `/api/agents/ingest`
- 목적: agent 가 batch payload 를 durable 하게 전달
- 인증: `X-Agent-Id`, `X-Agent-Token` 또는 동등한 방식

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
    },
    {
      "seq": 11,
      "payload_type": "process_snapshot",
      "occurred_at": "2026-04-10T10:20:00.100+09:00",
      "target_id": "app_main",
      "payload": {
        "pid": 1234,
        "state": "running",
        "cpu_usage": 3.2,
        "memory_rss": 10485760
      }
    },
    {
      "seq": 12,
      "payload_type": "process_event",
      "occurred_at": "2026-04-10T10:21:10.100+09:00",
      "target_id": "app_main",
      "payload": {
        "event_type": "process_stopped",
        "message": "process not found"
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

오류:
- `401`: agent 인증 실패
- `400`: payload 형식 오류

비고:
- 이 응답은 inbox 에 durable write 완료를 의미한다.
- latest state 반영과 raw event 생성은 worker 가 후처리한다.

## 6. Debug payload API

### 6.1 최소 범위 결정

- 최소 E2E 단계에서는 debug payload 조회 UI 를 구현하지 않아도 된다.
- 따라서 debug payload 조회용 공개 API 는 이번 단계에서 생략 가능하다.
- 단, backend 내부 저장은 반드시 동작해야 한다.

## 7. 공통 응답/오류 규칙

- 시간 값은 밀리초(1/1000초) 단위까지 표현한다.
- 성공 응답은 가능한 한 `ok`, `id`, `revision`, `updated_at`, `items` 같은 단순 키를 사용한다.
- 오류 응답은 최소한 다음 구조를 따른다.

Error JSON:
```json
{
  "error": {
    "code": "validation_error",
    "message": "containment rule violated"
  }
}
```

## 8. 최소 API에 대한 판단

- 이 API 집합은 최소 E2E 구현에 필요한 가장 작은 계약만 담고 있다.
- grouped event, SSE, metamodel registry, admin API 전체는 일부러 제외했다.
- 중요한 것은 `view 저장`, `agent ingest`, `latest state 조회`, `raw event 조회` 네 계약이 흔들리지 않는 것이다.

## 9. 다음 단계 입력

- 이 문서를 기준으로 Flask blueprint 와 route skeleton 을 만들 수 있어야 한다.
- 이 문서를 기준으로 pytest API 테스트 케이스를 바로 작성할 수 있어야 한다.
- 이 문서를 기준으로 frontend 와 agent 의 최소 연동 코드를 구현할 수 있어야 한다.
