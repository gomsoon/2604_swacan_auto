# Alert Lifecycle SQLite Draft

## 1. 목적

이 문서는 `alert_instances(current)` 와 `alert_history(archive)` 를 분리하는 방향으로 SQLite 스키마 초안을 정리하기 위한 문서이다.

대상 범위:
- current alert 저장 구조
- archive history 저장 구조
- 선택적 action log 구조
- 수동/자동 resolve와 시간 경과 정책 확장 여지

## 2. 설계 원칙

- 현재 살아 있는 alert는 `alert_instances`에서 관리한다.
- 종료된 alert lifecycle은 `alert_history`로 이동한다.
- `alert_history`는 `1 lifecycle = 1 row`를 목표로 한다.
- ACK, 상태 전이, 메모, severity escalation 같은 세부 action은 필요 시 `alert_action_log`에 append-only로 기록한다.
- 수동 resolve와 자동 resolve는 `resolution_source / resolution_reason`으로 구분한다.

## 3. 권장 테이블 구조

### 3.1 `alert_instances`

역할:
- 현재 살아 있는 alert 집합
- hot update 대상

권장 유지 필드:
- `id`
- `monitored_object_id`
- `alert_code`
- `source_rule_id`
- `severity`
- `status`
- `acknowledged_at`
- `acknowledged_by_user_id`
- `ack_note`
- `status_updated_at`
- `status_updated_by_user_id`
- `status_note`
- `first_occurred_at`
- `last_occurred_at`
- `repeat_count`
- `latest_message`
- `metadata_json`
- `created_at`
- `updated_at`

권장 제거/축소 검토:
- `resolved_at`
- `resolved_by_user_id`

이유:
- current alert 테이블은 unresolved alert만 관리하는 방향이 더 적절하다.
- resolved 정보는 archive row에 남기는 것이 의미상 더 명확하다.

### 3.2 `alert_history`

역할:
- 종료된 alert lifecycle summary
- 운영 화면의 종료 이력 기본 단위

권장 컬럼 초안:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `monitored_object_id INTEGER NOT NULL`
- `alert_code TEXT NOT NULL`
- `source_rule_id INTEGER`
- `opened_at TEXT NOT NULL`
- `resolved_at TEXT NOT NULL`
- `first_severity TEXT NOT NULL`
- `highest_severity TEXT NOT NULL`
- `final_severity TEXT NOT NULL`
- `final_status TEXT NOT NULL`
- `repeat_count INTEGER NOT NULL DEFAULT 1`
- `was_acknowledged INTEGER NOT NULL DEFAULT 0 CHECK (was_acknowledged IN (0, 1))`
- `last_acknowledged_at TEXT`
- `last_acknowledged_by_user_id INTEGER`
- `resolution_source TEXT NOT NULL`
- `resolution_reason TEXT`
- `resolved_by_user_id INTEGER`
- `latest_message TEXT`
- `metadata_json TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

권장 enum 예시:
- `final_status`
  - `resolved`
  - `closed_with_exception`
- `resolution_source`
  - `auto_recovery`
  - `manual_operator`
  - `auto_policy_timeout`
  - `system_cleanup`

설명:
- `opened_at`은 해당 lifecycle이 처음 열린 시각
- `resolved_at`은 종료 시각
- `first_severity`, `highest_severity`, `final_severity`를 분리하면 운영자가 lifecycle 전체를 더 잘 이해할 수 있다.

### 3.3 `alert_action_log` (선택)

역할:
- 세부 운영 action append-only log

권장 컬럼 초안:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `alert_instance_id INTEGER`
- `alert_history_id INTEGER`
- `monitored_object_id INTEGER NOT NULL`
- `action_type TEXT NOT NULL`
- `action_source TEXT NOT NULL`
- `previous_status TEXT`
- `new_status TEXT`
- `previous_severity TEXT`
- `new_severity TEXT`
- `performed_by_user_id INTEGER`
- `note TEXT`
- `payload_json TEXT`
- `created_at TEXT NOT NULL`

설명:
- current alert에 대한 action이면 `alert_instance_id` 사용
- 이미 archive로 넘어간 후에도 연결이 필요하면 `alert_history_id` 사용
- MVP에서는 바로 만들지 않고, 필요 시 2단계로 도입 가능

## 4. alert_instances -> alert_history archive 전환

### 4.1 전환 시점

다음 상황에서 archive row를 생성한다.
- worker가 상태 정상화로 auto recovery resolve
- 운영자가 수동 resolve
- 시간 경과 policy에 의해 auto resolve
- cleanup/system policy에 의해 종료

### 4.2 archive insert 흐름

1. current `alert_instances` row 조회
2. lifecycle summary 계산
3. `alert_history` insert
4. 필요 시 `alert_action_log` insert
5. `alert_instances` delete

### 4.3 장점

- current table에는 unresolved alert만 남는다.
- 운영 화면의 종료 이력은 한 줄로 표현된다.
- history는 append-only 중심이라 retention/cleanup이 단순하다.

## 5. 수동 resolve 필드 설계

수동 resolve 시 필요한 정보:
- `resolution_source = 'manual_operator'`
- `resolution_reason`
- `resolved_by_user_id`

권장 UI 입력:
- 운영자가 resolve하면서 note 또는 reason 입력
- bulk resolve도 같은 필드를 공유 가능

## 6. 시간 경과 정책 테이블 초안

시간 경과 escalation / auto resolve를 위해 별도 policy 테이블을 둘 수 있다.

### `alert_policies` 초안

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `scope_type TEXT NOT NULL`
- `object_type TEXT`
- `monitored_object_id INTEGER`
- `source_rule_id INTEGER`
- `escalate_after_minutes INTEGER`
- `escalate_to_severity TEXT`
- `auto_resolve_enabled INTEGER NOT NULL DEFAULT 0 CHECK (auto_resolve_enabled IN (0, 1))`
- `auto_resolve_after_minutes INTEGER`
- `auto_resolve_only_for_severity TEXT`
- `description TEXT`
- `is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1))`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

설명:
- MVP에서 즉시 구현하지 않아도 됨
- 하지만 schema 초안을 먼저 갖고 있으면 확장 방향이 흔들리지 않는다.

## 7. 인덱스 초안

### `alert_instances`
- `(status, severity, last_occurred_at DESC)`
- `(monitored_object_id, alert_code)`
- `(source_rule_id, status)`

### `alert_history`
- `(monitored_object_id, resolved_at DESC)`
- `(alert_code, resolved_at DESC)`
- `(resolution_source, resolved_at DESC)`
- `(source_rule_id, resolved_at DESC)`

### `alert_action_log`
- `(alert_instance_id, created_at DESC)`
- `(alert_history_id, created_at DESC)`
- `(monitored_object_id, created_at DESC)`
- `(action_type, created_at DESC)`

## 8. migration 방향

### Step 1
- 현재 `alert_history`는 skeleton action log로 유지
- 새 archive 테이블을 `alert_history_archive` 같은 임시 이름으로 먼저 추가할 수도 있음

### Step 2
- resolve 시점에 archive insert 경로 추가
- current alert는 delete

### Step 3
- frontend 종료 이력 화면은 archive 테이블을 읽도록 전환

### Step 4
- 기존 skeleton `alert_history`를 `alert_action_log`로 rename 또는 의미 재정의

## 9. 현재 추천 결론

현재 단계에서 바로 권장하는 구현 방향:
- `alert_instances`는 unresolved alert current set으로 유지
- 현재 `alert_history`는 임시 action log로 간주
- archive summary용 새 구조를 별도로 설계해 도입
- 수동 resolve와 auto resolve 모두 archive insert를 공통 경로로 사용

## 10. 추천 다음 순서

1. archive 테이블 이름과 최소 컬럼 확정
2. 수동 resolve API가 archive insert를 수행하도록 설계
3. worker auto recovery resolve가 같은 archive 경로를 쓰도록 정리
4. 이후 `alert_action_log` 도입 여부 결정
