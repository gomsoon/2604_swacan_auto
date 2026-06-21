# Software Architecture Runtime Monitoring System

## Metamodel Registry API 초안
버전: Draft 0.2  
작성일: 2026-04-15

목적: MVP 단계에서 backend가 제공해야 하는 metamodel/notation registry API를 정리한다. 이 API의 목적은 frontend editor, monitoring, admin 화면이 같은 metamodel 정의를 공통으로 조회하도록 만드는 것이다.

참고 문서:
- [160-metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/160-metamodel-notation-db-design-draft.md)
- [180-metamodel-registry-sqlite-draft.md](C:/2604_swacan_auto/docs/180-metamodel-registry-sqlite-draft.md)
- [070-minimal-api-draft.md](C:/2604_swacan_auto/docs/070-minimal-api-draft.md)

## 1. 설계 원칙

- registry API는 일반 view API와 분리된 전용 영역으로 둔다.
- 일반 사용자 화면은 published metamodel만 read-only로 조회한다.
- 관리자 화면은 draft/publish 흐름을 별도 admin API로 관리한다.
- frontend는 registry API 응답을 바탕으로 palette, 기본 크기, containment 보조 검증, render schema 해석을 수행한다.
- backend는 최종 validation 책임을 유지한다.

## 2. 현재 구현된 조회 API

현재 코드 기준으로 다음 API가 이미 구현되어 있다.

- `GET /api/metamodel/versions/published`
- `GET /api/metamodel/versions/{id}`
- `GET /api/metamodel/versions/{id}/palette`
- `GET /api/metamodel/versions/{id}/semantic-types`
- `GET /api/metamodel/versions/{id}/semantic-types/{type_code}/properties`
- `GET /api/metamodel/versions/{id}/containment-rules`
- `GET /api/metamodel/versions/{id}/associations`
- `GET /api/metamodel/versions/{id}/notations`

## 3. 일반 조회 API 상세

### 3.1 published metamodel 목록 조회
- Method: `GET`
- Path: `/api/metamodel/versions/published`
- 목적: 현재 사용 가능한 published metamodel 버전 목록 조회

응답 예시:
```json
{
  "items": [
    {
      "id": 1,
      "namespace_id": 1,
      "namespace_code": "core",
      "namespace_name": "Core",
      "version_code": "seed-v1",
      "status": "published",
      "description": "Seed metamodel for current MVP baseline",
      "published_at": "2026-04-15T09:00:00.000+09:00"
    }
  ]
}
```

### 3.2 metamodel version 상세 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}`
- 목적: 특정 published metamodel version의 기본 정보 조회

### 3.3 palette 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/palette`
- 목적: frontend palette 구성을 위한 그룹/항목 정보 조회

응답 예시:
```json
{
  "palette_groups": [
    {
      "id": 1,
      "code": "servers",
      "label": "Servers",
      "sort_order": 10,
      "items": [
        {
          "notation_id": 4001,
          "notation_code": "server.physical.rect",
          "display_name": "Physical Server",
          "semantic_type_id": 101,
          "semantic_type_code": "PhysicalServer",
          "semantic_type_display_name": "Physical Server",
          "render_primitive": "rect",
          "render_schema": {
            "primitive": "rect",
            "default_size": {"width": 520, "height": 280}
          },
          "style_tokens": {
            "fill": "server-fill",
            "stroke": "server-stroke"
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
- 목적: semantic type 목록과 기본 성격 조회

### 3.5 semantic type 속성 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/semantic-types/{type_code}/properties`
- 목적: 특정 semantic type의 property definition 조회

### 3.6 containment rule 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/containment-rules`
- 목적: parent-child containment 규칙 조회

### 3.7 association definition 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/associations`
- 목적: edge 관계 정의와 source/target 제약 조회

### 3.8 notation definition 조회
- Method: `GET`
- Path: `/api/metamodel/versions/{version_id}/notations`
- 목적: frontend render schema 조회

지원 query:
- `semantic_type_code` optional
- `palette_only=1` optional

## 4. 현재 frontend와의 연결 방향

현재 frontend는 다음 흐름으로 registry API를 사용한다.

- editor가 published version을 조회한다.
- editor가 palette를 조회해 생성 가능한 node/edge를 구성한다.
- editor와 monitor는 notation code를 기준으로 render schema를 해석한다.
- persisted view는 `semantic_type_code`, `notation_code`를 저장해 registry와 연결된다.

즉, registry API는 단순 참고 정보가 아니라 실제 생성/표현 흐름의 기준 API다.

## 5. 관리자용 다음 단계 API

MVP 다음 단계에서 권장하는 최소 admin API는 아래와 같다.

### 5.1 draft version 생성
- Method: `POST`
- Path: `/api/admin/metamodel/versions`
- 목적: 새로운 draft metamodel version 생성

### 5.2 semantic type 추가
- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/semantic-types`

### 5.3 notation 추가
- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/notations`

### 5.4 containment rule 추가
- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/containment-rules`

### 5.5 publish
- Method: `POST`
- Path: `/api/admin/metamodel/versions/{version_id}/publish`

의미:
- draft를 published로 승격한다.
- 기존 published version은 backend 정책에 따라 deprecated로 전환한다.

## 6. view/editor API와의 연결 방향

registry가 더 깊게 들어오면, 기존 view API는 아래 방향으로 점진 확장하는 것이 좋다.

### 6.1 view 상세 조회
현재:
- `node_type`, `edge_type`, `semantic_type_code`, `notation_code`

향후:
- `metamodel_version_id`
- `semantic_type_id`
- `notation_definition_id`
- `association_definition_id`

### 6.2 node 생성 API
현재:
- `node_type + semantic_type_code + notation_code`

향후:
- `notation_definition_id` 또는 `semantic_type_code + notation_code`를 공식 생성 키로 사용
- backend가 notation에서 semantic type을 해석하고 containment를 검증

## 7. 응답 구조 원칙

- 응답에는 가능한 한 `id`와 `code`를 함께 포함한다.
- frontend는 DB join 결과가 아니라 code 기반 해석이 가능해야 한다.
- `render_schema`, `style_tokens`, `semantics`는 JSON 구조 그대로 응답한다.
- draft와 published를 함께 다룰 때는 `status`를 명시한다.

## 8. 오류 처리 원칙

예시 오류 코드:
- `400 validation_error`
- `401 unauthorized`
- `403 forbidden`
- `404 metamodel_not_found`
- `404 semantic_type_not_found`
- `409 version_conflict`
- `409 publish_conflict`
- `422 unsupported_render_primitive`

## 9. MVP 범위와 후속 범위

### 9.1 MVP에서 포함할 것
- published version 조회
- palette 조회
- semantic type / property / containment / association / notation 조회
- frontend palette와 renderer가 registry를 사용하도록 연결

### 9.2 후속 단계로 미룰 것
- bulk import/export
- metamodel diff API
- notation preview asset 생성
- 세밀한 권한 제어
- visual rule engine과 registry의 완전 통합

## 10. 요약

- metamodel registry API는 backend와 frontend가 같은 모델 정의를 공유하게 만드는 핵심 계약이다.
- 현재는 조회 API가 먼저 구현되어 있고, 다음 단계는 관리자용 draft/publish API다.
- editor와 monitor가 이 API를 더 적극적으로 사용하게 될수록 하드코딩은 줄고 확장성은 올라간다.
