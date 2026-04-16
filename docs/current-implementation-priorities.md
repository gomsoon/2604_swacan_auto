# Current Implementation Priorities

버전: Draft 0.2  
작성일: 2026-04-16

목적: 현재 구현 상태를 기준으로, 앞으로의 실제 개발 우선순위를 다시 정리한다.

참고 문서:
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)
- [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)

## 1. 현재 상태 요약

- `Metamodel Editor`는 draft 편집, diff, validation, canvas 기반 직접 편집까지 1차 흐름이 구현되었다.
- `Architecture Editor`는 metamodel snapshot을 실제로 읽어 palette와 배치 제약을 적용하는 방향으로 전환되었다.
- `Monitoring View`는 active view snapshot, runtime identity, alert, grouped event를 기준으로 안정적으로 동작한다.
- alert는 1차 운영 가능 수준까지 올라왔고, 현재는 주력축보다 backlog 성격이 강하다.

## 2. 현재 최우선 3개

## Priority 1. Metamodel lifecycle hardening

가장 먼저 다뤄야 할 축이다.

핵심 원칙:
- lifecycle의 주체는 `Metamodel Version`과 `Semantic Type`이다.
- `Property Definition`, `Notation Definition`은 독립 lifecycle 객체가 아니라 `Semantic Type` 내부 구성요소다.
- `Containment Rule`, `Association Definition`은 version-scoped 관계 정의로 본다.

중점 항목:
- semantic type clone / safe delete / active-inactive
- semantic type 내부 요소(property / notation) 편집 보강
- draft / published / active / deprecated 버전 운영 UX 강화
- publish validation 확장

## Priority 2. Architecture Editor / Monitoring View 연동 안정화

메타모델 변경이 실제 편집/운영 화면에 안정적으로 반영되는지를 다지는 축이다.

중점 항목:
- `Architecture Editor`와 published metamodel snapshot의 경계 정리
- `Monitoring View`에서 notation/render 해석 경계 정리
- compatibility fallback 정리
- publish 전 영향도와 실제 사용 경로 연결 강화

## Priority 3. 권한 / 감사 로그

운영 책임과 변경 추적을 위한 축이다.

중점 항목:
- draft edit audit
- publish audit
- activate audit
- semantic type aggregate 변경 요약 이력

## 3. 2차 우선순위

### 3.1 Metamodel Editor UX refinement
- canvas hover / preview 강화
- quick action 확대
- layout / auto placement 개선
- validation / diff / inspector 연결 강화

### 3.2 Alert backlog
- archive / action log 역할 정리
- suppression 고도화
- rule preview / dry-run 보강
- operator metadata 보강

### 3.3 Agent efficiency and polish
- systemd / cgroup selector 검토
- multi-process daemon grouping 고도화
- 운영 배포 / 업데이트 보조

## 4. 지금 바로 크게 밀지 않아도 되는 항목

- Metamodel Canvas의 과도한 직접 편집 UX 확대
- editor 시각 효과 고도화
- 고급 실시간 갱신 구조
- alert correlation / root-cause grouping 고도화
- 고급 import / export

## 5. 권장 진행 방식

1. 기능 시작 전 구조 점검
- 작은 refactoring이 먼저 필요한지 확인

2. 최소 구현
- API / DB / UI를 가장 작은 닫힌 흐름으로 먼저 완성

3. 경계값 테스트 보강
- `boundary value analysis` 기준 우선 적용

4. 그 다음 확장
- quick UX 개선이나 고급 기능은 1차 흐름이 닫힌 뒤 추가

## 6. 현재 결론

지금은 `Metamodel Editor` 기능을 계속 넓히는 단계보다, `version + semantic type aggregate` 중심의 수명주기와 운영 안정성을 다지는 단계로 보는 것이 맞다.
