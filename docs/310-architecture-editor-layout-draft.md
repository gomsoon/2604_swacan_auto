# Architecture Editor Layout Draft

버전: Draft 0.2  
작성일: 2026-04-17

목적: `Architecture Editor`의 작업공간 레이아웃 원칙과 현재 구현 상태를 정리한다.

## 1. 기본 방향

- `Architecture Editor`는 `draft View Version`을 편집하는 화면이다.
- 이 화면은 자유 배치형 다이어그램 도구라기보다, 메타모델 containment와 association 제약을 따르는 구조 편집기다.
- 기본 레이아웃은 `좌측 View Outline Tree + 가운데 Architecture Canvas + 우측 Inspector`를 따른다.

## 2. 화면 구조

### 2.1 좌측 View Outline Tree

- root는 현재 편집 중인 `draft View Version`
- 하위 항목은 containment 구조 기준 tree 정렬
- 현재 선택과 canvas/inspector 동기화
- 검색, 모두 펼치기, 모두 접기 지원
- binding 여부, 자식 수, 관계 수 등 최소 배지 표시

### 2.2 가운데 Architecture Canvas

- node와 edge의 실제 배치와 연결을 다룬다.
- palette를 통한 node 생성
- relation 생성
- containment drag-drop 재배치
- 메타모델 제약 기반 candidate / blocked 가이드 표시

### 2.3 우측 Inspector

- 선택한 node 또는 edge의 상세 편집
- 메타모델 property 정의 기반 동적 속성 편집
- runtime binding 검색/선택/미리보기
- layout, style, relation 요약 확인

## 3. 현재 구현 상태

현재 1차 구현 기준으로 다음이 동작한다.

- `View Outline Tree`와 canvas/inspector 선택 동기화
- outline 검색, 펼치기/접기
- metamodel snapshot 기반 palette
- containment / association 제약 검증
- relation candidate / blocked 시각 가이드
- containment drag-drop
- runtime binding 검색, 미리보기, 중복/불일치 경고

## 4. 설계 판단

- `Architecture Editor`는 `Metamodel Editor`에서 정의한 semantic type과 notation을 소비하는 화면이다.
- 새로운 객체의 의미를 정의하지 않고, 이미 정의된 객체를 배치하고 연결해 `Monitoring View`의 구조를 만든다.
- 따라서 이 화면의 핵심은 “정의”보다 “구조 배치와 운영 연결”이다.

## 5. 후속 방향

- outline tree 기반 대형 view 편집 생산성 강화
- runtime binding UX polish
- 제약 기반 직접 편집 2차 고도화
- Monitoring View와의 반영 경계 안정화

세부 후속 목록은 [320-architecture-editor-backlog.md](C:/2604_swacan_auto/docs/320-architecture-editor-backlog.md)에 정리한다.
