# Alert Compound Threshold Storage Draft

버전: Draft 0.1  
작성일: 2026-05-10

목적: `compound threshold`를 preview 전용 기능에서 `draft 저장 가능` 단계로 확장하기 위한 저장모델 설계를 정리한다.  
이번 문서는 JSON 대신 RDBMS column 설계를 기준으로 하며, 구현 시 필요한 regression test 관점도 함께 고정한다.

## 1. 이번 단계 목표

- `compound threshold`를 draft rule에 저장할 수 있게 한다.
- preview / GET / PATCH / clone은 compound shape를 이해한다.
- publish와 runtime evaluator는 이번 단계에서 그대로 scalar 중심으로 유지한다.
- 즉, 이번 단계의 범위는 `draft-save-capable compound threshold`이다.

## 2. 설계 원칙

1. `warning_condition`과 `critical_condition`은 독립 group이다.
2. 저장모델은 JSON이 아니라 explicit column을 사용한다.
3. 현재 허용 grammar는 작다.
   - severity 2개: `warning`, `critical`
   - clause 최대 2개
   - logical operator: `and | or | null`
   - nested expression 없음
4. 기존 scalar threshold rule과 backward-compatible 해야 한다.
5. 이번 단계에서는 compound draft 저장까지만 허용하고, publish는 차단한다.

## 3. 권장 DB column 설계

기존 `alert_rules`의 scalar 필드는 유지한다.

- `comparison`
- `warning_threshold`
- `critical_threshold`

여기에 아래 column을 추가한다.

```sql
cond_mode TEXT NOT NULL DEFAULT 'scalar'
    CHECK (cond_mode IN ('scalar', 'compound')),

warning_logical_op TEXT NULL
    CHECK (warning_logical_op IN ('and', 'or')),
warning_cl1_comp TEXT NULL
    CHECK (warning_cl1_comp IN ('gt', 'gte', 'lt', 'lte')),
warning_cl1_val REAL NULL,
warning_cl2_comp TEXT NULL
    CHECK (warning_cl2_comp IN ('gt', 'gte', 'lt', 'lte')),
warning_cl2_val REAL NULL,

critical_logical_op TEXT NULL
    CHECK (critical_logical_op IN ('and', 'or')),
critical_cl1_comp TEXT NULL
    CHECK (critical_cl1_comp IN ('gt', 'gte', 'lt', 'lte')),
critical_cl1_val REAL NULL,
critical_cl2_comp TEXT NULL
    CHECK (critical_cl2_comp IN ('gt', 'gte', 'lt', 'lte')),
critical_cl2_val REAL NULL
```

### naming 원칙

- `condition` -> `cond`
- `operator` -> `op`
- `clause` -> `cl`
- `value` -> `val`

이 naming은 짧지만 규칙적이고, SQLite schema / migration / query에서 충분히 읽을 수 있다.

## 4. scalar / compound 저장 규칙

### 4.1 scalar

- `cond_mode = 'scalar'`
- 기존 scalar field가 source of truth
  - `comparison`
  - `warning_threshold`
  - `critical_threshold`
- compound column은 모두 `NULL`

### 4.2 compound

- `cond_mode = 'compound'`
- compound column이 source of truth
- 기존 scalar field는 compatibility를 위해 유지하되, 이번 단계에서는 source of truth로 사용하지 않는다
- preview / GET API는 compound column을 normalized condition shape로 조립해서 반환한다

## 5. mode별 validation 규칙

### 5.1 scalar

- `comparison`은 필수
- `warning_threshold` 또는 `critical_threshold` 중 하나 이상 필요
- compound column은 모두 `NULL`
- `warning-only`, `critical-only`는 허용

### 5.2 compound

- 각 severity group은 독립 검증
- group이 존재한다면:
  - `logical_op`는 `and | or`
  - `cl1_comp`, `cl1_val`, `cl2_comp`, `cl2_val`는 모두 필요
- `warning-only`, `critical-only`는 허용
- 둘 다 존재하면 `critical_condition ⊆ warning_condition`을 만족해야 한다

### 5.3 semantic validation

- unsatisfiable condition은 invalid
  - 예: `gte 80 AND lte 20`
- redundant clause는 warning
  - 예: `gte 80 OR gte 90`
- severity subset 위반은 invalid

## 6. API 단계별 해석

### 6.1 POST / PATCH

- `scalar`, `compound` 둘 다 draft에서 저장 가능
- serializer는 항상 normalized shape를 반환

### 6.2 GET

- DB row가 scalar든 compound든 normalized shape로 내려준다
- 즉 frontend는 `cond_mode`를 보고 렌더링만 분기하면 된다

### 6.3 clone

- compound draft도 그대로 복제 가능
- 새 rule은 항상 `draft`
- `is_enabled = false`

### 6.4 publish

이번 단계에서는 아래 정책을 유지한다.

- `scalar` draft는 기존 정책대로 publish 가능
- `compound` draft는 publish 차단
- 에러 메시지 예시:
  - `compound threshold publish is not enabled yet`

즉 이번 단계는 `save draft`까지이고, runtime/publish는 다음 단계 과제다.

## 7. migration / backfill

기존 rule은 모두 아래처럼 backfill 한다.

- `cond_mode = 'scalar'`
- compound column은 모두 `NULL`
- 기존 `comparison`, `warning_threshold`, `critical_threshold`는 그대로 유지
- 기존 `published` 상태도 그대로 유지

이 방식이 가장 안전하다.

## 8. 구현 slice 권장 순서

1. schema 확장
2. DB read serializer 확장
3. create / patch 저장 경로에 compound 수용
4. clone 수용
5. publish 차단
6. admin editor 저장 UX 연결
7. 전체 regression + coverage 확인

## 9. regression testing 관점

DB schema 변경이 포함되므로, 이번 단계에서는 기능 테스트뿐 아니라 migration / serialization / lifecycle 경계값을 꼭 같이 확인해야 한다.

### 9.1 DB / migration

- 기존 scalar rule backfill
- 기존 published rule이 손상되지 않는지
- 새 compound column 기본값 / NULL 처리
- clone 시 compound column 복사 확인

### 9.2 API create / patch

- scalar draft create
- compound draft create
- compound draft patch
- invalid compound shape reject
- subset violation reject
- redundant clause warning 유지

### 9.3 lifecycle

- compound draft save 가능
- compound draft clone 가능
- compound publish blocked
- scalar publish unaffected

### 9.4 GET / serializer

- scalar row -> normalized scalar shape
- compound row -> normalized compound shape
- list / detail / preview 응답 shape 일관성

### 9.5 UI regression

- scalar editor flow 유지
- compound editor flow 저장 가능
- published rule read-only 유지
- compound published 차단 메시지 확인

## 10. 이번 단계의 의도적 비범위

- runtime worker의 compound evaluator
- compound publish 허용
- candidate catalog full UI
- reason_code 구조화
- event / stale / no-data rule 저장모델

## 11. 현재 결론

현재 compound threshold는 JSON보다 explicit column 설계가 더 적합하다.  
특히 `severity 2개 + clause 최대 2개` 제약을 유지하는 동안은,

- schema가 읽기 쉽고
- validation이 명확하며
- migration / regression test 설계가 단순하다.

따라서 다음 구현은 `compound draft 저장 가능, publish 차단` 모델로 가는 것이 가장 안전하다.
