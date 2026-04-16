# Architecture Editor Layout Draft

버전: Draft 0.1  
작성일: 2026-04-16

목적: `Architecture Editor`의 작업공간 레이아웃을 containment 중심 구조에 맞춰 정리하고, 이후 UX 확장의 기준점을 정의한다.

## 1. 기본 방향

- `Architecture Editor`는 `draft View Version`을 편집하는 화면이다.
- 중심 모델은 자유 배치 도구가 아니라 `containment`를 따르는 구조 편집기다.
- 따라서 화면은 `좌측 View Outline Tree + 가운데 Architecture Canvas + 우측 Inspector`를 기본 레이아웃으로 사용한다.

## 2. 화면 구조

### 2.1 좌측 View Outline Tree

- root는 현재 편집 중인 `draft View Version`이다.
- 하위 항목은 `containment` 구조에 따라 tree 형태로 정렬한다.
- tree는 최소한 다음 기능을 제공해야 한다.
  - containment 계층 탐색
  - 현재 선택 항목 강조
  - 선택 시 canvas와 inspector 동기화
  - 자식 수와 관계선 수 같은 최소 요약 표시
- `association`과 `CommunicationLink`는 tree의 주 구조가 아니라 보조 정보로 표시한다.

### 2.2 가운데 Architecture Canvas

- SVG 기반 배치와 연결을 담당한다.
- 사용자는 palette에서 객체를 추가하고, containment 규칙을 따르며 배치한다.
- relation 생성 시 메타모델 association 정의를 참고해 기본 edge와 방향을 결정한다.
- outline에서 선택한 항목과 canvas 선택은 항상 동기화되어야 한다.

### 2.3 우측 Inspector

- 현재 선택한 node 또는 edge의 상세 정보를 편집한다.
- semantic type에 정의된 property를 편집 가능하게 확장하는 방향을 따른다.
- runtime binding, layout, style, relation summary를 함께 보여줄 수 있어야 한다.
- outline이나 canvas에서 선택한 항목이 inspector로 즉시 반영되어야 한다.

## 3. 1차 구현 범위

- `View Outline Tree` 렌더링
- root + containment tree 표시
- outline 선택과 canvas / inspector 동기화
- outline에서 child count, edge count, binding 여부의 최소 배지 표시

## 4. 후속 확장 후보

- outline 검색
- 접기 / 펼치기 상태 유지
- drag 기반 tree 재배치
- node별 quick action
- selection sync 시 자동 scroll
- relation 전용 보조 패널

## 5. 설계 판단

- `Architecture Editor`는 구조를 편집하는 화면이므로 tree 기반 탐색성이 중요하다.
- `Monitoring View`는 읽기 중심 화면이므로 동일한 tree 레이아웃을 반드시 요구하지 않는다.
- `Metamodel Editor`와 유사하게 `좌측 구조 + 가운데 시각 표현 + 우측 inspector` 패턴을 공유하면 제품 전체 UX 일관성이 좋아진다.
