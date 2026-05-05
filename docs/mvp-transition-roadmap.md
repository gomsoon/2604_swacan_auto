# Software Architecture Runtime Monitoring System

## MVP 전환 로드맵

버전: Draft 0.3  
작성일: 2026-04-18

목적: `minimal-e2e-v1` 이후 현재 구현 상태를 기준으로, MVP 단계에서 어떤 축을 우선적으로 다룰지 다시 정리한다.

참고 문서:
- [minimal-e2e-signoff.md](C:/2604_swacan_auto/docs/minimal-e2e-signoff.md)
- [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)
- [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)
- [monitoring-view-backlog.md](C:/2604_swacan_auto/docs/monitoring-view-backlog.md)
- [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)
- [alert-condition-flexibility-draft.md](C:/2604_swacan_auto/docs/alert-condition-flexibility-draft.md)

## 1. 현재 기준점

- `Metamodel Editor`는 draft 편집, diff, validation, 권한/감사 로그, canvas 기반 직접 편집까지 1차 기준점에 도달했다.
- `Architecture Editor`는 metamodel snapshot 기반 palette, outline tree, runtime binding 검색/미리보기, containment drag-drop, relation direct edit까지 1차 기준점에 도달했다.
- `Monitoring View`는 selection summary, alert/event drill-down, SSE partial refresh, 최소 운영 액션, 객체 이력 요약까지 1차 기준점에 도달했다.
- `Alert`는 운영 가능한 1차 기능을 확보했고, 다음부터는 기능 확장보다 조건 설계와 lifecycle 구조를 다시 검토하는 단계가 되었다.

## 2. 현재 MVP 주력 축

### Phase A. Backend Alert 조건 설계 재정리

목표:
- backend가 alert을 생성하는 조건을 얼마나 유연하게 제공할지 개념 모델을 먼저 고정한다.

중점 항목:
- threshold rule의 한계 정리
- `rule_key / display_name` 기반 rule identity / naming 정책 정리
- 읽을 수 있는 `rule_key` format과 freeze 정책 고정
- `rule_key` 직접 입력 + 자동 제안 + 운영 이후 clone 정책 정리
- `display_name` rename 기준과 `rule_key` 전역 unique / 재사용 금지 정책 정리
- `rule_key` 자동 제안 slug 규칙과 suffix 충돌 정책 정리
- `rule_key` validation 문자 집합과 segment 규칙 고정
- `alert_rules`를 `draft / published / deprecated` lifecycle 엔터티로 끌어올리는 schema/API/UI slice 정리
- `selector / signal / condition / aggregation / lifecycle policy` 모델 검토
- MVP에 포함할 rule 타입 범위 고정
- validation / preview / dry-run 방향 정리

### Phase B. Alert Lifecycle / Archive 구조 정교화

목표:
- current alert와 종료된 alert lifecycle을 더 명확하게 분리한다.

중점 항목:
- `alert_instances(current)` / `alert_history(archive)` 역할 정리
- `resolution_source / resolution_reason` 모델 정교화
- manual resolve / auto recovery / policy timeout 구분
- 필요 시 `alert_action_log` 도입 검토
- rule rename 이후에도 archive 문맥을 유지하기 위한 `rule display name snapshot` 검토

### Phase C. Monitoring / Architecture / Metamodel 안정화

목표:
- 이미 1차 기준점을 확보한 세 editor/view의 역할과 경계를 유지하면서 후속 기능을 backlog 기반으로 관리한다.

중점 항목:
- Monitoring View: backlog 중심 후속 관리
- Architecture Editor: backlog 중심 후속 관리
- Metamodel Editor: lifecycle hardening 후속 관리

## 3. 현재 우선순위 판단

지금은 새로운 화면 기능을 계속 늘리는 시점이 아니라,

1. alert 조건 설계
2. alert lifecycle 구조 정리
3. 운영 화면 backlog 관리

순서로 다시 설계에 무게를 두는 것이 맞다.

## 4. 관련 backlog 관리 방향

- `Monitoring View` 후속 기능은 [monitoring-view-backlog.md](C:/2604_swacan_auto/docs/monitoring-view-backlog.md)에서 관리
- `Architecture Editor` 후속 기능은 [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)에서 관리
- `Metamodel Editor` 후속 기능은 [metamodel-editor-backlog.md](C:/2604_swacan_auto/docs/metamodel-editor-backlog.md)에서 관리
- `Alert` 후속 기능은 [alert-management-backlog.md](C:/2604_swacan_auto/docs/alert-management-backlog.md)에서 관리

## 5. 현재 결론

지금 MVP 전환의 핵심은:

- editor/view 기능을 더 넓히는 것보다
- backend alert 조건과 lifecycle 구조를 더 유연하고 명확하게 만드는 것이다.

즉, 다음 단계는 구현보다 설계에 조금 더 무게를 두는 것이 적절하다.
