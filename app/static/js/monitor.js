import { apiFetch, clearBanner, formatTimestamp, showBanner } from "./common.js";
import { renderDiagram } from "./diagram.js";
import { loadMetamodelRegistry } from "./metamodel.js";
const POLL_INTERVAL_MS = 5000;

const appRoot = document.getElementById("monitor-app");
const svg = document.getElementById("monitor-canvas");
const monitorStatus = document.getElementById("monitor-status");
const agentSummary = document.getElementById("monitor-agent-summary");
const alertsList = document.getElementById("alerts-list");
const eventsList = document.getElementById("events-list");
const eventDetailPanel = document.getElementById("event-detail-panel");
const selectionSummary = document.getElementById("monitor-selection-summary");
const refreshEventsButton = document.getElementById("refresh-events-button");

const state = {
    viewId: Number(appRoot.dataset.viewId),
    metamodelVersionCode: null,
    notationDefinitionsByCode: new Map(),
    nodes: [],
    edges: [],
    latestStates: [],
    alerts: [],
    events: [],
    selectedEventId: null,
    eventDetails: [],
    selectedGroupedEvent: null,
    selectedRawEventId: null,
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

function runtimeLevel(stateRow) {
    if (!stateRow) {
        return "neutral";
    }

    if (stateRow.status === "down" || stateRow.severity === "critical") {
        return "down";
    }
    if (stateRow.status === "warning" || stateRow.severity === "warning") {
        return "warning";
    }
    if (
        stateRow.status === "up" ||
        stateRow.status === "healthy" ||
        stateRow.severity === "info" ||
        stateRow.severity === "normal"
    ) {
        return "up";
    }
    return "neutral";
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

function formatHeartbeatAge(payload) {
    if (payload.heartbeat_age_seconds === undefined) {
        return "-";
    }
    return `${formatNumber(payload.heartbeat_age_seconds, 1)}초`;
}

function latestStateForNode(node) {
    if (!node) {
        return null;
    }
    if (node.monitored_object_id) {
        const byObject = state.latestStates.find((item) => item.monitored_object_id === node.monitored_object_id);
        if (byObject) {
            return byObject;
        }
    }
    if (node.target_id) {
        return state.latestStates.find((item) => item.target_id === node.target_id) || null;
    }
    return null;
}

function agentStatusText(payload, stateRow) {
    if (payload.heartbeat_timeout_level === "down") {
        return "heartbeat 끊김";
    }
    if (payload.heartbeat_timeout_level === "warning") {
        return "heartbeat 지연";
    }
    return payload.backend_connection_status || stateRow?.status || "미수집";
}

function buildStateDetailRows(node, stateRow) {
    const payload = stateRow.state || {};
    const rows = [
        { label: "타겟", value: node.target_id || "-" },
        { label: "모니터링 객체", value: node.monitored_object_id ?? "-" },
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
            { label: "heartbeat 상태", value: payload.heartbeat_timeout_level || "normal" },
            { label: "heartbeat 경과", value: formatHeartbeatAge(payload) },
            { label: "outbox depth", value: formatNumber(payload.outbox_queue_depth, 0) },
            { label: "경고 임계치", value: formatNumber(payload.outbox_pending_warning_rows, 0) },
            { label: "last sent seq", value: formatNumber(payload.last_sent_seq, 0) },
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
            { label: "프로세스 상태", value: payload.state || stateRow.status || "-" },
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
            <article class="event-item event-summary-item is-interactive${state.selectedEventId === event.id ? " is-selected" : ""}" data-grouped-event-id="${escapeHtml(event.id)}">
                <h3>${escapeHtml(event.event_type)}</h3>
                <p>${escapeHtml(event.latest_message || event.message || "메시지 없음")}</p>
                <p>${escapeHtml(event.target_id)} | ${escapeHtml(event.severity)} | 반복 ${escapeHtml(event.repeat_count ?? 1)}회</p>
                <p>${escapeHtml(formatTimestamp(event.last_occurred_at || event.occurred_at))}</p>
            </article>
        `
        )
        .join("");
}

function renderEventDetails() {
    if (!state.selectedGroupedEvent) {
        eventDetailPanel.innerHTML = '<p class="section-copy">grouped event를 선택하면 raw event 상세를 볼 수 있습니다.</p>';
        return;
    }

    const groupedEvent = state.selectedGroupedEvent;
    const rawEventItems = state.eventDetails;
    const header = `
        <div class="section-header">
            <h3>${escapeHtml(groupedEvent.event_type)}</h3>
            <span class="meta-pill">반복 ${escapeHtml(groupedEvent.repeat_count ?? 1)}회</span>
        </div>
        <p class="admin-meta">${escapeHtml(groupedEvent.target_id || "-")} | ${escapeHtml(groupedEvent.severity)} | ${escapeHtml(formatTimestamp(groupedEvent.last_occurred_at || groupedEvent.occurred_at))}</p>
    `;

    if (rawEventItems.length === 0) {
        eventDetailPanel.innerHTML = `
            ${header}
            <p class="section-copy">조건에 맞는 raw event가 없습니다.</p>
        `;
        return;
    }

    const selectedRawEvent =
        rawEventItems.find((event) => event.id === state.selectedRawEventId) || rawEventItems[0];
    state.selectedRawEventId = selectedRawEvent.id;
    const payloadJson =
        selectedRawEvent.event !== undefined
            ? JSON.stringify(selectedRawEvent.event, null, 2)
            : null;

    eventDetailPanel.innerHTML = `
        ${header}
        <div class="event-drilldown-layout">
            <div class="event-list raw-event-list">
                ${rawEventItems
                    .map(
                        (event) => `
                            <article class="event-item raw-event-item is-interactive${event.id === state.selectedRawEventId ? " is-selected" : ""}" data-raw-event-id="${escapeHtml(event.id)}">
                                <h4>${escapeHtml(event.event_type)}</h4>
                                <p>${escapeHtml(event.message || "메시지 없음")}</p>
                                <p>${escapeHtml(event.target_id)} | ${escapeHtml(event.severity)} | agent ${escapeHtml(event.agent_id || "-")}</p>
                                <p>${escapeHtml(formatTimestamp(event.occurred_at))}</p>
                            </article>
                        `
                    )
                    .join("")}
            </div>
            <section class="raw-event-detail-panel">
                <div class="section-header">
                    <h4>Raw Event #${escapeHtml(selectedRawEvent.id)}</h4>
                    <div class="toolbar-inline">
                        <span class="meta-pill">${escapeHtml(selectedRawEvent.severity)}</span>
                        <span class="meta-pill">agent ${escapeHtml(selectedRawEvent.agent_id || "-")}</span>
                    </div>
                </div>
                <p class="admin-meta">target=${escapeHtml(selectedRawEvent.target_id || "-")} | object=${escapeHtml(selectedRawEvent.monitored_object_id ?? "-")}</p>
                <p class="admin-meta">occurred=${escapeHtml(formatTimestamp(selectedRawEvent.occurred_at))} | received=${escapeHtml(formatTimestamp(selectedRawEvent.received_at))}</p>
                <p>${escapeHtml(selectedRawEvent.message || "메시지 없음")}</p>
                ${
                    payloadJson
                        ? `<details class="state-payload-block" open><summary>Payload JSON</summary><pre>${escapeHtml(payloadJson)}</pre></details>`
                        : '<p class="section-copy">payload JSON이 없습니다.</p>'
                }
            </section>
        </div>
    `;
}

function renderAlerts() {
    if (state.alerts.length === 0) {
        alertsList.innerHTML = '<p class="section-copy">현재 표시할 alert가 없습니다.</p>';
        return;
    }

    alertsList.innerHTML = state.alerts
        .map(
            (alert) => `
            <article class="event-item alert-item severity-${escapeHtml(alert.severity)}">
                <h3>${escapeHtml(alert.alert_code)}</h3>
                <p>${escapeHtml(alert.latest_message || "메시지 없음")}</p>
                <p>object ${escapeHtml(alert.monitored_object_id)} | ${escapeHtml(alert.severity)} | 상태 ${escapeHtml(alert.status)} | 반복 ${escapeHtml(alert.repeat_count)}회</p>
                <p>rule ${escapeHtml(alert.source_rule_metric_key || "-")} | target ${escapeHtml(alert.source_rule_target_label || "-")}</p>
                ${
                    alert.is_acknowledged
                        ? `<p>ACK ${escapeHtml(alert.acknowledged_by_username || "-")} | ${escapeHtml(formatTimestamp(alert.acknowledged_at))}${alert.ack_note ? ` | ${escapeHtml(alert.ack_note)}` : ""}</p>`
                        : '<p>ACK 대기 중</p>'
                }
                <p>상태 업데이트 ${escapeHtml(alert.status_updated_by_username || "-")} | ${escapeHtml(formatTimestamp(alert.status_updated_at))}${alert.status_note ? ` | ${escapeHtml(alert.status_note)}` : ""}</p>
                ${
                    alert.resolved_at
                        ? `<p>해결 ${escapeHtml(alert.resolved_by_username || "-")} | ${escapeHtml(formatTimestamp(alert.resolved_at))}</p>`
                        : ""
                }
                <p>${escapeHtml(formatTimestamp(alert.last_occurred_at))}</p>
            </article>
        `
        )
        .join("");
}

function renderAgentSummary() {
    const agents = state.nodes.filter((node) => node.node_type === "MonitoringAgent");
    if (agents.length === 0) {
        agentSummary.innerHTML = '<p class="section-copy">현재 뷰에 MonitoringAgent가 없습니다.</p>';
        return;
    }

    agentSummary.innerHTML = agents
        .map((node) => {
            const stateRow = latestStateForNode(node);
            const payload = stateRow?.state || {};
            const level = runtimeLevel(stateRow);
            const statusText = agentStatusText(payload, stateRow);
            const queueDepth = formatNumber(payload.outbox_queue_depth, 0);
            const lastAckSeq = formatNumber(payload.last_ack_seq, 0);
            const heartbeat = formatTimestamp(payload.heartbeat_time || stateRow?.occurred_at);
            const heartbeatAge = formatHeartbeatAge(payload);
            const selectedClass = state.selectedNodeId === node.id ? " is-selected" : "";

            return `
                <article class="agent-state-card state-${level}${selectedClass}" data-node-id="${node.id}">
                    <div class="agent-state-header">
                        <strong>${escapeHtml(node.display_name)}</strong>
                        <span class="agent-state-pill">${escapeHtml(statusText)}</span>
                    </div>
                    <div class="agent-state-metrics">
                        <span>outbox ${escapeHtml(queueDepth)}</span>
                        <span>ack ${escapeHtml(lastAckSeq)}</span>
                    </div>
                    <p class="agent-state-meta">최근 heartbeat ${escapeHtml(heartbeat)} | 경과 ${escapeHtml(heartbeatAge)}</p>
                </article>
            `;
        })
        .join("");
}

function renderSelection() {
    const node = state.nodes.find((item) => item.id === state.selectedNodeId);
    if (!node) {
        selectionSummary.innerHTML = "<p>노드를 선택하면 latest state를 볼 수 있습니다.</p>";
        return;
    }

    const stateRow = latestStateForNode(node);
    const nodeAlerts = state.alerts.filter((item) => item.monitored_object_id === node.monitored_object_id);
    if (!stateRow) {
        selectionSummary.innerHTML = `
            <p><strong>${escapeHtml(node.display_name)}</strong></p>
            <p>아직 runtime state가 없습니다.</p>
            <p class="selection-kind">타겟 ID: ${escapeHtml(node.target_id || "-")}</p>
            <p class="selection-kind">열린 alert 수: ${escapeHtml(nodeAlerts.length)}</p>
        `;
        return;
    }

    const detailRows = buildStateDetailRows(node, stateRow);
    selectionSummary.innerHTML = `
        <p><strong>${escapeHtml(node.display_name)}</strong></p>
        <p class="selection-kind">열린 alert 수: ${escapeHtml(nodeAlerts.length)}</p>
        <div class="detail-grid">${renderDetailRows(detailRows)}</div>
        <details class="state-payload-block">
            <summary>Raw state payload</summary>
            <pre>${escapeHtml(JSON.stringify(stateRow.state, null, 2))}</pre>
        </details>
    `;
}

function render() {
    const latestStatesByTargetId = new Map(state.latestStates.map((item) => [item.target_id, item]));
    const latestStatesByMonitoredObjectId = new Map(
        state.latestStates
            .filter((item) => item.monitored_object_id !== null && item.monitored_object_id !== undefined)
            .map((item) => [item.monitored_object_id, item])
    );
    const alertsByMonitoredObjectId = new Map();
    for (const alert of state.alerts) {
        const items = alertsByMonitoredObjectId.get(alert.monitored_object_id) || [];
        items.push(alert);
        alertsByMonitoredObjectId.set(alert.monitored_object_id, items);
    }
    renderDiagram(svg, {
        nodes: state.nodes,
        edges: state.edges,
        notationDefinitionsByCode: state.notationDefinitionsByCode,
        selectedNodeId: state.selectedNodeId,
        latestStatesByTargetId,
        latestStatesByMonitoredObjectId,
        alertsByMonitoredObjectId,
        onNodeClick: (node, event) => {
            event.stopPropagation();
            state.selectedNodeId = node.id;
            render();
        },
        onEdgeClick: (_edge, event) => event.stopPropagation(),
    });
    renderAgentSummary();
    renderAlerts();
    renderEvents();
    renderEventDetails();
    renderSelection();
}

async function loadEventDetails(groupedEventId) {
    const payload = await apiFetch(`/api/views/${state.viewId}/events/${groupedEventId}/raw-events?limit=20`);
    state.selectedEventId = groupedEventId;
    state.selectedGroupedEvent = payload.grouped_event;
    state.eventDetails = payload.items;
    state.selectedRawEventId = payload.items[0]?.id ?? null;
    render();
}

async function loadView() {
    let payload;
    let metamodelVersionCode;

    try {
        payload = await apiFetch(`/api/views/${state.viewId}/active`);
        metamodelVersionCode = payload.version?.metamodel_version_code || payload.view.metamodel_version;
    } catch (error) {
        if (error.status !== 404) {
            throw error;
        }
        try {
            payload = await apiFetch(`/api/views/${state.viewId}/draft`);
            metamodelVersionCode = payload.version?.metamodel_version_code || payload.view.metamodel_version;
        } catch (draftError) {
            if (draftError.status !== 404) {
                throw draftError;
            }
            payload = await apiFetch(`/api/views/${state.viewId}`);
            metamodelVersionCode = payload.view.metamodel_version;
        }
    }

    if (state.metamodelVersionCode !== metamodelVersionCode || state.notationDefinitionsByCode.size === 0) {
        const registry = await loadMetamodelRegistry(metamodelVersionCode);
        state.metamodelVersionCode = registry.versionCode;
        state.notationDefinitionsByCode = registry.notationDefinitionsByCode;
    }
    state.nodes = payload.nodes;
    state.edges = payload.edges;
}

async function loadRuntimeData() {
    const [latest, alerts, events] = await Promise.all([
        apiFetch(`/api/views/${state.viewId}/latest-state`),
        apiFetch(`/api/views/${state.viewId}/alerts?limit=20`),
        apiFetch(`/api/views/${state.viewId}/events?limit=20`),
    ]);
    state.latestStates = latest.items;
    state.alerts = alerts.items;
    state.events = events.items;
    monitorStatus.textContent = `최근 갱신 ${new Date().toLocaleTimeString("ko-KR", { hour12: false })}`;
    if (state.selectedEventId && state.events.some((item) => item.id === state.selectedEventId)) {
        await loadEventDetails(state.selectedEventId);
        return;
    }
    state.selectedEventId = null;
    state.selectedGroupedEvent = null;
    state.eventDetails = [];
    state.selectedRawEventId = null;
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
eventsList?.addEventListener("click", async (event) => {
    const card = event.target instanceof Element ? event.target.closest("[data-grouped-event-id]") : null;
    if (!card) {
        return;
    }

    try {
        clearBanner();
        await loadEventDetails(Number(card.dataset.groupedEventId));
    } catch (error) {
        showBanner(error.message, "error");
    }
});
eventDetailPanel?.addEventListener("click", (event) => {
    const card = event.target instanceof Element ? event.target.closest("[data-raw-event-id]") : null;
    if (!card) {
        return;
    }
    state.selectedRawEventId = Number(card.dataset.rawEventId);
    renderEventDetails();
});
agentSummary?.addEventListener("click", (event) => {
    const card = event.target.closest("[data-node-id]");
    if (!card) {
        return;
    }
    state.selectedNodeId = Number(card.dataset.nodeId);
    render();
});
svg.addEventListener("click", () => {
    state.selectedNodeId = null;
    renderSelection();
    render();
});

refreshAll();
window.setInterval(refreshAll, POLL_INTERVAL_MS);


