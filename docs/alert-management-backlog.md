# Alert Management Backlog

## 1. 목적

이 문서는 현재까지 구현된 alert 관리 기능을 정리하고, 이후 MVP 단계에서 이어서 개발할 항목을 backlog 형태로 관리하기 위한 기준 문서이다.

alert 관리 기능은 단순히 alert를 생성하는 수준을 넘어서, 운영자가 실제로 alert를 확인하고 상태를 변경하며 원인과 영향 범위를 판단할 수 있는 수준까지 발전시키는 것을 목표로 한다.

## 2. 현재까지 구현된 기능

### 2.1 Alert 생성과 해소

- `latest_states`와 threshold rule 평가 결과를 기반으로 `alert_instances`를 생성한다.
- 동일한 `monitored_object`와 동일한 `alert_code`에 대해서는 반복 발생 시 `repeat_count`를 증가시키고 최신 메시지를 갱신한다.
- 조건이 해소되면 기존 alert를 `resolved` 상태로 전환한다.
- `monitored_object_id` 기준으로 alert를 저장하여, 여러 active view에 동일 alert를 fan-out 할 수 있다.

### 2.2 Alert lifecycle

- 현재 지원 상태:
  - `open`
  - `in_progress`
  - `suppressed`
  - `resolved`
- 운영자는 관리 화면에서 alert 상태를 직접 전환할 수 있다.
- `resolved` 상태에서는 `resolved_at`, `resolved_by_user_id`가 기록된다.
- 수동으로 `in_progress` 또는 `suppressed`로 변경한 alert는 동일 조건이 반복 발생해도 자동으로 `open`으로 되돌리지 않는다.

### 2.3 ACK 처리

- 운영자는 alert를 `ACK` 또는 `ACK 해제`할 수 있다.
- `acknowledged_at`, `acknowledged_by_user_id`, `ack_note`가 저장된다.
- resolved alert는 ACK할 수 없다.

### 2.4 Rule 기반 threshold 관리

- `alert_rules`를 관리자 화면에서 생성, 수정, 활성화, 비활성화할 수 있다.
- rule scope:
  - `object_type`
  - `monitored_object`
- rule은 다음 속성을 가진다.
  - `state_type`
  - `metric_key`
  - `comparison`
  - `warning_threshold`
  - `critical_threshold`

### 2.5 Rule preview와 영향도 확인

- 특정 rule에 대해 현재 매칭되는 monitored object 목록을 조회할 수 있다.
- preview summary에서 다음 정보를 확인할 수 있다.
  - `matched_object_count`
  - `active_view_count`
  - `active_node_count`
  - `open_alert_count`
  - `source_rule_open_alert_count`
  - `metric_available_count`
  - `warning_match_count`
  - `critical_match_count`
- 각 monitored object에 대해 다음 정보를 확인할 수 있다.
  - `display_name`
  - `runtime_binding_key`
  - `object_type`
  - `active_view_count`
  - `active_node_count`
  - `open_alert_count`
  - `source_rule_open_alert_count`
  - `latest_state_status`
  - `latest_state_severity`
  - `latest_received_at`
  - `current_metric_value`
  - `threshold_level`

### 2.6 Event 연계

- raw event는 그대로 저장된다.
- 반복 event는 `grouped_events`로 요약된다.
- grouped event에서 raw event drill-down이 가능하다.
- alert와 event는 모두 monitored object 기준으로 운영 화면에 fan-out 된다.

### 2.7 운영 화면 반영

- monitoring 화면에서 active view 기준 alert 목록을 조회할 수 있다.
- admin 화면에서 alert 목록, 상태, ACK, source rule, 상태 메모를 확인할 수 있다.
- monitoring/admin 모두 `active` 필터 개념을 사용하여 unresolved alert를 조회할 수 있다.

### 2.8 테스트

- alert lifecycle, ACK, status transition, preview, grouped event 관련 경계값 테스트가 추가되어 있다.
- 현재 regression 기준:
  - `199 passed`
  - `2 skipped`
- 앞으로도 test case는 `boundary value analysis` 기준을 우선 적용한다.

## 3. 현재 구조의 강점

- runtime identity가 `monitored_object` 기준으로 분리되어 있어, 동일 대상이 여러 view에 존재해도 alert는 한 번만 생성하고 여러 화면에 표시할 수 있다.
- alert rule preview가 단순 목록을 넘어서 실제 현재 상태 기반 영향도까지 보여준다.
- ACK와 상태 전이를 분리하여 운영자가 더 세밀하게 대응할 수 있다.
- grouped event와 retention/cleanup 구조가 이미 있어 운영 부하를 줄일 기반이 마련되어 있다.

## 4. 현재 구조에서 더 다듬으면 좋은 포인트

### 4.1 운영 이력 부족

- 현재는 현재 상태와 최근 메모만 볼 수 있지만, 누가 언제 어떤 상태 전이를 했는지 이력으로 추적하기 어렵다.

### 4.2 Suppression 의미 고도화 부족

- 현재 `suppressed`는 상태값으로만 존재한다.
- suppression 기간, 자동 해제, 규칙 단위 suppression 등은 아직 없다.

### 4.3 Rule 영향도 시뮬레이션 부족

- 현재 preview는 “지금 기준” 영향도만 보여준다.
- threshold를 변경했을 때 어떤 object가 새롭게 warning/critical이 되는지 비교하는 기능은 아직 없다.

### 4.4 운영자 처리 흐름 부족

- `ACK`와 `status`는 있으나, 운영자 메모 이력, 처리 담당자, 처리 시작/종료 기준 시간, resolution reason 같은 운영 메타데이터는 아직 부족하다.

### 4.5 Alert fan-out 가시성 부족

- 현재 구조상 여러 active view에 fan-out 할 수 있지만, 특정 alert가 어떤 active view에 표시되는지 직접 확인하는 UI는 아직 없다.

## 5. 우선순위 Backlog

### P1. Alert 운영 이력 추가

- 목표:
  - alert 상태 변경, ACK, 메모 변경 이력을 별도 테이블로 기록
- 제안 테이블:
  - `alert_history`
- 주요 필드 예시:
  - `alert_instance_id`
  - `action_type`
  - `previous_status`
  - `new_status`
  - `performed_by_user_id`
  - `note`
  - `created_at`
- 기대 효과:
  - 감사 추적 가능
  - 운영자 간 인수인계 개선

### P2. Alert suppression 고도화

- 목표:
  - `suppressed`를 일시적인 운영 도구로 확장
- 후보 기능:
  - suppression until timestamp
  - source rule 단위 suppression
  - monitored object 단위 suppression
  - suppression reason 필수화
- 기대 효과:
  - known noise를 더 안전하게 제어

### P3. Rule 변경 영향도 시뮬레이션

- 목표:
  - 현재 preview를 넘어서 “변경 후 영향”을 비교
- 후보 기능:
  - threshold draft 값 입력 후 dry-run preview
  - warning/critical 매칭 변화량 표시
  - 새로 열릴 가능성이 있는 alert 대상 목록 표시
- 기대 효과:
  - 운영자가 rule 변경을 더 안전하게 수행 가능

### P4. Alert 운영 상태 추가 확장

- 목표:
  - 현재 상태 집합을 더 운영 친화적으로 확장
- 후보 상태:
  - `acknowledged`
  - `monitoring`
  - `closed_with_exception`
- 참고:
  - 현재는 ACK를 별도 필드로 유지하고 있으므로, 상태 체계와의 관계를 먼저 정리해야 한다.

### P5. Operator note history와 resolution reason

- 목표:
  - 마지막 메모만이 아니라 메모 히스토리와 해결 사유를 남김
- 후보 기능:
  - resolution reason
  - operator note append-only log
  - 마지막 메모와 전체 이력 분리

### P6. Alert fan-out visibility

- 목표:
  - 특정 alert가 현재 어떤 active view에 표시되는지 확인
- 후보 기능:
  - active view count
  - active view 목록
  - 해당 view 내 node count
- 기대 효과:
  - 운영 영향 범위 파악이 쉬워진다.

### P7. Alert correlation

- 목표:
  - 동일 monitored object 또는 동일 source rule에서 연관된 alert끼리 묶기
- 후보 기능:
  - parent/child alert
  - correlated alert group
  - root cause 후보 표시

## 6. Metamodel 작업으로 넘어가기 전 기준

alert 관리 기능은 아래 조건이 충족되면 1차 정리 완료로 보고, metamodel draft 내부 편집으로 우선순위를 이동해도 된다.

- lifecycle이 운영 화면에서 일관되게 동작한다.
- rule preview가 현재 운영 판단에 충분한 정보를 제공한다.
- ACK와 상태 전이가 경계값 테스트 기준으로 안정화되어 있다.
- alert, event, grouped event의 저장 및 cleanup 정책이 정리되어 있다.

현재 기준으로는 위 조건에 상당 부분 도달했으며, 다음 선택지는 아래 둘 중 하나이다.

- alert 운영 이력까지 먼저 넣고 alert 기능을 한 단계 더 완성
- 현재 수준을 1차 완료로 보고 metamodel draft 편집 기능으로 우선순위를 이동

## 7. 추천 다음 순서

1. `alert_history` 설계 초안
2. suppression 정책 정리
3. rule 영향도 dry-run preview
4. 이후 metamodel draft 내부 편집 기능으로 전환
