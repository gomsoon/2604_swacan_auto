# Alert Condition Flexibility Draft

버전: Draft 0.1  
작성일: 2026-04-18

목적: backend에서 alert을 생성하는 조건을 앞으로 얼마나 유연하게 제공할지 설계 관점에서 정리한다.

이 문서는 “지금 바로 구현”을 목적으로 하지 않는다.  
현재 rule 구조의 한계와, 이후 확장 가능한 방향을 합의하기 위한 설계 초안이다.

## 1. 문제의식

현재 alert 생성은 대체로 다음 축에 기반한다.

- 특정 `state_type`
- 특정 `metric_key`
- 단순 비교 연산 (`gte`, `lte`)
- warning / critical threshold
- scope:
  - `object_type`
  - `monitored_object`

이 구조는 MVP 초기에 충분히 유용하지만, 조금만 운영이 복잡해져도 한계가 드러난다.

예를 들면 다음 요구가 자연스럽게 생긴다.

- CPU, memory, queue depth처럼 수치 threshold 기반 alert
- 특정 event가 일정 횟수 이상 반복될 때 alert
- heartbeat / no-data / stale 상태 alert
- 일정 시간 이상 해소되지 않을 때 severity 상향
- 특정 semantic type에만 적용되는 rule
- 특정 monitored object group에만 적용되는 rule
- 일시적 spike는 무시하고 window 기준 평균/최댓값으로 판단

즉, 앞으로는 “단순 threshold rule”보다 더 일반화된 alert 조건 모델이 필요하다.

## 2. 설계 원칙

### 2.1 runtime identity는 유지

alert 생성의 귀속 단위는 계속 `monitored_object`가 중심이어야 한다.

이유:
- 같은 runtime object가 여러 active view에 fan-out 되어도 alert는 1번만 생성되어야 한다.
- `Monitoring View`는 같은 alert를 여러 view에 표시할 수 있어야 한다.
- view snapshot과 runtime identity는 계속 분리되어 있어야 한다.

### 2.2 rule은 selector와 condition을 분리

rule은 최소한 다음 두 층으로 나뉘어야 한다.

- 어디에 적용할 것인가
- 무엇을 기준으로 판단할 것인가

즉 `selector`와 `condition`을 분리해야 한다.

### 2.3 현재 단순 rule도 계속 살아 있어야 한다

새 구조를 도입하더라도, 지금 있는 단순 threshold rule은 compatibility 경로로 유지하는 편이 좋다.

이유:
- MVP 초기에 가장 흔한 alert는 여전히 threshold 기반이다.
- 현재 admin UI / preview / worker 구조를 한 번에 전부 갈아엎을 필요는 없다.

### 2.4 구현보다 validation과 preview가 먼저 중요

rule이 복잡해질수록 “무엇에 적용되고 어떤 결과가 날지”를 미리 보여주는 preview가 더 중요해진다.

즉 유연한 alert 조건 설계는 곧:
- validation
- dry-run preview
- 영향도 표시

와 함께 가야 한다.

## 3. 권장 개념 모델

추천 모델은 다음 5개 층으로 나누는 것이다.

### 3.1 Selector

rule이 적용될 대상을 고른다.

예시:
- `object_type = SoftwareProcess`
- `monitored_object_id = 1302`
- `semantic_type_code = MonitoringAgent`
- 이후 확장:
  - tag
  - namespace
  - metamodel version

권장 필드 예시:
- `selector_type`
- `selector_json`

### 3.2 Signal

무엇을 입력값으로 볼지 정한다.

예시:
- latest state metric
- raw event
- grouped event
- heartbeat/no-data

권장 필드 예시:
- `signal_type`
  - `latest_state_metric`
  - `event_occurrence`
  - `grouped_event_repeat`
  - `stale_state`
  - `missing_data`
- `signal_key`
  - 예: `cpu_usage`, `outbox_queue_depth`, `process_stopped`

### 3.3 Condition

실제 판단식을 정의한다.

예시:
- `>= 80`
- `<= 5`
- `count >= 3`
- `exists`
- `no data for 30s`

권장 필드 예시:
- `comparison`
  - `gte`
  - `lte`
  - `eq`
  - `exists`
  - `missing`
- `warning_threshold`
- `critical_threshold`
- `condition_json`

### 3.4 Aggregation / Window

현재값 1개만 볼지, 시간 창을 둘지 정의한다.

예시:
- latest value
- last 5 minutes avg
- last 1 minute max
- event count in 10 minutes

권장 필드 예시:
- `window_seconds`
- `aggregation`
  - `latest`
  - `avg`
  - `max`
  - `min`
  - `count`

### 3.5 Lifecycle Policy

alert를 어떻게 유지/상향/해소할지 정한다.

예시:
- cooldown
- auto escalation
- auto resolve
- repeat suppression

권장 필드 예시:
- `cooldown_seconds`
- `escalate_after_seconds`
- `escalate_to_severity`
- `auto_resolve_enabled`
- `auto_resolve_after_seconds`
- `policy_json`

## 4. 현재 `alert_rules`와 개념 모델의 매핑

현재 `alert_rules`는 이미 아주 작은 형태의

- `selector`
- `signal`
- `condition`

모델로 해석할 수 있다.

다만 `aggregation / window`와 `lifecycle policy`는 아직 구조적으로 모델링되어 있지 않고, 일부는 worker 동작에 흩어져 있다.

### 4.1 필드 매핑표

| 현재 필드 | 새 개념 모델 | 현재 의미 | 비고 |
| --- | --- | --- | --- |
| `scope_type` | `selector` | 어떤 범위에 적용할지 | 현재는 `object_type`, `monitored_object` 두 종류만 지원 |
| `object_type` | `selector` | 특정 object type 선택 | `scope_type = object_type`일 때 사용 |
| `monitored_object_id` | `selector` | 특정 monitored object 선택 | `scope_type = monitored_object`일 때 사용 |
| `state_type` | `signal` | 어떤 latest state 축을 볼지 | 현재는 `process`, `agent`, `host` |
| `metric_key` | `signal` | 어떤 metric을 읽을지 | 예: `cpu_usage`, `outbox_queue_depth` |
| `comparison` | `condition` | 어떤 비교식인지 | 현재는 `gte`, `lte`만 지원 |
| `warning_threshold` | `condition` | warning 기준값 | optional |
| `critical_threshold` | `condition` | critical 기준값 | optional |
| `is_enabled` | rule metadata | rule 활성/비활성 | 개념 모델 핵심은 아니지만 계속 필요 |
| `description` | rule metadata | 운영 설명 | 계속 필요 |

### 4.2 현재 구조에서 이미 되는 것

- 특정 object type 전체에 대한 metric threshold rule
- 특정 monitored object 하나에 대한 metric threshold rule
- `process / agent / host` latest state를 기준으로 한 비교 rule
- `warning / critical` 2단계 severity 판정

즉 현재 구조는 다음 형태를 이미 표현할 수 있다.

- selector:
  - `object_type = SoftwareProcess`
- signal:
  - `latest_state_metric(process.cpu_usage)`
- condition:
  - `gte 80 / 95`

### 4.3 현재 구조에서 아직 어려운 것

- event 자체를 signal로 쓰는 rule
- grouped event repeat count rule
- `no-data`, `stale`를 rule 차원에서 명시하는 구조
- 최근 N분 평균/최댓값/횟수 같은 window rule
- cooldown, auto escalation, auto resolve 같은 lifecycle policy
- selector를 `semantic_type`, tag, group, namespace 수준으로 확장하는 구조

### 4.4 현재 worker에 암묵적으로 있는 정책

일부 lifecycle 의미는 현재 `alert_rules` 필드가 아니라 worker 로직에 암묵적으로 들어 있다.

예:
- 동일 rule / object 기준 alert reopen
- 조건 해소 시 auto recovery
- 일부 상태 유지(`in_progress`, `suppressed`) 처리

즉 앞으로는 다음 둘을 명확히 분리하는 게 좋다.

- `rule evaluation`
  - selector / signal / condition / aggregation
- `alert lifecycle policy`
  - cooldown / auto escalation / auto resolve / suppression

## 5. 단계별 확장 추천

한 번에 모든 rule 타입을 넣는 건 과합니다.  
다음처럼 단계적으로 가는 게 좋습니다.

### Phase A. 현재 rule 모델 정리

현재 구조 유지:
- `object_type / monitored_object`
- `state_type`
- `metric_key`
- `comparison`
- warning / critical threshold

추가 권장:
- selector / condition 개념을 문서와 API 응답에서 먼저 분리해서 표현

### Phase B. Event rule

추가 대상:
- 특정 event 발생
- 특정 grouped event repeat count

예시:
- `process_stopped`가 최근 5분 안에 3회 이상
- `agent_heartbeat_lost`가 최근 1분 안에 1회 이상

### Phase C. Stale / No-data rule

추가 대상:
- latest state가 일정 시간 이상 갱신되지 않음
- heartbeat가 일정 시간 이상 오지 않음

이건 Monitoring View와도 직접적으로 연결된다.

### Phase D. Window / Aggregation rule

추가 대상:
- average
- max
- count

이 단계부터는 단순 threshold보다 훨씬 유연해진다.

### Phase E. Policy rule

추가 대상:
- auto escalation
- auto resolve
- cooldown
- suppression

이 단계는 alert lifecycle과 같이 움직여야 한다.

## 6. 권장 API/DB 방향

### 5.1 현재 `alert_rules`를 유지하되 확장

가장 안전한 방법은 기존 `alert_rules`를 즉시 버리지 않고, 점진적으로 확장하는 것이다.

예시 방향:
- 기존 필드 유지
- 추가 필드:
  - `selector_type`
  - `selector_json`
  - `signal_type`
  - `signal_key`
  - `window_seconds`
  - `aggregation`
  - `condition_json`
  - `policy_json`

초기에는:
- 기존 필드를 우선 사용
- 새 필드는 optional

### 5.2 또는 `alert_rules_v2` 분리

장점:
- 현재 구조를 깔끔하게 보존
- 새 구조를 더 자유롭게 설계 가능

단점:
- migration과 UI가 이중화될 수 있음

현재 시점에서는 `기존 alert_rules 확장`이 더 현실적이다.

## 7. UI / 운영 관점

유연한 alert 조건은 단순히 DB schema 문제가 아니다.  
운영자가 이해할 수 있어야 한다.

그래서 다음이 반드시 같이 필요하다.

- rule preview
- 영향도 표시
- validation
- “이 rule이 현재 어떤 monitored object에 걸리는가” 설명
- “현재 어떤 객체가 warning/critical이 되는가” dry-run 결과

즉 구현 순서는:

1. 조건 모델 설계
2. validation / preview 설계
3. worker 평가 로직
4. admin UI 고도화

가 되어야 한다.

## 8. 현재 시점의 권장 결론

현재 backend alert 조건은 다음 방향으로 설계 검토를 진행하는 것이 적절하다.

- `monitored_object` 중심 alert 귀속 유지
- rule을 `selector / signal / condition / aggregation / lifecycle policy`로 분리
- 현재 단순 threshold rule은 compatibility 경로로 유지
- 다음 구현은 schema 변경보다:
  - 개념 모델 정리
  - validation / preview 방향 정리
  - 단계별 도입 순서 합의

를 먼저 하는 것이 맞다.

## 9. 다음 권장 작업

1. 현재 `alert_rules` 필드와 위 개념 모델의 매핑표 작성
2. 어떤 rule 타입을 MVP에 포함할지 범위 고정
3. `selector / signal / condition / window / policy` 기준 API 초안 작성
4. preview / dry-run 응답 형식 초안 작성
