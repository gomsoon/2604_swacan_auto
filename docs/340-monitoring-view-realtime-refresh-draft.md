# Monitoring View Realtime Refresh Draft

버전: Draft 0.1  
작성일: 2026-04-18

목적: `Monitoring View`의 실시간 갱신을 `view 전체 polling`에서 `monitored_object 단위 partial refresh` 중심 구조로 확장하기 위한 기준을 정리한다.

## 1. 현재 구조

현재 `Monitoring View`는 polling 기반 near-real-time 구조다.

- agent는 ingest batch를 backend에 보낸다.
- backend는 ingest inbox에 receipt ack를 남긴 뒤 worker가 비동기로 처리한다.
- worker는 `latest_states`, `alert_instances`, `grouped_events`를 갱신한다.
- frontend는 일정 주기로
  - `/latest-state`
  - `/alerts`
  - `/events`
  를 다시 읽는다.

이 구조는 안정적이지만, 변경된 객체가 적어도 view 전체를 다시 읽게 된다는 한계가 있다.

## 2. 목표 방향

다음 기본선은 아래와 같다.

- `SSE`로 변경 사실을 push
- payload는 `monitored_object_id` 중심의 작은 이벤트
- frontend는 해당 monitored object만 부분 갱신
- polling은 제거하지 않고 느린 주기의 full reconcile fallback으로 유지

## 3. 왜 monitored_object 단위인가

runtime identity는 이미 `monitored_object`로 분리되어 있다.

이 구조를 활용하면:

- 같은 runtime 대상을 여러 node가 fan-out해도 한 번의 partial refresh로 모두 갱신 가능
- 큰 view에서 네트워크/렌더링 비용 감소
- `Selection Summary`, alert list, grouped event list를 더 빠르게 갱신 가능
- 이후 SSE와 polling fallback을 함께 운영하기 쉬움

## 4. SSE payload 초안

최소 payload 예시는 아래와 같다.

```json
{
  "view_id": 1,
  "monitored_object_id": 1302,
  "change_types": ["latest_state", "alerts", "grouped_events"],
  "occurred_at": "2026-04-18T09:30:00.000+09:00"
}
```

필요 시 다음 정보를 추가할 수 있다.

- `alert_instance_id`
- `grouped_event_id`
- `severity`
- `event_type`

## 5. frontend 갱신 원칙

`refreshAll()` 대신 다음 순서로 갱신한다.

1. `GET /api/views/{view_id}/runtime-objects/{monitored_object_id}/slice`
2. 해당 monitored object를 참조하는 node overlay 갱신
3. 선택 중인 node / edge가 같은 monitored object를 참조하면 `Selection Summary` 갱신
4. alert / grouped event 목록에서 같은 monitored object에 해당하는 부분만 교체

## 6. partial refresh만으로 충분하지 않은 경우

아래 케이스는 여전히 full reconcile이 필요하다.

- active view 전환
- node binding 변경
- metamodel / published snapshot 변경
- stale 상태처럼 시간 경과만으로 바뀌는 파생 상태
- grouped event 정렬 재구성

따라서 최종 구조는 `partial refresh + 느린 full reconcile`이 적절하다.

## 7. 현재 반영한 구현 기반

현재 코드에는 아래 기반이 먼저 들어간 상태를 목표로 한다.

- `GET /api/views/{view_id}/runtime-objects/{monitored_object_id}/slice`
- `Selection Summary`에서 선택한 node / edge에 대해 monitored object slice를 즉시 다시 읽는 helper

이 단계는 아직 SSE 자체를 도입한 것은 아니지만, 나중에 SSE payload를 받았을 때 그대로 재사용할 수 있는 기반이 된다.

## 8. 다음 단계

1. `object-slice API` 안정화
2. `Selection Summary` partial refresh 정착
3. SSE 채널 도입
4. polling 주기를 느리게 조정하며 full reconcile fallback 유지
