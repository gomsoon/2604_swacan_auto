# Event Rule MVP Draft

버전: Draft 0.1  
작성일: 2026-05-12

## 목적

threshold / compound threshold 다음의 첫 번째 신규 alert family로 `event rule`을 여는 MVP 기준을 정리한다.

이번 MVP는 runtime과 preview가 같은 방향으로 동작하는 것을 우선한다.

## 범위

- `signal_type = grouped_event_repeat`
- `state_type = process`
- `signal_key`
  - `process_started`
  - `process_stopped`
  - `process_restarted`
- `scope_type`
  - `object_type`
  - `monitored_object`
- `comparison = gte`
- `warning_threshold`, `critical_threshold`
  - grouped event repeat count 기준

이번 MVP에서 하지 않는 것:

- raw event occurrence rule
- event + compound condition
- multi-signal boolean rule
- per-rule custom window
- event + threshold mixed rule

## 데이터 소스

event rule은 `raw_events`가 아니라 `grouped_events`를 기준으로 평가한다.

이유:

- noise가 한 번 정리된 뒤 repeat count를 읽을 수 있다.
- 현재 ingest worker 구조를 그대로 재사용할 수 있다.
- preview와 runtime에서 같은 repeat-count 판단을 하기 쉽다.

## 저장 모델

`alert_rules`는 기존 threshold 계열과 같은 테이블을 재사용한다.

추가 축:

- `signal_type`
- `signal_key`

현재 MVP 구현에서는 기존 schema compatibility를 위해 `metric_key`를 완전히 비우지 않고,
event rule일 때는 `metric_key = signal_key` shadow 값을 같이 저장한다.

즉:

- threshold rule
  - `signal_type = latest_state_metric`
  - `metric_key` 사용
  - `signal_key = NULL`
- event rule
  - `signal_type = grouped_event_repeat`
  - `signal_key` 사용
  - `metric_key`에는 compatibility shadow로 같은 값을 저장

이 shadow 값은 legacy NOT NULL schema와 기존 helper 흐름을 무리 없이 유지하기 위한 임시/호환 목적이다.

## Validation

event MVP validation 기준:

- `state_type = process`만 허용
- `signal_type = grouped_event_repeat`만 허용
- `signal_key`는 허용된 process event만 허용
- `comparison = gte`만 허용
- `condition_mode = scalar`만 허용
- `warning_threshold` 또는 `critical_threshold` 중 하나 이상 필요

## Preview

preview는 threshold preview 구조를 최대한 재사용하되 event-specific 필드를 추가한다.

item 최소 필드:

- `signal_type`
- `signal_key`
- `grouped_event_repeat_count`
- `grouped_event_first_occurred_at`
- `grouped_event_last_occurred_at`
- `grouped_event_latest_message`
- `current_metric_value`
  - event MVP에서는 repeat count를 float로 담는다

reason 예시:

- `process_restarted repeat count 4 met warning threshold 2`

## Runtime

runtime worker는 published event rule을 `grouped_events` repeat count 기준으로 평가한다.

family key:

- `event + state_type + signal_key + comparison`

precedence 규칙:

1. `monitored_object > object_type`
2. `critical > warning`
3. newer rule
4. `rule_id`

같은 `monitored_object_id`와 같은 event family에서는 winner 하나만 current alert로 유지한다.

## Closure / archive

event rule도 threshold와 같은 archive contract를 사용한다.

현재 MVP resolution reason:

- `event_window_elapsed`
- `suppressed_by_precedence`

archive snapshot에는 다음이 남아야 한다.

- `source_rule_key`
- `source_rule_display_name_snapshot`
- `signal_type`
- `signal_key`
- repeat count 관련 metadata

## UI

admin rule editor는 threshold와 event를 같은 form에서 다루되,
`Signal Type` 선택에 따라 입력 의미를 바꾼다.

- threshold
  - `Metric Key`
  - scalar / compound
- event
  - `Signal Key`
  - scalar repeat threshold만 허용

preview 패널과 rule 목록에서도 `signal_type`, `signal_key`, repeat-count 요약을 보여준다.

## 다음 단계

다음 후속 후보:

1. event rule explainability 보강
2. custom event window 설계
3. stale/no-data rule 범위 확장
