# Alert Lifecycle Redesign Draft

## 1. 목적

이 문서는 현재 구현된 `alert_instances + alert_history skeleton` 구조를 검토하고, 운영 관점에서 더 적절한 alert lifecycle 저장 모델을 제안하기 위한 초안이다.

핵심 목표는 다음과 같다.

- 현재 살아 있는 alert와 종료된 alert 이력을 분리한다.
- 운영 화면에서는 동일 alert lifecycle을 한 줄로 이해하기 쉽게 표현한다.
- 수동 resolve와 자동 resolve를 명확히 구분한다.
- 시간 경과에 따른 자동 escalation / 자동 resolve 정책을 구조적으로 수용한다.
- 향후 alert 운영 기능을 확장하더라도 저장 구조가 과도하게 흔들리지 않도록 한다.

## 2. 현재 구조와 우려 사항

현재 구현은 다음과 같은 특징을 가진다.

- `alert_instances`가 현재 alert 상태를 저장한다.
- 동일한 unresolved alert는 `alert_instances`에서 한 줄로 집계된다.
  - 반복 발생 시 새 row를 만들기보다
  - `repeat_count`, `last_occurred_at`, `latest_message`를 갱신한다.
- `alert_history`는 action row 기반 skeleton으로 동작한다.
- alert 생성 시 `alert_history`에 한 줄이 추가된다.
- ACK, status 변경, resolve 시에도 action row가 추가된다.

이 구조는 감사 추적 관점에서는 장점이 있지만, 운영 화면 관점에서는 다음과 같은 우려가 있다.

- 동일 alert lifecycle이 여러 row로 흩어져 보여 운영자가 한눈에 보기 어렵다.
- 운영자는 보통 `한 번 열린 alert가 언제 열렸고, 언제 닫혔는지`를 1건으로 파악하고 싶다.
- action log와 lifecycle summary가 같은 개념으로 섞이면 frontend 표현도 복잡해진다.

또한 다음 운영 시나리오도 반드시 고려해야 한다.

- backend 장애 등으로 인해 자동 resolve 되지 않는 alert가 남을 수 있다.
- 운영자는 이를 선택해서 수동으로 resolve 해야 한다.
- 일정 시간 이상 해소되지 않은 alert는 severity 상향 또는 자동 resolve 정책이 필요할 수 있다.
- 이러한 해소 방식은 `자동 복구`, `수동 운영자 처리`, `시간 경과 정책`을 구분해서 기록할 수 있어야 한다.

추가로 product 단계에서는 다음 질문도 다시 검토할 가치가 있다.

- 동일 alert의 반복 발생을 현재처럼 `repeat_count` 집계만으로 충분히 표현할 것인가
- 아니면 alert occurrence 자체를 별도 raw ledger로 남길 것인가

현재 MVP 관점에서는 “운영 화면에 한 줄로 보이게 하는 것”이 더 중요하므로, 지금 구조는 실용적이다.
다만 이후 다음 요구가 커질 수 있다.

- alert 발생 간격 분석
- 동일 alert의 반복 패턴 통계
- alert noise / storm 분석
- 특정 alert의 occurrence timeline 재구성

이 경우에는 `current alert summary`와 별도의 `alert occurrence ledger`를 분리하는 구조가 더 적절할 수 있다.

## 3. 제안하는 목표 구조

추천 구조는 다음 세 계층이다.

### 3.1 `alert_instances`

역할:
- 현재 살아 있는 alert만 저장
- 운영 중 자주 변경되는 hot table

예시 상태:
- `open`
- `in_progress`
- `suppressed`

특징:
- ACK, repeat count, latest message, 최신 severity, 최신 상태 메모를 계속 update
- resolve 되면 더 이상 current set에 남지 않음
- 운영 화면에서는 “동일 alert 한 줄” 표현의 기준 테이블 역할을 한다

### 3.2 `alert_history`

역할:
- 종료된 alert lifecycle summary 저장
- `1 lifecycle = 1 row`

핵심 개념:
- frontend 운영 화면에서 이력을 한 줄로 읽기 좋게 제공
- append-only 또는 resolve 시점 archive insert 구조를 목표로 함

추천 필드 예시:
- `id`
- `monitored_object_id`
- `alert_code`
- `source_rule_id`
- `source_rule_key`
- `source_rule_display_name_snapshot`
- `opened_at`
- `resolved_at`
- `first_severity`
- `highest_severity`
- `final_severity`
- `repeat_count`
- `was_acknowledged`
- `resolution_source`
- `resolution_reason`
- `resolved_by_user_id`
- `metadata_json`

추가 고려:
- current alert는 현재 rule row를 join해서 최신 `display_name`을 읽어도 된다.
- 하지만 archive/history는 당시 운영자가 보던 rule 이름을 유지하는 편이 자연스럽다.
- 따라서 `source_rule_display_name_snapshot` 같은 snapshot 필드를 함께 보관할 가치가 있다.

### 3.3 `alert_action_log` (선택)

역할:
- 세부 운영 이력의 append-only log

기록 예시:
- `acknowledged`
- `unacknowledged`
- `status_changed`
- `severity_escalated`
- `manual_resolved`
- `auto_resolved`
- `note_added`

이 테이블은 감사 추적과 drill-down에 유리하지만, MVP에서는 선택 항목으로 둘 수 있다.

### 3.4 `alert_occurrence_log` (product 단계 검토)

역할:
- 동일 alert의 개별 발생 occurrence를 append-only로 기록

기록 예시:
- `alert_code`
- `monitored_object_id`
- `occurred_at`
- `severity_at_occurrence`
- `metric_value`
- `message`
- `source_rule_id`
- `source_rule_key`
- `source_rule_display_name_snapshot`

이 테이블은 MVP 필수는 아니다.
현재 MVP에서는 `alert_instances.repeat_count`와 `last_occurred_at`로도 운영 화면 목적을 충분히 달성할 수 있다.

다만 product 단계에서는 다음 목적 때문에 검토 가치가 있다.

- 반복 발생 패턴 분석
- alert noise 통계
- rule 튜닝을 위한 occurrence 기반 분석
- alert correlation / burst 탐지

## 4. resolve 방식과 기록 모델

### 4.1 수동 resolve는 필수

운영자는 다음 상황에서 alert를 수동으로 resolve할 수 있어야 한다.

- 실제 장애는 해소되었지만 backend가 그 사실을 감지하지 못함
- backend 장애 또는 agent 지연으로 자동 resolve 경로가 끊김
- 운영자가 known issue 또는 외부 조치 완료를 근거로 직접 종료 판단을 내림

권장 동작:
- 운영자가 alert를 선택 후 수동 resolve
- 해당 alert는 `alert_instances`에서 current set에서 제거
- 종료 시점에 `alert_history`에 archive row가 생성

### 4.2 flag보다 enum 성격의 컬럼 권장

`is_auto_resolved` 같은 boolean flag보다는 다음과 같은 enum 성격의 컬럼이 더 적절하다.

- `resolution_source`
  - `auto_recovery`
  - `manual_operator`
  - `auto_policy_timeout`
  - `system_cleanup`

- `resolution_reason`
  - 자유 텍스트 또는 코드

이 구조의 장점:
- 수동/자동 여부뿐 아니라 어떤 경로로 종료되었는지 명확히 남길 수 있다.
- 추후 정책이 늘어나도 schema 변경이 덜 필요하다.

## 5. 시간 경과 정책

### 5.1 자동 escalation

오래 열려 있는 alert에 대해서는 severity를 자동으로 상향하는 정책이 유용하다.

예시 필드:
- `escalate_after_minutes`
- `escalate_to_severity`

이 경우 기록은 `alert_action_log` 또는 현재 skeleton 수준의 history row에 아래처럼 남길 수 있다.

- `action_type = 'severity_escalated'`
- `action_source = 'policy_timeout'`
- `previous_severity`
- `new_severity`

### 5.2 자동 resolve

자동 resolve도 필요할 수 있지만, 기본값으로는 보수적으로 적용하는 것이 좋다.

이유:
- 오래 열려 있다고 해서 실제로 해소된 것은 아닐 수 있다.
- 잘못된 자동 resolve는 운영자에게 더 큰 혼란을 줄 수 있다.

권장 정책:
- `auto_resolve_enabled`
- `auto_resolve_after_minutes`
- `auto_resolve_only_for_severity`
- `auto_resolve_only_for_rule_type`

자동 resolve 발생 시 `alert_history`에는 다음과 같이 남기는 것이 좋다.

- `resolution_source = 'auto_policy_timeout'`
- `resolution_reason = 'auto resolve after 120 minutes'`

## 6. 제안하는 저장 전략

### 6.1 권장 방향

운영 중에는:
- `alert_instances`만 계속 update

종료 시에는:
- `alert_history`에 archive row insert

필요 시 세부 액션은:
- `alert_action_log`에 append-only insert

product 단계에서 필요 시에는:
- `alert_occurrence_log`에 발생 단위 append-only insert

즉 장기적으로는 다음 세 층이 공존할 수 있다.

- `alert_instances`
  - current alert summary
- `alert_history`
  - resolved lifecycle archive
- `alert_occurrence_log`
  - raw occurrence ledger

### 6.2 피하고 싶은 방향

다음 구조는 가능은 하지만 장기적으로는 덜 권장된다.

- `alert_history` 한 row를 생성 시 insert하고
- resolve 시 같은 row의 `resolved_at`를 update

이 방식은 동작은 단순하지만,
- hot path에서 history row까지 계속 수정하게 되고
- current state와 archive 역할이 섞이며
- 장기적으로는 append-only 이력 구조의 장점을 잃게 된다.

## 7. 단계적 refactoring 제안

### Step 1. 현재 skeleton 유지 + 의미 재정의

- 현재 `alert_history`는 임시 action log로 간주
- 즉시 큰 파괴적 변경은 하지 않음

### Step 2. `alert_history` archive 구조 초안 추가

- 현재 `alert_instances`를 resolve할 때 archive row 생성
- 수동 resolve와 자동 resolve 모두 archive insert 경로 통일

### Step 3. `alert_action_log` 도입 여부 결정

- ACK, note, status 전이, escalation을 append-only로 분리할지 판단

### Step 4. frontend 운영 화면 전환

- 현재 alert 목록은 `alert_instances`
- 종료된 이력 화면은 `alert_history`
- drill-down은 필요 시 `alert_action_log`

## 8. 현재 시점의 권장 결론

현재 단계에서는 아래 판단을 권장한다.

- `alert_instances`는 current alert 테이블로 유지한다.
- 현재는 동일 alert을 한 줄로 집계하는 구조를 유지한다.
- `repeat_count`, `last_occurred_at`, `latest_message`로 운영 화면 표현을 단순하게 유지한다.
- `alert_history`는 장기적으로 `1 lifecycle = 1 row` archive 구조로 전환한다.
- 수동 resolve는 반드시 지원한다.
- resolve 방식은 boolean이 아니라 `resolution_source / resolution_reason` 계열로 기록한다.
- 시간 경과 정책은 `auto escalation`을 먼저, `auto resolve`는 선택적으로 도입한다.
- 다만 product 단계에서는 `alert occurrence ledger`를 별도 도입할지 다시 검토한다.

## 9. 추천 다음 순서

1. `alert_instances -> alert_history archive` 전환 설계 구체화
2. 수동 resolve 시 archive insert 경로 정의
3. `resolution_source / resolution_reason` 컬럼 초안 정의
4. 시간 경과 escalation / auto resolve policy 설계
5. 필요 시 `alert_action_log` 도입 여부 판단
