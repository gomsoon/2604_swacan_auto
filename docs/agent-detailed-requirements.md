# Software Architecture Runtime Monitoring System

## Agent 상세 요구사항

버전: Draft 0.1
작성일: 2026-04-08
목적: 본 문서는 MVP 구현을 위한 agent 상세 요구사항을 정의하며, 이후 agent 설정 구조, 로컬 SQLite 스키마, 전송 payload 스키마, 수집 모듈 설계의 직접적인 입력으로 사용한다.

## 1. 범위

- 본 문서는 `Python` 기반의 Linux 전용 비침습형 agent 를 대상으로 한다.
- agent 는 OS 위에서 별도 daemon process 로 동작하며, monitored software 내부에 삽입되지 않는다.
- 범위에는 host 및 process 수집, selector, self-state, batch payload 전송, ack 처리, SQLite outbox, 장애 복구, debug mode 지원이 포함된다.
- 각 요구사항은 `필수`, `선택`, `후속` 중 하나로 구분한다.

## 2. Agent 의 기본 역할

- [필수] agent 는 Linux host 의 기본 resource 상태와 지정된 process 상태를 수집해야 한다.
- [필수] agent 는 수집한 정보를 backend 가 요구하는 JSON batch payload 형식으로 변환하여 전송해야 한다.
- [필수] backend 연결 장애 시 수집 데이터를 로컬 SQLite outbox 에 안전하게 저장하고, 복구 후 순차 재전송해야 한다.
- [필수] agent 는 자기 자신의 상태를 `MonitoringAgent` runtime data 로 backend 에 전달해야 한다.
- [필수] agent 는 수집, 직렬화, 전송을 담당하고, alert 판단과 시각화 rule 계산은 backend 에 맡겨야 한다.

## 3. 핵심 설계 원칙

- [필수] agent 는 비침습형이어야 하며, `ptrace`, 코드 삽입, application 내부 hook 을 사용하지 않아야 한다.
- [필수] agent 는 Linux OS 가 제공하는 `/proc`, `/sys`, 파일 시스템 정보, 네트워크 통계 정보를 우선 활용해야 한다.
- [필수] agent 는 논리 대상 식별자인 `target_id` 를 중심으로 데이터를 수집해야 하며, PID 는 일시적인 runtime 식별자로 취급해야 한다.
- [필수] agent 는 하나의 논리 대상이 여러 process instance 로 확장될 수 있음을 전제로 설계되어야 한다.
- [필수] agent 는 backend 와의 통신 실패가 있더라도 데이터 유실 없이 복구 가능한 구조를 가져야 한다.
- [필수] agent 는 NTP 기반 시간 동기화를 전제로 하며, 모든 전송 시간 값은 최소 1/1000초 정밀도를 가져야 한다.

## 4. 구조적 아키텍처 요구사항

### 4.1 MVP agent 실행 구조

- [필수] MVP agent 는 다중 Python 프로세스 구조보다 단일 Python 프로세스 구조를 기본으로 채택해야 한다.
- [필수] 단일 프로세스 구조 안에서 역할 분리를 통해 수집, 직렬화, 저장, 전송, self-monitor 기능을 구성해야 한다.
- [필수] agent 는 재시작 후에도 outbox 와 sequence 상태를 복구할 수 있어야 하므로, 구조적 단순성과 내구성을 우선해야 한다.

### 4.2 내부 역할 분리

- [필수] agent 내부에는 최소한 `scheduler`, `selector/discovery`, `collector`, `SQLite writer`, `transport`, `self-monitor` 역할이 분리되어야 한다.
- [필수] sequence 생성 책임은 단일 경로에서 관리되어야 한다.
- [필수] SQLite 쓰기 책임은 가능한 한 단일 writer 흐름으로 모아야 한다.
- [필수] collector 와 transport 는 느슨하게 결합되어야 하며, backend 장애가 collector 중단으로 바로 이어지지 않아야 한다.

### 4.3 전송 및 내구성 구조

- [필수] agent 는 실시간 전송만을 신뢰하지 말고, outbox 기반 durable transport 구조를 가져야 한다.
- [필수] payload 는 전송 전에 로컬 SQLite 에 먼저 기록되고, ack 이후 완료 처리되어야 한다.
- [필수] backend 와의 통신은 외부 broker 없이 `HTTPS + JSON batch POST` 구조를 기본으로 유지해야 한다.
- [필수] debug mode 는 주 기능이 아니라 진단 기능으로서, 주 전송 경로를 복잡하게 만들지 않는 범위에서 동작해야 한다.

### 4.4 확장과 후속 분리 기준

- [필수] MVP 에서는 단일 프로세스 구조를 유지하되, 이후 필요 시 collector 와 transport 를 별도 프로세스나 서비스로 분리할 수 있는 모듈 경계를 가져야 한다.
- [필수] thread 상세 계측, 고빈도 수집, 다중 OS 지원이 필요해지는 시점 전까지는 multiprocess 구조를 도입하지 않는다.
- [필수] agent 구조적 아키텍처 요구사항은 이후 설정 스키마, 로컬 DB, payload 설계의 기준으로 사용해야 한다.

## 5. 실행 환경과 배포 요구사항

### 5.1 기본 실행 형태

- [필수] agent 는 Linux 에서 단독 실행되는 daemon process 여야 한다.
- [필수] agent 는 하나의 host 당 하나의 기본 agent process 로 운영하는 것을 전제로 한다.
- [필수] agent 는 재시작 후에도 이전 outbox 와 sequence 상태를 이어서 복구할 수 있어야 한다.
- [선택] systemd service unit 파일 제공을 고려할 수 있다.

### 5.2 권한과 보안

- [필수] agent 는 가능한 한 읽기 중심의 최소 권한으로 동작해야 한다.
- [필수] agent 는 수집을 위해 필요한 범위에서만 `/proc` 및 관련 시스템 정보를 읽어야 한다.
- [필수] agent 는 backend 와의 통신 시 HTTPS 를 사용해야 한다.
- [필수] agent 설정 파일 또는 환경 변수에 저장되는 인증 토큰은 로그에 평문으로 출력되어서는 안 된다.

## 6. 모니터링 대상 설정 요구사항

### 6.1 target_id 중심 관리

- [필수] agent 는 모니터링 대상을 `target_id` 기준으로 관리해야 한다.
- [필수] `target_id` 는 사람이 이해 가능한 안정적인 논리 식별자여야 하며, PID 변경과 무관해야 한다.
- [필수] 하나의 `target_id` 는 단일 process 또는 다수의 process instance 를 대표할 수 있어야 한다.

### 6.2 selector 요구사항

- [필수] agent 는 최소한 다음 selector 방식을 지원해야 한다.
- [필수] `command line regex`
- [필수] `executable path exact match`
- [필수] `process name exact match`
- [필수] `pid exact match`
- [필수] 하나의 target 은 `single` 또는 `multi` 매칭 모드를 가질 수 있어야 한다.
- [필수] `process name` 기반 selector 는 필요 시 사용자, 경로 또는 추가 조건과 함께 사용할 수 있어야 한다.
- [필수] selector 결과는 매 수집 주기마다 재평가되어야 한다.

### 6.3 다중 process 대응

- [필수] 하나의 selector 가 여러 PID 를 찾을 수 있어야 한다.
- [필수] agent 는 이러한 다중 PID 집합을 하나의 논리 target 에 연결할 수 있어야 한다.
- [필수] agent 는 group summary 와 instance detail 을 모두 생성할 수 있어야 한다.
- [필수] group summary 는 최소한 `actual_count`, `running_count`, `cpu_total`, `cpu_avg`, `memory_total`, `restart_detected` 정보를 포함해야 한다.
- [필수] instance detail 은 최소한 `pid`, `state`, `start_time`, `cpu_usage`, `memory_rss` 를 포함해야 한다.

## 7. 수집 대상 요구사항

### 7.1 Host 수준 수집

- [필수] agent 는 host 수준에서 최소한 다음 정보를 수집해야 한다.
- [필수] `hostname`
- [필수] `boot_id`
- [필수] `uptime`
- [필수] `load_average`
- [필수] `cpu_usage`
- [필수] `memory_total`, `memory_used`, `memory_free`
- [필수] `disk_total`, `disk_used`, `disk_free`
- [필수] `network_rx_bytes`, `network_tx_bytes`
- [선택] 파일 시스템별 상세 사용량
- [선택] 네트워크 인터페이스별 상세 통계

### 7.2 Process 수준 수집

- [필수] agent 는 지정된 process 에 대해 최소한 다음 정보를 수집해야 한다.
- [필수] `pid`
- [필수] `ppid`
- [필수] `name`
- [필수] `exe_path`
- [필수] `cmdline`
- [필수] `state`
- [필수] `start_time`
- [필수] `uptime`
- [필수] `cpu_usage`
- [필수] `memory_rss`
- [필수] `memory_vms`
- [필수] `thread_count`
- [필수] `fd_count`
- [필수] `io_read_bytes`
- [필수] `io_write_bytes`
- [선택] `listen_port` 또는 관련 소켓 요약 정보

### 7.3 Thread 관련 정책

- [필수] MVP 에서 agent 는 개별 thread 상세 계측보다 `thread_count` 중심 수집을 우선해야 한다.
- [필수] 개별 thread 의 이름 또는 개수 기반 단순 집계는 선택적으로 지원할 수 있다.
- [후속] TID 단위 상세 계측, thread pool 자동 식별, thread state 심화 수집은 후속 범위로 둔다.

## 8. 수집 주기와 전송 주기 요구사항

### 8.1 기본 주기

- [필수] agent 는 `heartbeat` 를 기본 5초 주기로 생성해야 한다.
- [필수] host/process snapshot 은 기본 5초 또는 10초 주기로 생성 가능해야 한다.
- [필수] backend 로의 outbox flush 는 연결 정상 시 1초 또는 2초 주기로 시도할 수 있어야 한다.
- [필수] backend 장애 시 재시도는 backoff 정책을 적용해야 한다.

### 8.2 즉시 전송 이벤트

- [필수] process 시작, 종료, 재시작, target 미탐지, agent 연결 복구 같은 상태 전이 이벤트는 가능한 한 즉시 outbox 에 기록되어야 한다.
- [필수] 즉시 전송 이벤트도 backend 미연결 시에는 outbox 를 통해 복구 가능해야 한다.

### 8.3 snapshot 과 event 분리

- [필수] agent 는 현재 상태를 나타내는 snapshot 과 상태 전이를 나타내는 event 를 구분해서 생성해야 한다.
- [필수] snapshot 은 최신 상태 계산용으로 사용되고, event 는 이력과 이상 상황 분석용으로 사용된다.

## 9. MonitoringAgent self-state 요구사항

- [필수] agent 는 자기 자신의 상태를 backend 에 주기적으로 보내야 한다.
- [필수] self-state 는 backend 에서 `MonitoringAgent` runtime data 로 처리될 수 있어야 한다.
- [필수] self-state 는 최소한 다음 정보를 포함해야 한다.
- [필수] `agent_id`
- [필수] `agent_pid`
- [필수] `agent_version`
- [필수] `start_time`
- [필수] `heartbeat_time`
- [필수] `backend_connection_status`
- [필수] `outbox_queue_depth`
- [필수] `last_sent_seq`
- [필수] `last_ack_seq`
- [필수] `monitored_target_count`
- [필수] `host_boot_id`
- [필수] self-state 는 문제가 발생했을 때 agent 자체의 장애와 monitored target 의 장애를 구분할 수 있게 해야 한다.

## 10. Payload 구조 요구사항

### 10.1 통신 방식

- [필수] agent 와 backend 간 통신은 `HTTPS + JSON batch POST` 방식으로 구현한다.
- [필수] agent 는 backend 로만 연결을 시작하는 단방향 클라이언트로 동작한다.
- [필수] backend 인증을 위해 `agent_id` 와 사전 공유 토큰 또는 동등한 인증 수단을 사용해야 한다.

### 10.2 batch payload 구조

- [필수] batch payload 는 최소한 다음 상위 필드를 포함해야 한다.
- [필수] `agent_id`
- [필수] `boot_id`
- [필수] `seq_start`
- [필수] `seq_end`
- [필수] `sent_at`
- [필수] `items`
- [필수] 각 item 은 최소한 `seq`, `payload_type`, `occurred_at`, `target_id` 또는 동등한 대상 식별자, payload 본문을 포함해야 한다.
- [필수] payload type 은 최소한 `host_snapshot`, `process_snapshot`, `process_event`, `agent_state` 를 지원해야 한다.
- [선택] `transport_event`, `diagnostic_event` 를 별도 type 으로 분리할 수 있다.

### 10.3 sequence 와 ack 처리

- [필수] `seq` 는 agent boot 단위에서 단조 증가해야 한다.
- [필수] agent 는 backend 응답의 `ack_seq` 를 기준으로 outbox 정리 여부를 판단해야 한다.
- [필수] 동일 payload 의 중복 전송이 발생하더라도 backend 가 중복 제거할 수 있도록 동일 `seq` 를 유지해야 한다.
- [필수] backend 응답에는 최소한 `ack_seq`, `accepted_count`, `server_time` 이 포함된다고 가정해야 한다.
- [필수] agent 는 부분 수용 응답에도 대응할 수 있어야 하며, ack 되지 않은 항목은 outbox 에 남겨 재전송해야 한다.

## 11. SQLite outbox 요구사항

### 11.1 로컬 저장 목적

- [필수] agent 는 backend 연결 실패 또는 일시 오류 시 payload 를 SQLite outbox 에 저장해야 한다.
- [필수] outbox 의 목적은 데이터 유실 방지와 순차 재전송이다.
- [필수] outbox 는 agent 재시작 후에도 복구 가능해야 한다.

### 11.2 로컬 SQLite 구조

- [필수] 로컬 SQLite 는 최소한 다음 논리 영역을 가져야 한다.
- [필수] `outbox`
- [필수] `agent_meta`
- [필수] `target_cache`
- [선택] `debug_transport_log`
- [필수] `outbox` 는 최소한 `seq`, `payload_json`, `occurred_at`, `retry_count`, `acked_at` 또는 동등한 필드를 가져야 한다.
- [필수] `agent_meta` 는 agent 고유 정보, 마지막 sequence, 마지막 ack 정보를 저장할 수 있어야 한다.
- [필수] `target_cache` 는 `target_id`, 최근 PID 집합, 마지막 탐지 시각, CPU 계산용 이전 샘플 값을 저장할 수 있어야 한다.
- [필수] 로컬 SQLite 는 `WAL` 모드 사용을 기본으로 고려해야 한다.

### 11.3 outbox 처리 정책

- [필수] payload 는 전송 전에 먼저 outbox 에 기록되어야 한다.
- [필수] backend 로부터 ack 가 확인된 후에만 outbox 항목을 완료 처리하거나 제거해야 한다.
- [필수] backend 장애가 길어질 경우 outbox queue depth 증가를 self-state 로 보고할 수 있어야 한다.
- [필수] outbox 는 seq 순서대로 읽고 전송해야 한다.
- [필수] agent 는 재시작 후 미처리 outbox 부터 재전송해야 한다.

## 12. 장애 복구와 stale 대응 지원 요구사항

- [필수] agent 는 일시적인 selector 미매칭, process 재시작, PID 변경을 일반적인 운영 상황으로 처리해야 한다.
- [필수] 이전에 존재하던 PID 가 사라졌을 때 즉시 target 삭제 의미로 보내지 않고, 상태 전이 정보와 함께 backend 가 stale 판단을 할 수 있도록 데이터를 제공해야 한다.
- [필수] 동일 target 이 새 PID 로 다시 발견되면 restart 또는 rematch 로 해석 가능한 정보를 포함해야 한다.
- [필수] agent 는 target 이 일정 시간 동안 발견되지 않을 경우 `not_found` 또는 동등한 event 를 생성할 수 있어야 한다.

## 13. Debug mode 요구사항

### 13.1 기본 원칙

- [필수] agent 는 debug mode 설정을 가질 수 있어야 한다.
- [필수] debug mode 의 기본값은 비활성화 상태여야 한다.
- [필수] debug mode 는 운영 상시 기능이 아니라 문제 재현과 조사 지원을 위한 기능이어야 한다.

### 13.2 backend debug 와의 연계

- [필수] agent 는 debug mode 에서 backend 가 payload 추적에 사용할 수 있는 일관된 `trace_id` 또는 동등한 추적 정보를 payload 또는 헤더에 포함할 수 있어야 한다.
- [필수] agent 는 debug mode 에서 요청 시각, 응답 시각, 응답 코드, payload size 와 같은 전송 메타데이터를 남길 수 있어야 한다.
- [필수] agent 는 민감 정보가 포함된 인증 토큰을 debug 로그에 평문으로 남겨서는 안 된다.
- [선택] agent 는 필요 시 제한된 기간 동안 로컬 `debug_transport_log` 에 요청/응답 메타데이터를 남길 수 있다.
- [필수] debug mode 사용 여부는 self-state 나 진단 정보로 backend 에 전달 가능해야 한다.

## 14. 설정과 운영 요구사항

### 14.1 기본 설정 항목

- [필수] agent 는 최소한 다음 설정 항목을 지원해야 한다.
- [필수] backend endpoint
- [필수] agent_id
- [필수] authentication token
- [필수] heartbeat interval
- [필수] snapshot interval
- [필수] retry backoff 정책
- [필수] monitored target 목록과 selector 정의
- [필수] debug mode on/off

### 14.2 설정 반영 방식

- [필수] MVP 에서는 설정 변경 시 agent 재시작 방식으로 반영해도 된다.
- [선택] 이후 버전에서는 무중단 reload 를 검토할 수 있다.

## 15. 보안과 개인정보 요구사항

- [필수] agent 는 payload 와 로그에 인증 토큰, 세션 토큰, 비밀번호를 평문으로 저장해서는 안 된다.
- [필수] debug mode 에서도 동일한 마스킹 정책이 적용되어야 한다.
- [필수] agent 는 필요한 범위를 넘어 monitored process 의 민감한 메모리 내용을 수집해서는 안 된다.
- [필수] 비침습형 agent 는 application 내부 데이터 구조를 직접 읽는 행위를 MVP 범위에서 제외해야 한다.

## 16. 테스트 요구사항

- [필수] `pytest` 를 사용하여 단위 테스트와 통합 테스트를 작성해야 한다.
- [필수] selector 매칭, target_id 기반 grouping, host/process snapshot 생성, self-state 생성에 대한 테스트가 필요하다.
- [필수] outbox enqueue, ack 후 정리, 장애 후 재전송, agent 재시작 복구에 대한 테스트가 필요하다.
- [필수] batch payload 직렬화, millisecond 시간 정밀도, sequence 증가, duplicate retransmission 에 대한 테스트가 필요하다.
- [필수] debug mode 에 대해서는 trace_id 포함, 민감 정보 마스킹, 전송 메타데이터 기록 여부에 대한 테스트가 필요하다.
- [선택] 이후 버전에서는 장시간 실행, 메모리 누수, 대량 target 시나리오에 대한 soak test 를 추가할 수 있다.

## 17. MVP 에서 제외하거나 단순화하는 항목

- [후속] application 내부 SDK 또는 침습형 agent
- [후속] `ptrace`, `eBPF`, syscall trace 기반 고급 계측
- [후속] 개별 thread 상세 계측과 thread pool 자동 분석
- [후속] Windows, macOS 지원
- [후속] backend 로부터의 원격 명령 제어
- [후속] 설정 hot reload

## 18. 다음 설계 단계 입력 항목

- [필수] agent 설정 파일 스키마 초안에는 backend endpoint, token, 주기 설정, target selector, debug mode 가 포함되어야 한다.
- [필수] 로컬 SQLite 스키마 초안에는 outbox, agent_meta, target_cache, 필요 시 debug_transport_log 가 포함되어야 한다.
- [필수] payload JSON schema 초안에는 host_snapshot, process_snapshot, process_event, agent_state 가 포함되어야 한다.
- [필수] backend API 연동 설계에는 ack 처리, duplicate 처리, partial accept 처리, trace_id 연동이 반영되어야 한다.

## 19. 요약

- 본 agent 는 Linux 전용 비침습형 daemon 으로서 host 와 process 상태를 수집하고 backend 로 안전하게 전달해야 한다.
- MVP agent 는 단일 Python 프로세스 구조를 기본으로 하고, 내부 역할 분리와 SQLite outbox 기반 내구성을 우선해야 한다.
- `target_id`, selector, multi-process 대응, self-state, SQLite outbox, batch payload, ack 처리, debug mode 는 MVP 의 핵심 요구사항이다.
- agent 는 데이터를 수집하고 복구 가능한 방식으로 전달하는 역할에 집중하고, 판단과 시각화는 backend 가 담당해야 한다.
- 본 문서는 이후 agent 설정, 로컬 DB, payload schema, 테스트 설계의 기준 문서로 사용한다.
