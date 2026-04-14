from __future__ import annotations

import time
from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from playwright.sync_api import expect

from app.db import get_db
from app.ingest_worker import process_pending_ingest
from test_playwright_e2e import browser_login


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def create_monitor_view(app) -> int:
    timestamp = now_iso()
    with app.app_context():
        db_conn = get_db()
        cursor = db_conn.execute(
            """
            INSERT INTO views (name, description, owner_user_id, metamodel_version, revision, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "SSH Linux Monitor View",
                "실제 Linux agent monitoring 확인용 view",
                1,
                "seed-v1",
                1,
                timestamp,
                timestamp,
            ),
        )
        view_id = cursor.lastrowid
        next_node_id = db_conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM view_nodes").fetchone()["next_id"]
        server_id = next_node_id
        process_id = server_id + 1
        agent_id = server_id + 2

        db_conn.executemany(
            """
            INSERT INTO view_nodes (
                id, view_id, parent_node_id, node_type, display_name, target_id,
                x, y, width, height, is_deleted, style_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            """,
            [
                (
                    server_id,
                    view_id,
                    None,
                    "PhysicalServer",
                    "Remote Host",
                    "agent_ssh_smoke:host",
                    100,
                    100,
                    340,
                    220,
                    timestamp,
                    timestamp,
                ),
                (
                    process_id,
                    view_id,
                    server_id,
                    "SoftwareProcess",
                    "Sleep Worker",
                    "ssh_smoke_target",
                    150,
                    180,
                    150,
                    76,
                    timestamp,
                    timestamp,
                ),
                (
                    agent_id,
                    view_id,
                    server_id,
                    "MonitoringAgent",
                    "Remote Agent",
                    "agent_ssh_smoke",
                    150,
                    280,
                    150,
                    76,
                    timestamp,
                    timestamp,
                ),
            ],
        )
        db_conn.execute(
            """
            INSERT INTO view_edges (
                id, view_id, edge_type, source_node_id, target_node_id,
                source_anchor, target_anchor, control_points_json, label, style_json,
                is_deleted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                db_conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM view_edges").fetchone()["next_id"],
                view_id,
                "CommunicationLink",
                agent_id,
                process_id,
                "right",
                "left",
                "[]",
                "agent link",
                '{"strokeStyle":"solid"}',
                timestamp,
                timestamp,
            ),
        )
        db_conn.commit()
        return int(view_id)


@pytest.mark.linux_agent_ssh
def test_linux_agent_results_visible_in_monitor_ui(page, linux_agent_ssh_session, network_live_server) -> None:
    run = linux_agent_ssh_session.create_run(run_id=f"ssh-ui-{uuid4().hex[:8]}")

    with network_live_server(
        linux_agent_ssh_session.config.host,
        app_config={
            "AGENT_TOKENS": {
                "agent_local": "dev-agent-token",
                "agent_ssh_smoke": "dev-agent-token",
            }
        },
    ) as (remote_endpoint, app, _db_path):
        parsed = urlparse(remote_endpoint)
        local_base_url = f"http://127.0.0.1:{parsed.port}"
        view_id = create_monitor_view(app)
        config_text = linux_agent_ssh_session.render_agent_config(
            run,
            agent_id="agent_ssh_smoke",
            target_id="ssh_smoke_target",
            process_name="sleep",
            heartbeat_seconds=1,
            snapshot_seconds=1,
            flush_seconds=1,
            retry_backoff_seconds=2,
            backend_endpoint=f"{remote_endpoint}/api/agents/ingest",
        )

        remote_sleep = linux_agent_ssh_session.run_ssh("nohup sleep 30 >/dev/null 2>&1 & echo $!")
        remote_sleep_pid = remote_sleep.stdout.strip()

        try:
            linux_agent_ssh_session.prepare_agent_run(run, config_text=config_text)
            linux_agent_ssh_session.start_agent(run, cycles=6)
            time.sleep(8.0)

            with app.app_context():
                result = process_pending_ingest(limit=100)
                assert result["processed_batches"] >= 1

            browser_login(page, local_base_url)
            page.goto(f"{local_base_url}/views/{view_id}/monitor")
            expect(page.get_by_role("heading", name="최근 이벤트")).to_be_visible()

            server_node = page.locator('g.diagram-node[data-node-type="PhysicalServer"]').first
            agent_shape = page.locator('g.diagram-node[data-node-type="MonitoringAgent"] .node-shape').first
            process_shape = page.locator('g.diagram-node[data-node-type="SoftwareProcess"] .node-shape').first

            server_node.click(force=True, position={"x": 24, "y": 24})
            expect(page.locator("#monitor-selection-summary")).to_contain_text("Remote Host")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("호스트명")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("CPU 사용률")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("Load Average")

            agent_shape.click(force=True)
            expect(page.locator("#monitor-selection-summary")).to_contain_text("Remote Agent")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("백엔드 연결")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("outbox depth")

            process_shape.click(force=True)
            expect(page.locator("#monitor-selection-summary")).to_contain_text("Sleep Worker")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("프로세스 상태")
            expect(page.locator("#monitor-selection-summary")).to_contain_text("PID")
        finally:
            linux_agent_ssh_session.stop_agent(run)
            if remote_sleep_pid:
                linux_agent_ssh_session.run_ssh(f"kill {remote_sleep_pid} 2>/dev/null || true", check=False)
            linux_agent_ssh_session.cleanup_remote(run)
