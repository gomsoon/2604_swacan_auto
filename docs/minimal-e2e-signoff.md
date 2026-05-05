# Software Architecture Runtime Monitoring System

## Minimal E2E Sign-off
작성일: 2026-04-14

## 1. 목표

이 문서는 현재 구현된 minimal end-to-end 범위가 실제로 닫혔는지 확인하고, 다음 단계인 MVP 확장으로 넘어가기 전의 기준점을 남기기 위한 sign-off 문서다.

## 2. 확인된 end-to-end 범위

- 사용자 로그인
- view 생성 및 저장
- SVG editor에서 `PhysicalServer`, `SoftwareProcess`, `MonitoringAgent`, `CommunicationLink` 편집
- backend view CRUD 및 monitoring 조회
- Linux agent의 host/process snapshot 수집
- agent SQLite outbox 적재 및 batch 전송
- backend ingest inbox 수신 및 worker 처리
- latest state / raw event 반영
- monitoring UI에서 실제 agent 데이터 확인
- admin UI에서 ingest, latest state, stale agent, debug payload, cleanup 결과 확인

## 3. 자동화 테스트 결과

최신 전체 회귀 결과:

- `97 passed`
- `2 skipped`

최신 branch coverage 결과:

- 대상: `app`, `agent`
- 총 branch coverage: `85%`
- 리포트: [coverage.xml](C:/2604_swacan_auto/test_artifacts/coverage.xml)

coverage 기준 메모:

- 장기 목표 기준은 `branch coverage 80% 이상`
- 현재 sign-off 기준에서는 coverage 측정과 report 생성 자체를 우선 필수로 보고, `fail-under 80` 하드 게이트는 이후 안정화 단계에서 적용한다.

## 4. 실제 Linux 검증 결과

실제 Linux agent 서버 기반 검증은 다음 문서에 정리되어 있다.

- [linux-agent-l01-evidence.md](C:/2604_swacan_auto/docs/linux-agent-l01-evidence.md)
- [agent-linux-runbook.md](C:/2604_swacan_auto/docs/agent-linux-runbook.md)

검증 요약:

- SSH 기반 smoke test 성공
- 동일 시나리오 3회 반복 성공
- monitoring UI에서 실제 Linux agent 결과 표시 확인

## 5. 구현 상태 판단

현재 상태는 minimal end-to-end 관점에서 `완료 가능` 수준으로 판단한다.

그 이유는 다음과 같다.

- 실제 Linux agent가 backend와 frontend까지 연결되는 흐름이 검증되었다.
- ingest/worker 경계, duplicate 처리, rollback, stale 파생 상태, retention cleanup까지 최소 구조가 갖춰졌다.
- admin 화면에서 운영자가 최소한의 문제 추적을 수행할 수 있다.
- 자동화 테스트와 branch coverage 기준이 함께 남아 있다.

## 6. 남은 비차단 항목

아래 항목들은 minimal E2E를 막는 필수 결함은 아니며, MVP 단계에서 자연스럽게 이어서 확장하면 된다.

- stale 감지 결과의 별도 raw event 고도화
- cleanup 결과의 추가 운영 자동화
- 관리자 화면의 고급 검색/필터
- agent 자동 업데이트
- systemd/cgroup 기반 process group 식별 고도화

## 7. 결론

현재 구현은 minimal end-to-end 목표를 충족하는 것으로 판단한다.  
다음 단계에서는 구현 범위를 다시 넓히기보다, 이 기준점을 바탕으로 MVP 기능 확장과 구조 보강으로 넘어가는 것이 적절하다.
