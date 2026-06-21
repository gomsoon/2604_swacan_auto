# Software Architecture Runtime Monitoring System

## View Versioning API 초안

버전: Draft 0.1  
작성일: 2026-04-15

목적: `draft / published / active / deprecated` 상태 모델을 기준으로, view versioning 기능에 필요한 최소 API 집합을 정리한다. 이 문서는 이후 Flask endpoint 설계와 frontend 연동 기준으로 사용한다.

참고 문서:
- [190-view-versioning-operational-publish-design-draft.md](C:/2604_swacan_auto/docs/190-view-versioning-operational-publish-design-draft.md)
- [210-view-versioning-erd-draft.md](C:/2604_swacan_auto/docs/210-view-versioning-erd-draft.md)
- [070-minimal-api-draft.md](C:/2604_swacan_auto/docs/070-minimal-api-draft.md)

## 1. 설계 원칙

- `views` 는 logical root 이고, 실제 편집/운영 대상은 `view_versions` 이다.
- editor 는 draft version 을 대상으로 동작한다.
- monitoring 은 active operational version 을 대상으로 동작한다.
- publish 는 draft 를 새 published snapshot 으로 고정하는 행위다.
- active 전환은 published version 중 하나를 운영 기준 버전으로 승인하는 행위다.
- published, active, deprecated 상태의 version 은 직접 편집하지 않는다.
- published 또는 deprecated 상태에서 수정이 필요하면 새 draft 를 복제 생성한다.

## 2. 상태 전이 규칙

- `draft -> published`
- `published -> active`
- `active -> deprecated`
- `published -> deprecated`
- `published -> new draft(clone)`
- `deprecated -> new draft(clone)` 는 선택

금지 규칙:
- `active -> draft` 직접 전환 금지
- `published -> draft` 직접 전환 금지
- `deprecated -> active` 직접 전환보다, 필요 시 정책적으로 허용하거나 새 draft/승인 흐름을 따르도록 분리

## 3. 권장 API 목록

### 3.1 Version 목록 조회
`GET /api/views/{view_id}/versions`

목적:
- logical view 아래의 모든 version 목록 조회

응답 예시:
```json
{
  "items": [
    {
      "id": 11,
      "view_id": 1,
      "version_no": 1,
      "version_code": "v1",
      "status": "active",
      "based_on_version_id": null,
      "description": "운영 중 버전",
      "published_at": "2026-04-15T09:00:00.000+09:00",
      "activated_at": "2026-04-15T09:10:00.000+09:00",
      "created_by_user_id": 1,
      "revision": 3,
      "created_at": "2026-04-15T08:30:00.000+09:00",
      "updated_at": "2026-04-15T09:10:00.000+09:00"
    }
  ]
}
```

### 3.2 Active version 조회
`GET /api/views/{view_id}/active`

목적:
- monitoring 이 사용해야 하는 active operational version 조회

### 3.3 Draft version 조회 또는 생성
`POST /api/views/{view_id}/drafts`

요청 예시:
```json
{
  "based_on_version_id": 11,
  "description": "운영 v1 기반 수정 초안"
}
```

동작:
- `based_on_version_id` 를 기준으로 새 draft snapshot 생성
- MVP 에서는 `view_id` 당 동시 draft 1개 정책을 둘 수 있음

### 3.4 Draft 상세 조회
`GET /api/view-versions/{version_id}`

목적:
- 특정 version 의 메타데이터와 node/edge/layout 전체 조회

주의:
- editor 는 draft version 을 열고
- monitoring 은 active version 을 열어야 한다

### 3.5 Draft 저장
`PUT /api/view-versions/{version_id}`

목적:
- draft version 내부 node/edge/layout 갱신

요청 예시:
```json
{
  "revision": 3,
  "name": "SimpleChatServer",
  "description": "수정 중 초안",
  "nodes": [],
  "edges": []
}
```

규칙:
- draft 상태에서만 허용
- revision mismatch 시 `409`

### 3.6 Publish
`POST /api/view-versions/{version_id}/publish`

목적:
- draft version 을 편집 완료된 published snapshot 으로 승격

규칙:
- draft 상태에서만 허용
- publish 후 해당 version 은 편집 불가
- active 전환은 자동으로 하지 않음

응답 예시:
```json
{
  "version": {
    "id": 15,
    "view_id": 1,
    "status": "published",
    "published_at": "2026-04-15T10:30:00.000+09:00"
  }
}
```

### 3.7 Active 승인/전환
`POST /api/view-versions/{version_id}/activate`

목적:
- published version 을 active operational version 으로 승인/전환

규칙:
- published 상태에서만 허용
- 기존 active version 은 자동으로 `deprecated` 또는 정책상 `published` 로 변경
- 한 logical view 당 active 는 최대 1개

응답 예시:
```json
{
  "version": {
    "id": 15,
    "view_id": 1,
    "status": "active",
    "activated_at": "2026-04-15T10:35:00.000+09:00"
  },
  "previous_active_version_id": 11
}
```

### 3.8 Deprecated 전환
`POST /api/view-versions/{version_id}/deprecate`

목적:
- active 또는 published version 을 운영 기준에서 제외

규칙:
- active 상태를 바로 deprecated 로 내릴 수 있는지 정책 결정 필요
- active 만 존재하는 상황에서는 먼저 다른 version 활성화 후 deprecated 처리하는 편이 안전

### 3.9 새 draft 복제 생성
`POST /api/view-versions/{version_id}/clone-to-draft`

목적:
- published 또는 deprecated 버전을 기준으로 새 draft 생성

의미:
- `published -> draft` 직접 상태 변경이 아니라
- `published 기반 새 draft 생성`으로 처리

## 4. 권장 응답 메타데이터

모든 version 응답에는 가능하면 다음을 포함하는 것이 좋다.

- `status`
- `version_no`
- `version_code`
- `based_on_version_id`
- `published_at`
- `activated_at`
- `created_by_user_id`
- `approved_by_user_id` 또는 `activated_by_user_id`
- `revision`

## 5. 권한 정책 초안

- 일반 사용자:
  - 자신이 접근 가능한 view 의 active/draft 조회 가능
  - draft 저장 가능 여부는 workspace 권한 정책에 따름

- 관리자 또는 권한 있는 승인자:
  - publish 가능
  - active 전환 가능
  - deprecated 처리 가능

MVP 메모:
- 초기에는 `admin` 만 publish/activate 가능하게 두는 것이 단순하다

## 6. 오류 응답 초안

### 6.1 draft가 아닌 version 저장 시
- `409 version_state_conflict`
- 메시지: `only draft versions can be edited`

### 6.2 published가 아닌 version activate 시
- `409 version_state_conflict`
- 메시지: `only published versions can be activated`

### 6.3 동시 draft 정책 위반 시
- `409 draft_conflict`
- 메시지: `draft version already exists for view`

### 6.4 revision mismatch
- `409 revision_mismatch`

## 7. Frontend 연동 메모

- view 목록 화면은 logical view 기준 목록을 보여준다
- editor 진입 시 최신 draft 를 열거나, 없으면 draft 생성 API 를 먼저 호출한다
- monitoring 진입 시 active version 조회 후 해당 version 을 연다
- 관리자 화면은 version 목록, publish 버튼, activate 버튼, 현재 active 표시를 제공해야 한다

## 8. 요약

- `published` 는 승인 대기/배포 후보 고정본
- `active` 는 실제 운영 중 버전
- `published -> draft` 는 직접 상태 전환이 아니라 `새 draft 생성`으로 처리
- MVP 에서는 이 API 집합으로 운영/편집 분리 구조를 충분히 구현할 수 있다
