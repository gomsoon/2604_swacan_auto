# Software Architecture Runtime Monitoring System

## 백엔드 상세 요구사항

버전: Draft 0.2
작성일: 2026-04-08
목적: 본 문서는 MVP 구현을 위한 백엔드 상세 요구사항을 정의하며, 이후 데이터베이스 설계, API 설계, 테스트 설계의 직접적인 입력으로 사용한다.

## 1. 범위

- 본 문서는 `Python`, `Flask`, `SQLite3`, `pytest` 기반의 MVP 백엔드를 대상으로 한다.
- 범위에는 메타모델 관리, notation registry, architecture model 저장, runtime binding, latest state 관리, event log 관리, agent 수집 API, 관리자 기능이 포함된다.
- 각 요구사항은 `필수`, `선택`, `후속` 중 하나로 구분한다.

## 2. 백엔드의 기본 역할

- [필수] 백엔드는 단순 저장소가 아니라 메타모델 기반 architecture information engine 으로 동작해야 한다.
- [필수] 백엔드는 frontend canvas 와 monitoring view 가 공통으로 사용할 수 있는 모델 데이터를 제공해야 한다.
- [필수] 백엔드는 agent 로부터 runtime 데이터를 수신하고 `latest state` 와 `event log` 를 분리하여 관리해야 한다.
- [필수] 백엔드는 관리자 화면을 위해 메타모델 조회 및 변경, 현재 세션 조회, 로그 조회, agent 상태 조회 기능을 제공해야 한다.

## 3. 핵심 설계 원칙

- [필수] `semantic type` 과 `notation` 은 분리하여 관리해야 한다.
- [필수] `architecture model instance` 와 `runtime instance` 는 분리하여 관리해야 한다.
- [필수] 모든 주요 객체는 내부 고유 식별자와 사람이 읽을 수 있는 코드 값을 함께 가져야 한다.
- [필수] containment 규칙은 프론트엔드 편의 기능이 아니라 백엔드가 강제하는 메타모델 규칙이어야 한다.
- [필수] canvas 의 객체 하나가 runtime 의 여러 인스턴스를 대표할 수 있어야 하며, 이를 위해 논리 객체와 실제 인스턴스를 1:N 으로 매핑할 수 있어야 한다.

## 4. 메타모델 요구사항

### 4.1 메타모델 구성

- [필수] 백엔드는 다음 개념을 메타모델 수준에서 관리해야 한다.
- [필수] `namespace`
- [필수] `semantic type`
- [필수] `property definition`
- [필수] `association definition`
- [필수] `containment rule`
- [필수] `notation definition`
- [필수] `palette group`
- [필수] `metamodel version`

### 4.2 기본 semantic type

- [필수] 최소한 다음 semantic type 을 지원해야 한다.
- [필수] `PhysicalServer`
- [필수] `VirtualMachine`
- [필수] `SoftwareProcess`
- [필수] `ExecutionThread`
- [필수] `MonitoringAgent`
- [필수] `CommunicationLink`
- [선택] `ProcessGroup`
- [선택] `ThreadPool`
- [선택] `ServerGroup`

### 4.3 포함 관계

- [필수] `PhysicalServer` 는 `VirtualMachine`, `SoftwareProcess`, `MonitoringAgent` 를 포함할 수 있어야 한다.
- [필수] `VirtualMachine` 은 `SoftwareProcess`, `MonitoringAgent` 를 포함할 수 있어야 한다.
- [필수] `SoftwareProcess` 는 `ExecutionThread` 를 포함할 수 있어야 한다.
- [필수] `ExecutionThread` 는 하위 containment 를 가질 수 없어야 한다.
- [필수] `MonitoringAgent` 는 containment 의 부모가 되지 않으며, 관측 대상과는 `monitors` association 으로 연결되어야 한다.
- [필수] 백엔드는 저장 시점과 갱신 시점 모두에서 containment 유효성을 검증해야 한다.

### 4.4 메타모델 버전 정책

- [필수] 메타모델은 `draft`, `published`, `deprecated` 상태를 가져야 한다.
- [필수] `published` 상태의 메타모델은 직접 수정할 수 없어야 한다.
- [필수] 기존 view 와 diagram 은 생성 당시의 `metamodel_version_id` 에 고정되어야 한다.
- [필수] MVP 에서는 자동 마이그레이션을 제공하지 않고, 새 버전으로의 이전은 수동 복제 및 수정 방식으로 처리한다.

## 5. Notation Registry 요구사항

### 5.1 notation 정의

- [필수] 각 notation 은 고유한 `notation_id` 와 사람이 읽을 수 있는 `notation_code` 를 가져야 한다.
- [필수] notation 은 특정 `semantic_type_id` 와 연결되어야 한다.
- [필수] notation 은 최소한 다음 정보를 가져야 한다.
- [필수] 도형 종류
- [필수] 기본 크기
- [필수] 선 스타일
- [필수] 배경 스타일
- [필수] 라벨 위치
- [필수] palette 노출 여부
- [필수] 그룹 표현 가능 여부
- [필수] containment 대상에서 사용 가능한지 여부

### 5.2 palette 연동

- [필수] 프론트엔드는 백엔드의 notation registry API 를 조회하여 palette 를 동적으로 구성해야 한다.
- [필수] 새 notation 이 메타모델과 registry 에 추가되면, 프론트엔드는 별도 하드코딩 없이 조회 결과에 따라 palette 에 반영할 수 있어야 한다.
- [필수] 다만 새로운 렌더링 primitive 가 필요한 경우에는 프론트엔드 확장이 필요하며, MVP 에서는 정해진 SVG 표현 범위 안에서만 동적 확장을 허용한다.

## 6. Architecture Model 저장 요구사항

### 6.1 모델과 뷰 분리

- [필수] architecture model 과 architecture view 는 분리하여 저장해야 한다.
- [필수] model 은 논리 구조와 의미 관계를 저장해야 한다.
- [필수] view 는 좌표, 크기, 접힘 상태, 선 제어점 등 시각 배치 정보를 저장해야 한다.
- [필수] 동일한 model 을 기준으로 여러 view 를 가질 수 있어야 한다.

### 6.2 요소 인스턴스 저장

- [필수] 각 model element 는 다음 정보를 가져야 한다.
- [필수] `element_id`
- [필수] `semantic_type_id`
- [필수] `notation_id`
- [필수] `parent_element_id`
- [필수] `display_name`
- [필수] `instance_mode`
- [필수] `cardinality_scope`
- [필수] `expected_min`
- [필수] `expected_max`
- [필수] `status_rule_set_id` 또는 동등한 규칙 참조 정보

### 6.3 그룹 추상화

- [필수] `Server`, `Process`, `Thread` 는 모두 `single`, `replicated`, `pool`, `cluster` 와 유사한 group abstraction 모드를 가질 수 있어야 한다.
- [필수] canvas 의 객체 하나가 여러 runtime instance 를 대표할 수 있어야 한다.
- [필수] `cardinality_scope` 를 통해 개수 의미를 `per_member` 또는 `group_total` 로 구분할 수 있어야 한다.
- [필수] group abstraction 이 적용된 객체는 expected count 와 actual count 를 비교할 수 있어야 한다.

### 6.4 복사 정책

- [필수] view 복사는 동일 model 을 공유하면서 layout 만 새로 생성하는 방식으로 지원해야 한다.
- [필수] diagram 복사는 model 과 view 를 함께 복제하는 방식으로 지원해야 한다.
- [선택] 이후 버전에서는 부분 복사와 템플릿 생성 기능을 검토할 수 있다.

## 7. Runtime Binding 요구사항

### 7.1 논리 객체와 runtime instance 매핑

- [필수] 하나의 model element 는 여러 runtime instance 와 연결될 수 있어야 한다.
- [필수] runtime binding 은 `target_id` 중심으로 관리해야 하며, PID 는 일시적인 runtime 식별자로 취급해야 한다.
- [필수] binding 은 selector 규칙, 최근 매칭 결과, 마지막 확인 시각을 포함해야 한다.
- [필수] selector 는 최소한 `process name`, `executable path`, `command line pattern`, `PID` 기반 매칭을 지원해야 한다.

### 7.2 stale 와 재매칭 정책

- [필수] 기존에 매칭되던 process 가 사라졌다고 해서 즉시 binding 을 삭제해서는 안 된다.
- [필수] 일정 시간 동안 미탐지된 대상은 `stale` 상태로 표시해야 한다.
- [필수] `stale` 상태에서 새 PID 가 동일 selector 로 다시 매칭되면 restart 또는 rematch 로 처리해야 한다.
- [필수] group 객체의 상태는 `expected_count` 와 `actual_count` 의 차이, 그리고 구성 인스턴스들의 상태를 바탕으로 계산해야 한다.

## 8. Latest State 와 Event 관리 요구사항

### 8.1 상태와 이벤트 분리

- [필수] 백엔드는 현재 상태를 저장하는 테이블과 이력 이벤트를 저장하는 테이블을 분리해야 한다.
- [필수] `latest state` 는 조회 최적화를 위해 upsert 중심으로 관리해야 한다.
- [필수] `event log` 는 append 중심으로 저장해야 한다.
- [필수] monitoring 화면은 기본적으로 latest state 를 사용하고, 하단 이벤트 패널은 최근 event log 를 사용해야 한다.

### 8.2 이벤트 종류

- [필수] 최소한 다음 이벤트를 저장해야 한다.
- [필수] process 시작
- [필수] process 종료
- [필수] process 재시작
- [필수] agent heartbeat 이상
- [필수] backend 수신 실패 또는 재시도
- [필수] binding 변경
- [필수] 관리자 메타모델 변경
- [필수] 사용자 주요 편집 작업

### 8.3 로그 보존 정책

- [필수] MVP 에서 구조화된 운영 로그와 중요 이벤트는 최근 1주일만 보존해야 한다.
- [필수] 1주일이 지난 데이터는 정리 작업을 통해 삭제 또는 보관 제외 처리해야 한다.
- [필수] 디버그 수준의 상세 애플리케이션 로그 전체를 SQLite 에 저장해서는 안 된다.
- [필수] 관리자 화면에는 경고 이상 수준의 구조화된 로그와 감사 로그를 우선 제공해야 한다.

### 8.4 반복 이벤트 그룹화와 event storm 완화

- [필수] 백엔드는 다수의 agent 로부터 유입되는 저수준 이벤트를 그대로 저장할 수 있어야 한다.
- [필수] 동시에 동일한 `agent_id`, 동일한 대상 항목, 동일한 이벤트 유형에 대해 반복적으로 발생하는 이벤트는 그룹화된 요약 이벤트로 집계할 수 있어야 한다.
- [필수] 저수준 이벤트 원본과 그룹화된 이벤트 요약은 논리적으로 분리하여 관리해야 한다.
- [필수] 저수준 이벤트 원본은 상세 분석과 추적을 위해 보존하고, 기본 monitoring 화면과 frontend 전송에는 그룹화된 이벤트 요약을 우선 사용해야 한다.
- [필수] 그룹화 조건은 최소한 `agent_id`, `event_type`, `target_id` 또는 동등한 대상 식별자, 심각도, 반복 발생 시간 구간을 기준으로 판단할 수 있어야 한다.
- [필수] 그룹화된 이벤트는 최소한 `first_occurred_at`, `last_occurred_at`, `repeat_count`, `latest_severity`, `group_status` 를 포함해야 한다.
- [필수] frontend 는 기본적으로 그룹화된 이벤트 목록을 조회하고, 사용자가 필요할 때만 해당 그룹에 포함된 저수준 이벤트 원본을 추가 조회할 수 있어야 한다.
- [필수] backend 는 event storm 상황에서도 동일 계열 이벤트를 개별 건으로 계속 push 하지 않고, 그룹화된 이벤트 요약 갱신 형태로 frontend 전송량을 줄일 수 있어야 한다.
- [필수] 이벤트 그룹화는 원본 이벤트의 삭제를 의미하지 않으며, 감사 및 원인 분석을 위한 저수준 이벤트 조회 가능성을 유지해야 한다.

## 9. Agent 수집 API 요구사항

### 9.1 통신 방식

- [필수] MVP 에서 agent 와 backend 의 통신은 `HTTPS + JSON batch POST` 방식으로 구현한다.
- [필수] agent 는 backend 로만 연결을 시작하는 단방향 클라이언트로 동작한다.
- [필수] backend 는 agent 인증을 위해 `agent_id` 와 사전 공유 토큰 또는 동등한 인증 수단을 사용해야 한다.

### 9.2 payload 처리

- [필수] backend 는 batch payload 에 대해 순서 확인, 중복 제거, 일부 수용, 전체 수용을 처리할 수 있어야 한다.
- [필수] 각 item 은 최소한 `agent_id`, `boot_id`, `seq`, `occurred_at`, `sent_at`, `payload type` 을 포함해야 한다.
- [필수] backend 는 `(agent_id, boot_id, seq)` 기준으로 중복 처리 정책을 수행해야 한다.
- [필수] backend 응답은 최소한 `ack_seq`, `accepted_count`, `server_time` 을 포함해야 한다.

### 9.3 MonitoringAgent 모델 연동

- [필수] backend 는 각 agent 를 `MonitoringAgent` semantic type 또는 동등한 내부 모델로 관리해야 한다.
- [필수] `MonitoringAgent` 는 특정 host 또는 virtual machine 내부의 별도 process 로 표현 가능해야 한다.
- [필수] `MonitoringAgent` 는 관측 대상과 `monitors` association 으로 연결될 수 있어야 한다.
- [필수] agent 상태는 최소한 `status`, `last_heartbeat_at`, `queue_depth`, `last_sent_seq`, `last_ack_seq`, `monitored_target_count` 를 포함해야 한다.

## 10. 관리자 기능 요구사항

### 10.1 메타모델 관리

- [필수] 관리자는 semantic type, notation, property definition, association definition, containment rule 을 조회할 수 있어야 한다.
- [필수] 관리자는 draft 상태의 메타모델만 수정할 수 있어야 한다.
- [필수] 관리자는 메타모델 버전을 publish 또는 deprecated 상태로 변경할 수 있어야 한다.

### 10.2 세션 및 사용자 조회

- [필수] 관리자는 현재 접속한 사용자의 목록을 조회할 수 있어야 한다.
- [필수] 관리자는 각 사용자의 현재 모드가 편집인지 관제인지 확인할 수 있어야 한다.
- [필수] 관리자는 사용자가 어떤 view 를 열고 있는지 확인할 수 있어야 한다.
- [필수] 세션 정보에는 마지막 활동 시각이 포함되어야 한다.

### 10.3 운영 로그 조회

- [필수] 관리자는 최근 1주일 범위의 구조화된 로그를 조회할 수 있어야 한다.
- [필수] 로그는 최소한 `timestamp`, `severity`, `component`, `message`, `related object id` 로 필터링 가능해야 한다.
- [필수] 관리자는 agent 연결 문제, 저장 실패, 인증 실패, 메타모델 변경, 주요 사용자 작업 로그를 확인할 수 있어야 한다.

## 11. 데이터 저장 전략 요구사항

### 11.1 SQLite 사용 전략

- [필수] MVP 에서는 `SQLite3` 를 사용한다.
- [필수] SQLite 는 `WAL` 모드로 운영해야 한다.
- [필수] 쓰기 경합을 줄이기 위해 latest state 갱신과 event 저장은 가능한 한 배치 처리 또는 직렬화된 쓰기 흐름을 사용해야 한다.
- [필수] 장기 시계열 저장소로 사용하지 않고, 메타모델, 모델, 최신 상태, 최근 로그 중심으로 사용해야 한다.

### 11.2 시간 정보 정책

- [필수] backend 와 agent 는 모두 NTP 기반으로 시간 동기화를 전제로 해야 한다.
- [필수] 내부에서 저장되고 전송되는 시간 값은 최소 1/1000초 단위의 정밀도를 가져야 한다.
- [필수] 모든 이벤트와 상태 갱신에는 `occurred_at`, `received_at`, `updated_at` 중 필요한 시간을 명시적으로 저장해야 한다.
- [필수] 상태 계산은 event stream 전체 재생이 아니라 latest snapshot 과 sequence 기준으로 수행해야 한다.

## 12. 테스트 요구사항

- [필수] `pytest` 를 사용하여 단위 테스트와 Flask API 테스트를 작성해야 한다.
- [필수] containment 검증, notation registry 조회, metamodel publish 정책, runtime binding, stale 처리, duplicate event 처리에 대한 테스트가 필요하다.
- [필수] agent payload 수신 API 는 정상 수신, 중복 수신, 순서 역전, 인증 실패, 부분 수용에 대한 테스트가 필요하다.
- [필수] 관리자 기능에 대해서는 메타모델 변경 권한, 로그 조회, 세션 조회 테스트가 필요하다.
- [선택] 이후 버전에서는 성능 테스트와 장시간 soak test 를 추가할 수 있다.

## 13. MVP 에서 제외하거나 단순화하는 항목

- [후속] 메타모델 자동 마이그레이션
- [후속] 복잡한 rule scripting engine
- [후속] 자유로운 다중 사용자 동시 편집
- [후속] 장기 시계열 분석 저장소
- [후속] WebSocket 기반의 고급 양방향 agent 제어
- [후속] VirtualMachine 내부 상세 수집과 하이퍼바이저 연동 심화
- [후속] ExecutionThread 의 상세 thread-level 계측

## 14. 다음 설계 단계 입력 항목

- [필수] SQLite ERD 초안에는 metamodel, notation registry, architecture model, runtime binding, latest state, event log, admin log 영역이 포함되어야 한다.
- [필수] API 명세 초안에는 metamodel 조회, notation registry 조회, model CRUD, view 복사, latest state 조회, event 조회, agent batch ingest, admin log 조회가 포함되어야 한다.
- [필수] 프론트엔드 상세 요구사항에서는 containment 기반 SVG canvas interaction, group abstraction 표현, MonitoringAgent 표시, monitoring view 갱신 방식이 반영되어야 한다.
- [필수] agent 상세 요구사항에서는 selector, outbox, ack, batch payload, self-state 수집 항목이 반영되어야 한다.

## 15. 요약

- 본 백엔드는 단순한 CRUD 서버가 아니라 메타모델 기반 architecture monitoring backend 로 설계해야 한다.
- 메타모델, notation, architecture model, runtime instance, latest state, event log 는 명확히 분리되어야 한다.
- containment 규칙, group abstraction, MonitoringAgent, stale 정책, 1주 로그 보존, NTP 기반 밀리초 시간 정책, event storm 완화를 위한 반복 이벤트 그룹화는 MVP 에서 반드시 반영되어야 한다.
- 본 문서는 이후 ERD, API, 테스트 설계의 기준 문서로 사용한다.
