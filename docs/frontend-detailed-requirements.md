# Software Architecture Runtime Monitoring System

## 프론트엔드 상세 요구사항

버전: Draft 0.1
작성일: 2026-04-08
목적: 본 문서는 MVP 구현을 위한 frontend 상세 요구사항을 정의하며, 이후 화면 설계, SVG canvas interaction 설계, API 연동 설계, 수동 테스트 시나리오의 직접적인 입력으로 사용한다.

## 1. 범위

- 본 문서는 `Bootstrap`, `inline SVG`, `커스텀 ES module`, `interact.js` 기반의 MVP frontend 를 대상으로 한다.
- frontend 는 editor canvas, monitoring view, 관리자 화면, debug 조회 화면을 포함한다.
- frontend 는 backend 의 메타모델, notation registry, latest state, grouped event, debug payload 정책과 일관되게 동작해야 한다.
- 각 요구사항은 `필수`, `선택`, `후속` 중 하나로 구분한다.

## 2. Frontend 의 기본 역할

- [필수] frontend 는 backend 메타모델과 notation registry 를 기반으로 architecture model 을 편집할 수 있어야 한다.
- [필수] frontend 는 저장된 architecture view 를 monitoring view 로 전환하여 runtime state 와 event 를 실시간에 가깝게 관찰할 수 있어야 한다.
- [필수] frontend 는 backend 가 강제하는 containment, metamodel version, grouped event 정책을 화면 상호작용에 반영해야 한다.
- [필수] frontend 는 관리자에게 메타모델 조회, 세션 조회, 운영 로그 조회, debug payload 조회 기능을 제공해야 한다.
- [필수] frontend 는 사용자의 역할에 따라 editor 기능, monitoring 기능, admin 기능의 접근 범위를 구분해야 한다.

## 3. 핵심 설계 원칙

- [필수] canvas 는 자유 드로잉 도구가 아니라 메타모델 제약을 따르는 모델 편집기여야 한다.
- [필수] frontend 는 `model` 과 `view` 를 구분해서 다루어야 하며, 구조 정보와 배치 정보를 혼합해서는 안 된다.
- [필수] frontend 는 하나의 canvas 객체가 여러 runtime instance 를 대표할 수 있다는 group abstraction 개념을 기본 전제로 가져야 한다.
- [필수] editor 화면과 monitoring 화면은 동일한 model/view 구조를 공유하고, runtime overlay 와 interaction 정책만 달라야 한다.
- [필수] frontend 는 backend 가 제공하는 latest state 와 grouped event 를 기본 화면 단위로 사용하고, 저수준 event 나 debug payload 는 on-demand 조회로 제한해야 한다.
- [필수] frontend 는 debug 기능이 활성화된 경우에도 민감 정보를 직접 노출하지 않아야 한다.

## 4. 기술 구성 요구사항

### 4.1 UI 기술 스택

- [필수] 일반 UI 와 관리자 화면은 `Bootstrap` 기반으로 구성한다.
- [필수] canvas 렌더링은 `inline SVG` 기반으로 구현한다.
- [필수] canvas 상호작용은 소규모 커스텀 JavaScript 계층과 `interact.js` 를 사용해 구현한다.
- [선택] 확대/축소와 패닝이 복잡해질 경우 `d3-zoom` 수준의 제한적 보조 라이브러리 도입을 검토할 수 있다.
- [후속] 대규모 다이어그램 전용 가상화 또는 별도 렌더링 엔진은 후속 범위로 둔다.

### 4.2 페이지 구조

- [필수] 최소한 다음 화면을 제공해야 한다.
- [필수] 로그인 화면
- [필수] workspace 및 view 목록 화면
- [필수] architecture editor 화면
- [필수] monitoring view 화면
- [필수] 관리자 메타모델 조회 화면
- [필수] 관리자 세션 및 로그 조회 화면
- [필수] 관리자 debug payload 조회 화면

## 5. 인증과 권한 요구사항

- [필수] 인증되지 않은 사용자는 editor, monitoring, admin 화면에 접근할 수 없어야 한다.
- [필수] 일반 사용자와 관리자 권한은 화면 메뉴와 API 호출 양쪽에서 구분되어야 한다.
- [필수] 일반 사용자는 자신에게 허용된 workspace 와 view 만 볼 수 있어야 한다.
- [필수] 관리자만 메타모델 관리, 운영 로그 조회, debug payload 조회에 접근할 수 있어야 한다.
- [필수] frontend 는 권한이 없는 기능 버튼을 숨기거나 비활성화하고, 직접 URL 접근 시에도 적절한 오류 화면을 보여줄 수 있어야 한다.

## 6. View 목록과 진입 흐름 요구사항

- [필수] 사용자는 로그인 후 접근 가능한 workspace 와 view 목록을 볼 수 있어야 한다.
- [필수] 각 view 항목에는 최소한 이름, 설명, 최근 수정 시각, metamodel version 정보가 표시되어야 한다.
- [필수] 사용자는 view 를 editor 모드 또는 monitoring 모드로 열 수 있어야 한다.
- [필수] backend 에서 edit lock 정책을 사용할 경우, 목록 또는 진입 시점에 현재 편집 중 여부를 볼 수 있어야 한다.
- [필수] metamodel 이 `deprecated` 상태인 view 라도 읽기 전용 또는 기존 버전 기준으로 열 수 있어야 한다.
- [선택] 최근 열람한 view, 즐겨찾기 view 는 후속 단계에서 추가할 수 있다.

## 7. Palette 와 notation 요구사항

### 7.1 동적 palette 구성

- [필수] editor 의 palette 는 backend notation registry 조회 결과로 동적으로 구성되어야 한다.
- [필수] palette 는 notation 의 group, semantic type, 표시 이름, 아이콘 또는 간단한 모형 표현을 보여줄 수 있어야 한다.
- [필수] palette 는 notation 의 활성화 여부, metamodel version, containment 가능 여부를 반영해야 한다.
- [필수] frontend 는 자신이 지원하는 SVG primitive 범위 안의 notation 만 정상 렌더링 대상으로 취급해야 한다.
- [필수] 지원하지 않는 notation 정의가 조회되면 사용자에게 unsupported 표시를 하고, 잘못된 편집을 막아야 한다.

### 7.2 semantic type 별 기본 표현

- [필수] `PhysicalServer`, `VirtualMachine`, `SoftwareProcess`, `ExecutionThread`, `MonitoringAgent`, `CommunicationLink` 의 기본 시각 표현을 제공해야 한다.
- [필수] `MonitoringAgent` 는 일반 process 와 구분 가능한 별도 semantic type 으로 표시되어야 한다.
- [필수] `MonitoringAgent` 의 기본 도형은 process 계열과 일관되게 라운드 사각형을 유지하는 것이 바람직하다.
- [필수] `MonitoringAgent` 는 특수한 process 임을 보여주기 위해 이중 테두리, 전용 배지, 또는 거의 원형에 가까운 라운드 사각형 같은 추가 스타일을 사용할 수 있어야 한다.
- [필수] group abstraction 이 적용된 `Server`, `Process`, `Thread` 는 stacked shape 또는 `xN` 배지 등으로 표현 가능해야 한다.
- [필수] `MonitoringAgent` 와 관측 대상의 관계는 containment 가 아니라 `monitors` association 으로 표현되어야 한다.

## 8. Editor Canvas 요구사항

### 8.1 기본 상호작용

- [필수] 사용자는 palette 에서 요소를 선택해 canvas 에 생성할 수 있어야 한다.
- [필수] 사용자는 node 를 선택, 이동, 위치 조정, 삭제할 수 있어야 한다.
- [필수] 사용자는 edge 를 생성하고 source 와 target 을 지정할 수 있어야 한다.
- [필수] 선택된 요소의 속성을 우측 패널 또는 동등한 편집 패널에서 수정할 수 있어야 한다.
- [필수] canvas 는 확대/축소와 패닝을 지원해야 한다.
- [선택] snap-to-grid 와 자동 정렬은 선택 기능으로 둘 수 있다.

### 8.2 containment 기반 편집 제약

- [필수] 빈 canvas 또는 최상위 영역에는 root 로 허용된 semantic type 만 생성할 수 있어야 한다.
- [필수] `PhysicalServer` 내부에는 `VirtualMachine`, `SoftwareProcess`, `MonitoringAgent` 만 생성 가능해야 한다.
- [필수] `VirtualMachine` 내부에는 `SoftwareProcess`, `MonitoringAgent` 만 생성 가능해야 한다.
- [필수] `SoftwareProcess` 내부에는 `ExecutionThread` 만 생성 가능해야 한다.
- [필수] `ExecutionThread` 는 자식 요소를 가질 수 없어야 한다.
- [필수] `MonitoringAgent` 는 자식 containment 의 부모가 될 수 없어야 한다.
- [필수] drag & drop 이동 중에도 부모 허용 타입과 경계 영역이 실시간으로 검증되어야 한다.
- [필수] 저장 시점에는 backend 검증 결과를 다시 반영해야 하며, 프론트 검증만으로 완료된 것으로 간주해서는 안 된다.

### 8.3 layout 저장 요구사항

- [필수] view layout 은 최소한 `x`, `y`, `width`, `height`, `z_index`, `collapsed_state` 를 저장할 수 있어야 한다.
- [필수] containment 자식 요소의 좌표는 부모 기준 좌표계로 해석되어야 한다.
- [필수] edge 는 최소한 source anchor, target anchor, control point 또는 동등한 경로 정보를 저장할 수 있어야 한다.
- [필수] 이동과 크기 변경 후의 최신 배치 정보는 view 저장 시 backend 로 전송되어야 한다.

### 8.4 속성 편집 요구사항

- [필수] 사용자는 semantic type 별 property definition 에 따라 속성을 입력할 수 있어야 한다.
- [필수] 입력 폼은 property type, 필수 여부, enum, 단위 정보를 반영해야 한다.
- [필수] `instance_mode`, `cardinality_scope`, `expected_min`, `expected_max`, `target_id` 같은 핵심 속성은 화면에서 명확히 구분되어야 한다.
- [필수] `cardinality_scope` 는 최소한 `per_member`, `group_total` 의미 차이를 설명과 함께 표시해야 한다.

### 8.5 연결 관계 편집 요구사항

- [필수] 사용자는 `CommunicationLink` 와 `monitors` association 을 구분해서 생성할 수 있어야 한다.
- [필수] `monitors` association 은 `MonitoringAgent` 와 관측 대상 사이에서만 생성 가능해야 한다.
- [필수] 잘못된 semantic type 조합으로 edge 를 연결하려 할 경우, frontend 는 즉시 생성 불가 상태를 표시해야 한다.

## 9. View 저장과 복사 요구사항

- [필수] 사용자는 현재 view 를 저장할 수 있어야 한다.
- [필수] 저장 시 dirty 상태가 해제되고 최근 저장 시각이 갱신되어야 한다.
- [필수] 사용자는 동일 model 을 공유하는 `view 복사`를 만들 수 있어야 한다.
- [필수] 사용자는 model 과 view 를 함께 복제하는 `diagram 복사`를 만들 수 있어야 한다.
- [필수] frontend 는 `view 복사` 와 `diagram 복사` 의 차이를 사용자에게 명확히 설명해야 한다.
- [필수] 저장 충돌이나 revision mismatch 발생 시, 사용자는 재조회 또는 read-only 전환 같은 명확한 선택지를 받아야 한다.

## 10. 편집 잠금과 협업 요구사항

- [필수] MVP 에서는 view 단위 편집 잠금 정책을 따른다.
- [필수] 한 사용자가 editor 모드로 진입해 잠금을 획득하면, 다른 사용자는 해당 view 를 read-only 로 열거나 monitoring 모드로만 볼 수 있어야 한다.
- [필수] 잠금 상태, 잠금 사용자, 마지막 heartbeat 또는 활동 시각이 화면에 표시되어야 한다.
- [필수] 잠금이 만료되거나 해제되면 frontend 는 이를 반영해 편집 가능 상태로 전환할 수 있어야 한다.
- [선택] 이후 버전에서는 요소 단위 협업 편집을 검토할 수 있다.

## 11. Monitoring View 요구사항

### 11.1 기본 구성

- [필수] monitoring view 는 editor 와 동일한 layout 을 기반으로 runtime overlay 를 표시해야 한다.
- [필수] monitoring view 는 기본적으로 읽기 전용이어야 한다.
- [필수] 화면 하단 또는 동등한 위치에 event panel 을 제공해야 한다.
- [필수] 사용자는 monitoring view 에 여러 명이 동시에 접속할 수 있어야 한다.

### 11.2 runtime overlay

- [필수] latest state 에 따라 node 와 edge 의 색상, 배지, 텍스트, 강조 효과를 갱신할 수 있어야 한다.
- [필수] stale 상태는 일반 정상 상태와 시각적으로 명확히 구분되어야 한다.
- [필수] `MonitoringAgent` 는 heartbeat, backend connection status, outbox queue depth 등 self-state 를 시각적으로 보여줄 수 있어야 한다.
- [필수] group abstraction 객체는 `expected_count` 와 `actual_count` 를 함께 보여줄 수 있어야 한다.
- [필수] 사용자는 group 객체에서 필요할 경우 개별 instance summary 를 펼쳐 볼 수 있어야 한다.
- [선택] 고급 애니메이션과 세밀한 마이크로 인터랙션은 후속 범위로 둔다.

### 11.3 event panel

- [필수] event panel 은 기본적으로 backend 가 제공하는 그룹화된 이벤트 요약을 사용해야 한다.
- [필수] 각 그룹화 이벤트 항목은 최소한 첫 발생 시각, 마지막 발생 시각, 반복 횟수, 최신 심각도, 대상 식별자 정보를 보여줄 수 있어야 한다.
- [필수] event panel 과 상세 이벤트 조회 화면은 필요한 경우 밀리초(1/1000초) 단위 시간 표시를 지원해야 한다.
- [필수] 사용자는 특정 그룹화 이벤트를 선택해 해당 그룹에 속한 저수준 이벤트 원본을 추가 조회할 수 있어야 한다.
- [필수] event panel 은 최소한 severity, 시간 범위, 대상, event type 으로 필터링할 수 있어야 한다.
- [필수] event storm 상황에서도 panel 이 원본 이벤트 단위로 과도하게 갱신되지 않도록 그룹화 이벤트 우선 갱신 정책을 따라야 한다.

## 12. 실시간 갱신 요구사항

### 12.1 기본 정책

- [필수] frontend 는 실시간 갱신을 위해 `SSE 우선 + 주기적 snapshot polling 보정` 구조를 사용해야 한다.
- [필수] SSE 연결이 끊기면 polling fallback 으로 전환할 수 있어야 한다.
- [필수] SSE 복구 후에는 snapshot 을 다시 받아 drift 를 보정해야 한다.
- [필수] frontend 는 backend heartbeat 또는 마지막 수신 시각을 기준으로 현재 데이터 신선도를 표시해야 한다.

### 12.2 stale 와 연결 상태 표시

- [필수] backend 연결 또는 실시간 스트림이 비정상일 경우 화면 상단 또는 동등한 위치에 연결 상태를 표시해야 한다.
- [필수] 일정 시간 동안 새 state/event 가 없으면 monitoring data 가 stale 할 수 있음을 사용자에게 알려야 한다.
- [필수] polling 만으로 임시 전환된 상태인지, 실시간 스트림이 정상인지 사용자가 구분할 수 있어야 한다.

## 13. 관리자 화면 요구사항

### 13.1 메타모델 조회 및 관리

- [필수] 관리자는 semantic type, property definition, association definition, containment rule, notation definition 을 조회할 수 있어야 한다.
- [필수] 관리자는 metamodel version 의 상태가 `draft`, `published`, `deprecated` 중 무엇인지 확인할 수 있어야 한다.
- [필수] MVP 에서는 메타모델 변경 UI 를 최소 범위로 두더라도, 조회 화면은 구조적으로 명확해야 한다.

### 13.2 세션과 운영 상태

- [필수] 관리자는 현재 접속 사용자, 열린 view, 편집/관제 모드, 마지막 활동 시각을 볼 수 있어야 한다.
- [필수] 관리자는 backend 상태, agent 연결 상태, 실시간 연결 수 등 운영에 필요한 요약 정보를 볼 수 있어야 한다.

### 13.3 운영 로그와 debug payload 조회

- [필수] 관리자는 최근 1주일 범위의 구조화된 운영 로그를 조회할 수 있어야 한다.
- [필수] 로그는 시간, severity, component, 관련 객체 기준으로 필터링할 수 있어야 한다.
- [필수] backend debug mode 가 활성화된 경우, 관리자는 debug payload 조회 화면에 접근할 수 있어야 한다.
- [필수] debug payload 조회 화면은 `channel`, `direction`, `endpoint_or_topic`, `agent_id`, `user_id`, `session_id`, `trace_id`, `status_code`, 시간 범위 기준 필터를 제공해야 한다.
- [필수] debug payload 화면은 민감 정보가 마스킹된 JSON 만 표시해야 한다.
- [필수] debug payload 와 운영 로그의 시간값은 밀리초(1/1000초) 단위까지 확인 가능해야 한다.
- [필수] debug payload 조회는 일반 운영 로그 조회와 분리된 화면 또는 탭으로 제공해야 한다.

## 14. 오류 처리와 사용자 피드백 요구사항

- [필수] 저장 실패, 권한 부족, lock 충돌, metamodel mismatch, 네트워크 단절에 대해 사용자에게 명확한 오류 메시지를 제공해야 한다.
- [필수] backend 검증 오류는 가능한 한 해당 요소와 속성 수준까지 연결해 표시해야 한다.
- [필수] unsupported notation, unsupported property type 이 발견되면 읽기 전용 또는 경고 표시로 안전하게 처리해야 한다.
- [필수] 사용자는 저장되지 않은 변경이 있는 상태를 명확히 볼 수 있어야 한다.

## 15. Debug 과 진단 요구사항

- [필수] frontend 는 debug payload 저장 기능 자체를 수행하지 않더라도, backend debug mode 와 연계된 조회 기능을 제공해야 한다.
- [필수] frontend 는 SSE 연결 상태, 마지막 snapshot 시각, 마지막 event 수신 시각을 개발자 또는 관리자에게 확인 가능한 형태로 제공할 수 있어야 한다.
- [필수] 문제 재현 시 특정 화면 동작이 어떤 API 호출과 대응되는지 추적 가능한 최소한의 trace 정보 표시를 고려해야 한다.
- [선택] 개발자용 진단 패널은 후속 단계에서 확장할 수 있다.

## 16. 테스트 요구사항

- [필수] 주요 화면 진입, 권한 제어, 목록 조회, editor 저장, monitoring 표시, 관리자 조회에 대한 통합 테스트 시나리오가 필요하다.
- [필수] containment 제약, `monitors` association 제약, lock 충돌, view 복사와 diagram 복사 구분에 대한 수동 또는 자동 테스트 시나리오가 필요하다.
- [필수] group abstraction 렌더링, stale 표시, MonitoringAgent 상태 표시, grouped event drill-down 에 대한 확인 시나리오가 필요하다.
- [필수] 실시간 갱신 경로에서는 `SSE 정상`, `SSE 단절 후 polling fallback`, `복구 후 snapshot 재동기화` 시나리오를 검증해야 한다.
- [필수] debug payload 조회 화면은 권한 제한, 마스킹 표시, trace_id 기반 필터링을 검증해야 한다.
- [선택] 이후 버전에서는 브라우저 자동화 테스트 도구를 추가할 수 있다.

## 17. 일관성 검토와 추가 상세화 필요 항목

### 17.1 현재 문서 간 일관성 검토

- [검토] 현재까지의 backend, agent, frontend 요구사항 사이에 직접적인 구조 모순은 크지 않다.
- [검토] `MonitoringAgent` 를 별도 semantic type 으로 두고 `monitors` association 으로 연결하는 방향은 세 문서에서 일관된다.
- [검토] `view 복사` 와 `diagram 복사` 를 분리하는 정책도 backend 저장 구조와 일치한다.
- [검토] grouped event 우선 표시, low-level event drill-down 정책은 backend event storm 완화 정책과 일치한다.
- [검토] `target_id`, group abstraction, latest state 기반 overlay 정책은 agent 와 backend 의 payload 구조와 충돌하지 않는다.

### 17.2 더 상세하게 못 박아야 하는 항목

- [필수] `cardinality_scope=per_member/group_total` 의 화면 표현 규칙을 더 구체적으로 정의해야 한다.
- [필수] group 객체를 펼쳤을 때 개별 instance summary 를 어느 수준까지 보여줄지 정해야 한다.
- [필수] `monitors` association 의 시각 스타일과 editor/monitoring 화면에서의 표시 여부를 더 명확히 해야 한다.
- [필수] metamodel version mismatch 또는 unsupported notation 발생 시 read-only 전환 규칙을 더 상세히 정의해야 한다.
- [필수] edit lock 만료 시간과 화면 갱신 주기를 구체화해야 한다.
- [필수] grouped event panel 의 기본 정렬 기준과 필터 기본값을 확정해야 한다.
- [필수] debug payload 조회 화면에서 trace_id 를 어떤 단위로 노출할지 결정해야 한다.

### 17.3 주요 리스크

- [리스크] SVG 기반 canvas 는 대형 다이어그램에서 성능 저하가 생길 수 있다.
- [리스크] 동적 notation 확장이 frontend 가 지원하는 SVG primitive 범위를 넘으면 렌더 불일치가 발생할 수 있다.
- [리스크] `per_member` 와 `group_total` 의미가 화면에서 충분히 설명되지 않으면 운영자가 실제 인스턴스 개수를 오해할 수 있다.
- [리스크] SSE 와 polling fallback 전환 로직이 불안정하면 stale 데이터가 실제 장애처럼 보일 수 있다.
- [리스크] debug payload 조회 기능은 민감 정보 노출 위험이 있으므로 관리자 권한과 마스킹 정책이 엄격해야 한다.
- [리스크] grouped event 중심 화면이 low-level event 접근성을 지나치게 떨어뜨리면 원인 분석 시간이 늘어날 수 있다.

## 18. 다음 설계 단계 입력 항목

- [필수] 화면 설계 초안에는 workspace 목록, editor, monitoring, admin, debug payload 화면이 포함되어야 한다.
- [필수] SVG canvas interaction 설계에는 palette drag, containment 검증, edge 생성, layout 저장, group 표현 규칙이 포함되어야 한다.
- [필수] frontend API 연동 명세에는 notation registry 조회, model/view CRUD, latest state 조회, grouped event 조회, low-level event drill-down, 세션 조회, 로그 조회, debug payload 조회가 포함되어야 한다.
- [필수] 실시간 연동 설계에는 SSE 이벤트 종류, snapshot polling 주기, reconnect 정책, stale 표시 정책이 포함되어야 한다.

## 19. 요약

- 본 frontend 는 메타모델 제약을 따르는 SVG 기반 architecture editor 와 runtime monitoring view 를 중심으로 설계해야 한다.
- containment, group abstraction, MonitoringAgent, grouped event, debug payload 조회, edit lock, SSE + polling fallback 은 MVP 에서 반드시 반영되어야 한다.
- 현재 요구사항 간 큰 모순은 없지만, group 표현 규칙, metamodel mismatch 처리, monitors 시각 스타일, lock 만료 정책은 다음 설계 단계에서 더 구체화해야 한다.
- 본 문서는 이후 화면 설계, API 연동 설계, SVG interaction 설계의 기준 문서로 사용한다.
