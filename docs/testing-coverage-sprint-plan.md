# Software Architecture Runtime Monitoring System

## Testing Coverage Sprint Plan

버전: Draft 0.2  
작성일: 2026-05-06

## 1. 목표

- 전체 statement(line) coverage를 장기적으로 `98% 이상`까지 끌어올린다.
- 전체 branch coverage를 장기적으로 `80% 이상`까지 끌어올린다.
- coverage 향상 작업은 기능 개발과 분리된 독립 sprint로도 수행할 수 있게 정리한다.

## 2. 현재 기준

최초 sprint 착수 시점 기준:

- 전체 회귀: `275 passed, 4 skipped`
- line coverage: `86.67%`
- branch coverage: `66.65%`
- 리포트: [coverage.xml](C:/2604_swacan_auto/test_artifacts/coverage.xml)

## 3. 기본 전략

### 3.1 한 가지 기법만으로는 부족하다

현재 프로젝트는 `boundary value analysis`를 기본 테스트 작성 원칙으로 사용하고 있다.  
하지만 branch coverage를 실제로 끌어올리려면 아래 기법을 함께 써야 한다.

- boundary value analysis
- equivalence partitioning
- decision table testing
- negative path testing
- lifecycle / permission matrix testing

### 3.2 작은 파일부터 먼저 닫는다

coverage 격차가 큰 대형 API 파일을 바로 공략하기보다, 다음처럼 작은 파일부터 닫는 편이 효율적이다.

- `agent/main.py`
- `agent/config.py`
- `agent/selector.py`
- `app/alert_archive.py`
- `app/metamodel_audit.py`

이 파일들은 테스트 몇 개만 추가해도 line/branch 개선 효과가 크다.

### 3.3 큰 API는 상태 조합으로 공략한다

다음 파일들은 happy path 추가보다 `상태 조합` 테스트가 더 중요하다.

- `app/admin_api.py`
- `app/views_api.py`
- `app/editor_api.py`
- `app/view_version_editor_api.py`

권장 축:

- draft / published / deprecated
- valid / warning / error
- enabled / disabled
- permission allow / deny
- selector / signal / condition mode 조합

즉, 이 구간은 decision table을 먼저 만들고 API 테스트로 옮기는 방식이 적절하다.

## 4. 우선순위 hotspot

coverage 기준으로 우선순위가 높은 파일은 다음과 같다.

1. [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py)
2. [views_api.py](C:/2604_swacan_auto/app/views_api.py)
3. [editor_api.py](C:/2604_swacan_auto/app/editor_api.py)
4. [main.py](C:/2604_swacan_auto/agent/main.py)
5. [selector.py](C:/2604_swacan_auto/agent/selector.py)
6. [config.py](C:/2604_swacan_auto/agent/config.py)
7. [admin_api.py](C:/2604_swacan_auto/app/admin_api.py)
8. [alert_archive.py](C:/2604_swacan_auto/app/alert_archive.py)
9. [metamodel_audit.py](C:/2604_swacan_auto/app/metamodel_audit.py)

## 5. Small Coverage Sprint #1

첫 번째 sprint는 `작고 branch 개선 효과가 높은 agent 계층`에 집중한다.

대상:

- [main.py](C:/2604_swacan_auto/agent/main.py)
- [config.py](C:/2604_swacan_auto/agent/config.py)
- [selector.py](C:/2604_swacan_auto/agent/selector.py)

테스트 방향:

- `agent/main.py`
  - invalid config exit path
  - `--cycles` 분기
  - service summary fallback path
  - `__main__` entrypoint smoke
- `agent/config.py`
  - missing file
  - invalid storage section shape
  - invalid target mode / pid / selector text
  - invalid debug_mode type
  - absolute storage path / env expansion
- `agent/selector.py`
  - missing proc root
  - invalid pid dir / missing `comm`
  - executable path filter
  - `cmdline` required but file missing
  - helper branch (`_read_cmdline`, `_read_exe_path`)

## 6. 테스트 작성 규칙

- 새 테스트는 가능한 한 기존 테스트 파일에 붙여서 맥락을 유지한다.
- 케이스 이름은 무엇을 허용하는지와 무엇을 차단하는지가 드러나야 한다.
- branch를 올리기 위한 테스트라면 과한 mock보다 실제 입력 조합을 우선한다.
- 단순 helper는 direct unit test를 허용한다.
- sprint가 끝나면 가급적 전체 `pytest`와 coverage를 다시 닫는다.

## 7. 리팩터링 원칙

coverage가 낮다고 무조건 테스트만 추가하지는 않는다.

다음 조건이면 작은 refactoring을 먼저 검토한다.

- validation 로직이 한 함수에 과도하게 몰려 있음
- permission / lifecycle matrix가 중복됨
- response shaping과 domain logic이 강하게 결합됨
- branch는 많지만 독립 테스트가 어려움

이 경우 helper/service로 분리한 뒤 테스트를 붙이는 편이 더 효율적이다.

## 8. 목표 관리 방식

coverage 목표는 한 번에 강제하지 않고 단계적으로 관리한다.

- 1차 목표: branch `70%+`
- 2차 목표: branch `75%+`
- 3차 목표: branch `80%+`

line coverage도 같은 방식으로 관리한다.

- 1차 목표: line `90%+`
- 2차 목표: line `95%+`
- 3차 목표: line `98%+`

## 9. 결론

현재 coverage 목표가 부족한 이유는 테스트 수가 절대적으로 적어서라기보다 `branch를 겨냥한 설계된 테스트`가 부족하기 때문이다.  
따라서 다음 반복은 `boundary value analysis + decision table + negative path`를 함께 사용하고, 작은 hotspot부터 닫는 coverage sprint 방식으로 진행하는 것이 가장 효율적이다.

## 10. Sprint #1 결과

첫 번째 작은 coverage sprint에서는 다음 파일을 우선 보강했다.

- [config.py](C:/2604_swacan_auto/agent/config.py)
- [selector.py](C:/2604_swacan_auto/agent/selector.py)
- [main.py](C:/2604_swacan_auto/agent/main.py)

보강한 테스트 축:

- invalid / missing config branch
- storage / target validation negative path
- proc selector helper branch
- executable path / missing cmdline branch
- CLI `--cycles` / invalid config / `__main__` entrypoint branch
- summary fallback branch

결과:

- 전체 회귀: `298 passed, 4 skipped`
- line coverage: `87.40%` (`+0.73%p`)
- branch coverage: `67.79%` (`+1.14%p`)

관찰:

- 작은 agent 계층만 보강해도 branch coverage가 꾸준히 올라간다.
- 다만 전체 branch `80%`까지 가려면 다음 sprint부터는 큰 API 파일에 decision-table 기반 테스트를 붙여야 한다.
- 다음 우선순위는 [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py), [views_api.py](C:/2604_swacan_auto/app/views_api.py), [editor_api.py](C:/2604_swacan_auto/app/editor_api.py) 순서가 적절하다.

## 11. Sprint #2 결과

두 번째 작은 coverage sprint에서는 helper 성격이 강한 app 모듈을 우선 보강했다.

- [alert_archive.py](C:/2604_swacan_auto/app/alert_archive.py)
- [metamodel_audit.py](C:/2604_swacan_auto/app/metamodel_audit.py)

보강한 테스트 축:

- invalid enum / invalid action branch
- archive insert happy path
- metadata JSON valid / invalid serialization
- audit actor resolution (`g.user`)
- `details_json` 유무에 따른 serialization branch

결과:

- 전체 회귀: `305 passed, 4 skipped`
- line coverage: `87.51%` (`+0.11%p`)
- branch coverage: `68.01%` (`+0.22%p`)

관찰:

- 작은 helper 모듈은 절대 상승폭은 크지 않지만, 저비용으로 branch를 꾸준히 올리는 데 유리하다.
- 직접 API를 치기 전에 공통 helper와 serializer를 먼저 닫아두면 이후 대형 API 테스트의 부담이 줄어든다.

## 12. Sprint #3 결과

세 번째 작은 coverage sprint에서는 schema / naming helper 성격의 DB 유틸리티를 보강했다.

- [db.py](C:/2604_swacan_auto/app/db.py)

보강한 테스트 축:

- `rule_key` / `display_name` helper normalization
- `alert_rules` 테이블 부재 branch
- lifecycle schema backfill branch
- invalid legacy `rule_key` fallback branch

결과:

- 전체 회귀: `309 passed, 4 skipped`
- line coverage: `87.67%` (`+0.16%p`)
- branch coverage: `68.28%` (`+0.27%p`)

관찰:

- 작은 helper / schema 계층은 무리 없이 조금씩 coverage를 올리는 데 적합하다.
- 이제부터 branch `80%`를 향해 의미 있게 올라가려면, 남은 큰 gap은 결국 [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py), [views_api.py](C:/2604_swacan_auto/app/views_api.py), [editor_api.py](C:/2604_swacan_auto/app/editor_api.py) 같은 큰 API 계층에서 메워야 한다.

## 13. Sprint #4 결과

네 번째 coverage sprint에서는 큰 API 파일 중 [views_api.py](C:/2604_swacan_auto/app/views_api.py)를 집중적으로 보강했다.

보강한 테스트 축:

- view ownership / not-found permission branch
- create / update endpoint validation branch
- serializer optional field branch
- `get_monitor_target_rows` fallback branch
- `detect_view_runtime_changes` initial / unchanged branch
- `validate_nodes` / `validate_edges` decision-table branch
- SSE payload formatting helper

결과:

- 전체 회귀: `321 passed, 4 skipped`
- line coverage: `88.47%` (`+0.80%p`)
- branch coverage: `70.40%` (`+2.12%p`)

관찰:

- 이번 sprint로 branch `70%+` 1차 목표를 넘겼다.
- 큰 API를 직접 공략하더라도, endpoint happy path보다 helper / validator / permission matrix를 decision-table로 메우는 방식이 훨씬 효율적이었다.
- 다음 우선순위는 [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py), 그 다음 [editor_api.py](C:/2604_swacan_auto/app/editor_api.py)가 자연스럽다.

## 14. Sprint #5 Result

This sprint focused on [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py) with the same limited coverage style used in Sprint #4.

Added tests in:

- [test_view_version_editor_api.py](C:/2604_swacan_auto/tests/test_view_version_editor_api.py)
- [test_view_version_editor_api_unit.py](C:/2604_swacan_auto/tests/test_view_version_editor_api_unit.py)

Main branch targets:

- monitored-object current-node ownership validation
- edge update and delete branches
- node delete not-found branch
- replace-version negative branches
- helper functions such as `slugify`, `make_element_key`, `parse_*`
- node/edge validator decision-table paths

Results:

- full regression: `330 passed, 4 skipped`
- line coverage: `90.10%`
- branch coverage: `72.85%`

Observations:

- [view_version_editor_api.py](C:/2604_swacan_auto/app/view_version_editor_api.py) improved to `84%` total coverage in the report.
- The next natural target remains [editor_api.py](C:/2604_swacan_auto/app/editor_api.py), especially helper, permission, and validation matrix branches.

## 15. Sprint #6 Result

This sprint focused on [editor_api.py](C:/2604_swacan_auto/app/editor_api.py) using the same low-risk coverage style as the previous API sprints.

Added tests in:

- [test_editor_unit_api.py](C:/2604_swacan_auto/tests/test_editor_unit_api.py)
- [test_editor_api_unit.py](C:/2604_swacan_auto/tests/test_editor_api_unit.py)

Main branch targets:

- view ownership `not_found` / `forbidden` route branches
- update unknown-field branches for node and edge patch endpoints
- delete not-found branches for node and edge delete endpoints
- serializer optional payload branches
- `next_layer_order`, `resolve_layer_order`, `require_revision` helper branches
- `validate_nodes` and `validate_edges` decision-table branches

Results:

- full regression: `340 passed, 4 skipped`
- line coverage: `90.65%`
- branch coverage: `74.43%`

Observations:

- [editor_api.py](C:/2604_swacan_auto/app/editor_api.py) improved from `76%` to `89%` total coverage in the report.
- The next high-value coverage target is likely [admin_api.py](C:/2604_swacan_auto/app/admin_api.py) or a focused slice of [agent_api.py](C:/2604_swacan_auto/app/agent_api.py), depending on whether we prefer API branch gain or smaller-module cleanup next.
