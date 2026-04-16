## Metamodel Editor Backlog

버전: Draft 0.1

목적: `Metamodel Editor`의 남은 구현 항목을 중요도와 영향도 기준으로 정리하고, 지금 바로 구현할 항목과 후속 backlog를 분리한다.

### 1. 현재 우선 구현 대상

1. 메타모델 변경 영향도 / diff 보기
- draft version이 baseline version 대비 무엇이 바뀌었는지 보여준다.
- `semantic type`, `property`, `containment`, `association`, `notation`의 `added / changed / removed`를 요약한다.
- publish 전에 운영자가 가장 먼저 판단해야 하는 정보라 우선순위가 가장 높다.

2. Architecture Editor 연동 강화
- draft metamodel에서 바뀐 `semantic type / notation / containment / association`이 `Architecture Editor`의 palette, 생성 가능 항목, 배치 제약에 더 직접적으로 반영되게 한다.
- 메타모델 편집이 실제 아키텍처 편집 경험으로 이어지는 핵심 연결 지점이다.

3. Metamodel Canvas 직접 편집 고도화
- `Metamodel Canvas`에서 semantic type, containment, association을 더 직관적으로 생성/수정한다.
- hover/preview, quick-create, quick-edit, 배치/정렬, quick-save를 editor다운 수준으로 보강한다.

### 2. 이번 단계 이후 backlog

4. publish 전 validation 확장
- orphan property
- inactive type 참조
- palette group 누락
- notation/render schema 필수값 누락
- editor/runtime 충돌 가능 규칙 추가 검증

5. 삭제 / 비활성화 / 복제 흐름
- semantic type/property/containment/association/notation 삭제
- soft disable
- clone
- replace

6. 메타모델 버전 운영 UX
- version 상태, 승인자, publish 시각, validation 결과, 변경 요약을 더 명확히 보여준다.

7. 용어 / 메시지 정리
- `Monitoring View`, `Architecture Editor`, `Metamodel Editor` 기준으로 화면/버튼/메시지 용어를 더 일관되게 맞춘다.

8. 권한 / 감사 로그
- 누가 draft를 수정했는지
- 누가 publish 했는지
- 누가 active 운영 화면에 반영했는지

### 3. 현재 판단

- 지금은 `1, 2, 3`을 실제 구현 대상으로 본다.
- `4` 이후는 제품 완성도를 올리는 backlog로 유지한다.
- 각 구현 단계에서는 기능 추가 전에 작은 구조 점검(refactoring 필요 여부 확인)을 먼저 수행한다.
- 테스트는 계속 `boundary value analysis` 기준을 우선 적용한다.
