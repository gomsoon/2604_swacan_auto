# Software Architecture Runtime Monitoring System

## Runtime Identity / Node Binding 설계 초안
버전: Draft 0.1  
작성일: 2026-04-16

목적: 여러 active view가 동일한 server, process, thread를 동시에 표현할 수 있는 구조에서, runtime state/event/alert를 어디에 귀속시키고 어떻게 fan-out할지 설계 방향을 정리한다.

참고 문서:
- [280-terminology-guidelines.md](C:/2604_swacan_auto/docs/280-terminology-guidelines.md)
- [210-view-versioning-erd-draft.md](C:/2604_swacan_auto/docs/210-view-versioning-erd-draft.md)
- [220-view-versioning-sqlite-draft.md](C:/2604_swacan_auto/docs/220-view-versioning-sqlite-draft.md)
- [160-metamodel-notation-db-design-draft.md](C:/2604_swacan_auto/docs/160-metamodel-notation-db-design-draft.md)
- [150-mvp-transition-roadmap.md](C:/2604_swacan_auto/docs/150-mvp-transition-roadmap.md)

## 1. 문제 정의

여러 active view가 동시에 존재할 수 있고, 서로 다른 view가 동일한 server, process, thread를 각각의 node로 표현할 수 있다.

이때 다음 문제가 생긴다.
- 같은 runtime 대상을 여러 `view_version_nodes`가 중복 표현할 수 있다.
- alert나 event가 발생했을 때, 이를 node row마다 별도로 생성하면 중복 저장과 중복 처리 문제가 생긴다.
- 현재처럼 `target_id`가 view node 안에만 있으면, 같은 대상을 view마다 다르게 적어버릴 위험이 있다.

따라서 view snapshot과 runtime identity는 분리돼야 한다.

## 2. 용어 적용

- `Monitoring View`는 `active view version`을 기준으로 runtime 상태를 조회하는 운영 화면이다.
- `Architecture Editor`는 `draft view version`을 대상으로 노드와 레이아웃을 편집하는 화면이다.
- `Monitored Object`는 runtime state, event, alert의 귀속 단위이고, `Node Binding`은 특정 view node와 monitored object를 연결하는 관계다.

## 3. 핵심 원칙

- view node는 화면 표현 책임을 가진다.
- runtime state, raw event, alert는 별도의 monitored object에 귀속된다.
- 하나의 runtime 문제는 한 번 생성되고, 여러 active view에서 fan-out되어 보여진다.
- `target_id`는 당분간 compatibility binding key로 유지할 수 있지만, 장기 주체는 monitored object여야 한다.

## 4. 권장 개념 모델

### 4.1 View Snapshot
- `view_version_nodes`
- `view_version_edges`
- 역할: 위치, 크기, 레이어, containment, notation, label 등 화면 표현

### 4.2 Monitored Object
- 실제 관측 대상의 전역 논리 ID
- 예:
  - `host.chat-01`
  - `proc.chat-main`
  - `agent.chat-01.local`
  - `procgroup.apache-workers`

### 4.3 Node Binding
- 어떤 `view_version_node`가 어떤 monitored object를 바라보는지 연결
- 같은 monitored object를 여러 node가 참조할 수 있다

### 4.4 Runtime State / Event / Alert
- `latest_states`
- `raw_events`
- `alert_instances`
- 귀속 단위: `monitored_object_id`

## 5. fan-out 방식

### 5.1 생성
- agent가 backend로 정보를 보낸다
- backend는 selector/binding 결과를 기준으로 monitored object를 찾는다
- `latest_states`, `raw_events`, `alert_instances`를 monitored object 기준으로 갱신한다

### 5.2 조회
- monitoring 화면은 현재 active view version을 읽는다
- active view의 node들이 참조하는 monitored object 집합을 구한다
- 각 node는 연결된 monitored object의 latest state / event / alert를 overlay한다

즉:
- 저장: 1회
- 표시: 여러 active view에 fan-out

## 6. 권장 테이블

### 6.1 monitored_objects
- `id INTEGER PRIMARY KEY`
- `object_key TEXT NOT NULL UNIQUE`
- `object_type TEXT NOT NULL`
- `display_name TEXT NOT NULL`
- `runtime_binding_key TEXT`
- `metadata_json TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 6.2 node_bindings
- `id INTEGER PRIMARY KEY`
- `view_version_node_id INTEGER NOT NULL`
- `monitored_object_id INTEGER NOT NULL`
- `binding_role TEXT NOT NULL DEFAULT 'primary'`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

### 6.3 alert_instances
- `id INTEGER PRIMARY KEY`
- `monitored_object_id INTEGER NOT NULL`
- `alert_code TEXT NOT NULL`
- `severity TEXT NOT NULL`
- `status TEXT NOT NULL`
- `first_occurred_at TEXT NOT NULL`
- `last_occurred_at TEXT NOT NULL`
- `repeat_count INTEGER NOT NULL DEFAULT 1`
- `latest_message TEXT`
- `metadata_json TEXT`

## 7. current target_id 구조 평가

현재 구조는 완전히 잘못된 것은 아니다.

장점:
- `target_id`가 전역적으로 일관되게 관리되면, latest state를 여러 node row마다 중복 저장할 필요가 없다
- 하나의 `target_id`에 대한 최신 상태를 여러 active view가 함께 읽을 수 있다

한계:
- `target_id`가 view snapshot row 안에 있어서 runtime identity 책임을 과도하게 진다
- 같은 process를 view마다 다른 `target_id`로 넣으면 같은 대상을 다르게 취급할 수 있다
- alert/event/latest state의 진짜 귀속 대상이 node인지 runtime 대상인지 의미가 흔들린다

## 8. 이행 전략

### 8.1 1단계
- 기존 `target_id` 유지
- `view_version_nodes.target_id`를 compatibility binding key로 사용

### 8.2 2단계
- `monitored_objects` 추가
- `node_bindings` 추가
- 새 draft/active view에서 주요 node를 monitored object와 연결 가능하게 준비

### 8.3 3단계
- `latest_states`, `raw_events`, `alert_instances`에 `monitored_object_id` 추가
- 새 경로는 monitored object 기준 저장
- 기존 `target_id` 기반 조회는 fallback으로 유지

### 8.4 4단계
- frontend monitoring은 active view node -> node_binding -> monitored_object -> latest state/event/alert 순서로 조회
- `target_id`는 점진적으로 축소

## 9. alert/event 관점의 권장 모델

- alert 생성 단위: monitored object
- alert 화면 fan-out 단위: active view node
- grouped event 집계 단위도 monitored object 중심이 더 적절하다

예시:
- Apache worker group 과부하 발생
- `alert_instances`에는 1건 생성
- 이를 참조하는 여러 view에서는 모두 경고 배지 표시
- 운영자는 어느 view에서 보더라도 같은 alert를 본다

## 10. 요약

- view snapshot과 runtime identity는 분리하는 것이 맞다.
- `view_version_nodes`는 화면 표현이다.
- `monitored_objects`는 실제 관측 대상이다.
- `node_bindings`는 둘을 연결한다.
- alert/event/latest state는 monitored object에 귀속되고, 여러 active view로 fan-out되어 보여져야 한다.
