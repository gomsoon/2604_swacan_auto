from __future__ import annotations

import json
import re
from datetime import datetime
from urllib import request

from playwright.sync_api import Page, expect

from app.db import get_db
from app.ingest_worker import process_pending_ingest


AGENT_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "X-Agent-Id": "agent_local",
    "X-Agent-Token": "dev-agent-token",
}


def browser_login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login")
    page.locator("#username").fill("admin")
    page.locator("#password").fill("admin123!")
    page.locator("#login-form button[type='submit']").click()
    page.wait_for_url(f"{base_url}/views")
    expect(page.get_by_role("heading", name="뷰 목록")).to_be_visible()


def post_ingest(base_url: str, payload: dict) -> None:
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url}/api/agents/ingest",
        data=payload_bytes,
        headers=AGENT_HEADERS,
        method="POST",
    )
    with request.urlopen(req) as response:  # noqa: S310
        assert response.status == 202


def test_playwright_minimal_e2e(page: Page, live_server) -> None:
    base_url, seeded_app = live_server
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-12T20:10:05.000+09:00")

    browser_login(page, base_url)

    page.get_by_label("이름").fill("Playwright Demo View")
    page.get_by_label("설명").fill("브라우저 기반 최소 E2E 검증")
    page.get_by_role("button", name="생성").click()

    page.wait_for_url(re.compile(r".*/views/\d+/edit$"))
    expect(page.get_by_role("button", name="물리 서버 추가")).to_be_visible()

    page.get_by_role("button", name="물리 서버 추가").click()
    server_shape = page.locator('g.diagram-node[data-node-type="PhysicalServer"] .node-shape').first
    expect(server_shape).to_be_visible()
    expect(page.locator('g.diagram-node[data-node-type="PhysicalServer"]')).to_have_count(1)

    server_shape.click(force=True)
    page.get_by_role("button", name="프로세스 추가").click()
    expect(page.locator('g.diagram-node[data-node-type="SoftwareProcess"]')).to_have_count(1)

    server_shape.click(force=True)
    page.get_by_role("button", name="에이전트 추가").click()
    expect(page.locator('g.diagram-node[data-node-type="MonitoringAgent"]')).to_have_count(1)
    expect(page.locator('g.diagram-node[data-notation-code="agent.rounded_rect.double_border"] .node-double-border')).to_have_count(1)

    view_id = int(re.search(r"/views/(\d+)/edit$", page.url).group(1))

    process_shape = page.locator('g.diagram-node[data-node-type="SoftwareProcess"] .node-shape').first
    agent_shape = page.locator('g.diagram-node[data-node-type="MonitoringAgent"] .node-shape').first

    process_shape.click(force=True)
    process_target_id = page.locator("#node-target-id").input_value()
    page.locator("#node-display-name").fill("Worker Alpha")
    page.get_by_role("button", name="선택 항목 저장").click()
    expect(page.locator('text="Worker Alpha"')).to_be_visible()

    expect(page.get_by_role("button", name="통신선 시작")).to_be_visible()
    page.get_by_role("button", name="통신선 시작").click()
    agent_shape.click(force=True)
    expect(page.locator("path.diagram-edge")).to_have_count(1)
    expect(page.locator("#editor-version-status-label")).to_contain_text("draft")

    page.get_by_role("button", name="Draft 발행").click()
    expect(page.locator("#editor-version-status-label")).to_contain_text("published")
    expect(page.locator("#editor-version-code-label")).to_contain_text("published")

    page.get_by_role("button", name="운영 반영").click()
    expect(page.locator("#editor-version-status-label")).to_contain_text("active")
    expect(page.locator("#editor-version-code-label")).to_contain_text("active")

    with seeded_app.app_context():
        db_conn = get_db()
        draft_row = db_conn.execute(
            """
            SELECT id
            FROM view_versions
            WHERE view_id = ? AND status = 'active'
            ORDER BY activated_at DESC, version_no DESC, id DESC
            LIMIT 1
            """,
            (view_id,),
        ).fetchone()
        assert draft_row is not None
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET display_name = ?, target_id = ?
            WHERE view_version_id = ? AND node_type = 'PhysicalServer'
            """,
            ("Host Alpha", "agent_local:host", draft_row["id"]),
        )
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET display_name = ?, target_id = ?
            WHERE view_version_id = ? AND node_type = 'MonitoringAgent'
            """,
            ("Agent Alpha", "agent_local", draft_row["id"]),
        )
        process_row = db_conn.execute(
            """
            SELECT id
            FROM view_version_nodes
            WHERE view_version_id = ? AND node_type = 'SoftwareProcess'
            LIMIT 1
            """,
            (draft_row["id"],),
        ).fetchone()
        db_conn.execute(
            "DELETE FROM node_bindings WHERE view_version_node_id = ?",
            (process_row["id"],),
        )
        db_conn.execute(
            """
            INSERT INTO node_bindings (
                view_version_node_id, monitored_object_id, binding_role, created_at, updated_at
            ) VALUES (?, ?, 'primary', ?, ?)
            """,
            (
                process_row["id"],
                1302,
                "2026-04-12T20:09:58.000+09:00",
                "2026-04-12T20:09:58.000+09:00",
            ),
        )
        db_conn.commit()

    post_ingest(
        base_url,
        {
            "agent_id": "agent_local",
            "boot_id": "boot-playwright",
            "seq_start": 1,
            "seq_end": 5,
            "items": [
                {
                    "seq": 1,
                    "payload_type": "agent_state",
                    "occurred_at": "2026-04-12T20:09:59.000+09:00",
                    "target_id": "agent_local",
                        "payload": {
                            "heartbeat_time": "2026-04-12T20:09:59.000+09:00",
                            "backend_connection_status": "connected",
                            "outbox_queue_depth": 0,
                            "last_ack_seq": 5,
                        },
                    },
                {
                    "seq": 2,
                    "payload_type": "host_snapshot",
                    "occurred_at": "2026-04-12T20:09:59.000+09:00",
                    "target_id": "agent_local:host",
                    "payload": {
                        "hostname": "host-alpha",
                        "cpu_usage": 18.4,
                        "loadavg_1": 0.24,
                        "loadavg_5": 0.31,
                        "loadavg_15": 0.4,
                        "memory_total": 16777216,
                        "memory_available": 6291456,
                        "memory_used": 10485760,
                    },
                },
                    {
                        "seq": 3,
                        "payload_type": "process_snapshot",
                        "occurred_at": "2026-04-12T20:10:00.000+09:00",
                        "target_id": "app_main",
                        "payload": {
                            "state": "running",
                            "severity": "info",
                        "cpu_usage": 12.5,
                        "memory_rss": 20480,
                    },
                },
                    {
                        "seq": 4,
                        "payload_type": "process_event",
                        "occurred_at": "2026-04-12T20:10:01.000+09:00",
                        "target_id": "app_main",
                        "payload": {
                            "event_type": "process_started",
                        "severity": "info",
                        "message": "Playwright process started",
                    },
                },
                    {
                        "seq": 5,
                        "payload_type": "process_event",
                        "occurred_at": "2026-04-12T20:10:02.000+09:00",
                        "target_id": "app_main",
                        "payload": {
                        "event_type": "process_restarted",
                        "severity": "warning",
                        "message": "Playwright process restarted",
                    },
                },
            ],
        },
    )

    with seeded_app.app_context():
        result = process_pending_ingest(limit=20)
        assert result["processed_batches"] == 1
        assert result["failed_batches"] == 0

    page.get_by_role("link", name="모니터링 보기").click()
    page.wait_for_url(re.compile(r".*/views/\d+/monitor$"))
    expect(page.get_by_role("heading", name="최근 이벤트")).to_be_visible()

    monitor_server_node = page.locator('g.diagram-node[data-node-type="PhysicalServer"]').first
    monitor_agent_shape = page.locator('g.diagram-node[data-node-type="MonitoringAgent"] .node-shape').first
    monitor_process_shape = page.locator('g.diagram-node[data-node-type="SoftwareProcess"] .node-shape').first
    expect(page.locator('g.diagram-node[data-notation-code="server.physical.rect"]')).to_have_count(1)
    expect(page.locator('g.diagram-node[data-notation-code="agent.rounded_rect.double_border"] .node-double-border')).to_have_count(1)

    expect(page.locator("#monitor-agent-summary")).to_contain_text("Agent Alpha")
    expect(page.locator("#monitor-agent-summary")).to_contain_text("connected")
    expect(page.locator("#monitor-agent-summary")).to_contain_text("outbox 0")
    expect(page.locator("#monitor-agent-summary")).to_contain_text("ack 5")

    monitor_server_node.click(force=True, position={"x": 24, "y": 24})
    expect(page.locator("#monitor-selection-summary")).to_contain_text("Host Alpha")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("호스트명")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("CPU 사용률")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("Load Average")

    monitor_agent_shape.click(force=True)
    expect(page.locator("#monitor-selection-summary")).to_contain_text("Agent Alpha")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("백엔드 연결")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("connected")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("last ack seq")

    monitor_process_shape.click(force=True)
    expect(page.locator("#monitor-selection-summary")).to_contain_text("Worker Alpha")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("프로세스 상태")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("최근 이벤트")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("process_restarted")
    expect(page.locator("#events-list")).to_contain_text("process_restarted")
    expect(page.locator("#events-list")).to_contain_text("Playwright process restarted")
    page.locator("#events-list .event-summary-item", has_text="process_restarted").click()
    expect(page.locator("#event-detail-panel")).to_contain_text("process_restarted")
    expect(page.locator("#event-detail-panel")).to_contain_text("Playwright process restarted")
    expect(page.locator("#event-detail-panel .raw-event-detail-panel")).to_contain_text("Payload JSON")
    expect(page.locator("#event-detail-panel .raw-event-detail-panel")).to_contain_text('"event_type": "process_restarted"')


def test_playwright_admin_page(page: Page, live_server) -> None:
    base_url, seeded_app = live_server

    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO alert_instances (
                monitored_object_id, alert_code, source_rule_id, severity, status, first_occurred_at,
                last_occurred_at, repeat_count, latest_message, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1303,
                "agent.warning",
                1502,
                "warning",
                "open",
                "2026-04-12T21:00:00.000+09:00",
                "2026-04-12T21:00:00.000+09:00",
                1,
                "Agent queue backlog",
                json.dumps({"metric_key": "outbox_queue_depth"}),
                "2026-04-12T21:00:00.000+09:00",
                "2026-04-12T21:00:00.000+09:00",
            ),
        )
        db_conn.commit()

    browser_login(page, base_url)
    page.goto(f"{base_url}/admin")

    expect(page.get_by_role("heading", name="기본 관리자 화면")).to_be_visible()
    expect(page.get_by_role("heading", name="시스템 요약", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="메타모델 버전")).to_be_visible()
    expect(page.get_by_role("heading", name="Alert Rule", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Latest State")).to_be_visible()
    expect(page.get_by_role("heading", name="Cleanup 기록")).to_be_visible()
    expect(page.locator("#admin-summary-cards")).to_contain_text("사용자")
    expect(page.locator("#admin-metamodel-versions-list")).to_contain_text("seed-v1")
    expect(page.locator("#admin-alert-rules-list")).to_contain_text("cpu_usage")

    page.locator("#metamodel-version-code").fill("core-v2-ui-draft")
    page.locator("#metamodel-version-description").fill("Playwright draft create")
    page.get_by_role("button", name="Draft 생성").click()

    createdVersion = page.locator(".admin-item", has_text="core-v2-ui-draft").first
    expect(createdVersion).to_contain_text("draft")
    expect(page.locator("#metamodel-draft-version-select")).to_contain_text("core / core-v2-ui-draft")

    page.locator("#metamodel-semantic-type-code").fill("WorkerPool")
    page.locator("#metamodel-semantic-type-display-name").fill("Worker Pool")
    page.locator("#metamodel-semantic-type-kind").select_option("container")
    page.locator("#metamodel-semantic-type-runtime-kind").fill("process-group")
    page.locator("#metamodel-semantic-type-description").fill("Playwright semantic type create")
    page.locator("#metamodel-semantic-type-groupable").check()
    page.locator("#save-metamodel-semantic-type-button").click()

    createdSemanticType = page.locator("#admin-metamodel-semantic-types-list .admin-item", has_text="Worker Pool").first
    expect(createdSemanticType).to_contain_text("WorkerPool")
    expect(createdSemanticType).to_contain_text("container")

    createdSemanticType.get_by_role("button", name="수정").click()
    expect(page.locator("#metamodel-semantic-type-form-mode")).to_contain_text("edit")
    page.locator("#metamodel-semantic-type-display-name").fill("Worker Pool Updated")
    page.locator("#metamodel-semantic-type-runtime-binding").uncheck()
    page.locator("#save-metamodel-semantic-type-button").click()

    expect(page.locator("#admin-metamodel-semantic-types-list .admin-item", has_text="Worker Pool Updated").first).to_contain_text("no-binding")

    page.locator("#metamodel-property-semantic-type-id").select_option(label="Worker Pool Updated (WorkerPool)")
    page.locator("#metamodel-property-code").fill("worker_count")
    page.locator("#metamodel-property-display-name").fill("Worker Count")
    page.locator("#metamodel-property-value-type").select_option("integer")
    page.locator("#metamodel-property-unit").fill("count")
    page.locator("#metamodel-property-sort-order").fill("30")
    page.locator("#metamodel-property-default-value-json").fill("4")
    page.locator("#metamodel-property-description").fill("Playwright property definition create")
    page.locator("#save-metamodel-property-button").click()

    createdProperty = page.locator("#admin-metamodel-properties-list .admin-item", has_text="Worker Count").first
    expect(createdProperty).to_contain_text("worker_count")
    expect(createdProperty).to_contain_text("integer")

    createdProperty.get_by_role("button", name="수정").click()
    expect(page.locator("#metamodel-property-form-mode")).to_contain_text("edit")
    page.locator("#metamodel-property-display-name").fill("Worker Count Updated")
    page.locator("#metamodel-property-user-editable").uncheck()
    page.locator("#save-metamodel-property-button").click()

    expect(page.locator("#admin-metamodel-properties-list .admin-item", has_text="Worker Count Updated").first).to_contain_text("user_editable=false")

    page.locator("#metamodel-containment-rule-version-id").select_option(label="core / core-v2-ui-draft")
    page.locator("#metamodel-containment-parent-type-id").select_option(label="Physical Server (PhysicalServer)")
    page.locator("#metamodel-containment-child-type-id").select_option(label="Worker Pool Updated (WorkerPool)")
    page.locator("#metamodel-containment-min-count").fill("0")
    page.locator("#metamodel-containment-max-count").fill("4")
    page.locator("#metamodel-containment-cardinality-scope").select_option("per_member")
    page.locator("#metamodel-containment-is-required").check()
    page.locator("#save-metamodel-containment-rule-button").click()

    createdContainment = page.locator("#admin-metamodel-containment-rules-list .admin-item", has_text="Worker Pool Updated").first
    expect(createdContainment).to_contain_text("PhysicalServer -> WorkerPool")
    expect(createdContainment).to_contain_text("per_member")

    createdContainment.get_by_role("button", name="수정").click()
    expect(page.locator("#metamodel-containment-rule-form-mode")).to_contain_text("edit")
    page.locator("#metamodel-containment-max-count").fill("8")
    page.locator("#save-metamodel-containment-rule-button").click()

    expect(page.locator("#admin-metamodel-containment-rules-list .admin-item", has_text="Worker Pool Updated").first).to_contain_text("max=8")

    page.locator("#metamodel-notation-semantic-type-id").select_option(label="Worker Pool Updated (WorkerPool)")
    page.locator("#metamodel-notation-palette-group-id").select_option(label="Processes (processes)")
    page.locator("#metamodel-notation-code").fill("workerpool.rounded_rect")
    page.locator("#metamodel-notation-display-name").fill("Worker Pool Notation")
    page.locator("#metamodel-notation-kind").select_option("node")
    page.locator("#metamodel-notation-render-primitive").select_option("rounded_rect")
    page.locator("#metamodel-notation-sort-order").fill("10")
    page.locator("#metamodel-notation-render-schema-json").fill('{"primitive":"rounded_rect","default_size":{"width":220,"height":88},"label_slots":[{"code":"title","source":"display_name"}],"anchors":["top","right","bottom","left"]}')
    page.locator("#metamodel-notation-style-tokens-json").fill('{"fill":"process-fill","stroke":"process-stroke","label":"process-label"}')
    page.locator("#metamodel-notation-is-default").check()
    page.locator("#metamodel-notation-is-visible-in-palette").check()
    page.locator("#save-metamodel-notation-button").click()

    createdNotation = page.locator("#admin-metamodel-notations-list .admin-item", has_text="Worker Pool Notation").first
    expect(createdNotation).to_contain_text("workerpool.rounded_rect")
    expect(createdNotation).to_contain_text("rounded_rect")
    expect(createdNotation).to_contain_text("default")

    createdNotation.get_by_role("button", name="수정").click()
    expect(page.locator("#metamodel-notation-form-mode")).to_contain_text("edit")
    page.locator("#metamodel-notation-display-name").fill("Worker Pool Notation Updated")
    page.locator("#metamodel-notation-render-primitive").select_option("rect")
    page.locator("#metamodel-notation-sort-order").fill("9999")
    page.locator("#metamodel-notation-render-schema-json").fill('{"primitive":"rect","default_size":{"width":180,"height":72}}')
    page.locator("#metamodel-notation-is-visible-in-palette").uncheck()
    page.locator("#save-metamodel-notation-button").click()

    expect(page.locator("#admin-metamodel-notations-list .admin-item", has_text="Worker Pool Notation Updated").first).to_contain_text("rect")
    expect(page.locator("#admin-metamodel-notations-list .admin-item", has_text="Worker Pool Notation Updated").first).to_contain_text("hidden")

    page.locator("#metamodel-association-source-type-id").select_option(label="Monitoring Agent (MonitoringAgent)")
    page.locator("#metamodel-association-target-type-id").select_option(label="Worker Pool Updated (WorkerPool)")
    page.locator("#metamodel-association-code").fill("monitors_worker_pool")
    page.locator("#metamodel-association-display-name").fill("Monitors Worker Pool")
    page.locator("#metamodel-association-direction").select_option("directed")
    page.locator("#metamodel-association-multiplicity-source").fill("1")
    page.locator("#metamodel-association-multiplicity-target").fill("0..n")
    page.locator("#metamodel-association-description").fill("Playwright association definition create")
    page.locator("#metamodel-association-semantics-json").fill('{"default_edge_type":"CommunicationLink"}')
    page.locator("#save-metamodel-association-button").click()

    createdAssociation = page.locator("#admin-metamodel-associations-list .admin-item", has_text="Monitors Worker Pool").first
    expect(createdAssociation).to_contain_text("monitors_worker_pool")
    expect(createdAssociation).to_contain_text("MonitoringAgent -> WorkerPool")
    expect(createdAssociation).to_contain_text("0..n")

    createdAssociation.get_by_role("button", name="수정").click()
    expect(page.locator("#metamodel-association-form-mode")).to_contain_text("edit")
    page.locator("#metamodel-association-display-name").fill("Monitors Worker Pool Updated")
    page.locator("#metamodel-association-direction").select_option("undirected")
    page.locator("#metamodel-association-multiplicity-target").fill("1..n")
    page.locator("#metamodel-association-semantics-json").fill('{"default_edge_type":"CommunicationLink","visual_hint":"dashed"}')
    page.locator("#save-metamodel-association-button").click()

    expect(page.locator("#admin-metamodel-associations-list .admin-item", has_text="Monitors Worker Pool Updated").first).to_contain_text("undirected")
    expect(page.locator("#admin-metamodel-associations-list .admin-item", has_text="Monitors Worker Pool Updated").first).to_contain_text("1..n")
    expect(page.locator("#metamodel-workspace-outline")).to_contain_text("Worker Pool Updated")
    expect(page.locator("#metamodel-workspace-outline")).to_contain_text("Monitors Worker Pool Updated")

    page.locator('#metamodel-workspace-outline [data-workspace-kind="semantic_type"]', has_text="Worker Pool Updated").click()
    expect(page.locator("#metamodel-workspace-inspector")).to_contain_text("Worker Pool Updated")
    expect(page.locator("#metamodel-workspace-inspector")).to_contain_text("Default Notation Preview")
    expect(page.locator("#metamodel-semantic-type-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-semantic-type-display-name")).to_have_value("Worker Pool Updated")
    page.locator("#metamodel-workspace-inspector").get_by_role("button", name="새 Property").click()
    expect(page.locator("#metamodel-property-form-mode")).to_contain_text("create")
    expect(page.locator("#metamodel-property-semantic-type-id option:checked")).to_contain_text("Worker Pool Updated (WorkerPool)")

    page.get_by_role("button", name="Containment 연결").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Physical Server").click()
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("Physical Server")
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Worker Pool Updated").click()
    expect(page.locator("#metamodel-containment-rule-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-containment-max-count")).to_have_value("8")
    expect(page.locator("body")).to_contain_text("이미 존재하는 containment rule을 편집 모드로 열었습니다.")
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("선택 모드")

    page.get_by_role("button", name="Containment 연결").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Worker Pool Updated").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Monitoring Agent").click()
    expect(page.locator("#metamodel-containment-rule-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-containment-parent-type-id option:checked")).to_contain_text("Worker Pool Updated (WorkerPool)")
    expect(page.locator("#metamodel-containment-child-type-id option:checked")).to_contain_text("Monitoring Agent (MonitoringAgent)")
    expect(page.locator("#metamodel-containment-min-count")).to_have_value("0")
    expect(page.locator("#metamodel-containment-cardinality-scope")).to_have_value("group_total")
    expect(page.locator("body")).to_contain_text("Containment rule을 canvas에서 생성했습니다.")
    expect(page.locator("#admin-metamodel-containment-rules-list")).to_contain_text("WorkerPool -> MonitoringAgent")
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("선택 모드")

    page.locator('#metamodel-workspace-outline [data-workspace-kind="association_definition"]', has_text="Monitors Worker Pool Updated").click()
    expect(page.locator("#metamodel-workspace-inspector")).to_contain_text("Monitors Worker Pool Updated")
    expect(page.locator("#metamodel-workspace-inspector")).to_contain_text("undirected")
    page.locator("#metamodel-workspace-inspector").get_by_role("button", name="Association 편집").click()
    expect(page.locator("#metamodel-association-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-association-display-name")).to_have_value("Monitors Worker Pool Updated")

    page.get_by_role("button", name="Association 연결").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Monitoring Agent").click()
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("Monitoring Agent")
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Worker Pool Updated").click()
    expect(page.locator("#metamodel-association-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-association-display-name")).to_have_value("Monitors Worker Pool Updated")
    expect(page.locator("body")).to_contain_text("이미 존재하는 association definition을 편집 모드로 열었습니다.")
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("선택 모드")

    page.get_by_role("button", name="Association 연결").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Worker Pool Updated").click()
    page.locator('#metamodel-workspace-canvas [data-workspace-kind="semantic_type"]').filter(has_text="Monitoring Agent").click()
    expect(page.locator("#metamodel-association-form-mode")).to_contain_text("edit")
    expect(page.locator("#metamodel-association-source-type-id option:checked")).to_contain_text("Worker Pool Updated (WorkerPool)")
    expect(page.locator("#metamodel-association-target-type-id option:checked")).to_contain_text("Monitoring Agent (MonitoringAgent)")
    expect(page.locator("#metamodel-association-code")).to_have_value("worker_pool_to_monitoring_agent")
    expect(page.locator("#metamodel-association-display-name")).to_have_value("Worker Pool Updated -> Monitoring Agent")
    expect(page.locator("#metamodel-association-multiplicity-source")).to_have_value("1")
    expect(page.locator("#metamodel-association-multiplicity-target")).to_have_value("0..n")
    expect(page.locator("body")).to_contain_text("Association definition을 canvas에서 생성했습니다.")
    expect(page.locator("#admin-metamodel-associations-list")).to_contain_text("worker_pool_to_monitoring_agent")
    expect(page.locator("#metamodel-workspace-mode-status")).to_contain_text("선택 모드")

    createdVersion.get_by_role("button", name="Validate").click()
    expect(page.locator("#metamodel-validation-panel")).to_contain_text("core / core-v2-ui-draft validation")
    expect(page.locator("#metamodel-validation-panel")).to_contain_text("valid")
    expect(page.locator("#metamodel-validation-panel")).to_contain_text("error 0")

    createdVersion.locator(".publish-metamodel-button").click()

    expect(page.locator(".admin-item", has_text="core-v2-ui-draft").first).to_contain_text("published")
    page.locator("#alert-rule-object-type").fill("SoftwareProcess")
    page.locator("#alert-rule-metric-key").fill("fd_count")
    page.locator("#alert-rule-warning-threshold").fill("50")
    page.locator("#alert-rule-critical-threshold").fill("100")
    page.locator("#alert-rule-description").fill("Playwright rule")
    page.locator("#save-alert-rule-button").click()

    createdRule = page.locator(".admin-item", has_text="fd_count").first
    expect(createdRule).to_contain_text("warning=50")
    expect(createdRule).to_contain_text("critical=100")

    createdRule.get_by_role("button", name="수정").click()
    page.locator("#alert-rule-critical-threshold").fill("120")
    page.locator("#save-alert-rule-button").click()

    expect(page.locator(".admin-item", has_text="fd_count").first).to_contain_text("critical=120")
    createdRule = page.locator(".admin-item", has_text="fd_count").first
    createdRule.get_by_role("button", name="미리보기").click()
    expect(page.locator("#alert-rule-preview-panel")).to_contain_text("App Process")
    expect(page.locator("#alert-rule-preview-panel")).to_contain_text("active alert 0")
    expect(page.locator("#alert-rule-preview-panel")).to_contain_text("current metric fd_count")

    createdRule.get_by_role("button", name="비활성화").click()
    expect(page.locator(".admin-item", has_text="fd_count").first).to_contain_text("disabled")

    page.locator("#alert-rule-enabled-filter").select_option("false")
    expect(page.locator("#admin-alert-rules-list")).to_contain_text("fd_count")

    page.locator("#alert-rule-enabled-filter").select_option("true")
    expect(page.locator("#admin-alert-rules-list")).not_to_contain_text("fd_count")
    page.locator("#alert-rule-enabled-filter").select_option("")

    alertCard = page.locator("#admin-alerts-list .admin-item", has_text="agent.warning").first
    expect(alertCard).to_contain_text("Agent queue backlog")
    page.once("dialog", lambda dialog: dialog.accept("운영 확인"))
    alertCard.get_by_role("button", name="ACK").click()
    expect(page.locator("#admin-alerts-list")).to_contain_text("운영 확인")
    page.locator("#alert-ack-filter").select_option("true")
    expect(page.locator("#admin-alerts-list")).to_contain_text("agent.warning")
    expect(page.locator("#admin-alerts-list")).to_contain_text("ACK")
    page.locator("#alert-ack-filter").select_option("")

    expect(page.locator("#admin-ingest-list")).to_contain_text("표시할 ingest batch가 없습니다.")
    expect(page.locator("#admin-latest-state-list")).to_contain_text("조건에 맞는 latest state가 없습니다.")
    expect(page.locator("#admin-cleanup-list")).to_contain_text("최근 cleanup 기록이 없습니다.")
