# Software Architecture Runtime Monitoring System

## View Versioning ERD 초안

버전: Draft 0.1  
작성일: 2026-04-15

목적: `draft / published / active operational view` 구조를 데이터베이스 엔터티 수준으로 구체화한다. 이 문서는 이후 SQLite 스키마 확장, API 설계, migration 계획의 기준 초안으로 사용한다.

참고 문서:
- [view-versioning-operational-publish-design-draft.md](C:/2604_swacan_auto/docs/view-versioning-operational-publish-design-draft.md)
- [minimal-erd-draft.md](C:/2604_swacan_auto/docs/minimal-erd-draft.md)
- [sqlite-create-table-draft.md](C:/2604_swacan_auto/docs/sqlite-create-table-draft.md)

## 1. 설계 목표

- 운영 중인 monitoring 화면과 편집 중인 draft 화면을 분리한다.
- `views` 는 논리 루트로 유지하고, 실제 편집/운영 대상은 `view_versions` 와 그 하위 snapshot row 로 옮긴다.
- publish 는 draft row 를 운영 원본에 덮어쓰지 않고, version snapshot 상태를 바꾸는 방식으로 처리한다.
- active operational version 을 명시적으로 고정해 운영 화면이 다른 사용자의 편집에 영향을 받지 않게 한다.
- 버전 간 동일 논리 객체를 이어가기 위해 `element_key` 를 도입한다.

## 2. 권장 엔터티 구조

### 2.1 views
역할:
- logical view 루트
- 사용자 입장에서 보이는 “하나의 아키텍처 화면” 정의

권장 컬럼:
- `id INTEGER PRIMARY KEY`
- `workspace_id INTEGER`
- `owner_user_id INTEGER NOT NULL`
- `name TEXT NOT NULL`
- `description TEXT`
- `metamodel_namespace_code TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

설계 메모:
- 현재 `views` 가 갖고 있는 `revision` 은 장기적으로 draft version 수준으로 이동하는 것이 더 자연스럽다.

### 2.2 view_versions
역할:
- logical view 의 snapshot 단위
- draft / published / active / deprecated 상태 관리

권장 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_id INTEGER NOT NULL`
- `version_no INTEGER NOT NULL`
- `version_code TEXT`
- `status TEXT NOT NULL`
- `based_on_version_id INTEGER`
- `metamodel_version_id INTEGER`
- `created_by_user_id INTEGER NOT NULL`
- `description TEXT`
- `published_at TEXT`
- `activated_at TEXT`
- `is_edit_locked INTEGER NOT NULL DEFAULT 0`
- `lock_owner_user_id INTEGER`
- `lock_acquired_at TEXT`
- `lock_expires_at TEXT`
- `revision INTEGER NOT NULL DEFAULT 1`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 제약:
- `(view_id, version_no)` unique
- `status` in (`draft`, `published`, `active`, `deprecated`)

권장 운영 규칙:
- 하나의 `view_id` 아래에는 `draft` 여러 개를 허용할지, 하나만 허용할지 정책 결정 필요
- MVP 에서는 `view_id` 당 동시 `draft` 1개로 제한하는 것이 단순하다
- `active` 는 `view_id` 당 최대 1개여야 한다

### 2.3 view_version_nodes
역할:
- 특정 version snapshot 에 속한 node 저장

권장 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_version_id INTEGER NOT NULL`
- `element_key TEXT NOT NULL`
- `parent_node_id INTEGER`
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

설계 메모:
- `parent_node_id` 는 같은 `view_version_id` 내부 row 를 참조해야 한다
- version 간 row id 는 바뀌어도 `element_key` 는 유지하는 것이 바람직하다

### 2.4 view_version_edges
역할:
- 특정 version snapshot 에 속한 edge 저장

권장 컬럼:
- `id INTEGER PRIMARY KEY`
- `view_version_id INTEGER NOT NULL`
- `element_key TEXT NOT NULL`
- `association_code TEXT NOT NULL`
- `notation_code TEXT`
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

설계 메모:
- 초기 migration 단계에서는 `source_node_id`, `target_node_id` 로 충분하다
- 장기적으로 version 간 안정 참조를 위해 `source_element_key`, `target_element_key` 를 병행하는 것이 좋다

## 3. 권장 관계

- `views 1 --- N view_versions`
- `view_versions 1 --- N view_version_nodes`
- `view_versions 1 --- N view_version_edges`
- `view_version_nodes 1 --- N child view_version_nodes`
- `view_version_nodes 1 --- N source view_version_edges`
- `view_version_nodes 1 --- N target view_version_edges`

## 4. 상태 모델 권장 해석

### 4.1 draft
- 편집 가능
- monitoring 에 직접 사용하지 않음

### 4.2 published
- publish 완료 snapshot
- active 전환 후보

### 4.3 active
- 현재 monitoring 이 참조하는 운영 버전
- 읽기 전용

### 4.4 deprecated
- 더 이상 운영 기준으로 쓰지 않는 과거 버전

설계 메모:
- 구현 단순화를 위해 `published` + `is_active` 조합으로도 가능하다
- 다만 질의와 운영 정책 설명은 `status='active'` 가 더 직관적이다

## 5. 최소 질의 패턴

### 5.1 Editor 열기
- logical view 선택
- 해당 view 의 최신 `draft` version 조회
- 없으면 active 또는 latest published 기준으로 새 draft 생성 후 진입

### 5.2 Monitoring 열기
- `view_id` 의 현재 `active` version 조회
- 해당 version 의 nodes/edges 조회

### 5.3 Publish
- draft version 조회
- 상태를 `published` 로 변경
- 기존 `active` 는 그대로 유지 가능

### 5.4 Active 전환
- chosen published version 의 상태를 `active` 로 변경
- 기존 active version 은 `published` 또는 `deprecated` 로 변경

## 6. Migration 전략

### 6.1 1단계
- 현재 `views`, `view_nodes`, `view_edges` 유지
- `view_versions` 추가
- `view_nodes`, `view_edges` 는 임시로 active snapshot row 로 간주

### 6.2 2단계
- `view_version_nodes`, `view_version_edges` 추가
- 기존 데이터 1회 이관
- API 가 `view_version_id` 를 우선 사용하도록 전환

### 6.3 3단계
- editor 는 draft version 전용 저장
- monitor 는 active version 전용 조회
- 기존 단일 `view_nodes`, `view_edges` 는 compatibility layer 또는 제거 대상

## 7. 인덱스 권장안

- `view_versions(view_id, status)`
- `view_versions(view_id, version_no)`
- `view_version_nodes(view_version_id, parent_node_id)`
- `view_version_nodes(view_version_id, element_key)`
- `view_version_nodes(view_version_id, target_id)`
- `view_version_edges(view_version_id, source_node_id)`
- `view_version_edges(view_version_id, target_node_id)`
- `view_version_edges(view_version_id, element_key)`

## 8. runtime binding 과의 연결 메모

- runtime binding 은 version row id 보다 `element_key` 또는 `target_id` 기준으로 유지하는 편이 안정적이다
- active version 이 바뀌어도 같은 논리 객체라면 runtime overlay 는 새 row 에 이어서 붙을 수 있어야 한다
- 따라서 version snapshot row 자체를 runtime identity 로 쓰는 것은 피하는 것이 좋다

## 9. 요약

- `views` 는 logical root
- `view_versions` 는 draft/published/active snapshot 관리
- `view_version_nodes`, `view_version_edges` 는 실제 구조 snapshot 저장
- `element_key` 는 버전 간 동일 논리 객체를 잇는 안정 키
- 이 구조가 운영 화면 안정성과 publish/rollback 정책을 가장 자연스럽게 지원한다
