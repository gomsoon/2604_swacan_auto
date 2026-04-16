## Metamodel Editor Backlog

버전: Draft 0.2

목적: `Metamodel Editor`의 현재 구현 상태를 기준으로, 이미 완료된 핵심 축과 앞으로의 실제 우선순위를 다시 정리한다.

## 1. 현재까지 완료된 핵심 구현

다음 항목들은 이제 “아이디어”가 아니라 실제 구현 축으로 본다.

1. 메타모델 변경 영향도 / diff 보기
- draft version이 baseline version 대비 무엇이 바뀌었는지 비교할 수 있다.
- `semantic type`, `property`, `containment`, `association`, `notation`의 `added / changed / removed / unchanged`를 요약한다.
- 현재 baseline을 참조하는 active `Monitoring View` 영향 수도 확인할 수 있다.

2. Architecture Editor 연동 1차
- `Architecture Editor`가 view version이 참조하는 metamodel snapshot을 읽어 palette와 생성 가능 항목을 계산한다.
- 하드코딩된 일부 타입 분기에서 벗어나 `semantic_type_code`, `notation_code`, containment 규칙을 실제로 사용한다.
- metamodel에 추가된 타입이 editor palette에 반영되는 흐름이 닫혀 있다.

3. Metamodel Canvas 직접 편집 1차
- `Metamodel Canvas`에서 semantic type quick-create가 가능하다.
- containment / association relation을 canvas에서 직접 생성 시작할 수 있다.
- inspector quick action과 quick-save로 relation과 semantic type을 바로 수정할 수 있다.
- semantic type 배치 상태를 draft version별로 유지하고 간단한 이동/정렬을 수행할 수 있다.

4. draft 편집 핵심 CRUD
- semantic type
- property definition
- containment rule
- notation definition
- association definition
모두 draft version 기준으로 조회/생성/수정 가능하다.

5. publish 전 검증 1차
- missing default notation
- invalid default notation
- containment cycle
- invalid association reference
- invalid association edge type
같은 핵심 구조 오류를 publish 전에 차단한다.

## 2. 현재 시점의 실제 최우선 과제

이제부터의 우선순위는 “더 많은 편집 기능 추가”보다 “수명주기와 운영 안전성 강화” 쪽으로 옮기는 것이 맞다.

### Priority 1. Metamodel lifecycle hardening

가장 먼저 다뤄야 할 축이다.

주요 항목:
- semantic type / property / containment / notation / association의 삭제 흐름
- soft disable / inactive 처리
- clone / replace 흐름
- publish validation 확장
- draft / published / active / deprecated 버전 운영 UX 보강

왜 중요한가:
- 지금은 “편집할 수 있다”는 점은 충분히 확보되었다.
- 다음은 “안전하게 publish하고 운영할 수 있다”가 중요하다.
- lifecycle이 약하면 메타모델 편집 기능이 많아질수록 운영 리스크가 커진다.

### Priority 2. Architecture Editor / Monitoring View 연동 안정화

메타모델 편집의 실효성을 제품 전체에서 더 단단하게 만드는 축이다.

주요 항목:
- metamodel 변경이 `Architecture Editor` palette와 배치 제약에 어디까지 반영되는지 정리
- published metamodel과 `Monitoring View`의 notation/render 호환성 점검
- old compatibility path(`node_type`, `edge_type`, fallback 분기) 정리
- publish 전에 실제 editor/view 영향도를 더 정확히 보여주는 연결 강화

왜 중요한가:
- 메타모델은 `Metamodel Editor` 안에서만 예쁘게 돌아가면 의미가 작다.
- 실제 `Architecture Editor`와 `Monitoring View`에서 같은 정의를 안전하게 소비해야 한다.

### Priority 3. 권한 / 감사 로그

운영성과 변경 추적을 붙이는 단계다.

주요 항목:
- 누가 draft를 만들고 수정했는지
- 누가 publish 했는지
- 누가 active 전환을 수행했는지
- 필요 시 semantic type / notation / containment 변경 이력 요약

왜 중요한가:
- 메타모델은 시스템 전체에 영향을 주는 중심 정의다.
- edit / publish / activate 같은 액션은 이후 운영 책임과 연결되므로, 감사 흔적이 중요하다.

## 3. 중간 우선순위 backlog

아래 항목들은 중요하지만, 현재 시점에서는 위 3개보다 한 단계 뒤에 둔다.

### 3.1 Metamodel Canvas UX refinement
- hover / preview 시각 강조 강화
- semantic type와 relation의 quick action 확대
- canvas 기반 정렬 / 묶기 / 자동 배치 보강
- canvas에서 선택된 요소와 validation / diff 결과를 더 직접 연결

### 3.2 publish validation 확장
- orphan property
- inactive type 참조
- palette group 누락
- notation/render schema 필수값 누락
- editor/runtime 충돌 가능 규칙 추가 검증

주의:
- 이 항목은 Priority 1 lifecycle hardening과 일부 겹치므로, 실제 구현 시 함께 묶어서 처리할 수 있다.

### 3.3 버전 운영 UX
- version 상태와 역할 설명
- validation 결과와 diff를 더 명확하게 제시
- publish / activate / deprecated 전환의 영향도 설명 강화
- rollback / clone from published 흐름 시각화

### 3.4 용어 / 메시지 정리
- `Monitoring View`
- `Architecture Editor`
- `Metamodel Editor`
기준으로 버튼/상태/메시지 용어를 더 일관되게 맞춘다.

## 4. 후속 backlog

아래 항목은 지금 당장보다, MVP 중후반 또는 product 단계에서 더 적절하다.

1. 세밀한 권한 모델
- read-only editor
- draft edit 권한
- publish 권한
- activate 권한

2. 고급 변경 이력
- element 단위 before/after diff archive
- change set 비교
- version 간 자동 migration helper

3. 메타모델 템플릿 / import-export
- namespace template
- seed에서 draft 생성
- JSON export/import

## 5. 현재 판단

- 예전 backlog의 상위 3개인 `diff`, `Architecture Editor 연동`, `Canvas 직접 편집`은 1차 목표가 이미 구현되었다.
- 따라서 지금부터는 새로운 편집 기능을 계속 추가하는 것보다, `lifecycle hardening -> product integration hardening -> audit` 순서로 가는 것이 더 좋다.
- 각 구현 단계에서는 기능 추가 전에 작은 구조 점검(refactoring 필요 여부 확인)을 먼저 수행한다.
- 테스트는 계속 `boundary value analysis` 기준을 우선 적용한다.
