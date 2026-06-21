# Alert Preview Decision Backlog

버전: Draft 0.1  
작성일: 2026-05-06

목적: alert rule preview 패널에서 `candidate / winner / suppressed` 설명을 단계적으로 확장하기 위한 후속 backlog를 분리 기록한다.

## 현재 구현 범위
- preview 패널은 현재 입력 rule 또는 저장된 rule 기준으로 target impact를 보여준다.
- scalar / compound threshold preview와 validation, `winning_condition_trace`까지는 확인 가능하다.
- 이번 slice에서는 `winner / suppressed`를 아주 얇게 설명하는 수준까지만 다룬다.

## 이번 slice에서 의도적으로 하는 것
- preview 응답에 item 단위 `winner`와 `suppressed` 최소 필드 추가
- preview 패널 item 카드에 `winner`와 `suppressed` 보조 설명 추가
- 현재 입력 rule과 published competing rule을 함께 본다는 점을 상단에 짧게 안내

## 이번 slice에서 하지 않는 것
- full `candidate_rule_catalog` UI
- rule 간 상세 trace tree
- suppressed rule별 clause trace
- compound threshold 저장 / publish
- runtime worker의 precedence / suppression enforcement 변경

## 다음 단계 backlog

### 1. Full Candidate Catalog
- top-level `candidate_rule_catalog`
- rule별 `display_name`, `rule_key`, `scope_type`, `metric_key`, `condition shape` 노출
- item row는 `winner_rule_key / suppressed_rule_keys` 참조 중심으로 연결

### 2. Decision Trace Deep Dive
- winner rule의 clause-level explanation 강화
- suppressed rule의 clause trace 노출
- preview 패널에서 `why this rule won` drill-down 지원

### 3. Runtime Precedence Alignment
- preview precedence 설명과 backend alert evaluation 정책의 정합성 재검토
- 필요 시 worker 기준 suppression / precedence enforcement 도입 검토

### 4. Product-Level Explainability
- `reason_code + reason_message + reason_params` 구조화
- decision statistics / audit / reporting과의 연결
