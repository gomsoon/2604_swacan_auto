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

### 4.1.1 Rule identity / naming 방향

threshold rule이 복잡해질수록, 운영자는 조건식 자체보다 “이 rule이 무엇을 의미하는지”를 이름으로 기억하는 편이 더 자연스럽다.

따라서 rule에는 다음 두 층의 식별자가 함께 있는 것이 적절하다.

- 시스템 중심 식별자
  - `rule_id`
    - PK
  - `rule_key`
    - 안정적인 고유 키
    - DB unique
    - preview / history / archive / API ref에서 장기 참조용
- 사용자 중심 식별자
  - `display_name`
    - 운영자가 UI와 메시지에서 읽는 이름
  - `description`
    - rule 의도 설명

권장 원칙:
- uniqueness는 `display_name`이 아니라 `rule_key`가 맡는다.
- `display_name`은 rename 가능성이 있으므로 내부 안정 키로 쓰지 않는다.
- preview, alert list, admin UI에서는 `display_name`을 우선 보여준다.
- `reason`은 판정 설명에 집중하고, rule 이름은 상위 문맥이나 catalog에서 보여주는 편이 적절하다.
- `display_name`을 `reason` 문자열 안에 직접 박아 넣기보다, 응답에서는 분리하고 표시 단계에서 조합하는 편이 적절하다.
- `display_name`은 표현 개선을 위해 수정할 수 있지만, rule의 의미 자체가 달라지는 경우는 rename보다 clone/new rule이 더 적절하다.

즉 시스템은 `rule_key`로 기억하고, 운영자는 `display_name`으로 기억하는 구조가 가장 좋다.

#### 권장 `rule_key` format

`rule_key`는 사람이 어느 정도 읽을 수 있으면서도, 시스템 기준으로 안정적으로 참조 가능한 키가 적절하다.

권장 원칙:
- 소문자 ASCII 사용
- 공백 없음
- 허용 문자는 `a-z`, `0-9`, `.`, `-`, `_`
- 구조 segment 구분은 `.`를 우선 사용
- 생성 후에는 가능하면 고정
- uniqueness는 전역 기준
- 사용자가 직접 입력할 수 있어야 한다
- 다만 UI는 `display_name`, `state_type`, `metric_key`를 바탕으로 자동 제안을 함께 제공하는 편이 좋다
- deprecated 포함 전체 rule 집합에서 재사용하지 않는 것이 적절하다

권장 해석:
- `.`
  - segment separator
- `_`
  - `metric_key`, `signal_key`, event name 같은 system token 보존용
- `-`
  - 사람 친화 slug 표현용

권장 포맷:

- `threshold.<state_type>.<metric_key>.<slug>`

예:
- `threshold.process.cpu_usage.process-cpu-high`
- `threshold.agent.outbox_queue_depth.agent-queue-high`
- `threshold.host.memory_used_ratio.host-memory-high`

이 포맷의 장점:
- rule family가 드러난다
- `state_type`과 `metric_key` 축이 드러난다
- 마지막 slug에 운영 의미를 담을 수 있다
- 이후 `event`, `stale`, `no-data` rule로 확장할 때도 일관성이 유지된다

확장 예시:
- `event.process.process_stopped.process-stop-burst`
- `stale.agent.heartbeat.agent-heartbeat-missing`

즉 다음과 같은 혼합 표현이 자연스럽다.

- `threshold.process.cpu_usage.process-cpu-high`
- `event.process.process_stopped.process-stop-burst`

여기서
- `cpu_usage`, `process_stopped`는 system token을 그대로 유지하고
- `process-cpu-high`, `process-stop-burst`는 사람이 읽기 쉬운 slug로 유지한다.

#### `rule_key` 자동 제안 방향

자동 제안은 `display_name` 단독 slug보다, 다음 조합으로 만드는 편이 적절하다.

- `family`
- `state_type`
- `metric_key` 또는 `signal_key`
- `display_name`에서 파생한 `short_slug`

즉 기본 제안 형식은 다음과 같다.

- `family.state_type.metric_or_signal.short_slug`

예:
- `threshold.process.cpu_usage.process-cpu-high`
- `threshold.agent.outbox_queue_depth.agent-queue-high`
- `stale.agent.heartbeat.agent-heartbeat-missing`

권장 이유:
- rule family가 즉시 드러난다
- 어떤 state/signal 축을 다루는지 바로 알 수 있다
- 마지막 slug는 운영자가 읽기 쉬운 의미를 담는다
- `display_name`이 일부 바뀌더라도 앞의 구조적 prefix는 안정적으로 유지된다

#### `short_slug` 생성 규칙

MVP에서는 `short_slug`를 과하게 똑똑하게 만들기보다, 단순 slugify를 우선 적용하는 것이 적절하다.

권장 규칙:
- source: `display_name`
- 소문자 변환
- 공백은 `-`로 치환
- 특수문자는 제거
- 너무 길면 뒤를 truncate

예:
- `Process CPU High` -> `process-cpu-high`
- `Agent Queue High` -> `agent-queue-high`

현재 시점에서는 stop word 제거, 중복 단어 축약 같은 공격적인 최적화보다, 예측 가능하고 안정적인 slugify가 더 적절하다.

#### `rule_key` validation 방향

권장 허용 문자 집합:

- `a-z`
- `0-9`
- `.`
- `-`
- `_`

예시 정규식:

- `^[a-z0-9._-]+$`

권장 추가 규칙:
- leading / trailing separator 금지
- `.` 기준 빈 segment 금지
  - 예: `threshold..cpu_usage` -> invalid
- 자동 제안에서는 `--`, `__` 같은 중복 separator를 만들지 않는 편이 좋다
- `metric_key` / `signal_key`는 가능하면 원래 token을 보존한다

즉 validation은 `_`를 허용하되, 구조는 `.` 기준 segment로 읽고, 사람 친화 slug는 `-` 중심으로 유지하는 방향이 적절하다.

#### 충돌 처리

자동 제안된 `rule_key`가 이미 존재하면 suffix를 붙이는 방식이 적절하다.

예:
- `threshold.process.cpu_usage.process-cpu-high`
- `threshold.process.cpu_usage.process-cpu-high-2`
- `threshold.process.cpu_usage.process-cpu-high-3`

즉 MVP에서는
- 제안 규칙은 단순하게
- uniqueness는 validation으로 보장하고
- 충돌 시 suffix를 붙이는 방식으로 해결하는 것이 가장 안전하다.

권장 정책:
- `rule_key`는 생성 시 사용자가 직접 입력 가능
- UI는 자동 제안을 제공하되, 최종 결정은 사용자가 한다
- `rule_key`는 `draft` 상태에서만 수정 가능
- `published` 이후에는 freeze하는 편이 적절하다
- `display_name`은 운영 필요에 따라 rename 가능하되, `rule_key`는 장기 참조 키로 유지한다
- 운영에 쓰이기 시작한 뒤 `rule_key`를 바꿔야 할 정도면, 기존 rule을 유지하고 새 rule을 clone/create 하는 흐름이 더 안전하다

`display_name` rename 권장 기준:
- 허용:
  - 오탈자 수정
  - 표현 개선
  - 더 이해하기 쉬운 이름으로 변경
- clone/new rule 권장:
  - threshold 의미 변경
  - selector 범위 변경
  - `state_type` / `metric_key` 변경
  - 운영 의도가 달라지는 경우

즉 `display_name`은 바꿀 수 있지만, 의미 변경 수준이면 새 rule로 다루는 것이 적절하다.

즉 `rule_key`는 “읽을 수 있는 immutable slug key”, `display_name`은 “운영자가 보는 이름”으로 분리하는 것이 적절하다.

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

## 5. Threshold Rule MVP 범위

현재 MVP에서 먼저 고정할 대상은 `threshold rule`이다.

이 단계에서는 rule을 최대한 단순하게 유지하는 편이 좋다.

### 5.1 MVP에서 허용하는 범위

- selector:
  - `scope_type = object_type`
  - `scope_type = monitored_object`
- signal:
  - `signal_type = latest_state_metric`
- state 축:
  - `process`
  - `agent`
  - `host`
- metric:
  - 숫자형 metric만 허용
- comparison:
  - `gte`
  - `lte`
- severity:
  - `warning_threshold`
  - `critical_threshold`
- 평가 방식:
  - `latest value`만 사용
- 해소 방식:
  - 조건 해소 시 auto recovery

즉 MVP threshold rule은 다음 한 문장으로 정의할 수 있다.

> 최신 latest_state의 단일 숫자 metric에 대해, 특정 monitored_object 또는 object_type 범위에서 `gte/lte` 비교로 warning/critical을 판단하는 rule

### 5.2 MVP에서 아직 넣지 않는 것

- `semantic_type_code` selector
- tag / group / namespace selector
- 평균 / 최댓값 / window / count
- boolean / string metric
- 여러 조건 조합
- expression language
- threshold와 event/stale 혼합 rule
- cooldown / hysteresis
- auto escalation / auto resolve policy

### 5.3 Threshold Rule validation 권장 기준

- `warning_threshold`, `critical_threshold` 중 적어도 하나는 있어야 한다.
- `warning_threshold`만 있는 rule은 허용한다.
- `critical_threshold`만 있는 rule도 허용한다.
- 두 threshold가 모두 없는 rule은 invalid다.
- 두 threshold가 모두 존재하고 `comparison = gte`이면:
  - `critical_threshold >= warning_threshold`
- 두 threshold가 모두 존재하고 `comparison = lte`이면:
  - `critical_threshold <= warning_threshold`
- `scope_type = monitored_object`이면 `monitored_object_id`는 필수
- `scope_type = object_type`이면 `object_type`은 필수
- `metric_key`는 해당 `state_type`에서 실제로 지원되는 숫자형 metric이어야 한다.

### 5.4 Severity 단독 rule 허용 정책

MVP에서는 다음 둘을 모두 허용하는 것이 적절하다.

- `warning-only` rule
- `critical-only` rule

이유:
- 운영 초기에는 “경고만 받고 싶은 rule”이 존재할 수 있다.
- 반대로 정말 치명적인 상태만 잡고 싶은 `critical-only` rule도 실용적이다.

다만 preview와 validation에서 다음 사실을 명확히 보여줘야 한다.

- `warning-only` rule은 critical을 생성하지 않는다.
- `critical-only` rule은 warning을 생성하지 않는다.
- 둘 다 있으면 warning/critical 2단계로 평가한다.

### 5.5 Compound Threshold 확장 방향

현재 MVP 기준은 단방향 scalar threshold rule이지만, 이후 확장으로 `양방향 threshold + logical operator` 구조를 검토할 가치가 있다.

실제 운영에서는 다음 패턴이 자연스럽게 필요해질 수 있다.

- 단방향:
  - `cpu >= 80`
  - `memory <= 10`
- 양방향 `AND`:
  - `40 <= cpu <= 60`
- 양방향 `OR`:
  - `cpu <= 20 OR cpu >= 80`

이 요구는 threshold rule의 자연스러운 확장으로 볼 수 있다.

다만 자유식 expression 전체를 허용하기보다, 구조화된 `condition group`으로 제한하는 편이 적절하다.

권장 방향:
- severity마다 독립된 condition group
- condition group은
  - `logical_operator`
  - `clauses`
  로 구성

예:

```json
{
  "warning_condition": {
    "logical_operator": "or",
    "clauses": [
      { "comparison": "lte", "value": 20 },
      { "comparison": "gte", "value": 80 }
    ]
  },
  "critical_condition": {
    "logical_operator": "or",
    "clauses": [
      { "comparison": "lte", "value": 10 },
      { "comparison": "gte", "value": 90 }
    ]
  }
}
```

단방향 rule은 같은 구조 안에서 clause 1개로도 표현할 수 있다.

다만 이는 `scalar mode` 기준의 내부 정규화 표현으로 보는 것이 적절하다.  
MVP 범위의 `compound mode`는 shape를 명확히 유지하기 위해 `logical_operator = and | or`와 clause 2개를 전제로 보는 편이 좋다.

예:

```json
{
  "warning_condition": {
    "logical_operator": null,
    "clauses": [
      { "comparison": "gte", "value": 80 }
    ]
  }
}
```

### 5.6 Compound Threshold 설계 원칙

- MVP의 scalar threshold와 compatibility를 유지한다.
- 자유식 expression language는 도입하지 않는다.
- 초기 확장에서는 clause 개수를 제한한다.
  - 권장: 최대 2개
- operator는 최소 범위만 허용한다.
  - `and`
  - `or`
  - `null`
- comparison은 threshold 성격에 맞는 범위만 허용한다.
  - `gt`
  - `gte`
  - `lt`
  - `lte`

### 5.7 Validation 관점

compound threshold를 도입하면 validation이 더 중요해진다.

예시:
- clause 2개인데 operator 없음 -> invalid
- clause 1개인데 operator 있음 -> invalid
- `scalar mode`인데 operator가 `and` 또는 `or` -> invalid
- `compound mode`인데 operator가 `null` -> invalid
- `gte 80 AND lte 20`처럼 항상 false가 되는 조합 -> invalid
- warning/critical 관계가 비정상적인 조합 -> warning 또는 invalid

즉 이 확장은 preview / validation과 반드시 함께 가야 한다.

권장 validation은 다음 3단계로 나누는 것이 적절하다.

#### 5.7.1 Shape validation

입력 구조 자체가 올바른지 확인한다.

예:
- clause 0개 -> invalid
- `scalar mode`인데 clause 수가 1개가 아님 -> invalid
- `scalar mode`인데 `logical_operator != null` -> invalid
- `compound mode`인데 clause 수가 2개가 아님 -> invalid
- `compound mode`인데 `logical_operator`가 `and | or`가 아님 -> invalid
- 지원하지 않는 comparison / operator -> invalid
- 숫자가 아닌 value -> invalid

즉 `shape validation` 단계에서는 다음을 syntax/shape error로 명확히 구분하는 것이 적절하다.

- `scalar + and/or`
- `compound + null`
- `scalar + 2 clauses`
- `compound + 1 clause`

#### 5.7.2 Condition group satisfiability validation

각 severity group이 스스로 의미가 있는지 확인한다.

예:
- `gte 80 AND lte 20` -> 항상 false -> invalid
- `gte 80 OR gte 90` -> 하나의 clause가 사실상 중복 -> warning
- `lte 20 AND lte 10` -> 더 강한 조건 하나로 축약 가능 -> warning

즉 각 group이 실제로 만족 가능한지, 또는 과도하게 중복되는지를 본다.

#### 5.7.3 Severity consistency validation

`warning_condition`과 `critical_condition` 사이의 관계가 운영적으로 자연스러운지 확인한다.

권장 원칙:
- `critical_condition`이 존재하면, 그 매칭 영역은 원칙적으로 `warning_condition`의 부분집합이어야 한다.
- 즉 critical은 warning보다 더 좁고 더 강한 영역이어야 한다.

예:
- warning: `cpu <= 20 OR cpu >= 80`
- critical: `cpu <= 10 OR cpu >= 90`
  - valid

- warning: `cpu >= 80`
- critical: `cpu <= 10`
  - 같은 rule 안에서 severity ladder 의미가 흐려짐
  - invalid

- warning: `cpu >= 80`
- critical: `cpu >= 80`
  - critical이 warning과 동일
  - warning path가 사실상 무의미
  - warning 또는 invalid 후보

현재 시점 권장:
- `warning-only` rule 허용
- `critical-only` rule 허용
- 둘 다 존재할 때는 `critical ⊆ warning` consistency를 강하게 검증

### 5.7.4 구현 관점의 권장 방향

MVP 범위의 compound threshold는 다음 제약이 있으므로, interval normalization 기반으로 검증하는 것이 적절하다.

- 단일 metric
- 최대 2 clauses
- comparison:
  - `gt`
  - `gte`
  - `lt`
  - `lte`
- logical operator:
  - `and`
  - `or`
  - `null`

예:
- `gte 80` -> `[80, +inf)`
- `lte 20 OR gte 80` -> `(-inf, 20] U [80, +inf)`
- `gte 40 AND lte 60` -> `[40, 60]`

이렇게 interval set으로 정규화하면 다음 검증이 가능하다.

- 결과 interval set이 empty -> invalid
- 중복/포함 관계 -> warning
- `critical_set ⊄ warning_set` -> invalid
- `warning_set == critical_set` -> warning
- `critical_set`이 `warning_set`의 proper subset -> valid

이 접근의 장점:
- 구현 복잡도를 과도하게 올리지 않는다
- preview evaluator와 validation이 같은 정규화 결과를 재사용할 수 있다
- 이후 `reason_code`, validation code, 통계화에도 유리하다

### 5.7.5 Validation code 방향

향후 구조화된 validation 응답에서는 다음 code들을 권장한다.

- `condition_unsatisfiable`
- `redundant_clause`
- `subsumed_clause`
- `critical_not_subset_of_warning`
- `warning_shadowed_by_critical`
- `single_severity_rule`

### 5.8 현재 시점의 권장 결론

현재 시점에서는 compound threshold를 바로 구현하기보다:

1. 현재 scalar threshold MVP를 먼저 고정하고
2. 이후 확장 방향으로 `condition_json` 또는 severity별 condition group 구조를 문서에 유지하며
3. 실제 구현은 preview evaluator와 validation이 충분히 정리된 뒤 진행

하는 것이 적절하다.

## 6. Rule 우선순위와 suppression 정책

현재 구조에서는 같은 대상에 대해

- `object_type` rule
- `monitored_object` rule

이 동시에 존재할 수 있다.

이 경우 더 구체적인 rule이 우선하도록 정책을 명확히 정하는 편이 좋다.

### 6.1 Specificity 원칙

selector의 구체성은 다음 순서로 본다.

- `monitored_object` > `object_type`

즉 특정 monitored object에 직접 걸린 rule이, 같은 object type 전체에 걸린 rule보다 우선한다.

### 6.2 Same Rule Family 정의

우선순위 / suppression 정책은 같은 `rule family` 안에서만 적용하는 것이 적절하다.

MVP에서는 다음이 같으면 같은 family로 본다.

- `signal_type`
- `state_type`
- `metric_key`
- `comparison`

예:
- 둘 다 `latest_state_metric`
- 둘 다 `process`
- 둘 다 `cpu_usage`
- 둘 다 `gte`

이면 같은 family로 본다.

### 6.3 발화 정책

같은 family 안에서:

1. 같은 `monitored_object_id`에 대해 매칭되는 rule들을 모은다
2. 그 안에서 `monitored_object` rule을 먼저 평가한다
3. 해당 rule이 fire되면
   - 같은 `monitored_object_id`에 대한 `object_type` rule은 같은 평가 사이클에서 fire되지 않는다
4. `monitored_object` rule이 fire되지 않을 때만
   - 같은 `monitored_object_id`에 대해 `object_type` rule을 평가한다

즉 MVP에서는 `specific-over-general suppression` 정책을 채택하는 것이 적절하다.

중요한 점은 suppression이 전역적으로 일어나는 것이 아니라, 같은 runtime identity 안에서만 일어난다는 점이다.

즉 특정 `monitored_object`에 대한 specific rule이 fire되더라도:

- 다른 `monitored_object_id`에는 영향을 주지 않는다
- 같은 `object_type`에 속한 다른 객체들은 general rule을 계속 평가할 수 있다

### 6.4 Preview에서 꼭 보여줄 것

이 정책은 운영자가 이해할 수 있어야 하므로 preview에 다음 정보가 필요하다.

- 매칭 후보 rule 목록
- 실제 winner rule
- suppress된 general rule 목록
- 현재 값 기준 예상 severity

## 7. Preview / Dry-run 응답 방향

MVP에서는 `preview`와 `dry-run`을 엄격히 분리하지 않아도 된다.

즉 운영자에게는 `preview`라는 하나의 기능으로 제공하되, 내부적으로는 “실제 평가 로직을 DB write 없이 실행하는 dry-run”처럼 동작하는 구조가 적절하다.

### 7.1 Preview가 답해야 하는 질문

preview는 최소한 다음 질문에 답해야 한다.

1. 이 rule은 어디에 적용되는가
2. 지금 당장 어떤 객체가 warning / critical이 되는가
3. 어떤 rule이 winner이고 어떤 rule이 suppress되는가
4. 왜 그런 판단이 나왔는가

### 7.2 권장 응답 구성

MVP preview 응답은 다음 5개 블록으로 구성하는 것이 적절하다.

- `normalized_rule`
- `validation`
- `selector_resolution`
- `candidate_rule_catalog`
- `evaluation_summary`
- `evaluation_sample`

특히 sample은 다음 둘을 분리하는 것이 좋다.

- `matched_object_sample`
  - selector에 의해 “적용 대상”으로 매칭된 객체 sample
- `evaluation_sample`
  - 현재 값 기준으로 실제 fire / suppress 판단이 있었던 객체 sample

이 둘은 질문 자체가 다르다.

- `matched_object_sample`
  - “이 rule이 어디에 적용되는가?”
- `evaluation_sample`
  - “그중 지금 실제로 무엇이 fire되는가?”

즉 `matched != firing`을 분리해서 보여주는 편이 운영자에게 더 명확하다.

또한 `matched candidate rules / winner / suppressed` 표현은 다음처럼 `catalog + refs` 구조로 가는 것이 적절하다.

- top-level:
  - `candidate_rule_catalog`
- per object:
  - `matched_candidate_rule_keys`
  - `winner_rule_key`
  - `suppressed_rule_keys`

이 방식의 장점:
- 같은 rule 정보를 sample마다 반복하지 않아도 된다
- object별 winner / suppressed 판단을 명확히 표현할 수 있다
- 이후 product 단계에서 `reason_code`, `priority`, `family_key` 같은 필드를 확장하기 쉽다

### 7.3 권장 필드

#### `normalized_rule`

사용자가 입력한 rule을 backend 기준으로 정규화해서 보여준다.

예:
- `scope_type`
- `object_type`
- `monitored_object_id`
- `state_type`
- `metric_key`
- `comparison`
- `warning_threshold`
- `critical_threshold`

#### `validation`

현재 rule 정의 자체가 유효한지 보여준다.

예:
- `is_valid`
- `errors`
- `warnings`
- `supported_severities`
  - `["warning"]`
  - `["critical"]`
  - `["warning", "critical"]`

MVP에서도 `errors` / `warnings`는 단순 문자열 배열보다 구조화된 항목 배열로 두는 것이 적절하다.

권장 최소 shape:
- `code`
- `message`
- `field`

예:

```json
{
  "code": "threshold_order_invalid",
  "message": "critical_threshold must be greater than or equal to warning_threshold",
  "field": "critical_threshold"
}
```

이 방향의 장점:
- form field highlight 용이
- 다국어 처리 확장성
- 통계 / 테스트 안정성
- 이후 validation rule 증가 시 구조 유지 가능

#### `selector_resolution`

이 rule이 실제로 몇 개 object에 적용되는지 보여준다.

예:
- `matched_object_count`
- `matched_object_sample`

권장 공통 필드:
- `monitored_object_id`
- `display_name`
- `object_type`

MVP 기본형에서는 `matched_object_sample`에 `current_value`를 포함하지 않는 것이 적절하다.

이유:
- 이 블록은 “어디에 적용되는가?”를 설명하는 selector 결과이기 때문이다.
- 현재값을 넣기 시작하면 evaluation 의미와 경계가 흐려질 수 있다.

다만 확장 여지는 남겨두는 것이 좋다.

예:
- `include_current_values = true` 같은 옵션
- 별도 확장 응답 블록

즉 MVP 기본형은 가볍게 유지하되, 운영 편의를 위해 이후 선택적으로 풍부한 selector sample을 제공할 수 있게 여지를 열어두는 것이 적절하다.

#### `candidate_rule_catalog`

preview 평가에 참여하는 candidate rule 목록을 top-level catalog로 제공한다.

권장 필드:
- `rule_key`
- `kind`
  - `preview`
  - `existing`
- `rule_id`
- `display_name`
- `scope_type`
- `scope_target_label`
- `state_type`
- `metric_key`
- `comparison`
- `warning_threshold`
- `critical_threshold`

`rule_key`는 sample에서 rule을 참조하는 안정 키 역할을 한다.

`display_name`은 운영자가 candidate rule을 이름으로 식별하도록 돕는다.

권장 해석:
- `rule_key`
  - 시스템 중심 안정 키
- `display_name`
  - UI / preview / 메시지 중심 이름

즉 catalog에서는 `rule_key`와 `display_name`을 함께 제공하는 것이 적절하다.

권장 표시 원칙:
- 제목/카드/목록 라벨:
  - `display_name`
- 판정 설명:
  - `reason`
- 한 줄 표현이 필요할 때만 표시 계층에서
  - `{display_name}: {reason}`
  형태로 조합

즉 preview API 응답 자체는 “이름”과 “판정 설명”을 분리해 유지하는 것이 좋다.

MVP에서는 `state_type`, `metric_key`, `comparison` 같은 family 공통 필드를 catalog item마다 반복해서 넣는 것이 적절하다.

이유:
- payload가 아직 크지 않다
- 각 rule row가 self-contained하게 읽힌다
- 디버깅과 로그 확인이 쉽다
- 이후 family 종류가 늘어나도 catalog item을 독립적으로 해석하기 쉽다

즉 MVP에서는 중복 최적화보다 `읽기 쉬움`, `안정성`, `확장성`을 우선한다.

예:
- `preview`
- `rule:17`

#### `evaluation_summary`

현재 latest state 기준으로 몇 개 object가 실제로 fire될지 요약한다.

예:
- `would_fire_count`
- `warning_count`
- `critical_count`
- `suppressed_count`

MVP에서는 `would_fire_count = warning_count + critical_count`로 단순하게 해석하는 것이 적절하다.

즉 `would_fire_count`는 “현재 기준으로 실제 alert가 열리는 객체 수”를 뜻한다.

이때 `suppressed_count`는 별도 의미를 유지하고, `would_fire_count` 안에 suppression 의미를 섞지 않는 편이 좋다.

또한 `non_firing_count`는 `matched_object_count - would_fire_count`로 계산 가능하므로, MVP summary에서는 별도 필드로 두지 않아도 된다.

MVP에서 `suppressed_count`는 “suppression이 발생한 monitored object 수”로 해석하는 것이 적절하다.

여기서도 기준은 “같은 `monitored_object_id` 안에서 general rule이 눌린 경우”이다.

즉 summary는 object 기준으로 읽고, 어떤 general rule이 눌렸는지의 상세 설명은 sample에서 본다.

`warning-only` / `critical-only` rule에서도 summary shape는 동일하게 유지하는 것이 적절하다.

즉:
- `warning-only` rule이면 `critical_count = 0`
- `critical-only` rule이면 `warning_count = 0`

이 rule이 어떤 severity만 지원하는지는 `validation.supported_severities`와 함께 해석하면 된다.

#### `evaluation_sample`

실제 예시 몇 건을 보여준다.

예:
- `monitored_object_id`
- `display_name`
- `object_type`
- `current_value`
- `severity`
- `would_fire`
- `matched_candidate_rule_keys`
- `winner_rule_key`
- `winner_rule_scope`
- `reason`

즉 `matched_object_sample`과 `evaluation_sample`은 분리하되, row shape는 비슷하게 맞추는 것이 frontend 구현에도 유리하다.

MVP에서는 `evaluation_sample`을 다음처럼 나누어 생각하는 것이 적절하다.

- 최소 필드 세트:
  - `monitored_object_id`
  - `display_name`
  - `object_type`
  - `current_value`
  - `severity`
  - `would_fire`
  - `matched_candidate_rule_keys`
  - `winner_rule_key`
  - `winner_rule_scope`
  - `reason`
- 선택 필드:
  - `winner_rule_id`
  - `suppressed_rule_keys`

즉 MVP에서는 운영자가 “왜 이 객체가 warning/critical이 되는지”를 이해하는 데 필요한 설명 필드를 우선 두고, 디버깅 성격이 강한 식별자 필드는 optional로 두는 편이 좋다.

이때 `suppressed_rule_keys`는 summary가 아니라 sample에서만 rule 단위 설명을 보강하는 용도로 사용한다.

추가 원칙:
- `reason`은 winner rule의 `display_name`을 직접 포함하지 않는다.
- winner rule 이름이 필요하면 `winner_rule_key`를 통해 `candidate_rule_catalog.display_name`을 참조한다.
- MVP에서는 `winner_rule_display_name` 같은 중복 convenience 필드는 두지 않는 편이 적절하다.
- 이후 실제 UI/알림 채널에서 lookup 비용이 불편해질 때만 보조 필드로 재검토한다.

MVP에서는 `evaluation_sample`의 shape를 row마다 바꾸지 않고, 가능한 한 고정적으로 유지하는 것이 적절하다.

권장 원칙:
- `matched_candidate_rule_keys`는 항상 배열
  - 최소 1개 이상
- `winner_rule_key`는 항상 존재
  - fire되면 문자열
  - fire되지 않으면 `null`
- `suppressed_rule_keys`는 항상 배열
  - suppression이 없으면 `[]`

즉 필드 존재 여부로 상태를 구분하지 않고, 값(`null`, `[]`)으로 상태를 표현하는 stable shape를 채택하는 것이 적절하다.

이 방식의 장점:
- frontend 분기 단순화
- 응답 스키마 안정성
- 이후 event/stale/window rule 확장 시 호환성 유지
- rule 평가 결과를 더 일관되게 직렬화 가능

`matched_candidate_rule_keys`는 winner/suppressed 이해를 위한 기본 컨텍스트이므로, suppression이 없는 row에서도 계속 포함하는 것이 적절하다.

즉 object별 해석은 다음처럼 읽는다.

- `matched_candidate_rule_keys`
  - 이 object 평가에 참가한 후보 rule들
- `winner_rule_key`
  - 그중 최종 승자
- `suppressed_rule_keys`
  - 승자에게 밀린 후보들

이 구조를 쓰면 `would_fire = false`인 row가 이후 들어오더라도 shape를 그대로 유지할 수 있다.

### 7.3.2 DB / runtime 매핑 방향

preview 응답 shape는 DB 테이블을 그대로 노출하는 것이 아니라, 저장된 데이터와 계산된 결과를 조합해서 만드는 것이 적절하다.

권장 매핑은 다음과 같다.

- `normalized_rule`
  - source: preview 요청 body
  - 저장 전이므로 DB row가 아닐 수 있음

- `selector_resolution`
  - source:
    - [monitored_objects](C:/2604_swacan_auto/db/schema.sql)
    - 필요 시 selector 해석 결과

- `candidate_rule_catalog`
  - source:
    - 요청으로 들어온 preview 대상 rule 1건
    - 기존 [alert_rules](C:/2604_swacan_auto/db/schema.sql) row 중 같은 family에서 경쟁 후보가 되는 row

- `evaluation_summary`
  - source:
    - selector로 매칭된 object 목록
    - [latest_states](C:/2604_swacan_auto/db/schema.sql)
    - 기존 [alert_rules](C:/2604_swacan_auto/db/schema.sql)
    - suppression 정책 적용 결과를 메모리에서 집계

- `evaluation_sample`
  - source:
    - object별 현재 latest state
    - object별 candidate rule 매칭 결과
    - winner / suppressed 판정 결과

즉 MVP preview 구현은 별도 preview 테이블을 만들기보다:

1. 요청 rule을 메모리에서 정규화
2. 같은 family의 기존 rule을 DB에서 조회
3. selector로 대상 object를 해석
4. object별 latest state와 candidate rules를 평가
5. catalog + summary + sample 응답으로 조립

하는 방식이 가장 현실적이다.

중요한 점:
- `candidate_rule_catalog` 안의 `preview` rule은 DB에 저장되지 않은 synthetic candidate일 수 있다.
- `existing` candidate만 실제 `alert_rules.id`를 가진다.
- 따라서 sample에서는 `winner_rule_key`를 기본 참조 키로 쓰고, `winner_rule_id`는 optional 보조 필드로 두는 것이 적절하다.

### 7.3.1 `reason` 필드의 단계별 방향

MVP에서는 `evaluation_sample.reason`을 자유 문자열로 제공하는 것이 적절하다.

이유:
- 운영자가 preview를 빠르게 읽고 이해하는 데 충분하다.
- 구현 복잡도를 불필요하게 올리지 않는다.
- threshold rule MVP 범위에서는 설명 패턴이 상대적으로 단순하다.

예:
- `specific monitored_object rule overrides object_type rule`
- `current value 97.2 is greater than critical threshold 95`
- `current value 82 is greater than warning threshold 80`

다만 product 단계에서는 `reason`을 문자열만으로 두기보다, 별도의 구조화된 code 체계를 같이 갖는 것이 좋다.

권장 방향:
- `reason_code`
- `reason_message`
- 필요 시 `reason_params`

예:
- `reason_code = threshold_critical_gte`
- `reason_code = threshold_warning_lte`
- `reason_code = specific_rule_suppressed_general`

이렇게 해두면 이후 다음 활용이 가능해진다.

- reason 기준 통계
- 특정 유형의 발화 원인 집계
- UI 다국어 처리
- 운영 리포트 / 분류 / 분석

즉 현재 결론은 다음과 같다.

- MVP:
  - `reason` 자유 문자열
- Product:
  - `reason_code` 중심 구조화 + `reason_message` 병행

추가 원칙:
- `reason`은 사람이 바로 읽을 수 있는 설명 문장이다.
- `reason`은 preview UI에서 운영자가 빠르게 의미를 파악하도록 돕는 역할에 집중한다.
- `reason`은 구조적 판정 근거를 완전히 대체하지 않는다.
- 구조적 판정 근거는 `winning_condition_trace`가 맡는다.
- `reason`은 rule 이름을 포함하는 제목 역할까지 동시에 맡지 않는다.

즉 `reason`과 `winning_condition_trace`는 다음처럼 역할을 나누는 것이 적절하다.

- `reason`
  - 사람 중심 설명
  - 자연어 문장
  - “왜 fire되었는가”를 빠르게 이해시키는 용도
  - rule 이름은 별도 문맥에서 표시
- `winning_condition_trace`
  - 기계적으로 해석 가능한 최소 구조 정보
  - 어떤 severity / operator / clause가 winner였는지 설명
  - UI 하이라이트, 디버깅, 이후 product 확장의 기반

### 7.4 MVP에서의 응답 범위 제한

preview 응답은 너무 커지지 않게 제한하는 편이 좋다.

권장:
- 전체 count는 summary로 제공
- 상세는 sample 위주로 제공
- sample은 예를 들어 최대 20건
- 필요 시 이후 pagination 확장

### 7.5 MVP에서 아직 하지 않는 것

- historical replay
- window 계산 preview
- event rule preview
- lifecycle policy preview

MVP preview는 “현재 latest state 기준으로 threshold rule이 어떻게 평가되는가”에 집중하는 것이 적절하다.

### 7.6 권장 Preview API 설계

현재 구현에는 저장된 rule id를 기준으로 미리보기를 보여주는 경로가 이미 있다.

- `GET /api/admin/alert-rules/{id}/targets-preview`

다만 앞으로의 preview는 “저장 전 draft rule”도 다뤄야 하므로, MVP 기준의 표준 경로는 다음처럼 가는 것이 적절하다.

- `POST /api/admin/alert-rules/preview`

권장 방향:
- `POST /preview`
  - 표준 preview endpoint
  - 저장되지 않은 draft rule도 평가 가능
- `GET /alert-rules/{id}/targets-preview`
  - compatibility wrapper
  - 기존 저장 rule을 읽은 뒤 공통 evaluator를 호출

즉 외부 API는 2개가 될 수 있지만, 내부 평가는 하나의 preview evaluator를 공유하는 구조가 적절하다.

### 7.7 권장 request shape

MVP에서는 threshold rule만 지원하는 request로 고정하는 것이 적절하다.

예:

```json
{
  "rule": {
    "scope_type": "object_type",
    "object_type": "SoftwareProcess",
    "monitored_object_id": null,
    "state_type": "process",
    "metric_key": "cpu_usage",
    "comparison": "gte",
    "warning_threshold": 80,
    "critical_threshold": 95,
    "is_enabled": true,
    "description": "Process CPU threshold"
  },
  "options": {
    "sample_limit": 20
  }
}
```

MVP에서는 `options.sample_limit` 정도만 두어도 충분하다.

### 7.8 권장 response shape 예시

예:

```json
{
  "normalized_rule": {
    "scope_type": "object_type",
    "object_type": "SoftwareProcess",
    "monitored_object_id": null,
    "state_type": "process",
    "metric_key": "cpu_usage",
    "comparison": "gte",
    "warning_threshold": 80,
    "critical_threshold": 95
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "supported_severities": ["warning", "critical"]
  },
  "selector_resolution": {
    "matched_object_count": 12,
    "matched_object_sample": [
      {
        "monitored_object_id": 101,
        "display_name": "proc-a",
        "object_type": "SoftwareProcess"
      }
    ]
  },
  "candidate_rule_catalog": [
    {
      "rule_key": "preview",
      "kind": "preview",
      "rule_id": null,
      "display_name": "Process CPU High Preview",
      "scope_type": "object_type",
      "scope_target_label": "SoftwareProcess",
      "state_type": "process",
      "metric_key": "cpu_usage",
      "comparison": "gte",
      "warning_threshold": 80,
      "critical_threshold": 95
    },
    {
      "rule_key": "rule:17",
      "kind": "existing",
      "rule_id": 17,
      "display_name": "Process CPU High",
      "scope_type": "monitored_object",
      "scope_target_label": "proc-a",
      "state_type": "process",
      "metric_key": "cpu_usage",
      "comparison": "gte",
      "warning_threshold": 70,
      "critical_threshold": 85
    }
  ],
  "evaluation_summary": {
    "would_fire_count": 4,
    "warning_count": 3,
    "critical_count": 1,
    "suppressed_count": 2
  },
  "evaluation_sample": [
    {
      "monitored_object_id": 101,
      "display_name": "proc-a",
      "object_type": "SoftwareProcess",
      "current_value": 97.2,
      "severity": "critical",
      "would_fire": true,
      "matched_candidate_rule_keys": ["preview", "rule:17"],
      "winner_rule_key": "rule:17",
      "winner_rule_scope": "monitored_object",
      "suppressed_rule_keys": ["preview"],
      "reason": "specific monitored_object rule overrides object_type rule"
    }
  ]
}
```

### 7.9 DB / runtime 매핑 방향

preview 응답은 DB row를 그대로 노출하는 것이 아니라, 저장된 데이터와 계산 결과를 조합해서 만드는 것이 적절하다.

권장 매핑:

- `normalized_rule`
  - source: preview 요청 body
- `selector_resolution`
  - source:
    - `monitored_objects`
- `candidate_rule_catalog`
  - source:
    - 요청 rule 1건
    - 기존 `alert_rules` 중 같은 family의 경쟁 후보
- `evaluation_summary`
  - source:
    - selector 대상 object
    - `latest_states`
    - 기존 `alert_rules`
    - suppression 정책 적용 결과를 메모리에서 집계
- `evaluation_sample`
  - source:
    - object별 latest state
    - object별 candidate rule 매칭 결과
    - winner / suppressed 판정 결과

즉 MVP에서는 별도 preview 테이블을 만들기보다:

1. 요청 rule 정규화
2. 같은 family의 기존 rule 조회
3. selector로 대상 object 해석
4. object별 latest state와 candidate rules 평가
5. catalog + summary + sample 응답 조립

방식이 가장 현실적이다.

중요한 점:
- `preview` rule은 저장되지 않은 synthetic candidate일 수 있다.
- `existing` candidate만 실제 `alert_rules.id`를 가진다.
- 따라서 `winner_rule_key`를 기본 참조 키로 쓰고, `winner_rule_id`는 optional 보조 필드로 두는 것이 적절하다.

### 7.10 권장 구현 slice

MVP 구현은 다음 순서가 적절하다.

1. 공통 preview evaluator 추출
2. `POST /api/admin/alert-rules/preview` 추가
3. 기존 `GET /alert-rules/{id}/targets-preview`를 compatibility wrapper로 정리
4. admin preview 패널을 새 response shape로 전환

### 7.11 Compound Threshold Preview Shape 확장 방향

`compound threshold`는 저장 모델을 바로 바꾸기보다, 먼저 preview shape와 evaluator를 compound 친화적으로 확장하는 것이 적절하다.

핵심 원칙:
- 기존 `evaluation_summary`와 `evaluation_sample`의 stable shape는 유지한다.
- rule 정규화 표현만 `scalar -> compound-compatible` 방향으로 확장한다.
- 저장 전 synthetic preview rule과 저장된 existing rule을 같은 evaluator로 비교할 수 있어야 한다.

#### 7.11.1 `normalized_rule` 확장

`normalized_rule`은 향후 compound threshold를 기준으로 다음 필드를 가질 수 있다.

- `condition_mode`
  - `scalar`
  - `compound`
- `warning_condition`
- `critical_condition`

예시:

```json
{
  "condition_mode": "compound",
  "warning_condition": {
    "logical_operator": "or",
    "clauses": [
      { "comparison": "lte", "value": 20 },
      { "comparison": "gte", "value": 80 }
    ]
  },
  "critical_condition": {
    "logical_operator": "or",
    "clauses": [
      { "comparison": "lte", "value": 10 },
      { "comparison": "gte", "value": 90 }
    ]
  }
}
```

현재 scalar threshold rule도 내부적으로는 다음처럼 정규화할 수 있다.

```json
{
  "condition_mode": "scalar",
  "warning_condition": {
    "logical_operator": null,
    "clauses": [
      { "comparison": "gte", "value": 80 }
    ]
  },
  "critical_condition": {
    "logical_operator": null,
    "clauses": [
      { "comparison": "gte", "value": 95 }
    ]
  }
}
```

즉 preview evaluator는 저장된 rule이 scalar인지 compound인지와 무관하게, severity별 condition group으로 정규화된 입력을 받는 구조가 적절하다.

다만 shape validation 기준은 명확히 유지한다.

- `condition_mode = scalar`
  - `logical_operator = null`
  - clause = 정확히 1개
- `condition_mode = compound`
  - `logical_operator = and | or`
  - clause = 정확히 2개

즉 내부 정규화는 “같은 evaluator가 이해할 수 있는 공통 구조”를 만드는 것이고, 잘못된 mode/operator/clause 조합을 normalize로 흡수하는 것은 MVP에서 권장하지 않는다.

#### 7.11.2 `candidate_rule_catalog` 확장

`candidate_rule_catalog`의 각 item도 self-contained 원칙을 유지하며, compound threshold 기준 필드를 함께 포함하는 것이 적절하다.

권장 방향:
- `state_type`
- `metric_key`
- `comparison`
- `warning_condition`
- `critical_condition`

즉 기존 scalar field를 compatibility를 위해 유지하더라도, preview shape는 condition group 표현을 함께 제공하는 방향이 좋다.

#### 7.11.3 `evaluation_summary` 유지

compound threshold를 도입하더라도 `evaluation_summary`의 shape와 의미는 바꾸지 않는 것이 적절하다.

- `would_fire_count`
- `warning_count`
- `critical_count`
- `suppressed_count`

즉 compound threshold는 rule 내부 condition 표현의 확장이지, preview summary의 집계 의미를 바꾸는 방향은 아니다.

#### 7.11.4 `evaluation_sample`의 얇은 condition trace

`evaluation_sample`은 기존 stable shape를 유지하되, compound threshold 설명력을 위해 얇은 trace 필드를 추가하는 것이 적절하다.

권장 확장 필드:
- `winning_condition_trace`

MVP에서의 권장 최소 shape:

- `severity`
  - `warning`
  - `critical`
- `condition_mode`
  - `scalar`
  - `compound`
- `logical_operator`
  - `null`
  - `and`
  - `or`
- `matched_clause_indexes`
  - winner condition 내부에서 실제로 매칭된 clause index 배열

즉 MVP trace는 “어떤 severity가 이겼는지”, “이 condition이 scalar인지 compound인지”, “and/or 중 어떤 방식으로 평가됐는지”, “어느 clause가 실제로 매칭됐는지”만 담는 최소 winner-trace로 유지하는 것이 적절하다.

이때 trace 해석이 깔끔해지려면 shape validation이 먼저 엄격해야 한다.  
즉 `compound`인데 `logical_operator = null`이거나, `scalar`인데 `logical_operator = and/or`인 상태는 trace 단계까지 오기 전에 invalid로 걸러지는 편이 좋다.

예시:

```json
{
  "monitored_object_id": 101,
  "display_name": "proc-a",
  "object_type": "SoftwareProcess",
  "current_value": 97.2,
  "severity": "critical",
  "would_fire": true,
  "matched_candidate_rule_keys": ["preview", "rule:17"],
  "winner_rule_key": "preview",
  "suppressed_rule_keys": [],
  "reason": "value matched critical upper-bound clause",
  "winning_condition_trace": {
    "severity": "critical",
    "condition_mode": "compound",
    "logical_operator": "or",
    "matched_clause_indexes": [1]
  }
}
```

이 필드의 목적:
- MVP에서는 `reason` 문자열만으로도 운영자가 빠르게 읽을 수 있게 한다.
- 이후 product 단계에서는 어떤 clause가 매칭되었는지 시각적으로 표시할 수 있다.
- scalar rule도 `matched_clause_indexes = [0]` 형태로 같은 구조를 유지할 수 있다.

역할 경계:
- `winning_condition_trace`는 “어떤 구조적 조건이 winner였는가”를 설명한다.
- `winning_condition_trace`는 자연어 설명을 대신하지 않는다.
- `reason`은 문장형 설명을 제공하고, `winning_condition_trace`는 그 설명의 최소 구조적 근거를 제공한다.
- 같은 정보라도 중복 필드를 불필요하게 늘리지 않는다.
  - 예: `matched_clause_count`는 `len(matched_clause_indexes)`로 계산 가능하므로 MVP에서는 별도 필드로 두지 않는다.

권장 해석 규칙:
- `would_fire = false`이면 `winning_condition_trace = null`
- `critical_condition`이 성립하면 trace는 `critical_condition` 기준으로만 기록
- `critical_condition`이 성립하지 않고 `warning_condition`이 성립하면 trace는 `warning_condition` 기준으로 기록
- suppression이 있더라도 trace는 최종 winner rule의 winner condition만 기록
- suppress된 후보 rule의 clause trace는 MVP에서 다루지 않음

권장 구현 규칙:
- `matched_clause_indexes`는 winner condition 내부의 index를 사용
- index는 `0-based`로 해석
- clause 순서는 request / normalized order를 그대로 유지
- scalar rule은 `logical_operator = null`, `matched_clause_indexes = [0]`으로 정규화
- `and` 조건은 보통 `[0, 1]`처럼 모든 매칭 clause를 기록
- `or` 조건은 실제로 매칭된 clause만 기록

즉 `logical_operator = null`은 “single-clause winner condition의 공통 표현”이라기보다, MVP 범위에서는 실질적으로 `scalar mode`와 함께 쓰이는 형태로 유지하는 편이 더 명확하다.

MVP에서 의도적으로 제외하는 범위:
- clause별 상세 reason code
- interval normalization 결과 전체
- warning / critical 동시 trace
- suppressed rule의 clause trace
- non-winning severity trace

즉 MVP 기준으로는:
- `reason`은 읽기 쉬운 설명
- `winning_condition_trace`는 최소 구조 근거
- 둘을 합쳐도 evaluator 내부 전체 판단 과정을 그대로 노출하지는 않음

#### 7.11.5 현재 시점의 권장 결론

현재 시점에서는 compound threshold를 즉시 저장 모델에 반영하기보다:

1. preview shape를 severity별 condition group 기준으로 정규화하고
2. validation과 evaluator를 같은 정규화 구조 위에 올리고
3. `evaluation_sample`에 최소 trace만 추가할 수 있게 준비한 뒤
4. 실제 DB schema / admin editor 확장은 다음 단계에서 검토

하는 것이 가장 안전하다.

## 8. 단계별 확장 추천

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

## 9. 권장 API/DB 방향

### 9.1 현재 `alert_rules`를 유지하되 확장

가장 안전한 방법은 기존 `alert_rules`를 즉시 버리지 않고, 점진적으로 확장하는 것이다.

예시 방향:
- 기존 필드 유지
- 추가 필드:
  - `rule_key`
  - `display_name`
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

권장 역할:
- `rule_key`
  - unique
  - 시스템 중심 안정 식별자
- `display_name`
  - 사용자 중심 이름
  - alert UI / preview / 운영 메시지에서 우선 사용

즉 `alert_rules` 확장 방향에서도 “고유 키”와 “운영자용 이름”을 분리하는 것이 적절하다.

### 9.2 또는 `alert_rules_v2` 분리

장점:
- 현재 구조를 깔끔하게 보존
- 새 구조를 더 자유롭게 설계 가능

단점:
- migration과 UI가 이중화될 수 있음

현재 시점에서는 `기존 alert_rules 확장`이 더 현실적이다.

## 10. UI / 운영 관점

유연한 alert 조건은 단순히 DB schema 문제가 아니다.  
운영자가 이해할 수 있어야 한다.

그래서 다음이 반드시 같이 필요하다.

- rule preview
- 영향도 표시
- validation
- “이 rule이 현재 어떤 monitored object에 걸리는가” 설명
- “현재 어떤 객체가 warning/critical이 되는가” dry-run 결과
- 운영자가 rule을 이름으로 기억하고 추적할 수 있는 naming 체계

즉 구현 순서는:

1. 조건 모델 설계
2. validation / preview 설계
3. worker 평가 로직
4. admin UI 고도화

가 되어야 한다.

## 11. 현재 시점의 권장 결론

현재 backend alert 조건은 다음 방향으로 설계 검토를 진행하는 것이 적절하다.

- `monitored_object` 중심 alert 귀속 유지
- rule을 `selector / signal / condition / aggregation / lifecycle policy`로 분리
- 현재 단순 threshold rule은 compatibility 경로로 유지
- 다음 구현은 schema 변경보다:
  - 개념 모델 정리
  - validation / preview 방향 정리
  - 단계별 도입 순서 합의

를 먼저 하는 것이 맞다.

## 12. 다음 권장 작업

1. 현재 `alert_rules` 필드와 위 개념 모델의 매핑표 작성
2. 어떤 rule 타입을 MVP에 포함할지 범위 고정
3. `selector / signal / condition / window / policy` 기준 API 초안 작성
4. preview / dry-run 응답 형식 초안 작성
