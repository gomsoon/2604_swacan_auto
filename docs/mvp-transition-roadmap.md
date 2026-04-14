# Software Architecture Runtime Monitoring System

## MVP 전환 로드맵
버전: Draft 0.1  
작성일: 2026-04-14

목적: `minimal-e2e-v1` 완료 기준점을 바탕으로, 다음 단계인 MVP 구현의 목표, 우선순위, 단계별 범위, 리스크를 정리한다.

참고 기준점:

- [minimal-e2e-signoff.md](C:/2604_swacan_auto/docs/minimal-e2e-signoff.md)
- Git tag: `minimal-e2e-v1`

## 1. 전환 원칙

- Minimal E2E에서 검증한 `agent -> backend -> DB -> frontend` 기본 흐름은 유지한다.
- MVP에서는 “전체 흐름이 되는가”보다 “제품으로 운영 가능한가”를 우선한다.
- 기능을 넓히기 전에 구조적 안정성, 운영성, 데이터 모델 일관성을 먼저 강화한다.
- 여전히 점진적 개발 방식을 유지하며, 각 단계마다 자동화 테스트와 회귀 검증을 함께 가져간다.

## 2. 현재 기준점 요약

- 실제 Linux agent가 backend와 frontend까지 연결되는 흐름이 검증되었다.
- monitoring UI와 admin UI에서 실제 데이터 확인이 가능하다.
- worker loop, duplicate/idempotency, batch rollback, stale 파생 상태, retention cleanup 1차가 반영되어 있다.
- 전체 회귀 테스트와 Playwright 브라우저 테스트가 안정적으로 통과한다.
- branch coverage 기준이 확보되어 있다.

## 3. MVP에서 반드시 강화할 축

### 3.1 메타모델과 notation

- seed 기반 최소 모델에서 실제 `metamodel/notation registry` 기반 구조로 전환
- semantic type, property definition, association, containment rule의 관리 체계 정리
- 관리자 화면에서 메타모델을 조회하고 점진적으로 관리할 수 있는 기반 강화

### 3.2 runtime 운영성

- stale event의 명시적 생성
- cleanup 실행 결과의 운영 흐름 연결
- grouped event 기반 event storm 완화
- latest state와 raw event의 운영 활용성 강화

### 3.3 agent 실전성

- multi-process daemon을 `Process Group` 관점으로 더 자연스럽게 처리
- selector를 systemd/cgroup 중심으로 확장할 수 있는 구조 준비
- host resource 수집 범위를 disk/network 쪽으로 점진 확장
- 실제 Linux 운영 runbook과 설정/배포 방식을 정리

### 3.4 frontend 제품성

- canvas/editor 사용성 보강
- monitoring view의 실시간성 고도화
- admin 화면의 운영 분석 기능 강화
- grouped event, stale state, debug 흐름의 가시성 강화

## 4. 권장 구현 순서

### Phase 1. 운영 안정화

목표:

- minimal E2E를 “운영 가능한 MVP 기반”으로 안정화한다.

주요 항목:

- stale 감지 결과를 별도 raw event로 생성
- cleanup 결과를 worker 주기 작업과 관리자 화면에 더 자연스럽게 연결
- debug payload와 운영 로그의 관리자 조회 흐름 정리
- sign-off 기준에 맞는 최종 증적 정리

완료 기준:

- stale/cleanup 관련 운영자가 추적해야 할 최소 정보가 admin 화면에서 확인 가능하다.
- 관련 자동화 테스트가 추가되고 전체 회귀가 안정적으로 유지된다.

### Phase 2. 메타모델/notation registry 고도화

목표:

- 현재 seed 기반 구조를 실제 메타모델 관리 구조로 확장한다.

주요 항목:

- semantic type / notation / containment rule / property definition 테이블 구체화
- notation registry API 고도화
- palette를 registry 기반으로 더 명확히 연결
- metamodel version 관리의 draft/published 흐름 도입

완료 기준:

- 새로운 notation이나 semantic type이 backend 데이터 기준으로 관리된다.
- frontend가 registry 조회를 통해 palette를 구성할 수 있다.

### Phase 3. event storm 대응과 관제 강화

목표:

- 운영 중 반복 이벤트와 대량 이벤트 상황을 제품 수준으로 다룬다.

주요 항목:

- raw event와 grouped event 분리 저장
- 동일 agent/동일 대상/동일 이벤트 유형 반복 시 그룹화
- frontend event panel은 grouped event 중심으로 표시
- low-level event drill-down 조회 기능 제공

완료 기준:

- event storm 상황에서도 frontend 전송량과 화면 복잡도가 통제된다.
- 운영자는 요약과 상세를 분리해서 볼 수 있다.

### Phase 4. agent 확장과 효율화

목표:

- 실제 운영 Linux 서버에서 agent 비용과 정확도를 더 개선한다.

주요 항목:

- systemd/cgroup 기반 selector 검토 및 도입
- multi-process daemon grouping 고도화
- host resource 확장 수집: disk, network
- retry/backoff, outbox 압력, cleanup 정책 세분화
- agent 자동 업데이트 설계 착수

완료 기준:

- 대규모 process 환경에서 agent 부담을 더 낮출 수 있다.
- multi-process daemon monitoring이 더 제품답게 동작한다.

### Phase 5. frontend 협업성과 제품성 보강

목표:

- editor와 monitoring을 실제 사용자가 더 편하게 쓰도록 다듬는다.

주요 항목:

- edit lock과 충돌 처리 UX 보강
- grouped event drill-down UI
- stale/agent/self-state 요약 보강
- monitoring의 SSE + polling hybrid 흐름 고도화
- 관리자 화면 검색/필터 보강

완료 기준:

- 사용자와 운영자 입장에서 실제 사용성이 눈에 띄게 좋아진다.

## 5. MVP 1차 우선순위

가장 먼저 추천하는 순서는 다음과 같다.

1. `Phase 1 운영 안정화`
2. `Phase 2 메타모델/notation registry 고도화`
3. `Phase 3 event storm 대응`
4. `Phase 4 agent 효율화`
5. `Phase 5 frontend 제품성 보강`

이 순서를 추천하는 이유:

- 지금 가장 큰 가치는 “확장”보다 “안정된 기반”을 먼저 만드는 데 있다.
- 메타모델과 event 구조를 먼저 고정해야 이후 frontend/agent 확장이 흔들리지 않는다.
- agent 고도화는 중요하지만, backend 데이터 모델과 운영 정책이 먼저 단단해져야 효과가 크다.

## 6. 단계별 산출물 권장안

각 phase마다 다음 산출물을 남기는 것을 권장한다.

- 요구사항 업데이트 문서
- DB/ERD 변경 초안
- API 변경 초안
- 자동화 테스트 추가
- 회귀 테스트 결과
- 필요 시 운영 runbook 업데이트

## 7. 주요 리스크

### 7.1 메타모델 범위 확장 리스크

- 메타모델과 notation registry를 너무 범용적으로 설계하면 MVP 속도가 급격히 느려질 수 있다.
- 따라서 처음에는 실제로 쓰는 semantic type 중심으로 좁게 가는 것이 좋다.

### 7.2 event storm 대응 리스크

- grouped event를 너무 늦게 넣으면 운영 화면이 noisy 해지고 backend/frontend 부담이 커진다.
- 반대로 너무 이르게 복잡한 룰을 넣으면 데이터 모델이 무거워질 수 있다.

### 7.3 agent 고도화 리스크

- systemd/cgroup, pidfd, 더 고급한 Linux 기능은 가치가 크지만 환경 의존성이 생긴다.
- 따라서 실제 운영 서버 특성을 보면서 단계적으로 적용해야 한다.

### 7.4 frontend 사용성 리스크

- canvas 기능을 너무 빨리 크게 넓히면 다시 editor 자체가 중심이 되어 MVP 초점이 흐려질 수 있다.
- backend 계약과 관제 가치 중심으로 우선순위를 유지해야 한다.

## 8. 바로 다음 추천 작업

지금 시점에서 가장 자연스러운 다음 작업은 아래 셋 중 하나다.

1. `Phase 1`을 더 구체화한 운영 안정화 백로그 작성
2. 메타모델/notation registry용 DB 설계 초안 작성
3. grouped event/event storm 대응 요구사항 상세화

제 추천은 `2번 메타모델/notation registry용 DB 설계 초안`부터 들어가는 것이다.  
이 축이 정리되면 backend, frontend, admin 화면, 이후 agent 확장까지 모두 같은 중심축 위에 올라갈 수 있다.

## 9. 요약

- minimal E2E는 성공적으로 완료되었고, 이제는 MVP 전환이 가능한 상태다.
- MVP의 핵심은 기능을 무작정 넓히는 것이 아니라, 메타모델 기반 구조와 운영성을 제품 수준으로 끌어올리는 것이다.
- 다음 단계는 운영 안정화와 메타모델/notation registry 고도화를 중심으로 시작하는 것이 가장 적절하다.
