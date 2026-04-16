# Software Architecture Runtime Monitoring System

## View Versioning ERD 초안
버전: Draft 0.2  
작성일: 2026-04-16

목적: `draft / published / active / deprecated` 상태 모델을 데이터베이스 구조로 구체화하고, 이후 runtime identity 분리 계층과 어떻게 연결할지 정리한다.

참고 문서:
- [terminology-guidelines.md](C:/2604_swacan_auto/docs/terminology-guidelines.md)
- [view-versioning-operational-publish-design-draft.md](C:/2604_swacan_auto/docs/view-versioning-operational-publish-design-draft.md)
- [view-versioning-sqlite-draft.md](C:/2604_swacan_auto/docs/view-versioning-sqlite-draft.md)
- [runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/runtime-identity-binding-design-draft.md)

## 1. 설계 목표

- `views`는 logical root로 유지한다.
- 실제 편집/운영 대상은 `view_versions`와 그 하위 snapshot row로 관리한다.
- 운영 중인 `active` 화면은 다른 사용자의 draft 편집에 영향을 받지 않는다.
- version row id와 별개로 `element_key`를 둬 version 간 동일 논리 객체를 잇는다.
- 장기적으로는 runtime state/event/alert를 `view_version_nodes`가 아니라 별도 monitored object에 귀속시킨다.

## 2. 용어 적용

- `Monitoring View`는 `active view version`을 읽는 운영 화면이다.
- `Architecture Editor`는 `draft view version`을 수정하는 편집 화면이다.
- `Logical View`는 사용자 관점의 논리적 화면 단위이고, `View Version`은 해당 화면의 snapshot 단위이다.

## 3. 권장 테이블 구조

### 3.1 views
역할:
- logical view root
- 사용자 관점의 화면 단위

핵심 컬럼:
- `id INTEGER PRIMARY KEY`
- `workspace_id INTEGER`
- `owner_user_id INTEGER NOT NULL`
- `name TEXT NOT NULL`
- `description TEXT`
- `metamodel_namespace_code TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 3.2 view_versions
역할:
- logical view 아래의 snapshot 단위
- `draft / published / active / deprecated` 상태 관리

핵심 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_id INTEGER NOT NULL`
- `version_no INTEGER NOT NULL`
- `version_code TEXT`
- `status TEXT NOT NULL`
- `based_on_version_id INTEGER`
- `metamodel_version_id INTEGER`
- `created_by_user_id INTEGER NOT NULL`
- `approved_by_user_id INTEGER`
- `activated_by_user_id INTEGER`
- `description TEXT`
- `published_at TEXT`
- `activated_at TEXT`
- `revision INTEGER NOT NULL DEFAULT 1`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 제약:
- `(view_id, version_no)` unique
- `status` in (`draft`, `published`, `active`, `deprecated`)

운영 규칙:
- MVP에서는 `view_id`별 동시 `draft`는 1개로 제한하는 편이 단순하다.
- `active`는 `view_id`별 최대 1개만 허용한다.

### 3.3 view_version_nodes
역할:
- 특정 version snapshot에 속한 node 표현

핵심 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_version_id INTEGER NOT NULL`
- `element_key TEXT NOT NULL`
- `parent_node_id INTEGER`
- `node_type TEXT NOT NULL`
- `semantic_type_code TEXT NOT NULL`
- `notation_code TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `target_id TEXT`
- `instance_mode TEXT`
- `cardinality_scope TEXT`
- `expected_min INTEGER`
- `expected_max INTEGER`
- `x REAL NOT NULL`
- `y REAL NOT NULL`
- `width REAL NOT NULL`
- `height REAL NOT NULL`
- `layer_order INTEGER NOT NULL`
- `collapsed_state INTEGER NOT NULL DEFAULT 0`
- `properties_json TEXT`
- `is_deleted INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 제약:
- `(view_version_id, element_key)` unique

메모:
- `target_id`는 현재 compatibility 용도로 유지할 수 있다.
- 장기적으로는 `target_id` 대신 `node_bindings`를 통한 monitored object 연결로 축소하는 편이 좋다.

### 3.4 view_version_edges
역할:
- 특정 version snapshot에 속한 edge 표현

핵심 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_version_id INTEGER NOT NULL`
- `element_key TEXT NOT NULL`
- `edge_type TEXT NOT NULL`
- `association_code TEXT`
- `semantic_type_code TEXT NOT NULL`
- `notation_code TEXT NOT NULL`
- `source_node_id INTEGER NOT NULL`
- `target_node_id INTEGER NOT NULL`
- `source_element_key TEXT`
- `target_element_key TEXT`
- `source_anchor TEXT`
- `target_anchor TEXT`
- `control_points_json TEXT`
- `label TEXT`
- `layer_order INTEGER NOT NULL`
- `style_json TEXT`
- `is_deleted INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 제약:
- `(view_version_id, element_key)` unique

## 4. 권장 관계

- `views 1 --- N view_versions`
- `view_versions 1 --- N view_version_nodes`
- `view_versions 1 --- N view_version_edges`
- `view_version_nodes 1 --- N child view_version_nodes`
- `view_version_nodes 1 --- N source view_version_edges`
- `view_version_nodes 1 --- N target view_version_edges`

## 5. runtime identity 분리 계층

view versioning만으로는 운영 데이터 fan-out 문제를 해결하기 어렵다. 같은 server/process/thread가 여러 active view에서 동시에 표현될 수 있기 때문이다.

그래서 장기적으로는 다음 계층이 필요하다.

### 5.1 monitored_objects
역할:
- 실제 관측 대상의 전역 논리 ID
- latest state, raw event, alert의 귀속 대상

예시 컬럼:
- `id INTEGER PRIMARY KEY`
- `object_key TEXT NOT NULL UNIQUE`
- `object_type TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `runtime_binding_key TEXT`
- `metadata_json TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 5.2 node_bindings
역할:
- 특정 `view_version_node`가 어떤 `monitored_object`를 바라보는지 연결

예시 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_version_node_id INTEGER NOT NULL`
- `monitored_object_id INTEGER NOT NULL`
- `binding_role TEXT NOT NULL DEFAULT 'primary'`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 제약:
- `(view_version_node_id, monitored_object_id)` unique

### 5.3 alert_instances
역할:
- runtime rule 평가 결과 생성된 alert
- view node가 아니라 monitored object에 귀속

예시 컬럼:
- `id INTEGER PRIMARY KEY`
- `monitored_object_id INTEGER NOT NULL`
- `alert_code TEXT NOT NULL`
- `severity TEXT NOT NULL`
- `status TEXT NOT NULL`
- `first_occurred_at TEXT NOT NULL`
- `last_occurred_at TEXT NOT NULL`
- `repeat_count INTEGER NOT NULL DEFAULT 1`
- `latest_message TEXT`
- `metadata_json TEXT`

## 6. fan-out 원칙

- latest state는 `monitored_object_id` 기준으로 1번 갱신한다.
- raw event도 `monitored_object_id` 기준으로 1번 생성한다.
- alert도 `monitored_object_id` 기준으로 1번 생성한다.
- 각 active view는 자신이 참조하는 monitored object를 화면에 fan-out해서 보여준다.

즉:
- 생성 단위: monitored object
- 표현 단위: view version node

## 7. 현재 구조 평가

현재 구조도 `target_id`가 전역적으로 일관되게 관리되면, 동일 runtime 대상을 여러 view에서 참조할 때 latest state를 여러 번 저장할 필요는 없다.

하지만 현재의 한계는 분명하다.
- `target_id`가 view snapshot row 안에 있어서 runtime identity 책임을 과도하게 진다.
- 같은 process를 서로 다른 view에서 다른 `target_id`로 저장하면 같은 대상을 다르게 취급할 수 있다.
- `latest_states.view_node_id` 같은 legacy linkage는 versioned 구조와 잘 맞지 않는다.

그래서 MVP에서는 `target_id`를 유지하되, 다음 방향으로 점진 전환하는 것이 좋다.

1. `target_id`를 compatibility binding key로 유지
2. `monitored_objects` 추가
3. `node_bindings` 추가
4. `latest_states`, `raw_events`, `alert_instances`를 점진적으로 `monitored_object_id` 기준으로 전환

## 8. 조회 패턴 권장

### 8.1 Editor
- logical view를 선택
- 현재 draft version 조회
- `view_version_nodes`, `view_version_edges` 기반으로 편집

### 8.2 Monitoring
- logical view를 선택
- 현재 active version 조회
- active version node가 참조하는 monitored object 집합 조회
- latest state / event / alert를 monitored object 기준으로 가져와 fan-out

### 8.3 Publish / Activate
- publish는 draft snapshot을 고정본으로 승격
- activate는 published snapshot을 운영본으로 승격
- 기존 active는 deprecated로 전환

## 9. migration 방향

### 9.1 1단계
- `view_versions`, `view_version_nodes`, `view_version_edges` 추가
- 기존 `views`, `view_nodes`, `view_edges`는 compatibility root로 유지

### 9.2 2단계
- editor는 draft version 기준으로 전환
- monitoring은 active version 기준으로 전환

### 9.3 3단계
- `monitored_objects`, `node_bindings` 추가
- `latest_states`, `raw_events`를 점진적으로 runtime identity layer 기준으로 전환

## 10. 요약

- `views`는 logical root다.
- `view_versions`는 draft/published/active/deprecated snapshot을 관리한다.
- `view_version_nodes`, `view_version_edges`는 화면 snapshot 표현이다.
- `element_key`는 version 간 동일 논리 객체를 잇는 핵심 키다.
- alert/event/latest state는 장기적으로 node가 아니라 monitored object에 귀속돼야 한다.
- 이 구조가 있어야 같은 runtime 대상을 여러 active view에서 안정적으로 동시에 표현할 수 있다.
