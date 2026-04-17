# Architecture Editor Backlog

버전: Draft 0.1  
작성일: 2026-04-17

목적: `Architecture Editor`의 남은 구현 항목을 backlog로 정리한다.

## 1. 현재까지 완료된 핵심

- `View Outline Tree + Architecture Canvas + Inspector` 작업공간 1차 구현
- outline 검색, 전체 펼치기/접기, 선택 동기화
- metamodel snapshot 기반 palette
- 메타모델 property 정의 기반 inspector 동적 편집
- containment / association 시각 가이드
- containment drag-drop 재배치
- runtime binding 검색, 후보 선택, 경고/미리보기

## 2. 다음에 다시 잡아야 할 높은 우선순위

### 2.1 대형 View 편집 UX 강화
- outline tree에서 reparent
- 선택 항목으로 자동 포커스 강화
- layer / order 조정
- multi-select 검토
- 접기 상태 유지 고도화

### 2.2 Runtime Binding UX 후속 polish
- monitored object 상태 표시 정교화
- binding 중복/불일치 경고 표현 polish
- 저장 전 영향 안내 강화
- binding 없는 node의 빠른 필터링/검색

### 2.3 제약 기반 직접 편집 2차 고도화
- canvas quick-connect
- invalid 이유의 더 명확한 표현
- relation handle 기반 생성 검토
- quick-create 후 즉시 edit 연결 강화

## 3. 중간 우선순위

### 3.1 대형 draft view 생산성
- 트리 검색 결과에서 즉시 scroll/focus
- 대규모 containment 구조 접기 전략
- selection history / back-forward 검토

### 3.2 시각 polish
- candidate / blocked 상태 시각 표현 refinement
- relation hover preview 강화
- 선택 강조와 binding 상태 강조 구분

### 3.3 운영 연결성
- active Monitoring View 반영 경계 점검
- publish 후 Architecture Editor의 안내 메시지 정리
- metamodel 변경 이후 기존 draft 호환성 점검

## 4. 지금 당장 주력으로 잡지 않아도 되는 항목

- 고급 자동 정렬 알고리즘
- canvas 고급 시각 효과
- 복잡한 keyboard shortcut 체계
- 대규모 일괄 편집 도구

## 5. 현재 판단

지금 시점에서는 `Architecture Editor`를 계속 넓히기보다, 현재 수준을 운영 가능한 1차 기준점으로 보고 나머지 항목은 backlog로 관리하는 것이 적절하다. 다음 주력 구현은 `Monitoring View`로 옮기는 것이 더 큰 가치가 있다.
