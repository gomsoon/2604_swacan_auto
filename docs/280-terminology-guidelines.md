# Software Architecture Runtime Monitoring System

## 용어 가이드
버전: Draft 0.1  
작성일: 2026-04-16

목적: 화면, 데이터 모델, 편집 흐름에서 반복적으로 사용되는 핵심 용어를 일관되게 정의한다. 본 문서는 다른 설계 문서에서 공통으로 참조하는 기준 용어집이다.

참고 문서:
- [150-mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/150-mvp-transition-roadmap.md)
- [190-view-versioning-operational-publish-design-draft.md](C:/2604_swacan_auto/docs/190-view-versioning-operational-publish-design-draft.md)
- [230-runtime-identity-binding-design-draft.md](C:/2604_swacan_auto/docs/230-runtime-identity-binding-design-draft.md)
- [160-metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/160-metamodel-notation-db-design-draft.md)

## 1. 화면 용어

### 1.1 Monitoring View
- runtime 상태, alert, event를 운영자가 조회하는 읽기 중심 화면
- 기본적으로 `active view version`을 기준으로 렌더링한다
- draft 편집 중인 내용은 Monitoring View에 직접 반영되지 않는다

### 1.2 Architecture Editor
- server, process, thread, communication line 등 아키텍처 요소를 편집하는 화면
- 기본적으로 `draft view version`을 대상으로 작업한다
- publish/activate는 editor에서 수행하지만, editor 자체는 운영 관제 화면이 아니다

### 1.3 Metamodel Editor
- semantic type, property, containment, association, notation을 편집하는 화면
- metamodel draft version을 대상으로 작업한다
- 좌측 목록, 중앙 구조 canvas/preview, 우측 inspector 기반의 편집 workspace를 기본 형태로 본다

## 2. 데이터 모델 용어

### 2.1 Logical View
- 사용자가 인식하는 하나의 아키텍처 화면 단위
- 예: `SimpleChatServer 운영 View`

### 2.2 View Version
- 특정 시점의 화면 snapshot
- 상태는 `draft`, `published`, `active`, `deprecated`를 사용한다

### 2.3 Draft View Version
- 편집 가능한 작업본
- Architecture Editor가 기본적으로 대상으로 삼는 version

### 2.4 Published View Version
- 편집이 끝난 고정 snapshot
- 승인 대기 또는 배포 후보

### 2.5 Active View Version
- 실제 Monitoring View가 읽는 운영 snapshot
- 동일 logical view에 대해 동시에 하나만 존재해야 한다

### 2.6 Deprecated View Version
- 더 이상 운영 기준으로 사용하지 않는 과거 snapshot
- 감사 추적, rollback 기준점으로 유지할 수 있다

## 3. Runtime Identity 용어

### 3.1 Monitored Object
- 실제 runtime 상태, event, alert의 귀속 대상이 되는 전역 논리 객체
- 예: host, process group, monitoring agent

### 3.2 Node Binding
- 특정 `view version node`가 어떤 `monitored object`를 참조하는지 연결하는 관계
- 하나의 monitored object는 여러 active view의 여러 node에 fan-out될 수 있다

## 4. 용어 사용 원칙

- `View`는 읽기 중심, 운영/관제 중심 의미로 사용한다
- `Editor`는 수정 중심, draft 작업 중심 의미로 사용한다
- 단독 `view`라는 표현이 모호할 때는 반드시 `Monitoring View`, `Logical View`, `View Version` 중 하나로 구체화한다
- runtime 상태 저장의 기준은 장기적으로 `view node`가 아니라 `monitored object`로 본다
- 화면 명칭은 가능하면 다음 세 가지로 고정한다
  - `Monitoring View`
  - `Architecture Editor`
  - `Metamodel Editor`

## 5. 권장 화면 구성 메모

### 5.1 Architecture Editor
- 좌측: palette
- 중앙: architecture canvas
- 우측: 선택 요소 inspector

### 5.2 Metamodel Editor
- 좌측: metamodel version, semantic type, notation, containment 목록
- 중앙: metamodel structure canvas 또는 notation preview canvas
- 우측: 선택 항목 상세 편집 inspector

### 5.3 Monitoring View
- 중앙: 운영 canvas
- 보조 영역: alert, event, latest state, drill-down 패널

## 6. 요약

- runtime monitoring 화면은 `Monitoring View`
- 아키텍처 편집 화면은 `Architecture Editor`
- 메타모델 편집 화면은 `Metamodel Editor`
- view snapshot과 runtime identity는 구분한다
- 문서, API, UI, 코드에서 위 용어를 일관되게 사용하는 것이 권장된다
