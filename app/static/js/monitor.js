import { apiFetch, clearBanner, formatTimestamp, showBanner } from "./common.js";
import { renderDiagram } from "./diagram.js";

const POLL_INTERVAL_MS = 5000;

const appRoot = document.getElementById("monitor-app");
const svg = document.getElementById("monitor-canvas");
const monitorStatus = document.getElementById("monitor-status");
const eventsList = document.getElementById("events-list");
const selectionSummary = document.getElementById("monitor-selection-summary");
const refreshEventsButton = document.getElementById("refresh-events-button");

const state = {
    viewId: Number(appRoot.dataset.viewId),
    nodes: [],
    edges: [],
    latestStates: [],
    events: [],
    selectedNodeId: null,
};

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatNumber(value, fractionDigits = 1) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return String(value);
    }
    return number.toLocaleString("ko-KR", {
        minimumFractionDigits: 0,
        maximumFractionDigits: fractionDigits,
    });
}

function formatPercent(value) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }
    return `${formatNumber(value, 1)}%`;
}

function formatBytes(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number < 0) {
        return "-";
    }
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = number;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }
    return `${formatNumber(size, size >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

function renderDetailRows(rows) {
    return rows
        .map(
            (row) => `
                <div class="detail-row">
                    <span class="detail-key">${escapeHtml(row.label)}</span>
                    <span class="detail-value">${escapeHtml(row.value)}</span>
                </div>
            `
        )
        .join("");
}

function buildStateDetailRows(node, stateRow) {
    const payload = stateRow.state || {};
    const rows = [
        { label: "대상", value: node.target_id || "-" },
        { label: "구성 요소", value: node.node_type },
        { label: "상태 종류", value: stateRow.state_type },
        { label: "상태", value: stateRow.status },
        { label: "심각도", value: stateRow.severity || "-" },
        { label: "발생 시각", value: formatTimestamp(stateRow.occurred_at) },
        { label: "수신 시각", value: formatTimestamp(stateRow.received_at) },
    ];

    if (stateRow.state_type === "agent") {
        rows.push(
            { label: "백엔드 연결", value: payload.backend_connection_status || "-" },
            { label: "outbox depth", value: formatNumber(payload.outbox_queue_depth, 0) },
            { label: "last ack seq", value: formatNumber(payload.last_ack_seq, 0) },
            { label: "heartbeat", value: formatTimestamp(payload.heartbeat_time) }
        );
    } else if (stateRow.state_type === "host") {
        rows.push(
            { label: "호스트명", value: payload.hostname || "-" },
            { label: "CPU 사용률", value: formatPercent(payload.cpu_usage) },
            {
                label: "Load Average",
                value: `${formatNumber(payload.loadavg_1)}, ${formatNumber(payload.loadavg_5)}, ${formatNumber(payload.loadavg_15)}`,
            },
            { label: "메모리 사용", value: formatBytes(payload.memory_used) },
            { label: "메모리 여유", value: formatBytes(payload.memory_available) },
            { label: "메모리 전체", value: formatBytes(payload.memory_total) }
        );
    } else if (stateRow.state_type === "process") {
        rows.push(
            { label: "프로세스 상태", value: payload.state || "-" },
            { label: "PID", value: formatNumber(payload.pid, 0) },
            { label: "CPU 사용률", value: formatPercent(payload.cpu_usage) },
            { label: "RSS 메모리", value: formatBytes(payload.memory_rss) },
            { label: "스레드 수", value: formatNumber(payload.thread_count, 0) },
            { label: "FD 수", value: formatNumber(payload.fd_count, 0) }
        );
        if (payload.event_type) {
            rows.push(
                { label: "최근 이벤트", value: payload.event_type },
                { label: "이벤트 메시지", value: payload.message || "-" }
            );
        }
    }

    return rows;
}

function renderEvents() {
    if (state.events.length === 0) {
        eventsList.innerHTML = '<p class="section-copy">아직 이벤트가 없습니다.</p>';
        return;
    }

    eventsList.innerHTML = state.events
        .map(
            (event) => `
            <article class="event-item">
                <h3>${event.event_type}</h3>
                <p>${event.message || "메시지 없음"}</p>
                <p>${event.target_id} · ${event.severity} · ${formatTimestamp(event.occurred_at)}</p>
            </article>
        `
        )
        .join("");
}

function renderSelection() {
    const node = state.nodes.find((item) => item.id === state.selectedNodeId);
    if (!node) {
        selectionSummary.innerHTML = "<p>노드를 선택하면 latest state를 볼 수 있습니다.</p>";
        return;
    }

    const stateRow = state.latestStates.find((item) => item.target_id === node.target_id);
    if (!stateRow) {
        selectionSummary.innerHTML = `
            <p><strong>${escapeHtml(node.display_name)}</strong></p>
            <p>아직 runtime state가 없습니다.</p>
            <p class="selection-kind">대상 ID: ${escapeHtml(node.target_id || "-")}</p>
        `;
        return;
    }

    const detailRows = buildStateDetailRows(node, stateRow);
    selectionSummary.innerHTML = `
        <p><strong>${escapeHtml(node.display_name)}</strong></p>
        <div class="detail-grid">${renderDetailRows(detailRows)}</div>
        <details class="state-payload-block">
            <summary>Raw state payload</summary>
            <pre>${escapeHtml(JSON.stringify(stateRow.state, null, 2))}</pre>
        </details>
    `;
}

function render() {
    const latestStatesByTargetId = new Map(state.latestStates.map((item) => [item.target_id, item]));
    renderDiagram(svg, {
        nodes: state.nodes,
        edges: state.edges,
        selectedNodeId: state.selectedNodeId,
        latestStatesByTargetId,
        onNodeClick: (node, event) => {
            event.stopPropagation();
            state.selectedNodeId = node.id;
            render();
        },
        onEdgeClick: (_edge, event) => event.stopPropagation(),
    });
    renderEvents();
    renderSelection();
}

async function loadView() {
    const payload = await apiFetch(`/api/views/${state.viewId}`);
    state.nodes = payload.nodes;
    state.edges = payload.edges;
}

async function loadRuntimeData() {
    const [latest, events] = await Promise.all([
        apiFetch(`/api/views/${state.viewId}/latest-state`),
        apiFetch(`/api/views/${state.viewId}/events?limit=20`),
    ]);
    state.latestStates = latest.items;
    state.events = events.items;
    monitorStatus.textContent = `최근 갱신 ${new Date().toLocaleTimeString("ko-KR", { hour12: false })}`;
}

async function refreshAll() {
    clearBanner();
    try {
        await loadView();
        await loadRuntimeData();
        render();
    } catch (error) {
        showBanner(error.message, "error");
        monitorStatus.textContent = "polling 오류";
    }
}

refreshEventsButton?.addEventListener("click", refreshAll);
svg.addEventListener("click", () => {
    state.selectedNodeId = null;
    renderSelection();
    render();
});

refreshAll();
window.setInterval(refreshAll, POLL_INTERVAL_MS);
