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
    base_url, _seeded_app = live_server

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

    createdVersion.locator(".publish-metamodel-button").click()

    expect(page.locator(".admin-item", has_text="core-v2-ui-draft").first).to_contain_text("published")
    page.locator("#alert-rule-object-type").fill("SoftwareProcess")
    page.locator("#alert-rule-metric-key").fill("fd_count")
    page.locator("#alert-rule-warning-threshold").fill("50")
    page.locator("#alert-rule-critical-threshold").fill("100")
    page.locator("#alert-rule-description").fill("Playwright rule")
    page.get_by_role("button", name="저장").click()

    createdRule = page.locator(".admin-item", has_text="fd_count").first
    expect(createdRule).to_contain_text("warning=50")
    expect(createdRule).to_contain_text("critical=100")

    createdRule.get_by_role("button", name="수정").click()
    page.locator("#alert-rule-critical-threshold").fill("120")
    page.get_by_role("button", name="저장").click()

    expect(page.locator(".admin-item", has_text="fd_count").first).to_contain_text("critical=120")
    createdRule = page.locator(".admin-item", has_text="fd_count").first
    createdRule.get_by_role("button", name="미리보기").click()
    expect(page.locator("#alert-rule-preview-panel")).to_contain_text("App Process")
    expect(page.locator("#alert-rule-preview-panel")).to_contain_text("open alert 0")

    createdRule.get_by_role("button", name="비활성화").click()
    expect(page.locator(".admin-item", has_text="fd_count").first).to_contain_text("disabled")

    page.locator("#alert-rule-enabled-filter").select_option("false")
    expect(page.locator("#admin-alert-rules-list")).to_contain_text("fd_count")

    page.locator("#alert-rule-enabled-filter").select_option("true")
    expect(page.locator("#admin-alert-rules-list")).not_to_contain_text("fd_count")
    page.locator("#alert-rule-enabled-filter").select_option("")

    expect(page.locator("#admin-ingest-list")).to_contain_text("표시할 ingest batch가 없습니다.")
    expect(page.locator("#admin-latest-state-list")).to_contain_text("조건에 맞는 latest state가 없습니다.")
    expect(page.locator("#admin-cleanup-list")).to_contain_text("최근 cleanup 기록이 없습니다.")
