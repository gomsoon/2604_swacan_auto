# Alert Lifecycle API Draft

## 1. 목적

이 문서는 `alert_instances(current)` 와 `alert_history(archive)` 분리 구조를 전제로, 운영자와 관리자 화면이 사용할 alert lifecycle API 초안을 정리한다.

대상 범위:
- 현재 alert 조회
- 수동 resolve
- archive history 조회
- 시간 경과 정책과 action log 확장 여지

## 2. API 설계 원칙

- 현재 살아 있는 alert는 current API로 조회한다.
- 종료된 alert lifecycle은 history API로 조회한다.
- 수동 resolve는 current alert를 archive history로 이동시키는 동작으로 정의한다.
- `resolution_source`와 `resolution_reason`은 응답에도 명시적으로 포함한다.
- 경계값 검증은 기존 기준대로 `boundary value analysis` 우선 적용한다.

## 3. Current alert API

### 3.1 목록 조회

`GET /api/admin/alerts`

역할:
- unresolved current alert 조회

주요 query:
- `status`
  - `active`
  - `open`
  - `in_progress`
  - `suppressed`
- `severity`
- `is_acknowledged`
- `limit`

응답 예시:

```json
{
  "items": [
    {
      "id": 101,
      "monitored_object_id": 1302,
      "display_name": "App Process",
      "alert_code": "process.down",
      "severity": "critical",
      "status": "open",
      "is_acknowledged": false,
      "source_rule_id": null,
      "first_occurred_at": "2026-04-16T09:00:00.000+09:00",
      "last_occurred_at": "2026-04-16T09:05:00.000+09:00",
      "repeat_count": 3,
      "latest_message": "process not found"
    }
  ]
}
```

### 3.2 상세 조회

`GET /api/admin/alerts/{alert_id}`

역할:
- 특정 current alert 상세 조회

응답에는 다음을 포함하는 것을 권장한다.
- current 상태
- source rule
- ack 정보
- 최근 status note
- active fan-out view/node 요약

### 3.3 ACK / ACK 해제

`PATCH /api/admin/alerts/{alert_id}`

요청 예시:

```json
{
  "acknowledged": true,
  "ack_note": "운영자가 확인함"
}
```

설명:
- current alert에만 허용
- 종료된 alert에는 허용하지 않음

### 3.4 status 전이

`PATCH /api/admin/alerts/{alert_id}/status`

요청 예시:

```json
{
  "status": "in_progress",
  "status_note": "조사중"
}
```

허용 대상:
- `open`
- `in_progress`
- `suppressed`

주의:
- 이 API는 status 전이용
- 수동 resolve는 별도 endpoint로 분리하는 것이 더 명확하다

### 3.5 수동 resolve

`POST /api/admin/alerts/{alert_id}/resolve`

요청 예시:

```json
{
  "resolution_reason": "운영자가 수동으로 종료 처리",
  "note": "backend 장애로 auto resolve 되지 않음"
}
```

동작:
1. current alert 조회
2. archive history row 생성
3. `resolution_source = manual_operator`
4. current alert 삭제
5. 결과로 archive history payload 반환

응답 예시:

```json
{
  "history": {
    "id": 9001,
    "monitored_object_id": 1302,
    "alert_code": "process.down",
    "opened_at": "2026-04-16T09:00:00.000+09:00",
    "resolved_at": "2026-04-16T09:30:00.000+09:00",
    "final_status": "resolved",
    "resolution_source": "manual_operator",
    "resolution_reason": "운영자가 수동으로 종료 처리",
    "resolved_by_user_id": 1
  }
}
```

### 3.6 bulk resolve

`POST /api/admin/alerts/resolve-bulk`

요청 예시:

```json
{
  "alert_ids": [101, 102, 103],
  "resolution_reason": "점검 종료 후 수동 정리"
}
```

설명:
- 운영자가 오래 남은 current alert를 일괄 정리할 때 필요
- MVP에서 가치가 높다

## 4. Archive history API

### 4.1 목록 조회

`GET /api/admin/alert-history`

주요 query:
- `monitored_object_id`
- `alert_code`
- `source_rule_id`
- `resolution_source`
- `resolved_by_user_id`
- `limit`

응답 예시:

```json
{
  "items": [
    {
      "id": 9001,
      "monitored_object_id": 1302,
      "display_name": "App Process",
      "alert_code": "process.down",
      "opened_at": "2026-04-16T09:00:00.000+09:00",
      "resolved_at": "2026-04-16T09:30:00.000+09:00",
      "first_severity": "critical",
      "highest_severity": "critical",
      "final_severity": "critical",
      "repeat_count": 3,
      "was_acknowledged": true,
      "resolution_source": "manual_operator",
      "resolution_reason": "운영자가 수동으로 종료 처리"
    }
  ]
}
```

### 4.2 상세 조회

`GET /api/admin/alert-history/{history_id}`

역할:
- 특정 lifecycle summary 상세

선택 사항:
- 필요한 경우 action log 요약도 함께 포함

### 4.3 모니터링 화면의 종료 이력 조회

`GET /api/views/{view_id}/alert-history`

역할:
- active view에 fan-out 되는 monitored object 기준 종료 이력 조회

주요 query:
- `limit`
- `resolution_source`
- `severity`

## 5. Action log API (선택)

### 5.1 현재 alert action log

`GET /api/admin/alerts/{alert_id}/actions`

### 5.2 종료된 lifecycle action log

`GET /api/admin/alert-history/{history_id}/actions`

설명:
- MVP에서 바로 필요하지 않으면 뒤로 미룰 수 있다
- 현재 skeleton `alert_history`를 이 역할로 재정의하는 방식도 가능

## 6. Policy API 초안

### 6.1 시간 경과 escalation / auto resolve 정책 조회

`GET /api/admin/alert-policies`

### 6.2 정책 생성/수정

`POST /api/admin/alert-policies`
`PATCH /api/admin/alert-policies/{id}`

핵심 필드:
- `escalate_after_minutes`
- `escalate_to_severity`
- `auto_resolve_enabled`
- `auto_resolve_after_minutes`
- `auto_resolve_only_for_severity`

## 7. 경계값 테스트 후보

### 7.1 current alert list
- `limit = 1`
- `limit = 100`
- `limit = 0`
- `limit = 101`
- `limit = abc`

### 7.2 manual resolve
- 빈 `resolution_reason`
- `resolution_reason` 최대 길이
- 최대 길이 + 1
- 이미 resolve 된 alert에 대한 재요청
- 존재하지 않는 `alert_id`

### 7.3 bulk resolve
- `alert_ids` 길이 0
- 1
- 최대 허용 개수
- 최대 허용 개수 + 1
- 중복 ID 포함

### 7.4 history query
- `limit` 경계
- 없는 `resolution_source`
- 없는 `history_id`

## 8. 단계적 적용 제안

### Step 1
- `POST /api/admin/alerts/{id}/resolve`
- `GET /api/admin/alert-history`

### Step 2
- bulk resolve
- monitoring history 조회

### Step 3
- action log API
- 시간 경과 policy API

## 9. 현재 추천 결론

현재 바로 구현 가치가 높은 API는 아래 두 개다.

1. `POST /api/admin/alerts/{id}/resolve`
2. `GET /api/admin/alert-history`

이 두 개가 들어가면:
- current alert와 종료 이력이 명확히 분리되고
- 운영자가 자동 resolve 실패 상황을 직접 정리할 수 있으며
- frontend도 current/history를 구분해서 단순하게 표현할 수 있다.
