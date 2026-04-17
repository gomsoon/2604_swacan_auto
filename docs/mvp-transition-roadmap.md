# Software Architecture Runtime Monitoring System

## MVP 전환 로드맵
버전: Draft 0.2  
작성일: 2026-04-15

목적: `minimal-e2e-v1` 기준점을 바탕으로, 현재 구현 상태에서 MVP 단계로 넘어가기 위한 우선순위와 다음 확장 방향을 정리한다.

참고 문서:
- [minimal-e2e-signoff.md](C:/2604_swacan_auto/docs/minimal-e2e-signoff.md)
- [metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/metamodel-notation-db-design-draft.md)
- [architecture-editor-layout-draft.md](C:/2604_swacan_auto/docs/architecture-editor-layout-draft.md)
- [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)
- [terminology-guidelines.md](C:/2604_swacan_auto/docs/terminology-guidelines.md)
- Git tag: `minimal-e2e-v1`

## 1. 현재 기준점 요약

- 실제 Linux agent가 backend와 frontend까지 연결되는 최소 end-to-end 흐름이 검증되었다.
- monitoring, admin, cleanup, stale 파생 상태까지 minimal E2E 기준으로 닫혔다.
- metamodel registry의 기본 테이블, seed 데이터, 조회 API가 이미 구현되었다.
- editor와 persisted view는 `semantic_type_code`, `notation_code`를 함께 저장하도록 전환되었다.
- frontend editor는 metamodel palette를 조회해 node 생성에 활용하고 있다.
- 다음 단계의 핵심은 metamodel/notation이 실제 제품 동작 전반을 더 강하게 지배하도록 만드는 것이다.

## 2. MVP 전환의 핵심 원칙

- MVP에서는 기능 수를 늘리는 것보다 메타모델 기반 구조를 제품 중심축으로 고정하는 것이 우선이다.
- backend는 semantic type, notation, containment, association, property를 일관되게 관리한다.
- frontend는 backend가 제공하는 선언형 render schema를 해석하는 SVG 렌더러 역할을 맡는다.
- 기존 minimal E2E 구조는 유지하되, `하드코딩된 타입 분기`를 점진적으로 `registry 기반 해석`으로 바꾼다.
- agent와 runtime 파이프라인은 이미 닫힌 흐름을 유지하면서 운영성과 효율을 높이는 방향으로 확장한다.
- 운영 안정성을 위해 `draft 편집본` 과 `active operational view` 는 분리하고, publish 기반 snapshot 전환 구조를 채택한다.

## 3. 용어 정리

- runtime 상태를 읽는 운영 화면은 `Monitoring View`로 부른다.
- draft 아키텍처를 편집하는 화면은 `Architecture Editor`로 부른다.
- metamodel draft를 편집하는 화면은 `Metamodel Editor`로 부른다.
- 데이터 모델의 `Logical View`, `View Version`과 화면 이름인 `Monitoring View`는 구분된 개념으로 사용한다.

## 4. MVP 주요 단계

### Phase 1. 메타모델 기반 표현 강화
목표:
- frontend와 persisted view가 metamodel/notation registry를 실질적으로 사용하도록 만든다.

주요 항목:
- editor와 monitor가 `notation_code + render_schema` 기반으로 렌더링
- `semantic_type_code`, `notation_code`를 기준으로 생성/저장/조회 흐름 정리
- metamodel registry가 제공하는 palette/notation 정보를 재사용하는 공통 helper 정리
- 오래된 초안 문서를 현재 코드 기준으로 정비

완료 기준:
- 새 notation이 기존 primitive 범위 안에서는 frontend 수정 없이 palette와 렌더링에 반영된다.
- editor와 monitor가 같은 metamodel registry 정보를 바탕으로 그려진다.

### Phase 2. 관리자용 metamodel 관리 기능
목표:
- 관리자 화면에서 metamodel draft/publish 흐름을 다룰 수 있는 최소 관리 기능을 연다.

주요 항목:
- draft metamodel version 생성 API
- semantic type / notation / containment rule 추가 API
- publish API와 최소 검증
- 관리자 화면에서 published/draft 버전 조회
- view versioning, publish, active operational view 전환 정책 설계

완료 기준:
- 코드 수정 없이 draft metamodel을 만들고 publish할 수 있다.
- published version 기준으로 일반 editor와 monitor가 안정적으로 동작한다.
- draft 편집이 운영 중 monitoring 화면에 직접 영향을 주지 않는다.

### Phase 3. runtime identity 분리와 운영 모델 정리
목표:
- view snapshot과 runtime identity를 분리해, 여러 active view가 동일 runtime 대상을 안정적으로 공유하게 만든다.

주요 항목:
- `monitored_objects` 개념 도입
- `node_bindings` 구조 설계
- latest state / raw event / alert의 monitored object 귀속 모델 정리
- `target_id` compatibility 경로와 점진 migration 전략 수립

완료 기준:
- 동일 runtime 대상이 여러 active view에서 fan-out되어도 저장과 alert 생성은 1회만 일어난다.
- view snapshot과 runtime state 귀속 단위가 분리된다.

### Phase 4. event storm 대응과 운영 고도화
목표:
- 반복 이벤트와 대량 이벤트 상황에서도 운영 화면이 유지되도록 만든다.

주요 항목:
- grouped event 모델과 집계 로직 도입
- low-level event와 grouped event를 분리 저장
- 관리자/모니터링 화면에서 grouped event 우선 표시
- drill-down으로 raw event 상세 조회

완료 기준:
- 동일 원인 반복 이벤트가 요약되어 표시된다.
- 운영자는 필요할 때만 raw event를 세부 조회한다.

추가 검토:
- alert 관리 고도화 시 `alert_instances(current)` 와 `alert_history(archive)` 의 역할 분리를 적용한다.
- 수동 resolve, 자동 resolve, 시간 경과 escalation 정책을 `resolution_source / resolution_reason` 기준으로 기록한다.

### Phase 5. agent 효율화와 식별 전략 강화
목표:
- 실제 운영 Linux 서버에서 agent 부하를 줄이고 multi-process daemon 감시 품질을 높인다.

주요 항목:
- discovery와 collection 분리 강화
- 단일 `/proc` 순회로 다중 target 평가
- multi-process daemon을 `Process Group`으로 모델링
- systemd/cgroup selector 검토 및 단계적 도입
- host resource 수집 범위의 점진 확장

완료 기준:
- 다수의 process 환경에서도 agent 부하가 예측 가능하게 관리된다.
- multi-process daemon이 개별 PID가 아니라 논리 group으로 표현된다.

### Phase 6. 제품성 보강
목표:
- 운영자와 관리자 입장에서 더 자연스럽게 사용할 수 있는 화면으로 다듬는다.

주요 항목:
- editor 계층 순서(layer) 조정 UI
- grouped event drill-down UI
- agent self-state, stale 상태, cleanup 결과의 가시성 보강
- 필요 시 polling 이후의 실시간 갱신 구조 보강

완료 기준:
- 운영자가 주요 상태를 적은 클릭으로 파악할 수 있다.
- editor가 실제 설계 도구로 사용 가능한 수준으로 다듬어진다.

## 5. 현재 시점의 우선순위

Phase 기준의 큰 방향은 여전히 유효하지만, 현재 구현 상태를 반영하면 실제 우선순위는 아래처럼 다시 읽는 것이 더 적절하다.

1. 메타모델 lifecycle hardening
2. Architecture Editor / Monitoring View 연동 안정화
3. 권한 / 감사 로그
4. alert backlog와 운영 고도화는 후속 축으로 유지
5. agent 효율화와 product polish는 그 다음 단계로 확장

이 순서를 추천하는 이유:
- 메타모델 편집 기능 자체는 이미 상당 부분 구현되었으므로, 이제는 `무엇을 더 편집할 수 있는가`보다 `안전하게 publish하고 운영할 수 있는가`가 더 중요하다.
- 이때 lifecycle의 주체는 `Metamodel Version`과 `Semantic Type`으로 보는 것이 더 적절하다.
- `Property Definition`, `Notation Definition`은 독립 lifecycle 객체가 아니라 `Semantic Type` 내부 구성요소로 보는 편이 구조적으로 더 건강하다.
- 같은 metamodel 정의가 `Architecture Editor`와 `Monitoring View`에서 일관되게 소비되어야 제품 중심축이 흔들리지 않는다.
- 메타모델은 시스템 전체에 영향을 주는 정의이므로, edit / publish / activate에 대한 감사 흔적이 점점 중요해진다.
- alert는 이미 1차 운영 가능 수준까지 올라와 있으므로, 지금은 메타모델 주력축을 먼저 다지는 편이 더 효율적이다.

## 6. 현재 바로 이어갈 추천 작업

지금 시점에서 가장 자연스러운 다음 작업은 아래와 같다.

1. 메타모델 lifecycle hardening
- `Metamodel Version`과 `Semantic Type` 중심의 delete / disable / clone / replace 흐름
- semantic type 내부 property / notation 편집 보강
- publish validation 확장
- draft / published / active / deprecated 버전 운영 UX 보강

2. Architecture Editor / Monitoring View 연동 안정화
- metamodel 변경이 editor와 monitor에 실제로 어떻게 반영되는지 경계를 더 명확히 고정
- compatibility fallback 정리
- publish 전 영향도와 실제 사용 경로를 더 강하게 연결
- `Architecture Editor`는 현재 수준을 1차 기준점으로 두고, 남은 확장은 [architecture-editor-backlog.md](C:/2604_swacan_auto/docs/architecture-editor-backlog.md)로 관리
- 다음 주력 구현은 `Monitoring View` 확대에 둔다

3. 권한 / 감사 로그
- draft edit
- publish
- activate
에 대한 사용자, 시각, 변경 흔적 기록

4. alert backlog는 `archive/action log 역할 분리`, `suppression 고도화`, `rule dry-run preview`를 후속 과제로 유지

## 7. 주요 리스크

### 7.1 메타모델 범위 확장 리스크
- metamodel/notation registry를 지나치게 범용적으로 설계하면 MVP 범위를 빠르게 벗어날 수 있다.
- primitive whitelist와 선언형 schema 범위를 엄격히 관리해야 한다.

### 7.2 runtime과 metamodel의 연결 리스크
- metamodel이 너무 앞서가고 persisted view, runtime binding이 뒤따르지 못하면 실제 제품 일관성이 흔들릴 수 있다.
- 따라서 `registry -> view persistence -> renderer` 순서로 단계적으로 묶어야 한다.

### 7.3 agent 효율화 리스크
- systemd/cgroup, pidfd, 고급 Linux 기능은 가치가 크지만 환경 의존성이 있다.
- MVP에서는 구조를 열어두되, 단계적으로 적용해야 한다.

## 8. 요약

- minimal E2E는 완료되었고, 현재는 MVP 구조 확장을 시작하기에 적절한 상태다.
- MVP의 중심축은 `메타모델/notation registry를 실제 제품 구조의 기준으로 만드는 것`이다.
- 지금은 기능을 무작정 늘리기보다, backend와 frontend가 같은 metamodel 정의를 실제로 공유하도록 만드는 단계다.
