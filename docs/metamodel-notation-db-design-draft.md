# Software Architecture Runtime Monitoring System

## 메타모델/Notation Registry DB 설계 초안
버전: Draft 0.1  
작성일: 2026-04-14

목적: 본 문서는 MVP 단계에서 사용할 `metamodel/notation registry`의 데이터베이스 설계 방향을 정의한다. 이 설계의 목표는 backend가 메타모델의 의미와 기본 시각 표현을 함께 관리하고, frontend는 이를 해석하여 SVG로 렌더링하는 구조를 만드는 것이다.

참고 문서:

- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [backend-detailed-requirements.md](C:/2604_swacan_auto/docs/backend-detailed-requirements.md)
- [frontend-detailed-requirements.md](C:/2604_swacan_auto/docs/frontend-detailed-requirements.md)
- [software-architecture-runtime-monitoring-mvp-plan.md](C:/2604_swacan_auto/docs/software-architecture-runtime-monitoring-mvp-plan.md)

## 1. 설계 목표

- 메타모델의 의미 구조와 notation 표현 구조를 backend/DB에서 관리할 수 있어야 한다.
- frontend는 backend가 제공하는 선언형 render schema를 해석하는 SVG 렌더링 엔진으로 동작해야 한다.
- 새로운 semantic type 또는 notation이 추가되더라도, frontend가 이미 지원하는 primitive 범위 안에서는 frontend 코드 변경 없이 palette와 canvas에 반영될 수 있어야 한다.
- `architecture model`, `runtime model`, `visual notation`을 서로 분리하되 일관된 식별 체계로 연결해야 한다.
- SQLite 기반 MVP에서 시작하되, 이후 PostgreSQL로 이관해도 같은 도메인 구조를 유지할 수 있어야 한다.

## 2. 핵심 설계 원칙

- `semantic type`과 `notation`은 반드시 분리한다.
- `notation`은 임의의 UI 코드가 아니라 backend가 관리하는 선언형 render schema로 저장한다.
- frontend는 허용된 primitive 집합만 렌더링해야 하며, backend가 전달한 임의 JavaScript/CSS/SVG 템플릿을 실행하지 않는다.
- `architecture instance`는 특정 `semantic type`과 특정 `notation`을 참조해야 한다.
- 하나의 `semantic type`에는 여러 개의 notation이 존재할 수 있어야 한다.
- `containment`, `association`, `property`는 notation이 아니라 메타모델의 의미 규칙으로 관리해야 한다.
- 메타모델은 버전 개념을 가져야 하며, `draft -> published -> deprecated` 흐름을 따라야 한다.

## 3. 책임 분리

### 3.1 Backend/DB가 관리할 것

- namespace
- metamodel version
- semantic type
- property definition
- association definition
- containment rule
- notation definition
- palette group
- default size
- label slot
- badge slot
- anchor/port 위치 정책
- style token
- monitoring overlay 기본 규칙

### 3.2 Frontend가 관리할 것

- SVG primitive의 실제 렌더링
- 드래그, 리사이즈, 선택, 줌, 팬
- render schema 해석 로직
- palette 표시와 interaction
- backend가 제공한 style token을 실제 CSS/SVG 속성으로 매핑하는 테마 계층

### 3.3 경계 원칙

- backend는 “무엇을 보여줄 것인가”를 정의한다.
- frontend는 “어떻게 그릴 것인가”를 구현한다.
- backend가 지원 범위를 넘는 새로운 primitive를 추가하면 frontend 업데이트가 필요하다.
- backend가 기존 primitive 조합만 사용하는 새로운 notation을 추가하는 경우에는 frontend 수정 없이 반영될 수 있어야 한다.

## 4. 계층 구조

본 설계는 아래 4개 계층으로 본다.

1. `Metamodel Layer`
- semantic type, property, association, containment를 정의한다.

2. `Notation Layer`
- semantic type을 canvas에서 어떤 형태로 표현할지 정의한다.

3. `Architecture Model Layer`
- 사용자가 실제로 만든 view, node, edge를 저장한다.

4. `Runtime Layer`
- agent가 수집한 latest state, raw event, runtime binding을 저장한다.

이 중 본 문서는 `Metamodel Layer`와 `Notation Layer`를 중심으로 설계한다.

## 5. SQLite 기준 핵심 테이블 제안

### 5.1 metamodel_namespaces

목적:
- 메타모델의 논리적 구분 단위

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `code TEXT NOT NULL UNIQUE`
- `name TEXT NOT NULL`
- `description TEXT`
- `is_system INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

예시:
- `core`
- `linux`
- `custom`

### 5.2 metamodel_versions

목적:
- namespace별 메타모델 버전 관리

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `namespace_id INTEGER NOT NULL`
- `version_code TEXT NOT NULL`
- `status TEXT NOT NULL`
- `description TEXT`
- `based_on_version_id INTEGER`
- `published_at TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(namespace_id, version_code)` unique
- `status`는 `draft`, `published`, `deprecated`

비고:
- MVP에서는 namespace당 `published` 1개 정책을 권장한다.

### 5.3 semantic_types

목적:
- 아키텍처 구성 요소의 의미 타입 정의

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `code TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `description TEXT`
- `kind TEXT NOT NULL`
- `runtime_kind TEXT`
- `is_groupable INTEGER NOT NULL DEFAULT 0`
- `allows_runtime_binding INTEGER NOT NULL DEFAULT 1`
- `default_notation_id INTEGER`
- `is_active INTEGER NOT NULL DEFAULT 1`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(metamodel_version_id, code)` unique
- `kind` 예시: `node`, `edge`, `container`, `runtime-only`

MVP 기본 semantic type 예시:
- `PhysicalServer`
- `VirtualMachine`
- `SoftwareProcess`
- `MonitoringAgent`
- `ExecutionThread`
- `CommunicationLink`
- `ProcessGroup`
- `ThreadPool`
- `ServerGroup`

### 5.4 property_definitions

목적:
- semantic type별 속성 정의

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `semantic_type_id INTEGER NOT NULL`
- `code TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `description TEXT`
- `value_type TEXT NOT NULL`
- `unit TEXT`
- `default_value_json TEXT`
- `is_required INTEGER NOT NULL DEFAULT 0`
- `is_runtime INTEGER NOT NULL DEFAULT 0`
- `is_user_editable INTEGER NOT NULL DEFAULT 1`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(semantic_type_id, code)` unique

value_type 예시:
- `string`
- `integer`
- `number`
- `boolean`
- `enum`
- `json`

### 5.5 association_definitions

목적:
- semantic type 간의 의미 관계 정의

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `code TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `description TEXT`
- `source_type_id INTEGER NOT NULL`
- `target_type_id INTEGER NOT NULL`
- `direction TEXT NOT NULL`
- `multiplicity_source TEXT`
- `multiplicity_target TEXT`
- `semantics_json TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(metamodel_version_id, code)` unique

예시:
- `communicates_with`
- `monitors`
- `depends_on`
- `hosts`

### 5.6 containment_rules

목적:
- 부모-자식 포함 규칙 정의

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `parent_type_id INTEGER NOT NULL`
- `child_type_id INTEGER NOT NULL`
- `min_count INTEGER`
- `max_count INTEGER`
- `cardinality_scope TEXT NOT NULL DEFAULT 'group_total'`
- `is_required INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(metamodel_version_id, parent_type_id, child_type_id)` unique

cardinality_scope 예시:
- `group_total`
- `per_member`

### 5.7 palette_groups

목적:
- frontend palette 표시 그룹 관리

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `code TEXT NOT NULL`
- `label TEXT NOT NULL`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(metamodel_version_id, code)` unique

예시:
- `servers`
- `processes`
- `communication`
- `monitoring`

### 5.8 notation_definitions

목적:
- semantic type의 기본 시각 표현 정의

주요 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `semantic_type_id INTEGER NOT NULL`
- `palette_group_id INTEGER`
- `code TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `kind TEXT NOT NULL`
- `render_primitive TEXT NOT NULL`
- `render_schema_json TEXT NOT NULL`
- `style_tokens_json TEXT`
- `is_default INTEGER NOT NULL DEFAULT 0`
- `is_visible_in_palette INTEGER NOT NULL DEFAULT 1`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

주요 제약:
- `(metamodel_version_id, code)` unique

비고:
- `render_primitive`는 frontend가 지원하는 primitive whitelist 안의 값만 허용한다.
- 세부 표현은 `render_schema_json`으로 관리한다.

## 6. render schema 저장 전략

### 6.1 기본 방향

- MVP에서는 render schema를 `notation_definitions.render_schema_json`에 JSON 문자열로 저장한다.
- SQLite에서는 JSON 전용 타입이 없으므로 `TEXT`로 저장하되, 구조는 명확히 문서화한다.
- PostgreSQL 전환 시에는 `JSONB`로 자연스럽게 이관할 수 있어야 한다.

### 6.2 MVP primitive whitelist

현재 MVP에서 backend가 사용할 수 있는 primitive는 최소한 아래 범위로 제한하는 것이 좋다.

- `rect`
- `rounded_rect`
- `line`
- `badge`
- `label`

비고:
- `MonitoringAgent`는 `rounded_rect`를 유지하되 `double_border` 같은 modifier로 구분한다.
- `PhysicalServer`는 `rect`
- `SoftwareProcess`는 `rounded_rect`
- `CommunicationLink`는 `line`
- `VirtualMachine`은 `rect` + dashed style token 조합으로 표현할 수 있다.
- `ExecutionThread`용 `ellipse` 또는 `capsule` primitive는 이후 frontend renderer 확장과 함께 도입하는 것이 안전하다.

### 6.3 render_schema_json 예시

```json
{
  "primitive": "rounded_rect",
  "default_size": {
    "width": 180,
    "height": 72
  },
  "label_slots": [
    {"code": "title", "source": "display_name"},
    {"code": "subtitle", "source": "target_id"}
  ],
  "badge_slots": [
    {"code": "status", "source": "runtime.status"},
    {"code": "count", "source": "runtime.actual_count"}
  ],
  "anchors": ["top", "right", "bottom", "left"],
  "modifiers": {
    "double_border": true
  },
  "interaction": {
    "resizable": true,
    "draggable": true
  }
}
```

### 6.4 style_tokens_json 예시

```json
{
  "fill": "agent-fill",
  "stroke": "agent-stroke",
  "label": "agent-label",
  "selected": "agent-selected",
  "warning": "agent-warning"
}
```

## 7. Architecture Model과의 연결

메타모델 registry가 도입되면 현재 architecture model 테이블은 아래 방향으로 연결되어야 한다.

### 7.1 views

추가 권장 컬럼:
- `metamodel_version_id INTEGER NOT NULL`

의미:
- 특정 view는 어떤 메타모델 버전 위에서 작성되었는지 명시한다.

### 7.2 view_nodes

현재 방향:
- `node_type` 기반 최소 모델

MVP 전환 방향:
- `semantic_type_id INTEGER NOT NULL`
- `notation_definition_id INTEGER NOT NULL`

의미:
- node는 의미 타입과 시각 표현을 분리해서 참조한다.

### 7.3 view_edges

현재 방향:
- `edge_type` 기반 최소 모델

MVP 전환 방향:
- `association_definition_id INTEGER`
- `notation_definition_id INTEGER`

의미:
- edge도 단순 선이 아니라 의미 관계 + 표현 방식으로 분리한다.

## 8. 점진 전환 전략

### 8.1 1단계

- 현재 seed 기반 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink`를 metamodel registry seed 데이터로 재정의한다.
- frontend는 여전히 현재 primitive 렌더러를 사용한다.
- backend는 registry API를 통해 palette와 node 기본값을 내려줄 수 있게 한다.

### 8.2 2단계

- `views.metamodel_version_id` 도입
- `view_nodes.semantic_type_id`, `view_nodes.notation_definition_id` 도입
- `view_edges.association_definition_id`, `view_edges.notation_definition_id` 도입

### 8.3 3단계

- 기존 `node_type`, `edge_type` 컬럼은 마이그레이션 완료 후 제거하거나 compatibility layer로만 유지한다.

## 9. API 방향

MVP 1차에서 권장하는 registry API는 아래와 같다.

- `GET /api/metamodel/versions/published`
- `GET /api/metamodel/versions/{id}`
- `GET /api/metamodel/versions/{id}/palette`
- `GET /api/metamodel/versions/{id}/semantic-types`
- `GET /api/metamodel/versions/{id}/notations`
- `GET /api/metamodel/versions/{id}/containment-rules`
- `GET /api/metamodel/versions/{id}/associations`

관리자용 API는 후속으로 아래를 준비한다.

- `POST /api/admin/metamodel/versions`
- `POST /api/admin/metamodel/semantic-types`
- `POST /api/admin/metamodel/notations`
- `POST /api/admin/metamodel/containment-rules`
- `POST /api/admin/metamodel/publish`

## 10. 관리자 화면 관점

관리자 화면은 최소한 아래를 조회할 수 있어야 한다.

- published metamodel version
- semantic type 목록
- notation 목록
- palette group 목록
- containment rule 목록
- association definition 목록

후속 단계에서 아래 관리 기능을 추가한다.

- draft 버전 생성
- notation 추가/비활성화
- semantic type 속성 정의 편집
- publish/deprecate 처리

## 11. MVP 범위와 후속 범위

### 11.1 MVP에서 포함할 것

- namespace, version, semantic type, property, association, containment, palette, notation 기본 테이블
- `render_schema_json` 기반 선언형 표현 정의
- current frontend renderer가 지원하는 primitive 범위 안의 notation
- registry 조회 API
- seed 기반 metamodel published version 1개

### 11.2 MVP에서 보류할 것

- semantic type inheritance
- 다국어 label 체계
- notation별 고급 animation 정의
- arbitrary template 기반 렌더링
- 사용자 정의 script 평가
- visual rule engine과 notation registry의 완전 통합

## 12. 리스크와 대응

### 12.1 리스크

- notation을 너무 유연하게 설계하면 frontend renderer 복잡도가 급증할 수 있다.
- semantic type과 notation의 참조 관계가 과도하게 세분화되면 SQLite MVP에서 관리 복잡도가 커질 수 있다.
- registry 도입 시 기존 `view_nodes`, `view_edges`와의 점진 전환 전략이 불명확하면 구현이 흔들릴 수 있다.

### 12.2 대응

- primitive whitelist를 좁게 유지한다.
- MVP에서는 inheritance와 dynamic template 기능을 넣지 않는다.
- registry는 먼저 조회 중심으로 도입하고, 관리자 편집 기능은 다음 단계로 나눈다.
- architecture model 테이블은 compatibility layer를 거쳐 점진 이행한다.

## 13. 요약

- backend가 메타모델과 기본 시각 표현을 함께 관리하는 구조는 제품 확장성과 운영 일관성 측면에서 매우 적절하다.
- 다만 backend가 임의 UI 코드를 관리하는 방식이 아니라, 선언형 render schema와 제한된 primitive 집합을 관리하는 방향이어야 한다.
- 이 설계를 적용하면 새로운 semantic type과 notation을 DB에 추가하고, frontend는 이를 palette/canvas/monitoring에 일관되게 반영할 수 있다.
- 다음 단계는 이 문서를 바탕으로 `SQLite 테이블 추가 초안`과 `registry 조회 API 초안`으로 내려가는 것이다.
