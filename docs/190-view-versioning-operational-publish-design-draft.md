# Software Architecture Runtime Monitoring System

## View Versioning / Publish / Active Operational View 설계 초안
버전: Draft 0.2  
작성일: 2026-04-16

목적: architecture view를 편집용 `draft`, 승인 대기용 `published`, 운영용 `active` snapshot으로 분리하는 설계 방향을 정리한다. 이 문서는 이후 ERD, SQLite 스키마, API, 화면 흐름의 기준 초안으로 사용한다.

참고 문서:
- [001-software-architecture-runtime-monitoring-mvp-plan.md](C:/2604_swacan_auto/docs/001-software-architecture-runtime-monitoring-mvp-plan.md)
- [150-mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/150-mvp-transition-roadmap.md)
- [280-terminology-guidelines.md](C:/2604_swacan_auto/docs/280-terminology-guidelines.md)
- [210-view-versioning-erd-draft.md](C:/2604_swacan_auto/docs/210-view-versioning-erd-draft.md)
- [230-runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/230-runtime-identity-binding-design-draft.md)

## 1. 문제 정의

- 운영자가 관제 중인 화면은 다른 사용자의 편집으로 즉시 바뀌면 안 된다.
- 같은 logical view라도 편집 중인 작업본과 실제 운영 중인 화면은 분리돼야 한다.
- publish는 기존 운영본을 덮어쓰는 동작이 아니라, 고정된 snapshot을 새로 만드는 동작이어야 한다.
- 하나의 server, process, thread를 여러 view가 동시에 표시할 수 있으므로, view snapshot과 runtime identity는 장기적으로 분리돼야 한다.

## 2. 용어 적용

- 운영자가 runtime 상태를 확인하는 읽기 중심 화면은 `Monitoring View`로 부른다.
- 아키텍처 layout과 노드를 수정하는 화면은 `Architecture Editor`로 부른다.
- `Logical View`는 사용자 관점의 논리 화면 단위이고, `View Version`은 그 시점별 snapshot이다.
- 따라서 `Monitoring View`와 `Logical View`는 같은 단어 `view`를 쓰더라도 다른 계층의 개념이다.

## 3. 핵심 원칙

- 편집은 항상 `draft view version`에서만 수행한다.
- 운영 monitoring은 항상 `active view version`을 기준으로 수행한다.
- `published`는 승인 대기 또는 배포 후보인 고정 snapshot이다.
- `active`는 실제 운영 중인 snapshot이다.
- `deprecated`는 더 이상 운영 기준으로 사용하지 않는 과거 snapshot이다.
- `published -> draft`는 직접 상태 변경이 아니라 `published 기반 새 draft 생성`으로 처리한다.

## 4. 상태 모델

### 4.1 draft
- 편집 가능
- node/edge/layout 수정 가능
- 운영 화면에서 직접 사용하지 않음

### 4.2 published
- 편집 완료된 고정 snapshot
- 승인 대기 또는 배포 후보
- 수정 불가

### 4.3 active
- 실제 monitoring 화면이 참조하는 운영 snapshot
- 수정 불가
- 하나의 logical view에 대해 동시에 하나만 존재해야 한다

### 4.4 deprecated
- 더 이상 운영 기준으로 사용하지 않는 과거 snapshot
- rollback 또는 감사 추적용으로 보존

## 5. 권장 상태 전이

- `draft -> published`
- `published -> active`
- `published -> deprecated`
- `active -> deprecated`
- `published -> new draft(clone)`
- `deprecated -> new draft(clone)`는 선택적으로 허용 가능

운영 규칙:
- 새 version이 `active`가 되면 기존 `active`는 자동으로 `deprecated`로 전환한다.
- `published`, `active`, `deprecated`는 직접 수정하지 않는다.
- 수정이 필요하면 기존 version을 기반으로 새 `draft`를 만든다.

## 6. 핵심 개념

### 6.1 Logical View
- 사용자가 인식하는 하나의 architecture 화면
- 예: `SimpleChatServer 운영 View`

### 6.2 View Version
- 특정 시점의 snapshot
- logical view 아래에 여러 version이 존재할 수 있다

### 6.3 Element Key
- version 간 동일한 논리 객체를 잇는 안정 키
- 예:
  - `srv_main`
  - `proc_chat_main`
  - `agent_local_main`

장점:
- version row id가 바뀌어도 같은 논리 객체를 추적할 수 있다
- runtime binding, event overlay, alert fan-out을 안정적으로 연결할 수 있다

## 7. 운영/편집 분리의 의미

### 7.1 Editor
- logical view를 열면 현재 `draft`가 있으면 그 version을 연다
- draft가 없으면 active 또는 published를 기준으로 새 draft를 생성한다

### 7.2 Monitoring
- logical view를 열면 현재 `active` version만 본다
- active가 없고 초기 작성 단계라면 선택적으로 draft preview를 허용할 수 있다
- draft 편집은 운영 화면에 즉시 반영되지 않는다

### 7.3 Publish
- draft를 고정 snapshot으로 승격한다
- 운영 반영은 하지 않는다

### 7.4 Activate
- published snapshot을 active로 승격한다
- monitoring은 이후부터 이 snapshot을 기준으로 동작한다

## 8. runtime identity와의 연결

view versioning만으로는 운영 문제가 완전히 해결되지 않는다. 같은 process를 여러 active view에서 동시에 표시할 수 있기 때문이다.

따라서 다음 원칙을 함께 가져가야 한다.
- view snapshot은 화면 표현 책임을 가진다
- 실제 runtime state, event, alert는 별도의 monitored object에 귀속된다
- active view는 자신이 참조하는 monitored object를 화면에 fan-out해서 보여준다

즉:
- 생성 단위: monitored object
- 표현 단위: active view version node

이 구조는 [230-runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/230-runtime-identity-binding-design-draft.md)에서 별도로 정리한다.

## 9. 최소 API 방향

### 9.1 Version 목록 조회
- `GET /api/views/{view_id}/versions`

### 9.2 Draft 생성
- `POST /api/views/{view_id}/drafts`

### 9.3 Draft 상세 조회
- `GET /api/views/{view_id}/draft`

### 9.4 Draft 편집
- `PUT /api/view-versions/{version_id}`
- 또는 node/edge 단위 CRUD API 사용

### 9.5 Publish
- `POST /api/view-versions/{version_id}/publish`

### 9.6 Activate
- `POST /api/view-versions/{version_id}/activate`

### 9.7 Active 조회
- `GET /api/views/{view_id}/active`

## 10. 구현 순서 권장

1. `views`를 logical root로 유지
2. `view_versions`, `view_version_nodes`, `view_version_edges` 도입
3. editor를 draft 기준으로 전환
4. monitoring을 active 기준으로 전환
5. publish / activate lifecycle 추가
6. runtime identity 분리 계층 추가

## 11. 요약

- 운영 안정성을 위해 편집본과 운영본은 분리돼야 한다.
- `draft / published / active / deprecated` 상태 모델은 운영 승인 흐름과 잘 맞는다.
- publish는 overwrite가 아니라 snapshot 생성이다.
- `element_key`는 version 간 논리 객체를 잇는 핵심 키다.
- 장기적으로는 view snapshot과 runtime identity를 분리해, alert/event/latest state가 monitored object에 귀속되도록 가야 한다.
