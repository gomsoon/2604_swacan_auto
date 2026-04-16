# Current Implementation Priorities

버전: Draft 0.1  
작성일: 2026-04-16

목적: 현재 구현 상태를 기준으로, 앞으로의 개발 방향을 한 번에 판단할 수 있도록 전반 backlog의 우선순위를 다시 정리한다.

참고 문서:
- [mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/mvp-transition-roadmap.md)
- [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)
- [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)

## 1. 현재 판단 요약

- `Metamodel Editor`는 이제 핵심 draft 편집과 canvas 기반 직접 편집의 1차 축이 닫혔다.
- `Architecture Editor`는 metamodel snapshot을 실제로 소비하는 구조까지 연결되었다.
- `Monitoring View`는 runtime identity, alert, grouped event, active view snapshot을 기준으로 동작하는 운영 흐름을 갖추었다.
- `alert`는 1차 운영 가능 수준까지 올라왔고, 이제는 주력축이 아니라 운영 고도화 backlog로 보는 것이 적절하다.
- 따라서 지금부터의 주력축은 `메타모델 수명주기와 운영 안전성 강화`이다.

## 2. 현재 최우선 3개

### Priority 1. Metamodel lifecycle hardening

가장 먼저 다뤄야 한다.

주요 이유:
- 편집 기능은 이미 충분히 생겼다.
- 이제 중요한 것은 `안전하게 publish하고 운영할 수 있는가`이다.

대표 항목:
- delete / disable / clone / replace
- publish validation 확장
- draft / published / active / deprecated 운영 UX 강화

### Priority 2. Architecture Editor / Monitoring View 연동 안정화

메타모델 편집의 실효성을 제품 전체로 연결하는 축이다.

주요 이유:
- metamodel이 editor 안에서만 동작하면 의미가 작다.
- `Architecture Editor`와 `Monitoring View`에서 같은 정의를 안정적으로 소비해야 한다.

대표 항목:
- editor/monitor 반영 경계 정리
- compatibility fallback 정리
- publish 전 영향도와 실제 사용 경로 연결 강화

### Priority 3. 권한 / 감사 로그

운영 책임과 변경 추적을 붙이는 단계다.

주요 이유:
- metamodel 변경은 제품 전체에 영향이 있다.
- 누가 edit / publish / activate 했는지 남겨야 운영성이 올라간다.

대표 항목:
- draft edit audit
- publish audit
- activate audit
- 필요 시 메타모델 변경 요약 이력

## 3. 2차 우선순위

### 3.1 Metamodel Editor UX refinement
- canvas hover/preview 강화
- quick action 확대
- layout / auto placement 개선
- validation / diff / inspector 연결 강화

### 3.2 Alert backlog
- archive/action log 역할 분리
- suppression 고도화
- rule dry-run preview 확장
- operator metadata / resolution taxonomy 보강

### 3.3 Agent efficiency and polish
- systemd / cgroup selector 검토
- multi-process daemon grouping 고도화
- 운영용 배포/업데이트 보조

## 4. 지금 보수적으로 뒤로 두어도 되는 항목

아래 항목은 가치가 있지만, 현재 시점에서는 바로 앞 순위보다 한 단계 뒤에 두는 편이 좋다.

- Metamodel Canvas의 더 화려한 직접 편집 UX
- editor 시각 효과 강화
- 고급 실시간 갱신 구조
- alert correlation / root-cause grouping
- 고급 import/export

## 5. 권장 진행 방식

앞으로도 아래 순서를 유지하는 것이 좋다.

1. 기능 시작 전 구조 점검
- 작은 refactoring이 먼저 필요한지 확인

2. 최소 구현
- API / DB / UI를 가장 작은 닫힌 흐름으로 먼저 완성

3. 경계값 테스트 보강
- `boundary value analysis` 기준 우선

4. 그 다음 확장
- quick UX 개선이나 추가 고도화는 1차 흐름이 닫힌 뒤에 수행

## 6. 한 줄 결론

지금부터의 최우선은 `더 많은 메타모델 편집 기능 추가`가 아니라, `메타모델의 수명주기와 운영 안전성을 단단하게 만드는 것`이다.
