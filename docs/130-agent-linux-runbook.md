# Software Architecture Runtime Monitoring System

## Linux Agent 실행 가이드

버전: Draft 0.1  
작성일: 2026-04-14

## 1. 목적

- 이 문서는 Linux 서버에서 agent를 실제로 배치하고 실행하는 최소 절차를 정리한다.
- minimal end-to-end 검증, 운영 점검, 장애 재현 시 동일한 실행 기준으로 사용한다.
- 대상은 `Python 3.11+` 환경의 Linux 서버이다.

## 2. 준비 조건

- Linux 서버에 `python3.11` 이상이 설치되어 있어야 한다.
- backend ingest endpoint 에 HTTPS 또는 테스트용 HTTP로 접근 가능해야 한다.
- agent가 읽을 설정 파일과 로컬 SQLite 저장 경로를 준비해야 한다.
- 운영 계정 또는 서비스 계정이 `/opt/swacan-agent` 같은 배치 경로에 접근 가능해야 한다.

## 3. 권장 디렉터리 구조

```text
/opt/swacan-agent/
  agent/
  agent.toml
  agent.sqlite3
  logs/
```

권장 사항:
- 코드: `/opt/swacan-agent/agent`
- 설정: `/opt/swacan-agent/agent.toml`
- SQLite outbox: `/opt/swacan-agent/agent.sqlite3`
- 로그: `/opt/swacan-agent/logs/`

## 4. 샘플 설정

샘플 파일은 [agent.example.toml](C:/2604_swacan_auto/deploy/linux/agent.example.toml) 에 있다.

핵심 설정 항목:
- `[agent]`
  - `agent_id`
  - `token`
  - `debug_mode`
- `[backend]`
  - `endpoint`
- `[storage]`
  - `database_path`
  - `keep_acked_rows`
  - `cleanup_batch_size`
  - `pending_warning_rows`
- `[intervals]`
  - `heartbeat_seconds`
  - `snapshot_seconds`
  - `flush_seconds`
  - `retry_backoff_seconds`
- `[[targets]]`
  - `target_id`
  - `mode`
  - `process_name` 또는 `command_line_regex` 또는 `executable_path` 또는 `pid`

## 5. 수동 실행 절차

### 5.1 배치

1. Linux 서버에 agent 소스를 업로드한다.
2. `agent.toml`을 환경에 맞게 수정한다.
3. backend endpoint 와 token 값을 확인한다.

### 5.2 설정 확인

```bash
python3.11 -m agent --config /opt/swacan-agent/agent.toml --dump-config
```

확인 포인트:
- `agent_id`
- `endpoint`
- `targets`
- `storage_path`

### 5.3 단일 cycle 실행

```bash
python3.11 -m agent --config /opt/swacan-agent/agent.toml --once
```

이 명령은 다음 확인에 적합하다.
- 설정 로딩 성공 여부
- selector 기본 동작 여부
- outbox enqueue 여부
- transport/ack 기본 동작 여부

### 5.4 반복 cycle 실행

```bash
python3.11 -m agent --config /opt/swacan-agent/agent.toml --cycles 10
```

이 명령은 테스트 목적의 제한 실행에 적합하다.

### 5.5 장기 실행

systemd 사용을 권장한다. 예시는 [swacan-agent.service.example](C:/2604_swacan_auto/deploy/linux/swacan-agent.service.example) 에 있다.

## 6. systemd 예시 적용 순서

1. 예시 파일을 `/etc/systemd/system/swacan-agent.service` 로 복사한다.
2. `ExecStart`, `WorkingDirectory`, `User`, `Group` 값을 환경에 맞게 수정한다.
3. 다음 명령을 실행한다.

```bash
sudo systemctl daemon-reload
sudo systemctl enable swacan-agent
sudo systemctl start swacan-agent
```

확인 명령:

```bash
sudo systemctl status swacan-agent
journalctl -u swacan-agent -n 100 --no-pager
```

## 7. 운영 점검 체크리스트

- agent 프로세스가 실행 중인가
- `agent.toml`의 endpoint/token이 현재 backend와 일치하는가
- `agent.sqlite3`가 생성되었는가
- outbox pending row가 계속 증가하고 있지 않은가
- backend의 `/api/agents/ingest`로 payload가 들어오는가
- monitoring 화면에서 `MonitoringAgent` 상태가 보이는가
- admin 화면에서 ingest inbox, raw event, debug payload를 확인할 수 있는가

## 8. 장애 시 확인 순서

1. `--dump-config`로 설정 오타 여부 확인
2. Python 버전 확인
3. backend endpoint 네트워크 도달성 확인
4. token/agent_id 일치 여부 확인
5. `agent.sqlite3`의 outbox pending 증가 여부 확인
6. backend ingest inbox 와 raw event 확인
7. monitoring/admin 화면 반영 여부 확인

## 9. SSH 기반 테스트와의 연결

Windows 개발 환경에서는 pytest SSH 통합 테스트가 다음 흐름으로 동작한다.

1. SSH 접속
2. 원격 작업 디렉터리 준비
3. agent 소스 업로드
4. 임시 `agent.toml` 생성
5. dummy process 실행
6. agent 실행
7. 로그/SQLite 수집
8. agent 종료 및 정리

관련 구현:
- [linux_agent_ssh_support.py](C:/2604_swacan_auto/tests/linux_agent_ssh_support.py)
- [test_linux_agent_ssh_integration.py](C:/2604_swacan_auto/tests/test_linux_agent_ssh_integration.py)
- [test_linux_agent_monitor_ui.py](C:/2604_swacan_auto/tests/test_linux_agent_monitor_ui.py)

## 10. 현재 기준 결론

- minimal end-to-end 기준으로 Linux 서버에 agent를 실제 배치하고 backend 및 UI까지 연결하는 절차는 재현 가능하다.
- 운영 단계에서는 수동 실행보다 systemd 기반 장기 실행을 기본 경로로 삼는 것이 적절하다.
