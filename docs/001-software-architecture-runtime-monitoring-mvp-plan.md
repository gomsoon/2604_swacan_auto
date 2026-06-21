# Software Architecture Runtime Monitoring System

## 정식 기획서 초안

문서 버전: Draft 0.1  
작성 기준일: 2026-04-08  
목적: 본 문서는 Software Architecture Runtime Monitoring System의 제품 방향과 MVP 범위를 정리한 정식 기획서 초안이다. 이후 상세 요구사항, 데이터베이스 설계, API 설계, 화면 설계, 개발 일정 수립의 기준 문서로 사용한다.

## 1. 프로젝트 개요

### 1.1 프로젝트명
- Software Architecture Runtime Monitoring System

### 1.2 프로젝트 목적
- 소프트웨어 아키텍처를 시각적으로 모델링하고, 런타임 상태 및 이벤트를 동일한 구조 위에 매핑하여 버그와 성능 문제를 더 빠르게 발견하고 대응할 수 있도록 한다.

### 1.3 제품 정의
- 본 시스템은 단순 드로잉 툴이나 일반 시스템 모니터링 툴이 아니다.
- 본 시스템은 공통 정보 모델(Common Information Model) 기반의 메타모델을 사용하여 소프트웨어 아키텍처를 저장하고, 이를 canvas에서 notation으로 표현하며, agent가 수집한 런타임 데이터를 해당 모델에 연결하는 구조를 가진다.
- 즉, 설계 시점의 architecture model과 운영 시점의 runtime model을 하나의 플랫폼에서 연결하는 것을 목표로 한다.

## 2. 배경 및 문제 인식

### 2.1 배경
- 대규모 또는 장기간 운영되는 소프트웨어는 내부 구조가 복잡하고, 시간이 지날수록 설계 문서와 실제 실행 구조 사이의 괴리가 커진다.
- 기존 NMS 및 로그/메트릭 중심 도구는 서버, 프로세스, 자원 상태를 개별 지표로 제공하지만, 실제 소프트웨어 내부 구조와의 연결성이 부족한 경우가 많다.
- 이로 인해 장애나 성능 문제 발생 시 어느 구성 요소에서 문제가 시작되었는지 빠르게 파악하기 어렵다.

### 2.2 해결하려는 문제
- 아키텍처 문서와 런타임 운영 상태 사이의 단절
- 소프트웨어 내부 구조에 대한 시각적 맥락 부족
- 개별 수치와 이벤트는 존재하지만 구조적 의미를 파악하기 어려운 문제
- 운영자가 장애 전파 경로와 병목 지점을 직관적으로 파악하기 어려운 문제

## 3. 제품 비전

### 3.1 비전
- 소프트웨어 아키텍처를 살아 있는 모델로 다루고, 그 위에 실시간 상태와 이벤트를 중첩하여 설계와 운영을 통합한다.

### 3.2 기대 효과
- 운영자가 구조와 상태를 동시에 이해할 수 있다.
- 버그와 성능 문제의 발생 위치와 영향 범위를 더 빠르게 파악할 수 있다.
- 설계 모델이 실제 운영 데이터와 지속적으로 동기화되어 문서와 현실의 괴리를 줄일 수 있다.
- 향후 자동 검증, 영향도 분석, 이상 감지, 원인 추론 기능으로 확장할 수 있는 기반을 마련한다.

## 4. 핵심 설계 원칙

### 4.1 모델 우선 설계
- canvas의 도형은 단순한 UI 요소가 아니라 메타모델 기반의 의미 객체를 표현하는 시각 요소로 간주한다.
- backend와 DBMS에는 먼저 의미 모델이 저장되어야 하며, notation은 그 모델의 표현 방식으로 관리한다.

### 4.2 Semantic Type과 Notation의 분리
- `Process`, `Thread`, `Physical Server`, `Virtual Machine`, `Communication` 등의 의미 타입은 backend 메타모델로 관리한다.
- 각 의미 타입은 하나 이상의 notation 정의와 연결될 수 있다.
- frontend palette는 backend의 notation registry를 조회하여 동적으로 구성한다.

### 4.3 Model Instance와 Runtime Instance의 분리
- canvas에 그린 객체는 architecture model의 인스턴스이다.
- 실제 Linux OS에서 실행 중인 PID, TID, host 정보는 runtime instance이다.
- 하나의 모델 객체가 하나 이상의 런타임 인스턴스와 매핑될 수 있어야 한다.

### 4.4 편집본과 운영본의 분리
- 사용자가 편집 중인 architecture view 와 운영자가 관제 중인 architecture view 는 동일 row 를 직접 공유해서는 안 된다.
- 편집은 `draft view version` 에 대해 수행하고, 운영 관제는 `published` 또는 `active operational view version` 을 기준으로 수행하는 것이 원칙이다.
- publish 는 draft 를 운영 중인 원본에 덮어쓰는 것이 아니라, 새 snapshot 을 생성하는 방식이어야 한다.
- 운영 화면은 특정 active version 에 고정되어야 하며, 다른 사용자의 편집 중 변경이 운영 화면에 즉시 반영되어서는 안 된다.

### 4.5 Containment 기반 모델링
- 본 시스템은 자유 드로잉 툴이 아니라 containment 규칙을 따르는 모델 편집기이다.
- `Physical Server -> Virtual Machine -> Process -> Thread` 또는 `Physical Server -> Process -> Thread`와 같은 포함 관계를 메타모델에 정의하고 이를 canvas와 backend 검증에 모두 반영한다.
- 잘못된 포함 구조는 저장할 수 없어야 한다.

- A non-invasive `MonitoringAgent` is treated as a separate process-like element inside a `PhysicalServer` or `VirtualMachine`, and observes process or group elements through the `monitors` association.
### 4.6 Group Abstraction
- 실제 runtime은 multi-server, multi-process, multi-thread 구조를 가지므로, canvas의 객체는 개별 실행 인스턴스가 아니라 논리 실행 단위 또는 실행 그룹을 표현할 수 있어야 한다.
- 하나의 `Server`, `Process`, `Thread` 객체가 여러 runtime instance를 대표할 수 있어야 한다.

### 4.7 실시간 처리의 균형
- frontend는 실시간 이벤트 처리를 위해 event stream 기반 통신을 우선 사용하되, 주기적 snapshot 조회를 병행하여 장애 및 데이터 유실 상황을 보완한다.
- backend와 agent는 과도한 고빈도 전송보다 안정적인 상태 수집과 순차 복구에 우선순위를 둔다.

## 5. 주요 사용자

### 5.1 관리자
- 사용자, 권한, 워크스페이스를 관리한다.
- 메타모델, notation, containment rule, 시각화 규칙을 관리한다.
- 현재 접속 세션, backend 로그, 시스템 상태를 관제한다.

### 5.2 설계자
- canvas를 이용해 software architecture를 모델링한다.
- view를 생성, 편집, 복제하고 속성과 바인딩 규칙을 정의한다.

### 5.3 운영자
- monitoring view에서 실시간 상태와 이벤트를 관찰한다.
- 여러 명이 동시에 동일한 view를 열어 관제할 수 있다.

## 6. 시스템 구성

### 6.1 Frontend
- 사용자/관리자 인증 화면
- architecture editor canvas
- monitoring view
- event panel
- 관리자 콘솔

### 6.2 Backend
- 인증/권한 관리
- 메타모델 및 notation registry 관리
- architecture model 저장
- containment 및 validation 처리
- runtime binding 및 집계 처리
- 실시간 이벤트 수신 및 전파
- 관리자용 운영 상태 및 로그 제공

- MonitoringAgent definition, runtime state, and monitor associations
### 6.3 Agent
- Linux OS 상에서 단독 실행되는 비침습형 daemon
- host와 process 수준의 자원 정보를 수집
- backend 미연결 시 로컬 SQLite outbox에 임시 저장
- 연결 복구 시 순차 재전송

- It runs as a separate process inside the monitored execution node and can be represented in the canvas as a `MonitoringAgent` element.
## 7. 메타모델 및 공통 정보 모델 구조

### 7.1 메타모델 방향
- 표준 CIM 전체를 직접 구현하기보다, 본 시스템 목적에 맞춘 경량 메타모델을 설계한다.
- 다만 CIM의 핵심 개념인 타입, 속성, 상속, 관계, 관리 객체 개념은 적극 반영한다.

### 7.2 권장 의미 타입 계층
- `ManagedElement`
- `ExecutionNode`
- `PhysicalServer`
- `VirtualMachine`
- `SoftwareProcess`
- `ExecutionThread`
- `CommunicationLink`

- `MonitoringAgent`
### 7.3 관계 유형
- `contains`
- `communicates_with`
- `depends_on`
- `hosts`
- `runs_on`

- `monitors`
### 7.4 속성 정의 방식
- 각 의미 타입은 property definition을 가진다.
- 속성은 이름, 데이터 타입, 단위, 기본값, 필수 여부, 런타임 수집 가능 여부를 가진다.
- 속성은 모델 속성과 런타임 속성으로 구분한다.

- `MonitoringAgent` can expose properties such as `agent_id`, `agent_version`, `status`, `last_heartbeat_at`, `backend_connection_status`, `queue_depth`, and `last_ack_seq`.
### 7.5 Notation 정의 방식
- notation은 의미 타입에 매핑되는 표현 규칙이다.
- notation은 도형 종류, 기본 크기, 선 스타일, 라벨 위치, 포트 위치, palette 노출 여부, 시각 표현 스키마를 가진다.
- 새로운 notation이 DBMS에 추가되면 frontend palette는 이를 조회하여 자동으로 반영해야 한다.

- `MonitoringAgent` may use a process-like notation, but should still be visually distinguished from a normal `SoftwareProcess` by color, badge, or label treatment.
## 8. Backend 상세 기획

### 8.1 Backend의 역할 정의
- backend는 단순 저장소가 아니라 메타모델 기반 아키텍처 정보 관리 엔진이다.
- 의미 모델, 표기 규칙, architecture model, runtime data를 일관된 방식으로 저장하고 연결한다.

### 8.2 핵심 관리 대상
- semantic type
- notation definition
- property definition
- association definition
- containment rule
- palette group
- architecture model
- runtime binding
- latest runtime state
- runtime event
- user session
- audit log

- monitoring agent definition
- monitoring agent state
### 8.3 Notation Registry
- backend는 notation registry를 제공해야 한다.
- 각 notation은 고유 식별자와 사람이 읽을 수 있는 안정적인 code 값을 함께 가져야 한다.
- 권장 식별자는 내부 PK로 `ULID`, 외부 참조용 코드로 `process.basic`, `thread.pool`, `server.physical`, `server.vm` 같은 형식을 사용한다.
- registry 조회 API를 통해 frontend palette를 동적으로 구성한다.

### 8.4 Containment Rule Engine
- backend는 타입 간 허용 포함 관계를 저장하고 검증해야 한다.
- `PhysicalServer`는 `VirtualMachine`과 `SoftwareProcess`를 포함할 수 있다.
- `VirtualMachine`은 `SoftwareProcess`를 포함할 수 있다.
- `SoftwareProcess`는 `ExecutionThread`를 포함할 수 있다.
- 저장 전 validation 단계에서 containment 위반 여부를 검사해야 한다.
- drag and drop, 복사, 붙여넣기, 이동, 삭제 후에도 containment 규칙이 유지되어야 한다.

- `PhysicalServer` and `VirtualMachine` can contain a `MonitoringAgent`.
- `MonitoringAgent` does not contain `SoftwareProcess` or `ExecutionThread` as children; it connects to them through the `monitors` association.
### 8.5 Group Abstraction과 Aggregation
- backend는 모델 객체 1개가 runtime instance 여러 개를 대표할 수 있도록 지원해야 한다.
- 이를 위해 각 요소에 `instance_mode`를 둔다.
- 권장 값은 `single`, `replicated`, `pool`, `cluster`이다.
- 각 요소는 `expected_min`, `expected_max`, `cardinality_scope`, `aggregation_policy`를 가질 수 있다.
- `cardinality_scope`는 상위 그룹 구성원별 적용인지, 전체 그룹 합산 기준인지를 나타낸다.
- `aggregation_policy`는 상태 집계 방식을 의미한다. 예를 들어 `worst_of_children`, `majority`, `threshold_based` 등을 지원할 수 있다.

### 8.6 Runtime Binding
- backend는 architecture model 요소와 runtime instance의 연결 규칙을 관리한다.
- binding은 `target_id`, selector, OS 정보, agent 식별자, 현재 매칭된 PID/host 목록 등을 포함한다.
- 논리 객체는 사람이 이해하는 안정적인 target 단위로 관리하고, PID/TID는 런타임 식별자로만 사용한다.

- The backend should manage the relationship between a `MonitoringAgent`, its execution node, and its monitored targets, together with the agent runtime state.
### 8.7 실시간 상태 및 이벤트 처리
- latest state와 event log는 분리 관리한다.
- latest state는 monitoring view의 즉시 렌더링에 사용한다.
- event log는 이력 확인, 장애 추적, 복구 검증에 사용한다.
- backend는 WebSocket 또는 유사한 실시간 채널을 통해 frontend로 변경 사항을 전달한다.
- 동시에 snapshot 조회 API를 제공하여 데이터 보정과 상태 동기화에 사용한다.

### 8.8 관리자 콘솔
- 관리자 콘솔은 다음 기능을 포함해야 한다.
- 메타모델 관리
- notation/palette 관리
- containment 규칙 관리
- 사용자/권한 관리
- 현재 접속 사용자 및 세션 현황 조회
- backend 로그 조회
- WebSocket 연결 수, 이벤트 처리량, agent 연결 수, DB 처리 상태 조회
- 감사 로그 조회

### 8.9 자기 관제(Self-Monitoring)
- 본 시스템 backend 역시 동일한 철학에 따라 관제 대상이 될 수 있어야 한다.
- 관리자 콘솔은 backend 구성 요소 상태, 로그, 접속 상태를 자체적으로 시각화하고 확인할 수 있어야 한다.

### 8.10 데이터 저장 전략
- MVP는 SQLite를 사용하되, PostgreSQL 전환을 고려한 도메인 모델을 유지한다.
- 메타모델, notation registry, architecture model, runtime latest state, event, 세션, 로그 메타데이터를 저장한다.
- SQLite는 WAL 모드와 단일 writer 전략을 고려한다.
- 확장 시 PostgreSQL로 이전할 수 있도록 SQL 종속성을 최소화한다.

## 9. Frontend 상세 기획

### 9.1 Editor Canvas
- backend의 notation registry를 기반으로 palette를 생성한다.
- containment 규칙에 따라 생성 가능한 요소와 위치를 제한한다.
- 요소 좌표, 크기, 계층, 라벨, edge routing 정보를 저장한다.
- 완성된 view는 복제하여 새로운 view로 쉽게 생성할 수 있어야 한다.

- The editor canvas should provide `MonitoringAgent` as a separate palette element and allow placement inside a `PhysicalServer` or `VirtualMachine`.
### 9.2 Monitoring View
- architecture model 위에 latest runtime state를 overlay 형태로 표현한다.
- 색상, 텍스트, 배지, 강조 효과는 속성값과 시각화 규칙에 따라 동적으로 변경한다.
- group abstraction이 적용된 요소는 `xN` 형태의 배지 또는 겹침 표기 등으로 표현할 수 있어야 한다.
- monitoring view 하단에는 이벤트 패널을 제공한다.

- The monitoring view should visualize internal agent state such as heartbeat, backend connection status, and queue depth.
### 9.3 실시간 통신 방식
- WebSocket 기반 이벤트 수신을 기본으로 한다.
- 주기적 snapshot 조회를 병행하여 데이터 유실, 연결 장애, frontend/backend 불일치 상태를 복구한다.
- heartbeat 및 stale 상태를 사용자에게 표시할 수 있어야 한다.

### 9.4 관리자 화면
- 일반 사용자 화면과 분리된 관리자 콘솔을 제공한다.
- 메타모델 관리, 접속자 현황, 로그 확인, backend 운영 상태 확인이 가능해야 한다.

## 10. Agent 상세 기획

### 10.1 MVP Agent의 방향
- MVP agent는 Linux OS에서 단독으로 실행되는 비침습형 daemon으로 설계한다.
- 대상 소프트웨어 내부에 삽입하지 않는다.
- `/proc`, `/sys` 등 OS가 제공하는 정보를 활용해 host 및 process 상태를 수집한다.

- The agent itself runs as a separate process, so the canvas should be able to represent it as `MonitoringAgent` and the backend should accept its self-state as runtime data.
### 10.2 수집 범위
- Host: hostname, uptime, cpu, memory, disk, network, agent health
- Process: pid, ppid, name, exe path, cmdline, state, uptime, cpu, memory, thread_count, fd_count, io bytes
- Thread: MVP에서는 개별 thread 상세보다 `thread_count` 중심으로 제한한다.

- Agent Self State: agent pid, start time, heartbeat time, backend connection status, outbox queue depth, last_sent_seq, last_ack_seq
### 10.3 대상 Process 지정 방식
- 관리 대상은 `target_id` 기준으로 정의한다.
- selector는 `command line regex`, `executable path`, `process name`, `pid` 등을 지원한다.
- PID는 변경 가능하므로 주 식별자가 아니라 런타임 매핑 대상이다.

### 10.4 Group 개념 지원
- 하나의 target이 여러 PID를 매칭할 수 있어야 한다.
- agent는 그룹 단위 요약 정보와 개별 인스턴스 정보를 함께 수집할 수 있어야 한다.
- MVP에서는 group summary와 기본 detail 전송 정도로 제한한다.

### 10.5 로컬 임시 저장 및 복구
- backend 연결 장애 시 agent는 SQLite outbox에 데이터를 저장한다.
- 연결 복구 후 순차적으로 전송하고 backend ack를 기준으로 삭제 또는 완료 처리한다.
- 이벤트와 상태 스냅샷에는 순서 보장을 위한 시퀀스 번호가 필요하다.

### 10.6 통신 프로토콜
- MVP에서는 HTTPS 기반 JSON batch POST 방식을 사용한다.
- payload에는 agent_id, boot_id, seq 범위, timestamp, items가 포함된다.
- backend는 ack_seq와 처리 결과를 반환한다.
- 인증은 pre-shared token 기반으로 시작하고, TLS를 필수 적용한다.

## 11. 데이터 모델 관점의 핵심 개념

### 11.1 주요 객체 계층
- 메타모델 객체
- notation 객체
- architecture model 객체
- runtime 객체

### 11.2 공통 식별자 전략
- 내부 식별자: ULID 기반 TEXT
- 외부 코드: 사람이 읽을 수 있는 안정적인 코드
- runtime 측 식별자: agent_id, target_id, pid, tid, host_id, boot_id

### 11.3 좌표 및 레이아웃
- node는 부모 좌표계 기준 위치를 갖는다.
- edge는 source/target anchor와 routing 정보를 가진다.
- 복제 시에는 model 복제와 layout 복제를 구분할 수 있어야 한다.

## 12. MVP 범위

### 12.1 포함 범위
- 사용자 계정 및 권한 관리
- 메타모델 및 notation registry 기본 관리
- containment 기반 architecture canvas 편집
- view 저장 및 복제
- monitoring view 및 event panel
- Linux 비침습형 agent
- host/process 중심 수집
- group abstraction을 고려한 runtime binding
- latest state와 event log 저장
- 관리자 콘솔 기본 기능

- `MonitoringAgent` modeling and status visualization
### 12.2 제한 범위
- 개별 thread 상세 분석
- 침습형 agent 또는 application 내부 SDK
- 고급 시계열 분석
- 자동 root cause 분석
- 복잡한 협업 편집 충돌 해결
- 다중 OS 지원
- VM 내부 상세 수집

## 13. 비기능 요구 고려사항

### 13.1 확장성
- MVP는 SQLite를 사용하지만, PostgreSQL 전환이 가능해야 한다.
- 메타모델과 도메인 구조는 저장소 교체와 무관하게 유지되어야 한다.

### 13.2 안정성
- agent 미전송 데이터는 로컬 outbox에 보관하여 복구 가능해야 한다.
- frontend는 실시간 채널 장애 시 snapshot 재동기화를 수행해야 한다.

### 13.3 일관성
- containment 규칙과 메타모델 규칙은 frontend 편집 제한과 backend 저장 검증에 모두 반영되어야 한다.

### 13.4 보안
- 사용자 인증 및 권한 분리가 필요하다.
- agent와 backend 간 통신은 TLS 기반으로 보호해야 한다.
- 관리자 기능은 일반 사용자 기능과 분리된 권한 체계를 가져야 한다.

### 13.5 관측 가능성
- backend 자체의 로그, 세션, 처리 상태를 관리자 콘솔에서 확인할 수 있어야 한다.

## 14. MVP 결정 사항 요약

### 14.1 메타모델 변경 관리
- 메타모델과 notation은 `draft`, `published`, `deprecated` 상태를 사용한다.
- `published` 상태의 항목은 직접 수정하지 않는다. 변경이 필요하면 새로운 draft 버전을 만든 뒤 publish하는 방식으로 처리한다.
- 각 architecture model과 view는 자신이 참조하는 `metamodel_version_id`를 명시적으로 가져야 한다.
- 파괴적 변경에 대한 자동 마이그레이션은 MVP 범위에 포함하지 않는다.

### 14.2 시각화 규칙 정책
- MVP의 시각화 규칙은 스크립트 실행 방식이 아니라 선언형 rule table 방식으로 구성한다.
- 하나의 규칙은 `대상 타입`, `속성`, `연산자`, `비교값`, `우선순위`, `효과 유형`을 가진다.
- MVP의 효과 유형은 `color`, `badge`, `text override`, `visibility/emphasis` 수준으로 제한한다.
- 규칙 평가는 backend에서 수행하고, frontend는 계산된 결과만 렌더링한다.
- 사용자 정의 코드 실행과 복잡한 중첩 표현식은 MVP 범위에 포함하지 않는다.

### 14.3 다중 사용자 편집 정책
- monitoring view에 대한 동시 접속과 동시 관람은 허용한다.
- 편집은 view 단위 잠금 방식으로 제한한다. 한 시점에는 한 명의 사용자만 view를 편집할 수 있고, 나머지 사용자는 read-only 상태로 접근한다.
- 저장 시에는 revision 검사 또는 optimistic concurrency 검사를 포함해야 한다.
- 잠금은 heartbeat로 유지하며 세션 종료 또는 timeout 시 자동 해제한다.
- 세밀한 단위의 협업 병합 편집은 MVP 범위에 포함하지 않는다.

### 14.4 로그 저장 정책
- 전체 애플리케이션 로그는 파일 또는 stdout/stderr 기반으로 관리한다.
- 데이터베이스에는 관리자 콘솔에 필요한 구조화된 운영 로그와 감사 로그만 저장한다.
- MVP에서 DB에 저장하는 로그는 `warning/error`, 인증 실패, agent 통신 오류, 메타모델 변경, 중요 사용자 행위로 제한한다.
- 관리자 콘솔은 이러한 구조화된 로그를 필터링하여 조회할 수 있어야 한다.
- 전체 로그의 중앙집중 저장 및 고급 분석은 MVP 범위에 포함하지 않는다.

### 14.5 시간 동기화 및 이벤트 순서 정책
- 이벤트 순서는 전역 절대 순서가 아니라 agent별 순서 보장을 기준으로 관리한다.
- 각 이벤트와 스냅샷에는 `agent_id`, `boot_id`, `seq`, `occurred_at`, `received_at`를 포함해야 한다.
- 중복 제거와 순서 판정에는 `(agent_id, boot_id, seq)`를 사용한다.
- 최신 상태는 전체 이벤트 재생이 아니라 snapshot/upsert 방식으로 유지한다.
- 늦게 도착한 이벤트는 event log에는 남기되, 현재 상태 계산은 최신 snapshot을 우선한다.

## 15. MVP 최소 반영 추가 고려사항

### 15.1 메타모델 버전 운영 최소 기준
- 각 view는 생성 시점의 `metamodel_version_id`에 고정된다.
- 새 메타모델 버전 publish 이후에도 기존 view는 계속 사용 가능해야 한다.
- MVP에서는 메타모델 버전 전환을 자동 처리하지 않고, 필요 시 view 복제와 수동 수정으로 이전한다.

### 15.2 시각화 규칙 우선순위 최소 기준
- MVP에서는 `타입 기본 규칙`과 `개별 요소 규칙`까지만 지원한다.
- 우선순위는 `개별 요소 규칙 > 타입 기본 규칙`으로 정의한다.
- 같은 수준의 규칙이 충돌할 경우 `priority` 값이 높은 규칙을 우선 적용한다.
- `view 단위 override`는 MVP 범위에 포함하지 않는다.

### 15.3 Runtime Binding 및 Stale 상태 최소 기준
- `target_id`를 논리 식별자로 사용하고, PID/TID는 변경 가능한 런타임 식별자로 취급한다.
- selector에 맞는 PID 또는 host가 일시적으로 사라진 경우 즉시 삭제하지 않고 `stale` 상태로 전환한다.
- 일정 시간 내 동일 `target_id`에 새 PID 또는 host가 다시 매칭되면 재시작 또는 교체 이벤트로 처리한다.
- group abstraction이 적용된 요소는 `expected_count`와 `actual_count` 차이를 기준으로 상태를 계산한다.

### 15.4 로그 보존 최소 기준
- 구조화된 운영 로그와 감사 로그는 MVP에서 최근 1주일 분량만 유지한다.
- 애플리케이션 로그 파일은 회전 정책을 적용하고, 관리자 화면에는 최근 1주일 범위의 구조화된 로그만 조회 가능하도록 한다.
- 로그 보존 기간 초과 데이터는 자동 정리 대상에 포함한다.
- 외부 로그 시스템 연계는 MVP 범위에 포함하지 않는다.

### 15.5 시간 동기화 최소 기준
- agent host와 backend host의 시간은 NTP로 반드시 동기화한다.
- agent가 전송하는 모든 시간 값은 최소 1/1000초 단위까지 표현해야 한다.
- `occurred_at`, `received_at`, `updated_at` 등 주요 시간 필드는 밀리초 정밀도로 저장하고 처리한다.
- 이벤트 화면 정렬 기준과 상태 계산 기준은 별도로 정의하되, 시간 정밀도 자체는 MVP에서 반드시 확보한다.

## 16. 향후 확장 검토 항목

### 16.1 메타모델 버전 자동 마이그레이션
- 정식 제품 단계에서는 기존 view와 binding을 새로운 메타모델 버전으로 옮기는 자동 또는 반자동 마이그레이션 정책이 필요하다.
- 호환성 검사와 영향도 분석 기능도 후속 단계에서 검토해야 한다.

### 16.2 시각화 규칙 범위 확장
- 향후 버전에서는 type 기본 규칙, model별 규칙, view 단위 override를 포함하는 다층 우선순위 체계를 검토할 수 있다.
- 같은 속성에 여러 규칙이 동시에 영향을 줄 때의 고급 충돌 해소 정책도 추가 설계가 필요하다.

### 16.3 Runtime Binding 고도화
- PID 또는 host 변경을 재시작, 교체, 소실로 더 정교하게 판별하는 정책은 후속 단계에서 고도화할 수 있다.
- 그룹 내 일부 인스턴스 소실, 장기 stale 상태, binding 재학습 정책도 추가 검토가 필요하다.

### 16.4 로그 외부 연계 및 장기 보존
- 로그 보존 기간 확대, PostgreSQL 전환 이후 저장 범위 확대, 외부 로그 시스템 연계는 후속 단계 검토 대상이다.
- 장기 보존, 검색, 분석을 위한 별도 로그 저장소 도입 여부도 함께 판단해야 한다.

### 16.5 시간 동기화 고도화
- host 시계 오차 감시, NTP 상태 점검, agent 간 이벤트 상관 분석 정책은 후속 단계에서 강화할 수 있다.
- 늦게 도착한 이벤트를 UI에서 어떻게 표시하고 보정할지에 대한 세부 UX 정책도 추가 설계가 필요하다.

## 17. Summary


- 본 시스템은 단순 아키텍처 드로잉 도구가 아니라, 메타모델 기반 아키텍처 정보 관리와 런타임 관측을 결합한 플랫폼으로 정의하는 것이 적절하다.
- MVP 범위는 충분히 현실적이며, Linux 비침습형 agent와 SQLite 기반 backend로 시작해도 제품의 핵심 가치를 검증할 수 있다.
- 특히 `containment`, `notation registry`, `logical component vs runtime instances`, `group abstraction`, `관리자 콘솔`은 초기 설계에 반드시 반영해야 할 핵심 개념이다.
- 이후 요구사항 추출 단계에서는 본 문서를 기준으로 `사용자 기능`, `관리 기능`, `실시간 처리`, `데이터 모델`, `운영 및 보안`으로 나누어 상세 요구사항을 도출하는 것이 바람직하다.

## 18. Next Steps

- 본 문서를 기준으로 기능 요구사항을 사용자 스토리 또는 시스템 요구사항 형태로 분해한다.
- SQLite 기준의 개념 ERD와 테이블 초안을 작성한다.
- frontend 화면 목록과 핵심 화면 흐름을 정의한다.
- agent와 backend 간 API 및 payload 초안을 정의한다.
