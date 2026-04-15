# Software Architecture Runtime Monitoring System

## View Versioning / Publish / Active Operational View 설계 초안

버전: Draft 0.1  
작성일: 2026-04-15

목적: architecture view 를 편집용 draft 와 운영용 active snapshot 으로 분리하기 위한 설계 방향을 정리한다. 이 문서는 이후 ERD, API, 화면 설계의 기준 초안으로 사용한다.

참고 문서:
- [software-architecture-runtime-monitoring-mvp-plan.md](C:/2604_swacan_auto/docs/software-architecture-runtime-monitoring-mvp-plan.md)
- [backend-detailed-requirements.md](C:/2604_swacan_auto/docs/backend-detailed-requirements.md)
- [frontend-detailed-requirements.md](C:/2604_swacan_auto/docs/frontend-detailed-requirements.md)
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)

## 1. 문제 정의

- 현재 `views`, `view_nodes`, `view_edges` 가 하나의 편집 대상이자 하나의 운영 대상처럼 동작하면, 운영자가 관제 중인 화면 구조가 다른 사용자의 편집에 의해 즉시 바뀔 수 있다.
- 이 구조는 관제 도구 관점에서 위험하다. 장애 분석 중에 화면 구조가 바뀌면 운영자가 무엇을 보고 있는지 기준이 흔들리기 때문이다.
- 따라서 편집본과 운영본을 분리하고, 운영 화면은 명시적으로 배포된 snapshot 을 기준으로 동작해야 한다.

## 2. 설계 원칙

- 편집은 항상 `draft view version` 에 대해 수행한다.
- 운영 monitoring 은 항상 `active operational view version` 을 기준으로 수행한다.
- publish 는 기존 운영 row 를 수정하는 방식이 아니라, draft 를 기준으로 새로운 version snapshot 을 만드는 방식이어야 한다.
- active operational version 전환은 publish 와 분리할 수 있어야 한다.
- rollback 을 위해 과거 published version 을 다시 active 로 전환할 수 있어야 한다.
- version 별 row id 는 달라질 수 있으므로, 논리 객체 동일성을 위해 별도 `element_key` 를 유지하는 것이 바람직하다.

## 3. 핵심 개념

### 3.1 Logical View
- 사용자 입장에서 하나의 architecture 화면을 의미한다.
- 예: `SimpleChatServer 운영 view`

### 3.2 View Version
- 특정 시점의 snapshot 이다.
- 하나의 logical view 아래에 여러 version 이 존재할 수 있다.

### 3.3 Draft Version
- 편집 가능한 작업본
- 운영 화면에서는 직접 사용하지 않는다.

### 3.4 Published Version
- 배포 가능한 고정본
- immutable snapshot 으로 취급하는 것이 바람직하다.

### 3.5 Active Operational Version
- 실제 monitoring 화면이 참조하는 현재 운영 기준 버전
- published version 중 하나를 가리킨다.

## 4. 권장 상태 모델

- `draft`
- `published`
- `active`
- `deprecated`

설계 메모:
- 구현 단순화를 위해 `active` 를 published 의 한 종류로 볼 수도 있다.
- 다만 의미상으로는 `published` 와 `active` 를 구분하는 편이 운영 정책을 설명하기 쉽다.

## 5. 권장 데이터 모델 방향

### 5.1 logical view 루트
- `views`
- 역할:
  - view 의 논리적 루트
  - 이름, 설명, owner, workspace 등의 상위 정보 보관

### 5.2 version 테이블
- 예시: `view_versions`
- 핵심 컬럼 제안:
  - `id`
  - `view_id`
  - `version_no` 또는 `version_code`
  - `status`
  - `based_on_version_id`
  - `published_at`
  - `activated_at`
  - `created_by_user_id`
  - `created_at`
  - `updated_at`

### 5.3 version별 node/edge
- 예시:
  - `view_version_nodes`
  - `view_version_edges`
- 현재 `view_nodes`, `view_edges` 는 장기적으로 이 구조로 이동하는 것이 바람직하다.

### 5.4 element_key
- version 간 동일 논리 객체를 이어주기 위한 안정 키
- 예:
  - `srv_main`
  - `proc_worker_group`
  - `agent_local_main`
- 장점:
  - row id 가 바뀌어도 runtime binding 을 유지하기 쉽다.
  - publish 시 snapshot row 가 새로 생겨도 이벤트 매핑 기준이 유지된다.

## 6. 동작 흐름

### 6.1 Draft 생성
- 기존 active 또는 published version 을 기준으로 새 draft 생성
- 편집자는 이 draft 만 수정

### 6.2 저장
- draft 내부 row 만 갱신
- 운영 화면에는 영향 없음

### 6.3 Publish
- draft 를 immutable published snapshot 으로 승격
- 기존 active version 은 자동으로 바꾸지 않을 수 있음

### 6.4 Active 전환
- 관리자 또는 권한 있는 사용자가 특정 published version 을 active operational version 으로 전환
- monitoring 화면은 이후부터 새 active version 을 기준으로 열림

### 6.5 Rollback
- 이전 published version 을 다시 active 로 지정

## 7. Frontend 관점 요구사항

- editor 는 현재 보고 있는 대상이 `draft` 임을 명확히 보여주어야 한다.
- monitoring 은 현재 보고 있는 대상이 `active operational version` 임을 보여주어야 한다.
- publish 이후에도 운영 화면이 자동 변경되는지, 수동 active 전환이 필요한지 사용자에게 분명히 안내해야 한다.
- version 목록, 현재 active 표시, publish 버튼, active 전환 버튼이 필요하다.

## 8. Backend 관점 요구사항

- draft 저장과 publish 를 분리해야 한다.
- active version 조회 API 가 필요하다.
- monitoring latest state 조회는 active version 기준 node/edge 구조를 참조해야 한다.
- revision 충돌은 draft version 내부에서만 관리하면 된다.
- 운영 화면은 draft row 를 직접 조회하지 않아야 한다.

## 9. Migration 관점 메모

- 현재 구조는 `views`, `view_nodes`, `view_edges` 가 단일 버전처럼 동작한다.
- MVP 초기 전환은 다음 순서가 적절하다.

1. `views` 는 logical root 로 유지
2. `view_versions` 추가
3. 기존 `view_nodes`, `view_edges` 를 `view_version_nodes`, `view_version_edges` 구조로 이관
4. active version 조회 API 도입
5. editor/monitoring 화면 분리

## 10. 요약

- 운영 안정성을 위해 편집본과 운영본은 분리되어야 한다.
- 가장 적절한 구조는 `logical view + draft/published/active version snapshot` 모델이다.
- publish 는 덮어쓰기가 아니라 snapshot 생성이어야 한다.
- runtime binding 과 event 매핑을 위해 `element_key` 같은 안정 식별자 도입이 유리하다.
- 이 설계는 이후 view versioning ERD 와 publish/active 전환 API 설계의 기준이 된다.

## 11. 권장 최소 API 초안

### 11.1 Version 조회
- `GET /api/views/{view_id}/versions`
- 목적:
  - logical view 아래의 draft/published/active/deprecated version 목록 조회

### 11.2 Draft 생성
- `POST /api/views/{view_id}/drafts`
- 목적:
  - 특정 published 또는 active version 을 기준으로 새 draft 생성

### 11.3 Draft 저장
- `PUT /api/view-versions/{version_id}`
- 목적:
  - draft version 내부 node/edge/layout 갱신

### 11.4 Publish
- `POST /api/view-versions/{version_id}/publish`
- 목적:
  - draft version 을 새 published snapshot 으로 승격

### 11.5 Active 전환
- `POST /api/view-versions/{version_id}/activate`
- 목적:
  - 특정 published version 을 active operational version 으로 지정

### 11.6 Active 조회
- `GET /api/views/{view_id}/active`
- 목적:
  - monitoring 화면이 사용해야 하는 현재 active version 반환

## 12. 권장 구현 순서

1. `view_versions` 테이블과 상태 모델 추가
2. 기존 `views` 와 `view_nodes/view_edges` 를 logical root + active snapshot 관점으로 해석하는 compatibility layer 도입
3. editor 는 draft version 기준으로 저장
4. monitoring 은 active version 기준으로 조회
5. publish / activate API 추가
6. 이후 `element_key` 와 version별 node/edge 이관 진행
