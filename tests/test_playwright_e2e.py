from __future__ import annotations

import json
import re
from urllib import request

from playwright.sync_api import Page, expect

from app.ingest_worker import process_pending_ingest


AGENT_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "X-Agent-Id": "agent_local",
    "X-Agent-Token": "dev-agent-token",
}


def browser_login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login")
    page.get_by_label("사용자 이름").fill("admin")
    page.get_by_label("비밀번호").fill("admin123!")
    page.get_by_role("button", name="로그인").click()
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

    process_shape = page.locator('g.diagram-node[data-node-type="SoftwareProcess"] .node-shape').first
    agent_shape = page.locator('g.diagram-node[data-node-type="MonitoringAgent"] .node-shape').first

    process_shape.click(force=True)
    process_target_id = page.locator("#node-target-id").input_value()
    page.locator("#node-display-name").fill("Worker Alpha")
    page.get_by_role("button", name="선택 항목 저장").click()
    expect(page.locator('text="Worker Alpha"')).to_be_visible()

    process_shape.click(force=True)
    page.get_by_role("button", name="통신선 시작").click()
    agent_shape.click(force=True)
    expect(page.locator("path.diagram-edge")).to_have_count(1)

    post_ingest(
        base_url,
        {
            "agent_id": "agent_local",
            "boot_id": "boot-playwright",
            "seq_start": 1,
            "seq_end": 2,
            "items": [
                {
                    "seq": 1,
                    "payload_type": "process_snapshot",
                    "occurred_at": "2026-04-12T20:10:00.000+09:00",
                    "target_id": process_target_id,
                    "payload": {
                        "state": "running",
                        "severity": "info",
                        "cpu_usage": 12.5,
                        "memory_rss": 20480,
                    },
                },
                {
                    "seq": 2,
                    "payload_type": "process_event",
                    "occurred_at": "2026-04-12T20:10:01.000+09:00",
                    "target_id": process_target_id,
                    "payload": {
                        "event_type": "process_started",
                        "severity": "info",
                        "message": "Playwright process started",
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

    monitor_process_shape = page.locator('g.diagram-node[data-node-type="SoftwareProcess"] .node-shape').first
    monitor_process_shape.click(force=True)

    expect(page.locator("#monitor-selection-summary")).to_contain_text("Worker Alpha")
    expect(page.locator("#monitor-selection-summary")).to_contain_text("상태: up")
    expect(page.locator("#events-list")).to_contain_text("process_started")
    expect(page.locator("#events-list")).to_contain_text("Playwright process started")
