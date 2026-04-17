# Software Architecture Runtime Monitoring System

## Metamodel/Notation Registry DB 설계 초안
버전: Draft 0.2  
작성일: 2026-04-15

목적: MVP 단계에서 사용할 metamodel/notation registry의 데이터베이스 설계 방향을 정리한다. 이 설계의 목표는 backend가 메타모델 의미와 기본 시각 표현을 함께 관리하고, frontend는 이를 해석하는 SVG 렌더러로 동작하도록 만드는 것이다.

참고 문서:
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [terminology-guidelines.md](C:/2604_swacan_auto/docs/terminology-guidelines.md)
- [backend-detailed-requirements.md](C:/2604_swacan_auto/docs/backend-detailed-requirements.md)
- [frontend-detailed-requirements.md](C:/2604_swacan_auto/docs/frontend-detailed-requirements.md)
- [software-architecture-runtime-monitoring-mvp-plan.md](C:/2604_swacan_auto/docs/software-architecture-runtime-monitoring-mvp-plan.md)

## 1. 설계 목표

- backend와 DB가 semantic type, property, association, containment, notation을 함께 관리한다.
- frontend는 backend가 제공하는 선언형 render schema를 해석해 SVG로 표현한다.
- 새로운 semantic type이나 notation이 추가되더라도, 기존 primitive 범위 안에서는 frontend 수정 없이 palette와 렌더링에 반영될 수 있어야 한다.
- architecture model, runtime model, visual notation을 서로 분리하되 연결 가능한 구조로 유지한다.
- SQLite 기반 MVP에서 시작하되, 이후 PostgreSQL로 옮겨도 같은 도메인 모델을 유지할 수 있어야 한다.

## 2. 책임 분리

### 2.1 Backend/DB가 관리할 것
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
- anchor 규칙
- style token

### 2.2 Frontend가 관리할 것
- SVG primitive 실제 렌더링
- drag/drop, selection, zoom/pan
- render schema 해석 로직
- palette interaction
- style token과 실제 CSS/SVG 속성의 매핑

### 2.3 경계 원칙
- backend는 `무엇을 보여줄 것인가`를 정의한다.
- frontend는 `어떻게 그릴 것인가`를 구현한다.
- backend는 arbitrary UI 코드를 저장하지 않고, 선언형 schema만 저장한다.
- frontend는 허용된 primitive 집합 안에서만 registry를 해석한다.

### 2.4 용어 적용 메모
- runtime 상태를 읽는 운영 화면은 `Monitoring View`로 본다.
- 아키텍처 draft를 수정하는 화면은 `Architecture Editor`로 본다.
- semantic type, containment, notation을 수정하는 화면은 `Metamodel Editor`로 본다.
- Metamodel Editor는 좌측 목록, 중앙 구조 canvas/preview, 우측 inspector를 갖는 편집 workspace를 기본 형태로 삼는다.

## 3. 계층 구조

이 설계는 다음 네 계층을 전제로 한다.

1. `Metamodel Layer`
- semantic type, property, association, containment 정의

2. `Notation Layer`
- semantic type의 기본 시각 표현 정의

3. `Architecture Model Layer`
- 실제 view, node, edge 인스턴스

4. `Runtime Layer`
- agent가 수집한 latest state, raw event, runtime binding

본 문서는 1, 2 계층을 중심으로 정리한다.

### 3.1 Runtime Layer 보강 메모
- 여러 active view가 동일한 runtime 대상을 동시에 표현할 수 있으므로, runtime layer는 장기적으로 `view node`가 아니라 별도의 `monitored object`를 기준으로 구성하는 편이 더 안정적이다.
- 이 경우 view는 `node binding`을 통해 monitored object를 참조하고, latest state / raw event / alert는 monitored object에 1회 생성된 뒤 여러 view로 fan-out된다.
- 관련 상세는 [runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/runtime-identity-binding-design-draft.md)에서 별도로 정리한다.

## 4. 핵심 테이블

### 4.1 metamodel_namespaces
목적:
- metamodel을 논리적 namespace 단위로 구분

핵심 컬럼:
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

### 4.2 metamodel_versions
목적:
- namespace별 metamodel version 관리

핵심 컬럼:
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

### 4.3 semantic_types
목적:
- backend가 이해하는 의미 타입 정의

핵심 컬럼:
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

예시 semantic type:
- `PhysicalServer`
- `VirtualMachine`
- `SoftwareProcess`
- `MonitoringAgent`
- `CommunicationLink`

### 4.4 property_definitions
목적:
- semantic type별 속성 정의

핵심 컬럼:
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

### 4.5 association_definitions
목적:
- edge 관계 정의

핵심 컬럼:
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

예시:
- `communicates_with`
- `monitors`

### 4.6 containment_rules
목적:
- parent-child containment 규칙 정의

핵심 컬럼:
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

예시:
- `PhysicalServer -> SoftwareProcess`
- `PhysicalServer -> MonitoringAgent`
- `PhysicalServer -> VirtualMachine`
- `VirtualMachine -> SoftwareProcess`

### 4.7 palette_groups
목적:
- frontend palette 그룹 정의

핵심 컬럼:
- `id INTEGER PRIMARY KEY`
- `metamodel_version_id INTEGER NOT NULL`
- `code TEXT NOT NULL`
- `label TEXT NOT NULL`
- `sort_order INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

예시:
- `servers`
- `processes`
- `monitoring`
- `communication`

### 4.8 notation_definitions
목적:
- semantic type의 시각 표현 정의

핵심 컬럼:
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

## 5. render schema 방향

### 5.1 기본 원칙
- MVP에서는 `render_schema_json`을 JSON 문자열로 저장한다.
- frontend는 이 schema를 해석해 SVG를 그린다.
- backend는 CSS/JS 템플릿이 아니라 선언형 속성만 저장한다.

### 5.2 현재 primitive whitelist
- `rect`
- `rounded_rect`
- `line`
- `badge`
- `label`

### 5.3 현재 seed 기준 표현 예
- `PhysicalServer` -> `rect`
- `SoftwareProcess` -> `rounded_rect`
- `MonitoringAgent` -> `rounded_rect` + `double_border`
- `CommunicationLink` -> `line`
- `VirtualMachine` -> `rect` + `dashed_border`

### 5.4 render_schema 예시
```json
{
  "primitive": "rounded_rect",
  "default_size": {"width": 180, "height": 72},
  "label_slots": [
    {"code": "title", "source": "display_name"},
    {"code": "subtitle", "source": "target_id"}
  ],
  "badge_slots": [
    {"code": "status", "source": "runtime.status"}
  ],
  "anchors": ["top", "right", "bottom", "left"],
  "modifiers": {
    "double_border": true
  },
  "interaction": {
    "draggable": true,
    "resizable": true
  }
}
```

## 6. Architecture Model과의 연결

현재 persisted view는 다음 전략으로 registry와 연결된다.

### 6.1 views
현재:
- `metamodel_version` 문자열 저장

향후 권장:
- `metamodel_version_id`를 추가해 정식 FK 연결

### 6.2 view_nodes
현재:
- `node_type`
- `semantic_type_code`
- `notation_code`

의미:
- 기존 분기 로직과의 호환을 유지하면서 registry 기반 참조를 병행한다.

향후 권장:
- `semantic_type_id`
- `notation_definition_id`

### 6.3 view_edges
현재:
- `edge_type`
- `semantic_type_code`
- `notation_code`

향후 권장:
- `association_definition_id`
- `notation_definition_id`

## 7. 점진 전환 전략

### 7.1 1단계
- seed 기반 metamodel published version 유지
- frontend가 registry 조회로 palette와 notation 정보를 읽는다.
- persisted view는 code 기반 참조를 저장한다.

### 7.2 2단계
- `views.metamodel_version_id` 도입
- `view_nodes.semantic_type_id`, `view_nodes.notation_definition_id` 도입
- `view_edges.association_definition_id`, `view_edges.notation_definition_id` 도입

### 7.3 3단계
- 기존 `node_type`, `edge_type`는 compatibility layer로 축소
- 충분한 마이그레이션 후 제거 여부 판단

## 8. 현재 시점의 구현 상태

현재 코드 기준으로 다음이 이미 반영되어 있다.

- registry 테이블과 seed 데이터 존재
- registry 조회 API 구현
- editor가 palette를 registry에서 읽음
- `view_nodes`, `view_edges`가 `semantic_type_code`, `notation_code`를 저장함
- diagram renderer가 `notation_code + render_schema`를 해석하기 시작함

즉 이 설계는 단순 아이디어가 아니라 이미 일부 구현된 구조의 확장 설계다.

## 9. 주요 리스크와 대응

### 9.1 지나친 범용성 리스크
- notation schema를 너무 자유롭게 열면 frontend renderer가 급격히 복잡해진다.
- 대응: primitive whitelist를 엄격히 유지한다.

### 9.2 코드와 id 참조 혼재 리스크
- 현재는 code 기반 참조와 기존 타입 문자열이 함께 존재한다.
- 대응: MVP 동안은 code 기반을 먼저 안정화하고, id 기반 전환은 다음 단계로 분리한다.

### 9.3 metamodel과 runtime의 분리 리스크
- metamodel이 풍부해져도 runtime binding이 따라오지 못하면 실제 가치가 떨어진다.
- 대응: persisted view와 latest state 연결을 점진적으로 강화한다.

## 10. 요약

- metamodel/notation registry는 앞으로의 확장성과 사용성을 결정하는 핵심 축이다.
- backend는 의미와 표현 정의를 관리하고, frontend는 이를 해석하는 역할로 분리하는 것이 가장 적절하다.
- 현재는 code 기반 참조와 선언형 render schema를 이용해 점진적으로 registry 중심 구조로 이동하는 단계다.
