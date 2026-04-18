# Current Implementation Priorities

버전: Draft 0.3  
작성일: 2026-04-17

목적: 현재 구현 상태를 기준으로, 앞으로의 실제 개발 우선순위를 다시 정리한다.

참고 문서:
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)
- [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)
- [monitoring-view-backlog.md](C:/2604_swacan_auto/docs/monitoring-view-backlog.md)
- [monitoring-view-realtime-refresh-draft.md](C:/2604_swacan_auto/docs/monitoring-view-realtime-refresh-draft.md)
- [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)

## 1. 현재 상태 요약

- `Metamodel Editor`는 draft 편집, diff, validation, 권한/감사 로그, canvas 기반 직접 편집까지 1차 흐름이 갖춰졌다.
- `Architecture Editor`는 metamodel snapshot을 실제로 소비하며, `View Outline Tree + Architecture Canvas + Inspector` 작업공간, runtime binding 검색/미리보기, containment drag-drop, relation 생성 가이드까지 올라온 상태다.
- `Monitoring View`는 active snapshot, runtime identity, alert, grouped event를 바탕으로 안정적으로 동작하지만, 운영 화면으로서의 깊이는 더 키울 여지가 많다.
- `Alert`는 운영 가능한 1차 수준까지 올라왔고, 이후에는 backlog 기반 고도화 축으로 관리하는 것이 적절하다.

## 2. 현재 최우선 3개

### Priority 1. Monitoring View 구현 확대

지금부터의 주력 축은 `Monitoring View`다.

중점 항목:
- node/edge 선택에 따른 runtime overlay 정보 확대
- alert, grouped event, latest state의 운영자 관점 정리
- monitored object fan-out 결과를 더 직관적으로 보여주는 시각화
- active view snapshot과 runtime 상태의 연결을 더 명확하게 표현
- `SSE + monitored_object 단위 partial refresh + 느린 full reconcile` 구조를 다음 실시간 갱신 기본선으로 고정

### Priority 2. Monitoring View / Architecture Editor 연동 안정화

두 화면이 같은 메타모델과 같은 runtime identity 계층을 일관되게 소비하도록 더 다듬는 축이다.

중점 항목:
- Architecture Editor에서 설정한 runtime binding이 Monitoring View에서 어떻게 해석되는지 경계 정리
- active snapshot 전환 후 Monitoring View 반영 시나리오 점검
- 메타모델 변경 이후 Monitoring View가 깨지지 않도록 compatibility 경로 점검

### Priority 3. 운영/감사 추적 고도화

운영 관점에서 누가 무엇을 바꾸고, 무엇이 실제 운영 화면에 영향을 주는지 추적하는 축이다.

중점 항목:
- metamodel publish / activate 이후 영향 범위 추적
- view version publish / activate 흐름 감사 로그 강화
- Monitoring View에서 alert/event/operator action 사이의 연결성 보강

## 3. 2차 우선순위

### 3.1 Architecture Editor backlog
- outline tree 고도화
- runtime binding UX 후속 polish
- 제약 기반 직접 편집 2차 고도화
- 대형 view 편집 생산성 기능

자세한 목록은 [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)를 따른다.

### 3.2 Metamodel Editor backlog
- semantic type aggregate 중심 lifecycle 추가 보강
- publish validation 확장
- diff / review / version 운영 UX polish

### 3.3 Alert backlog
- archive / action log 역할 분리 정교화
- suppression / escalation 정책 고도화
- 운영자 처리 흐름 세분화

## 4. 지금 바로 무겁게 들어가지 않아도 되는 항목

- Architecture Editor의 과도한 시각 효과 확장
- Metamodel Canvas의 고급 배치 알고리즘
- alert correlation / root-cause grouping 고도화
- 고급 실시간 push 구조 전환
- agent productization 마무리 작업

## 5. 권장 진행 방식

1. 기능 시작 전 구조 점검
- 작은 refactoring이 먼저 필요한지 확인

2. 최소 구현
- API / DB / UI를 작은 닫힌 흐름으로 먼저 완성

3. 경계값 테스트 보강
- `boundary value analysis` 기준을 계속 적용

4. 그 다음 확장
- quick UX 개선이나 고급 기능은 1차 흐름이 닫힌 뒤 추가

## 6. 현재 결론

지금은 `Architecture Editor`를 계속 넓히기보다, 현재 수준을 backlog로 명확히 관리하면서 `Monitoring View`를 다음 주력 구현 축으로 가져가는 것이 맞다.
