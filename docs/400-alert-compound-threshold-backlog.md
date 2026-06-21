# Alert Compound Threshold Backlog

버전: Draft 0.1  
작성일: 2026-05-10

## 현재 기준

- `compound threshold`는 draft 저장, 조회, 수정, 복제까지 지원한다.
- preview / validation / winner trace는 admin UI에서 확인할 수 있다.
- publish 와 runtime evaluator는 아직 scalar threshold만 지원한다.

## 2차 구현으로 미루는 항목

1. `compound publish enablement`
- compound draft도 publish 가능한 lifecycle 정책 정리
- publish 시 validation / warnings / rollout 메시지 정교화

2. `runtime evaluator parity`
- preview 의 winner / suppressed 판단과 runtime worker 판단 정합성 확보
- precedence / suppression enforcement 를 실제 alert evaluation 경로에 반영

3. `candidate_rule_catalog full explainability`
- preview 패널에서 후보 rule 목록, winner, suppressed rule 상세 trace 시각화
- clause-level reason / structured explainability 확장

4. `compound list/detail visibility polish`
- alert rule 목록과 detail 에서 scalar / compound shape 를 더 잘 요약
- warning / critical condition 을 compact summary 로 표시

5. `coverage follow-up`
- compound save / reopen / clone / publish-block UI 회귀를 안정적으로 유지
- runtime parity 가 열리면 branch coverage 를 함께 끌어올리는 테스트 추가
