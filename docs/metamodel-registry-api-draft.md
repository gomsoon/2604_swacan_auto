# Software Architecture Runtime Monitoring System

## 메타모델 Registry API 초안
버전: Draft 0.1  
작성일: 2026-04-15

목적: 본 문서는 MVP 단계에서 backend가 제공해야 하는 metamodel/notation registry API를 정리한다. 이 API의 목적은 frontend palette, editor, monitoring, 관리자 화면이 공통 메타모델 정보를 일관되게 조회할 수 있게 하는 것이다.

참고 문서:

- [metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/metamodel-notation-db-design-draft.md)
- [metamodel-registry-sqlite-draft.md](C:/2604_swacan_auto/docs/metamodel-registry-sqlite-draft.md)
- [minimal-api-draft.md](C:/2604_swacan_auto/docs/minimal-api-draft.md)

## 1. 설계 원칙

- registry API는 현재 minimal API와 분리된 새 영역으로 정의한다.
- MVP 1차에서는 조회 API를 우선 제공하고, 관리자 편집 API는 최소 범위로 시작한다.
- published 메타모델은 일반 사용자 화면에서 read-only로 조회한다.
- frontend는 registry API 응답을 기반으로 palette, 기본 크기, containment 검증 보조, render schema 해석을 수행한다.
- backend는 최종 검증 책임을 유지한다.

## 2. API 그룹

권장 blueprint:
- `metamodel_api`
- `admin_metamodel_api`

## 3. 일반 조회 API

### 3.1 published 메타모델 목록 조회

- Method: `GET`
- Path: `/api/metamodel/versions/published`
- 목적: 현재 사용 가능한 published 메타모델 목록 조회

Response JSON 200:

```json
{
  "items": [
    {
      "id": 1,
      "namespace_code": "core",
      "version_code": "1.0.0",
      "status": "published",
      "description": "Core MVP metamodel",
      "published_at": "2026-04-15T09:00:00.000+09:00"
    }
  ]
}
```

### 3.2 메타모델 버전 상세 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}`
- 목적: 특정 메타모델 버전의 기본 정보 조회

Response JSON 200:

```json
{
  "version": {
    "id": 1,
    "namespace_code": "core",
    "version_code": "1.0.0",
    "status": "published",
    "description": "Core MVP metamodel"
  }
}
```

### 3.3 palette 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/palette`
- 목적: frontend palette 구성 정보 조회

Response JSON 200:

```json
{
  "palette_groups": [
    {
      "code": "servers",
      "label": "Servers",
      "sort_order": 10,
      "items": [
        {
          "notation_id": 11,
          "notation_code": "server.physical.rect",
          "semantic_type_code": "PhysicalServer",
          "display_name": "Physical Server",
          "render_primitive": "rect",
          "render_schema": {
            "primitive": "rect",
            "default_size": {"width": 520, "height": 280}
          }
        }
      ]
    }
  ]
}
```

### 3.4 semantic type 목록 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/semantic-types`
- 목적: semantic type 목록과 기본 속성 정의 조회

Response JSON 200:

```json
{
  "items": [
    {
      "id": 101,
      "code": "SoftwareProcess",
      "display_name": "Software Process",
      "kind": "node",
      "is_groupable": true,
      "allows_runtime_binding": true,
      "default_notation_code": "process.rounded_rect"
    }
  ]
}
```

### 3.5 semantic type 속성 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/semantic-types/{type_code}/properties`
- 목적: 특정 semantic type에 대한 property 정의 조회

Response JSON 200:

```json
{
  "semantic_type_code": "SoftwareProcess",
  "items": [
    {
      "code": "display_name",
      "display_name": "Display Name",
      "value_type": "string",
      "is_required": true,
      "is_runtime": false
    },
    {
      "code": "cpu_usage",
      "display_name": "CPU Usage",
      "value_type": "number",
      "unit": "percent",
      "is_required": false,
      "is_runtime": true
    }
  ]
}
```

### 3.6 containment rule 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/containment-rules`
- 목적: editor와 backend 검증에 필요한 포함 규칙 조회

Response JSON 200:

```json
{
  "items": [
    {
      "parent_type_code": "PhysicalServer",
      "child_type_code": "SoftwareProcess",
      "min_count": 0,
      "max_count": null,
      "cardinality_scope": "group_total"
    }
  ]
}
```

### 3.7 association definition 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/associations`
- 목적: edge 의미와 source/target 제약 조회

Response JSON 200:

```json
{
  "items": [
    {
      "code": "communicates_with",
      "display_name": "Communicates With",
      "source_type_code": "SoftwareProcess",
      "target_type_code": "SoftwareProcess",
      "direction": "directed"
    },
    {
      "code": "monitors",
      "display_name": "Monitors",
      "source_type_code": "MonitoringAgent",
      "target_type_code": "SoftwareProcess",
      "direction": "directed"
    }
  ]
}
```

### 3.8 notation definition 조회

- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/notations`
- 목적: frontend render schema 조회

Query:
- `semantic_type_code` optional
- `palette_only=1` optional

Response JSON 200:

```json
{
  "items": [
    {
      "id": 201,
      "code": "agent.rounded_rect.double_border",
      "display_name": "Monitoring Agent",
      "semantic_type_code": "MonitoringAgent",
      "render_primitive": "rounded_rect",
      "render_schema": {
        "primitive": "rounded_rect",
        "default_size": {"width": 180, "height": 72},
        "modifiers": {"double_border": true}
      },
      "style_tokens": {
        "fill": "agent-fill",
        "stroke": "agent-stroke"
      }
    }
  ]
}
```

## 4. 관리자 편집 API

MVP 1차에서는 아래를 최소 범위로 권장한다.

### 4.1 draft 버전 생성

- Method: `POST`
- Path: `/api/admin/metamodel/versions`
- 목적: 새 draft 메타모델 버전 생성

Request JSON:

```json
{
  "namespace_code": "core",
  "version_code": "1.1.0-draft",
  "based_on_version_id": 1,
  "description": "Add ProcessGroup notation"
}
```

### 4.2 semantic type 추가

- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/semantic-types`

### 4.3 notation 추가

- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/notations`

### 4.4 containment rule 추가

- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/containment-rules`

### 4.5 메타모델 publish

- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/publish`

의미:
- draft 버전을 published로 승격
- 기존 published는 deprecated 처리 또는 유지 정책을 backend가 판단

## 5. view/editor와의 연결 API 방향

registry 도입 후 view 관련 API는 아래 정보를 포함하는 방향이 좋다.

### 5.1 view 상세 조회 확장

현재:
- `node_type`, `edge_type` 중심

향후:
- `metamodel_version_id`
- 각 node의 `semantic_type_id`, `notation_definition_id`
- 각 edge의 `association_definition_id`, `notation_definition_id`

### 5.2 node 생성 API 확장

현재:
- `node_type` 기반 생성

향후:
- `notation_definition_id` 또는 `semantic_type_code + notation_code`

예시 Request JSON:

```json
{
  "revision": 7,
  "notation_code": "process.rounded_rect",
  "display_name": "Worker Group",
  "parent_node_id": 10,
  "x": 120,
  "y": 140,
  "width": 200,
  "height": 80
}
```

backend 처리:
- notation에서 semantic type 도출
- containment rule 검증
- 기본 속성 seed

## 6. 응답 구조 원칙

- JSON 응답에는 `id`와 `code`를 가능하면 함께 포함한다.
- frontend는 내부 조인보다는 `code` 기반 해석에 유리하도록 응답을 받는 편이 좋다.
- `render_schema`와 `style_tokens`는 파싱된 JSON 형태로 응답한다.
- draft와 published 구분이 필요한 경우 `status`를 명시한다.

## 7. 오류 처리 원칙

예시 오류 코드:
- `400 validation_error`
- `401 unauthorized`
- `403 forbidden`
- `404 metamodel_not_found`
- `409 version_conflict`
- `409 publish_conflict`
- `422 unsupported_render_primitive`

오류 응답 예시:

```json
{
  "error": "unsupported_render_primitive",
  "message": "render primitive 'ellipse' is not supported by the current frontend renderer"
}
```

## 8. MVP 범위와 후속 범위

### 8.1 MVP에서 포함할 것

- published version 조회
- palette 조회
- semantic type / property / containment / association / notation 조회
- 관리자용 draft 생성, notation 추가, publish API 최소 세트

### 8.2 MVP에서 보류할 것

- bulk import/export
- metamodel diff API
- notation preview 이미지 생성
- permission granularity를 메타모델 단위까지 세분화

## 9. 다음 단계

이 문서를 바탕으로 다음을 이어서 진행하는 것이 좋다.

1. `db/schema.sql`에 메타모델 registry 테이블 추가 초안 반영
2. Flask `metamodel_api` blueprint 골격 추가
3. seed 데이터에 `core / 1.0.0 published` 메타모델 세트 추가
4. frontend palette를 registry API 기반으로 전환하는 설계 시작
