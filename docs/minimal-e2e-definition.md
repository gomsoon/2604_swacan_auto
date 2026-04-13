# Software Architecture Runtime Monitoring System

## 최소 E2E 버전 정의

버전: Draft 0.1
작성일: 2026-04-10
목적: 본 문서는 점진적 개발 방식에 맞춰 MVP 이전 단계의 최소 end-to-end 버전을 정의하고, 이 단계에서 반드시 통과해야 하는 수용 기준과 필수 테스트 게이트를 정리한다.

## 1. 문서의 목적

- 본 문서는 전체 MVP 구현에 앞서 가장 작은 단위의 실제 동작 경로를 고정하기 위한 기준 문서다.
- 최소 E2E 버전은 `agent -> backend -> DB -> frontend` 흐름이 실제로 동작하는지 검증하는 것을 목표로 한다.
- 본 문서는 이후 기능 추가 전에 구조적 refactoring 이 필요한지 판단하는 기준으로도 사용한다.
- 본 문서는 `backend 상세 요구사항`, `agent 상세 요구사항`, `frontend 상세 요구사항`의 공통 실행 기준이다.

## 2. 기본 원칙

- [필수] 최소 E2E 버전은 기능 수를 최소화하되, 핵심 데이터 흐름은 실제 운영 구조와 최대한 비슷해야 한다.
- [필수] 이 단계에서는 "모든 기능을 조금씩" 넣기보다 "가장 중요한 흐름을 끝까지" 연결하는 것을 우선한다.
- [필수] 기능 추가보다 먼저 자동화 가능한 회귀 테스트 기반을 확보해야 한다.
- [필수] 구조적 문제가 확인되면 새 기능을 추가하기 전에 refactoring 을 먼저 수행한다.
- [필수] 상세 요구사항 문서가 도메인 순서로 정리되어 있더라도, 실제 구현 순서는 별도 구현 백로그 문서를 기준으로 따라야 한다.
- [필수] 최소 E2E 자동화 테스트는 backend/agent 는 `pytest`, 브라우저 흐름은 `Playwright` 를 기준으로 한다.
- [필수] backend 와 agent 자동화 테스트에는 branch coverage 측정과 report 생성이 포함되어야 한다.
- [필수] agent 테스트는 `단위 테스트`, `backend 계약 테스트`, `Linux 실제 통합 테스트`의 세 층으로 나누어 관리해야 한다.
- [필수] 최소 E2E 버전이 안정적으로 통과되기 전에는 고급 기능, 고급 UI, 확장성 기능을 추가하지 않는다.

## 3. 최소 E2E 버전의 목표

- [필수] 사용자가 로그인할 수 있어야 한다.
- [필수] 사용자가 editor 에서 최소 구조의 architecture view 를 만들고 저장할 수 있어야 한다.
- [필수] Linux agent 가 실제 process 하나를 감시하고 backend 로 데이터를 전송할 수 있어야 한다.
- [필수] backend 가 해당 데이터를 latest state 로 반영하고 event 를 기록할 수 있어야 한다.
- [필수] monitoring view 에서 process 와 MonitoringAgent 상태 변화를 시각적으로 확인할 수 있어야 한다.
- [필수] target process 상태 변화가 event panel 에 반영되어야 한다.
- [필수] backend debug mode 에서 agent 통신 payload 를 저장할 수 있어야 한다.

## 4. 최소 E2E 범위

### 4.1 포함 범위

- [필수] 인증: seed 된 관리자 계정 또는 단일 테스트 계정으로 로그인 가능해야 한다.
- [필수] 메타모델: 최소한 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink` 정의가 seed 되어 있어야 한다.
- [필수] notation: 위 semantic type 에 대응하는 최소 SVG 표현 정의가 존재해야 한다.
- [필수] editor: `PhysicalServer` 내부에 `SoftwareProcess` 와 `MonitoringAgent` 를 배치하고, 컴포넌트 간 단순 `CommunicationLink` line 을 생성하여 저장할 수 있어야 한다.
- [필수] view 저장: node layout 좌표, edge 연결 정보, 최소 속성이 DB 에 저장되어야 한다.
- [필수] backend ingest: agent payload 를 수신하고 durable write 후 처리할 수 있어야 한다.
- [필수] agent 는 최소한 host resource 정보로 `stat`, `loadavg`, `meminfo` 기반 snapshot 을 생성할 수 있어야 한다.
- [필수] agent 는 outbox 에 item 단위로 저장된 heartbeat, host snapshot, process snapshot 을 여러 개 묶어 batch 로 backend ingest 에 전송할 수 있어야 한다.
- [필수] latest state: process up/down 과 agent heartbeat 상태가 latest state 에 반영되어야 한다.
- [필수] event 기록: 최소한 `process started`, `process stopped`, `agent heartbeat lost` 수준의 event 를 기록할 수 있어야 한다.
- [필수] monitoring view: polling 기반으로 상태 변화를 표시할 수 있어야 한다.
- [필수] event panel: 최근 event 몇 건을 보여줄 수 있어야 한다.
- [필수] debug mode: backend 가 agent 요청/응답 payload 를 debug 저장 영역에 기록할 수 있어야 한다.

### 4.2 제외 범위

- [후속] 동적 메타모델 편집 UI
- [후속] VirtualMachine 표현과 관련 runtime 수집
- [후속] ExecutionThread 상세 표현 및 thread-level 계측
- [후속] group abstraction 고도화
- [후속] grouped event 고도화와 event storm 완화 고급 정책
- [후속] `/proc/diskstats`, `/proc/net/dev` 기반 host 상세 resource 수집
- [후속] SSE 기반 실시간 갱신
- [후속] 관리자 운영 콘솔 전체
- [후속] debug payload 조회 UI
- [후속] view 복사, diagram 복사
- [후속] 다중 사용자 편집 잠금
- [후속] backend 와 연계된 agent 자동 업데이트

## 5. 최소 E2E 시스템 구성

### 5.1 Backend

- [필수] 최소 E2E 단계에서는 worker 가 `ingest_inbox` 를 polling 하며 pending payload 를 처리하는 단순 loop 구조를 사용해도 된다.
- [필수] MVP 최소 E2E 구조에서도 `web` 과 `worker` 의 책임 경계는 유지해야 한다.
- [필수] `web` 은 로그인, view 저장, monitoring 조회, agent ingest 를 담당한다.
- [필수] `worker` 는 latest state 갱신과 단순 event 생성 정도의 최소 후처리를 담당한다.
- [필수] queue 역할은 SQLite 기반 `inbox/work queue` 로 처리한다.

### 5.2 Agent

- [필수] agent 는 단일 Python 프로세스 구조를 사용한다.
- [필수] agent 는 Linux 에서 단독 실행되며, target process 하나를 selector 로 감시한다.
- [필수] agent 는 outbox 기반 durable transport 를 유지한다.
- [필수] agent 최소 구현 순서는 `설정/runner -> selector -> snapshot collector -> SQLite outbox -> transport -> backend 계약 테스트 -> Linux 실제 통합 테스트` 순서를 기본으로 한다.
- [필수] agent 단위 테스트는 backend 나 frontend 개발과 분리해서 빠르게 반복 가능해야 한다.
- [필수] agent 와 backend 사이의 payload 형식, `ack_seq`, `target_id`, `payload_type` 은 별도의 계약 테스트로 지속 검증되어야 한다.
- [필수] minimal E2E 단계의 host collector 는 `/proc/stat`, `/proc/loadavg`, `/proc/meminfo` 범위까지만 구현하고, disk/network 상세는 후속으로 둔다.

### 5.3 Frontend

- [필수] frontend 는 login 화면, editor 화면, monitoring 화면의 최소 세 화면을 제공해야 한다.
- [필수] editor 는 inline SVG 기반으로 최소한의 node 배치, edge 생성, 저장이 가능해야 한다.
- [필수] monitoring 화면은 polling 기반 상태 갱신만 우선 지원한다.

## 6. 최소 E2E 시나리오

1. 사용자가 로그인한다.
2. 사용자가 새 architecture view 를 생성한다.
3. editor 에서 `PhysicalServer` 하나, 그 내부에 `SoftwareProcess` 하나와 `MonitoringAgent` 하나를 배치한다.
4. 사용자는 `SoftwareProcess` 와 `MonitoringAgent` 또는 필요한 두 node 사이에 단순 `CommunicationLink` line 을 추가한다.
5. 사용자가 해당 view 를 저장한다.
6. Linux host 에서 agent 를 실행하고, 지정된 target process 하나를 감시하도록 설정한다.
7. agent 가 heartbeat 와 process snapshot 을 backend 로 전송한다.
8. backend 는 payload 를 저장하고 latest state 를 갱신한다.
9. monitoring 화면에서 process 상태와 agent 상태가 표시되고, 저장된 communication line 이 함께 렌더링된다.
10. target process 를 중지하거나 재시작한다.
11. agent 가 상태 변화를 감지해 event 를 전송한다.
12. backend 가 event 를 저장하고 monitoring 화면 및 event panel 에 반영한다.
13. backend debug mode 가 활성화되어 있다면, 해당 통신 payload 가 저장된다.

## 7. 최소 E2E 수용 기준

### 7.1 기능 수용 기준

- [필수] 로그인 성공 후 사용자가 editor 화면으로 진입할 수 있어야 한다.
- [필수] 사용자는 editor 에서 최소 구성 요소를 배치하고 저장할 수 있어야 한다.
- [필수] 저장된 view 를 monitoring 모드로 열 수 있어야 한다.
- [필수] agent 가 실제 Linux process 하나를 식별하고 backend 로 snapshot 을 보낼 수 있어야 한다.
- [필수] backend 는 해당 snapshot 을 latest state 로 반영해야 한다.
- [필수] monitoring 화면은 process 와 MonitoringAgent 상태를 각각 구분해서 보여줄 수 있어야 한다.
- [필수] process 종료 또는 재시작 시 event 가 최소 1건 이상 생성되어 화면에서 확인 가능해야 한다.
- [필수] backend debug mode 활성화 시 agent ingest payload 가 저장되어야 한다.

### 7.2 구조 수용 기준

- [필수] backend ingest 요청 경로에서 무거운 후처리를 직접 수행하지 않고 durable write 후 worker 처리 구조를 유지해야 한다.
- [필수] agent 는 SQLite outbox 없이 직접 전송만 하는 구조로 구현되어서는 안 된다.
- [필수] frontend 는 editor 와 monitoring view 를 분리하되, 동일한 view layout 을 공유해야 한다.
- [필수] 메타모델 seed 와 notation seed 는 코드에 하드코딩되더라도 별도 seed 구조로 분리되어야 한다.

### 7.3 품질 수용 기준

- [필수] 최소 E2E 흐름은 수동 실행뿐 아니라 자동 테스트 일부로 재현 가능해야 한다.
- [필수] 치명적 예외나 프로세스 크래시 없이 기본 시나리오를 3회 이상 반복 수행할 수 있어야 한다.
- [필수] debug mode 비활성화 상태에서는 debug payload 가 저장되지 않아야 한다.

## 8. 필수 테스트 게이트

### 8.1 자동화 테스트

- [필수] backend 와 agent 자동화 테스트는 `pytest` 기반으로 작성해야 한다.
- [필수] 로그인과 주요 브라우저 흐름 자동화 테스트는 `Playwright` 기반으로 작성해야 한다.
- [필수] backend 와 agent 자동화 테스트 실행 시 branch coverage report 가 생성되어야 한다.
- [필수] agent 자동화 테스트는 `단위 테스트`와 `backend 계약 테스트`로 구분해서 실행 가능해야 한다.
- [필수] 인증 테스트: 로그인 성공/실패
- [필수] model 저장 테스트: 최소 view 생성 및 저장
- [필수] agent ingest API 테스트: 정상 payload 수신
- [필수] latest state 갱신 테스트: process snapshot 반영
- [필수] event 생성 테스트: process stopped 또는 restarted event 생성
- [필수] debug mode 테스트: payload 저장 on/off 동작
- [필수] outbox 테스트: backend 미연결 시 로컬 저장, 복구 후 재전송
- [필수] agent 단위 테스트에는 설정 로딩, selector, snapshot 생성, payload 직렬화, sequence 증가, outbox enqueue/ack 정리가 포함되어야 한다.
- [필수] backend 계약 테스트에는 agent payload 를 backend ingest API 로 보내고 `ack_seq`, latest state 반영, raw event 반영을 함께 검증하는 경로가 포함되어야 한다.

### 8.2 수동 통합 테스트

- [필수] Linux 에서 실제 target process 를 실행한 상태로 agent 를 붙여 monitoring 화면까지 확인해야 한다.
- [필수] target process 종료 시 화면 상태 색상과 event panel 이 함께 변하는지 확인해야 한다.
- [필수] agent 중지 시 MonitoringAgent 상태가 비정상으로 보이는지 확인해야 한다.
- [필수] backend debug mode 활성화 후 payload 저장 여부를 확인해야 한다.
- [필수] Linux 실제 통합 테스트는 dummy target process 를 이용해 `발견 -> 수집 -> 전송 -> 종료 감지 -> 재전송/복구` 흐름을 별도 증적으로 남겨야 한다.

### 8.3 회귀 테스트 최소 세트

- [필수] 로그인 -> view 열기 -> monitoring 조회 경로
- [필수] agent ingest -> latest state 갱신 경로
- [필수] process down -> event 생성 경로
- [필수] outbox 복구 경로
- [필수] debug payload 저장 on/off 경로

## 9. 다음 단계로 넘어가기 위한 조건

- [필수] 7절 수용 기준이 모두 충족되어야 한다.
- [필수] 8절 필수 테스트 게이트가 자동 또는 수동 방식으로 통과되어야 한다.
- [필수] 최소 E2E 자동화 게이트는 `pytest + Playwright` 조합으로 통과되어야 한다.
- [필수] backend 와 agent 의 branch coverage report 가 증적 자료로 남아 있어야 한다.
- [필수] agent 는 모의 payload 주입 수준이 아니라 실제 Linux process 를 감시하는 최소 실행체 기준으로 한 번 이상 검증되어야 한다.
- [필수] 반복 실행 중 구조적 병목이나 책임 혼합이 확인되면, 기능 추가 전 refactoring 후보를 먼저 정리해야 한다.
- [필수] 최소 E2E 단계 완료 전에는 SSE, grouped event 고도화, admin UI 확장, 동적 metamodel UI 추가, agent 자동 업데이트를 시작하지 않는다.

## 10. 최소 E2E 이후 우선 확장 후보

- [후속] backend 와 연계된 agent 자동 업데이트
- [후속] polling 에서 SSE 기반 실시간 갱신으로 확장
- [후속] grouped event 및 event storm 완화 추가
- [후속] 관리자 운영 콘솔 추가
- [후속] debug payload 조회 UI 추가
- [후속] view 복사, diagram 복사 기능 추가
- [후속] group abstraction 과 multi-process 표현 고도화

## 11. 리스크와 관찰 포인트

- [리스크] 최소 E2E 범위가 커지면 개발 속도가 다시 느려질 수 있다.
- [리스크] 반대로 범위가 너무 작으면 이후 구조를 다시 뜯어야 해서 검증 가치가 낮아질 수 있다.
- [리스크] polling 기반 monitoring 만으로도 최신 상태 갱신 구조가 불안정하면 이후 SSE 확장 시 더 큰 문제가 생길 수 있다.
- [리스크] agent outbox 와 backend worker 경계가 흐려지면 초기부터 내구성 문제가 발생할 수 있다.
- [리스크] agent 자동 업데이트를 최소 E2E 범위에 너무 이르게 넣으면, 핵심 ingest/monitoring 흐름 검증 전에 운영 복잡도가 급격히 증가할 수 있다.
- [관찰] 최소 E2E 단계에서는 기능 수보다 장애 없이 반복 재현 가능한 흐름 확보가 더 중요하다.

## 12. 요약

- 최소 E2E 버전은 MVP 전체 기능의 축소판이 아니라, 가장 중요한 end-to-end 데이터 흐름을 검증하는 단계다.
- 이 단계에서는 `로그인 -> editor 저장 -> agent 수집 -> backend 반영 -> monitoring 표시 -> event 확인` 흐름이 완성되어야 한다.
- 기능 추가 전에 이 흐름을 자동화 가능한 테스트 게이트로 고정해야 이후 refactoring 과 regression testing 이 쉬워진다.
- 본 문서는 이후 구현 순서 결정과 초기 백로그 분해의 기준 문서로 사용한다.
