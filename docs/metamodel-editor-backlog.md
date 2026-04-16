# Metamodel Editor Backlog

버전: Draft 0.4  
작성일: 2026-04-16

목적: 현재 구현 상태를 기준으로 `Metamodel Editor`의 남은 작업을 다시 정리한다.  
이번 정리의 핵심은 `lifecycle의 주체`를 더 명확히 하는 것이다.

## 1. 핵심 구조 판단

- `Metamodel Version`이 가장 큰 lifecycle 단위다.
- `Semantic Type`은 그 아래의 핵심 편집 객체이자 aggregate root로 본다.
- `Property Definition`, `Notation Definition`은 독립 lifecycle 객체가 아니라 `Semantic Type` 내부 구성요소로 본다.
- `Containment Rule`, `Association Definition`은 개별 CRUD는 가능하지만, lifecycle 주체라기보다 `Metamodel Version` 범위의 관계 정의로 본다.

즉, 앞으로의 lifecycle hardening은 아래 두 축을 중심으로 진행한다.

1. `Metamodel Version` lifecycle  
   `draft -> published -> active -> deprecated`
2. `Semantic Type` aggregate 관리  
   clone / disable / safe delete / 내부 property / notation 포함 관리

## 2. 현재까지 1차 구현 완료로 보는 항목

아래 항목은 이제 “아이디어 단계”가 아니라 1차 구현 완료로 본다.

1. 메타모델 diff / 영향도 보기
- draft version과 baseline version 간 `semantic type`, `property`, `containment`, `association`, `notation` 차이를 비교할 수 있다.
- baseline을 참조하는 active `Monitoring View` 영향 수와 샘플 목록도 확인할 수 있다.

2. `Architecture Editor` 1차 연동
- `Architecture Editor`가 view version이 참조하는 metamodel snapshot을 읽어 palette와 생성 가능 항목을 계산한다.
- `semantic_type_code`, `notation_code`, containment 규칙을 실제로 사용한다.

3. `Metamodel Canvas` 직접 편집 1차
- semantic type quick-create
- containment / association canvas 생성 시작
- inspector quick action / quick save
- semantic type 배치 상태 저장과 간단한 위치 이동

4. draft 편집 CRUD
- semantic type
- property definition
- containment rule
- notation definition
- association definition

5. publish 전 기본 validation
- missing default notation
- invalid default notation
- containment cycle
- invalid association reference
- invalid association edge type

## 3. 현재 최우선 과제

## Priority 1. Metamodel lifecycle hardening

가장 먼저 다뤄야 할 축이다.

이번 우선순위에서 중요한 원칙:
- `property`와 `notation`은 독립 lifecycle 객체처럼 다루지 않는다.
- 대신 `semantic type aggregate 내부 편집 요소`로 보고 관리 편의 기능을 붙인다.
- 사용자가 보는 lifecycle는 크게 `version`과 `semantic type` 단위에 집중한다.

주요 작업:
- semantic type clone / safe delete / active-inactive 정리
- semantic type 내부 요소(property / notation) 편집 보강
- draft / published / active / deprecated 버전 운영 UX 보강
- publish validation 확장

메모:
- notation clone / delete / palette visibility toggle 같은 기능은 필요하다.
- 다만 이것을 “notation lifecycle”로 설명하지 않고, “semantic type 내부 정의 편집 보강”으로 설명하는 것이 맞다.

## Priority 2. Architecture Editor / Monitoring View 연동 안정화

메타모델 편집의 효과가 실제 제품 동작으로 안정적으로 이어지는지를 다지는 축이다.

주요 작업:
- published metamodel과 `Architecture Editor` palette 동기화 경계 정리
- `Monitoring View`에서 notation/render 해석 경계 정리
- compatibility fallback 정리
- publish 전 영향도와 실제 사용 경로 연결 강화

## Priority 3. 권한 / 감사 로그

운영 책임과 변경 추적을 위한 축이다.

주요 작업:
- draft 편집 이력
- publish 이력
- activate 이력
- semantic type aggregate 변경 요약 이력

## 4. 중간 우선순위 backlog

아래 항목은 중요하지만, 현재 상위 3개를 마친 뒤 들어가는 것이 더 적절하다.

### 4.1 Metamodel Canvas UX refinement
- hover / preview 시각 강화
- quick action 확대
- layout / auto placement 개선
- validation / diff / inspector 연결 강화

### 4.2 Validation 확장
- orphan property
- inactive type 참조
- palette group 누락
- render schema 필수 필드 부족
- editor/runtime 충돌 가능 규칙

주의:
- 이 항목은 Priority 1과 많이 겹친다.
- 실제 구현 때는 lifecycle hardening 작업 안에 일부 흡수될 수 있다.

### 4.3 Version 운영 UX
- version 상태와 역할 설명 강화
- validation 결과와 diff를 더 명확히 제시
- publish / activate / deprecated 전환 영향 설명 강화
- rollback / clone from published 흐름 시각화

### 4.4 용어 / 메시지 정리
- `Monitoring View`
- `Architecture Editor`
- `Metamodel Editor`
기준으로 버튼, 상태, 안내 메시지를 더 일관되게 맞춘다.

## 5. 후속 backlog

아래 항목은 MVP 중후반이나 product 단계에서 더 적절하다.

1. 세분화된 권한 모델
- read-only editor
- draft edit 권한
- publish 권한
- activate 권한

2. 고급 변경 이력
- element 단위 before / after diff archive
- change set 비교
- version 간 migration helper

3. 메타모델 템플릿 / import-export
- namespace template
- seed 기반 draft 생성
- JSON export / import

## 6. 현재 결론

- 예전 상위 3개였던 `diff`, `Architecture Editor 연동`, `Canvas 직접 편집`은 1차 구현 완료로 본다.
- 지금부터의 중심은 “편집 기능을 더 많이 붙이는 것”이 아니라 “version과 semantic type aggregate를 더 안전하게 운영할 수 있는 구조를 만드는 것”이다.
- 특히 `property`와 `notation`은 독립 lifecycle 객체가 아니라 `semantic type` 내부 구성요소라는 원칙을 계속 유지하는 것이 중요하다.
- 테스트는 계속 `boundary value analysis` 기준을 우선 적용한다.
