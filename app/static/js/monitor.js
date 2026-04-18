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
    selectedEdgeId: null,
    realtimeSource: null,
    realtimeReconnectTimerId: null,
};

let realtimeUpdateQueue = Promise.resolve();

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

function runtimeStatusLabel(stateRow) {
    if (!stateRow) {
        return "미수집";
    }
    if (stateRow.status === "down" || stateRow.severity === "critical") {
        return "critical";
    }
    if (stateRow.status === "warning" || stateRow.severity === "warning") {
        return "warning";
    }
    if (stateRow.status === "up" || stateRow.status === "healthy" || stateRow.severity === "info") {
        return "normal";
    }
    return stateRow.status || stateRow.severity || "unknown";
}

function cardSeverityClass(severity) {
    if (severity === "critical" || severity === "down") {
        return "is-critical";
    }
    if (severity === "warning") {
        return "is-warning";
    }
    if (severity === "normal" || severity === "info" || severity === "up") {
        return "is-ok";
    }
    return "";
}

function bindingKeyForNode(node) {
    if (!node) {
        return null;
    }
    if (node.monitored_object_id !== null && node.monitored_object_id !== undefined) {
        return `monitored:${node.monitored_object_id}`;
    }
    if (node.target_id) {
        return `target:${node.target_id}`;
    }
    return null;
}

function alertsForNode(node) {
    if (!node) {
        return [];
    }
    if (node.monitored_object_id !== null && node.monitored_object_id !== undefined) {
        return state.alerts.filter((item) => item.monitored_object_id === node.monitored_object_id);
    }
    return [];
}

function groupedEventsForNode(node) {
    if (!node) {
        return [];
    }
    if (node.monitored_object_id !== null && node.monitored_object_id !== undefined) {
        return state.events.filter((item) => item.monitored_object_id === node.monitored_object_id);
    }
    if (node.target_id) {
        return state.events.filter((item) => item.target_id === node.target_id);
    }
    return [];
}

function fanoutNodesForNode(node) {
    const bindingKey = bindingKeyForNode(node);
    if (!bindingKey) {
        return [node].filter(Boolean);
    }
    return state.nodes.filter((candidate) => bindingKeyForNode(candidate) === bindingKey);
}

function uniqueById(items) {
    const seen = new Set();
    return items.filter((item) => {
        if (!item || seen.has(item.id)) {
            return false;
        }
        seen.add(item.id);
        return true;
    });
}

function sortLatestStateItems(items) {
    return [...items].sort((left, right) => {
        const leftType = left.state_type || "";
        const rightType = right.state_type || "";
        return leftType.localeCompare(rightType, "en");
    });
}

function alertSeverityRank(item) {
    if (item.severity === "critical") {
        return 0;
    }
    if (item.severity === "warning") {
        return 1;
    }
    return 2;
}

function sortAlertItems(items) {
    return [...items].sort((left, right) => {
        const severityGap = alertSeverityRank(left) - alertSeverityRank(right);
        if (severityGap !== 0) {
            return severityGap;
        }
        const leftTime = left.last_occurred_at || "";
        const rightTime = right.last_occurred_at || "";
        if (leftTime !== rightTime) {
            return rightTime.localeCompare(leftTime);
        }
        return (right.id || 0) - (left.id || 0);
    });
}

function sortGroupedEventItems(items) {
    return [...items].sort((left, right) => {
        const leftTime = left.last_occurred_at || left.occurred_at || "";
        const rightTime = right.last_occurred_at || right.occurred_at || "";
        if (leftTime !== rightTime) {
            return rightTime.localeCompare(leftTime);
        }
        return (right.id || 0) - (left.id || 0);
    });
}

function replaceItemsForMonitoredObject(items, monitoredObjectId, nextItems) {
    return items.filter((item) => item.monitored_object_id !== monitoredObjectId).concat(nextItems);
}

function findGroupedEventForAlert(alert) {
    if (!alert) {
        return null;
    }

    const eventType = alert.metadata?.event_type;
    const monitoredObjectId = alert.monitored_object_id;
    const targetId = alert.target_id;

    if (eventType && monitoredObjectId !== null && monitoredObjectId !== undefined) {
        const byObjectAndType = state.events.find(
            (event) => event.monitored_object_id === monitoredObjectId && event.event_type === eventType
        );
        if (byObjectAndType) {
            return byObjectAndType;
        }
    }

    if (eventType && targetId) {
        const byTargetAndType = state.events.find(
            (event) => event.target_id === targetId && event.event_type === eventType
        );
        if (byTargetAndType) {
            return byTargetAndType;
        }
    }

    if (monitoredObjectId !== null && monitoredObjectId !== undefined) {
        return state.events.find((event) => event.monitored_object_id === monitoredObjectId) || null;
    }

    return null;
}

function sectionBlock(title, bodyHtml, metaHtml = "") {
    return `
        <section class="selection-summary-section">
            <div class="selection-summary-section-header">
                <h3>${escapeHtml(title)}</h3>
                ${metaHtml}
            </div>
            ${bodyHtml}
        </section>
    `;
}

function renderAlertCards(items, emptyMessage) {
    if (items.length === 0) {
        return `<p class="section-copy">${escapeHtml(emptyMessage)}</p>`;
    }
    return `
        <div class="selection-summary-card-list">
            ${items
                .map((alert) => {
                    const linkedEvent = findGroupedEventForAlert(alert);
                    return `
                        <article class="selection-summary-card ${cardSeverityClass(alert.severity)}${linkedEvent ? " is-actionable" : ""}" data-alert-id="${escapeHtml(alert.id)}"${linkedEvent ? ` data-linked-grouped-event-id="${escapeHtml(linkedEvent.id)}"` : ""}>
                            <h4>${escapeHtml(alert.alert_code)}</h4>
                            <p>${escapeHtml(alert.latest_message || "메시지 없음")}</p>
                            <p>${escapeHtml(alert.severity)} | ${escapeHtml(alert.status)} | 반복 ${escapeHtml(alert.repeat_count ?? 1)}회</p>
                            <p>${escapeHtml(formatTimestamp(alert.last_occurred_at))}</p>
                            ${linkedEvent ? `<p>관련 이벤트 열기: ${escapeHtml(linkedEvent.event_type)}</p>` : ""}
                        </article>
                    `;
                })
                .join("")}
        </div>
    `;
}

function renderGroupedEventCards(items, emptyMessage) {
    if (items.length === 0) {
        return `<p class="section-copy">${escapeHtml(emptyMessage)}</p>`;
    }
    return `
        <div class="selection-summary-card-list">
            ${items
                .map(
                    (event) => `
                        <article class="selection-summary-card ${cardSeverityClass(event.severity)} is-actionable" data-grouped-event-id="${escapeHtml(event.id)}">
                            <h4>${escapeHtml(event.event_type)}</h4>
                            <p>${escapeHtml(event.latest_message || "메시지 없음")}</p>
                            <p>${escapeHtml(event.severity)} | 반복 ${escapeHtml(event.repeat_count ?? 1)}회</p>
                            <p>${escapeHtml(formatTimestamp(event.last_occurred_at || event.occurred_at))}</p>
                            <p>raw event 상세 열기</p>
                        </article>
                    `
                )
                .join("")}
        </div>
    `;
}

function renderFanoutPills(items, currentNodeId) {
    if (items.length === 0) {
        return '<p class="section-copy">같은 runtime binding을 참조하는 노드가 없습니다.</p>';
    }
    return `
        <div class="selection-fanout-list">
            ${items
                .map(
                    (node) => `
                        <span class="selection-fanout-pill">
                            ${escapeHtml(node.display_name)}
                            <span>${escapeHtml(node.id === currentNodeId ? "현재 선택" : node.node_type)}</span>
                        </span>
                    `
                )
                .join("")}
        </div>
    `;
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
    const edge = state.edges.find((item) => item.id === state.selectedEdgeId);

    if (!node && !edge) {
        selectionSummary.innerHTML = "<p>노드나 관계선을 선택하면 runtime binding, latest state, alert, event를 함께 볼 수 있습니다.</p>";
        return;
    }

    if (node) {
        renderNodeSelection(node);
        return;
    }

    renderEdgeSelection(edge);
}

function renderNodeSelection(node) {
    const stateRow = latestStateForNode(node);
    const nodeAlerts = alertsForNode(node);
    const nodeEvents = groupedEventsForNode(node);
    const fanoutNodes = fanoutNodesForNode(node);
    const bindingRows = [
        { label: "타겟", value: node.target_id || "-" },
        { label: "모니터링 객체", value: node.monitored_object_id ?? "-" },
        { label: "구성 요소", value: node.node_type },
        { label: "semantic type", value: node.semantic_type_code || "-" },
        { label: "fan-out", value: `${fanoutNodes.length}개 node` },
    ];
    const overviewSection = sectionBlock(
        `${node.display_name}`,
        `<p class="selection-kind">${escapeHtml(node.node_type)}${stateRow ? ` | 상태 ${escapeHtml(runtimeStatusLabel(stateRow))} | 열린 alert ${escapeHtml(nodeAlerts.length)}건 | grouped event ${escapeHtml(nodeEvents.length)}건` : " | latest state 미수집"}</p>`,
        `<span class="meta-pill">${escapeHtml(node.node_type)}</span>`
    );
    const bindingSection = sectionBlock(
        "Runtime Binding",
        `
            <div class="detail-grid">${renderDetailRows(bindingRows)}</div>
            ${renderFanoutPills(fanoutNodes, node.id)}
        `
    );

    if (!stateRow) {
        selectionSummary.innerHTML = `
            ${overviewSection}
            ${bindingSection}
            ${sectionBlock("Open Alert", renderAlertCards(nodeAlerts.slice(0, 3), "현재 열린 alert가 없습니다."))}
            ${sectionBlock("최근 Grouped Event", renderGroupedEventCards(nodeEvents.slice(0, 3), "최근 grouped event가 없습니다."))}
        `;
        return;
    }

    const detailRows = buildStateDetailRows(node, stateRow);
    selectionSummary.innerHTML = `
        ${overviewSection}
        ${bindingSection}
        ${sectionBlock(
            "Latest State",
            `
                <div class="detail-grid">${renderDetailRows(detailRows)}</div>
                <details class="state-payload-block">
                    <summary>Raw state payload</summary>
                    <pre>${escapeHtml(JSON.stringify(stateRow.state, null, 2))}</pre>
                </details>
            `,
            `<span class="meta-pill">${escapeHtml(runtimeStatusLabel(stateRow))}</span>`
        )}
        ${sectionBlock("Open Alert", renderAlertCards(nodeAlerts.slice(0, 3), "현재 열린 alert가 없습니다."))}
        ${sectionBlock("최근 Grouped Event", renderGroupedEventCards(nodeEvents.slice(0, 3), "최근 grouped event가 없습니다."))}
    `;
}

function renderEdgeSelection(edge) {
    if (!edge) {
        selectionSummary.innerHTML = "<p>노드나 관계선을 선택하면 runtime binding, latest state, alert, event를 함께 볼 수 있습니다.</p>";
        return;
    }

    const sourceNode = state.nodes.find((item) => item.id === edge.source_node_id) || null;
    const targetNode = state.nodes.find((item) => item.id === edge.target_node_id) || null;
    const edgeEvents = uniqueById([
        ...groupedEventsForNode(sourceNode),
        ...groupedEventsForNode(targetNode),
    ]);
    const edgeAlerts = uniqueById([
        ...alertsForNode(sourceNode),
        ...alertsForNode(targetNode),
    ]);
    const edgeRows = [
        { label: "edge type", value: edge.edge_type || "-" },
        { label: "association", value: edge.association_code || "-" },
        { label: "semantic type", value: edge.semantic_type_code || "-" },
        { label: "source", value: sourceNode?.display_name || "-" },
        { label: "target", value: targetNode?.display_name || "-" },
    ];
    const endpointCard = (label, node) => {
        if (!node) {
            return `
                <article class="selection-summary-card">
                    <h4>${escapeHtml(label)}</h4>
                    <p>연결된 노드를 찾을 수 없습니다.</p>
                </article>
            `;
        }
        const latestState = latestStateForNode(node);
        const alerts = alertsForNode(node);
        const events = groupedEventsForNode(node);
        return `
            <article class="selection-summary-card ${cardSeverityClass(latestState?.severity || latestState?.status)}">
                <h4>${escapeHtml(label)} · ${escapeHtml(node.display_name)}</h4>
                <p>${escapeHtml(node.node_type)} | target ${escapeHtml(node.target_id || "-")}</p>
                <p>status ${escapeHtml(runtimeStatusLabel(latestState))} | alert ${escapeHtml(alerts.length)}건 | event ${escapeHtml(events.length)}건</p>
                <p>binding ${escapeHtml(node.monitored_object_id ?? "-")}</p>
            </article>
        `;
    };

    selectionSummary.innerHTML = `
        ${sectionBlock(
            edge.label || edge.association_code || edge.edge_type || "관계선",
            `
                <p class="selection-kind">${escapeHtml(sourceNode?.display_name || "-")} → ${escapeHtml(targetNode?.display_name || "-")}</p>
                <div class="detail-grid">${renderDetailRows(edgeRows)}</div>
            `,
            `<span class="meta-pill">${escapeHtml(edge.edge_type || "edge")}</span>`
        )}
        ${sectionBlock(
            "연결된 Runtime 대상",
            `<div class="selection-endpoint-grid">${endpointCard("Source", sourceNode)}${endpointCard("Target", targetNode)}</div>`
        )}
        ${sectionBlock("연결 Endpoint Alert", renderAlertCards(edgeAlerts.slice(0, 4), "연결된 endpoint에 열린 alert가 없습니다."))}
        ${sectionBlock("연결 Endpoint Event", renderGroupedEventCards(edgeEvents.slice(0, 4), "연결된 endpoint의 recent grouped event가 없습니다."))}
    `;
}

function render() {
    if (state.selectedNodeId !== null && !state.nodes.some((item) => item.id === state.selectedNodeId)) {
        state.selectedNodeId = null;
    }
    if (state.selectedEdgeId !== null && !state.edges.some((item) => item.id === state.selectedEdgeId)) {
        state.selectedEdgeId = null;
    }
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
        selectedEdgeId: state.selectedEdgeId,
        latestStatesByTargetId,
        latestStatesByMonitoredObjectId,
        alertsByMonitoredObjectId,
        onNodeClick: (node, event) => {
            event.stopPropagation();
            void selectNode(node.id);
        },
        onEdgeClick: (edge, event) => {
            event.stopPropagation();
            void selectEdge(edge.id);
        },
    });
    renderAgentSummary();
    renderAlerts();
    renderEvents();
    renderEventDetails();
    renderSelection();
}

function mergeRuntimeObjectSlice(payload) {
    state.latestStates = sortLatestStateItems(
        replaceItemsForMonitoredObject(state.latestStates, payload.monitored_object_id, payload.latest_states)
    );
    state.alerts = sortAlertItems(
        replaceItemsForMonitoredObject(state.alerts, payload.monitored_object_id, payload.alerts)
    );
    state.events = sortGroupedEventItems(
        replaceItemsForMonitoredObject(state.events, payload.monitored_object_id, payload.events)
    );
}

function selectedMonitoredObjectIds() {
    const selectedIds = new Set();
    const selectedNode = state.nodes.find((item) => item.id === state.selectedNodeId);
    if (selectedNode?.monitored_object_id) {
        selectedIds.add(selectedNode.monitored_object_id);
    }

    const selectedEdge = state.edges.find((item) => item.id === state.selectedEdgeId);
    if (selectedEdge) {
        const sourceNode = state.nodes.find((item) => item.id === selectedEdge.source_node_id);
        const targetNode = state.nodes.find((item) => item.id === selectedEdge.target_node_id);
        if (sourceNode?.monitored_object_id) {
            selectedIds.add(sourceNode.monitored_object_id);
        }
        if (targetNode?.monitored_object_id) {
            selectedIds.add(targetNode.monitored_object_id);
        }
    }

    return [...selectedIds];
}

function queueRealtimeUpdate(task) {
    realtimeUpdateQueue = realtimeUpdateQueue
        .then(task)
        .catch((error) => {
            showBanner(error.message, "error");
        });
    return realtimeUpdateQueue;
}

async function refreshRuntimeObjectSlice(monitoredObjectId, renderAfter = true) {
    const payload = await apiFetch(`/api/views/${state.viewId}/runtime-objects/${monitoredObjectId}/slice?limit=20`);
    mergeRuntimeObjectSlice(payload);

    if (state.selectedEventId && state.selectedGroupedEvent?.monitored_object_id === monitoredObjectId) {
        if (state.events.some((item) => item.id === state.selectedEventId)) {
            await loadEventDetails(state.selectedEventId);
            monitorStatus.textContent = `부분 갱신 ${new Date().toLocaleTimeString("ko-KR", { hour12: false })}`;
            return;
        }
        state.selectedEventId = null;
        state.selectedGroupedEvent = null;
        state.eventDetails = [];
        state.selectedRawEventId = null;
    }

    if (renderAfter) {
        render();
    }
    monitorStatus.textContent = `부분 갱신 ${new Date().toLocaleTimeString("ko-KR", { hour12: false })}`;
}

async function refreshRuntimeObjectSlices(monitoredObjectIds) {
    const uniqueIds = [...new Set(monitoredObjectIds.filter((value) => value !== null && value !== undefined))];
    if (uniqueIds.length === 0) {
        return;
    }
    await Promise.all(uniqueIds.map((monitoredObjectId) => refreshRuntimeObjectSlice(monitoredObjectId, false)));
    render();
    monitorStatus.textContent = `실시간 갱신 ${new Date().toLocaleTimeString("ko-KR", { hour12: false })}`;
}

async function refreshSelectionRuntimeSlice() {
    const objectIds = selectedMonitoredObjectIds();
    if (objectIds.length === 0) {
        return;
    }
    await Promise.all(objectIds.map((monitoredObjectId) => refreshRuntimeObjectSlice(monitoredObjectId, false)));
    render();
}

function clearRealtimeReconnectTimer() {
    if (state.realtimeReconnectTimerId !== null) {
        window.clearTimeout(state.realtimeReconnectTimerId);
        state.realtimeReconnectTimerId = null;
    }
}

function disconnectRealtimeStream() {
    clearRealtimeReconnectTimer();
    if (state.realtimeSource) {
        state.realtimeSource.close();
        state.realtimeSource = null;
    }
}

function scheduleRealtimeReconnect() {
    if (state.realtimeReconnectTimerId !== null) {
        return;
    }
    state.realtimeReconnectTimerId = window.setTimeout(() => {
        state.realtimeReconnectTimerId = null;
        connectRealtimeStream();
    }, 3000);
}

function connectRealtimeStream() {
    if (!window.EventSource || state.realtimeSource) {
        return;
    }

    clearRealtimeReconnectTimer();
    const stream = new window.EventSource(`/api/views/${state.viewId}/stream`);
    state.realtimeSource = stream;

    stream.addEventListener("connected", () => {
        monitorStatus.textContent = "실시간 연결됨";
    });

    stream.addEventListener("runtime_change", (event) => {
        queueRealtimeUpdate(async () => {
            const payload = JSON.parse(event.data);
            if (payload.view_id !== state.viewId) {
                return;
            }
            if (payload.full_refresh) {
                await refreshAll();
                return;
            }
            await refreshRuntimeObjectSlices(payload.monitored_object_ids || []);
        });
    });

    stream.onerror = () => {
        if (state.realtimeSource === stream) {
            state.realtimeSource = null;
        }
        stream.close();
        monitorStatus.textContent = "실시간 연결 재시도";
        scheduleRealtimeReconnect();
    };
}

async function selectNode(nodeId) {
    state.selectedNodeId = nodeId;
    state.selectedEdgeId = null;
    render();
    try {
        await refreshSelectionRuntimeSlice();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function selectEdge(edgeId) {
    state.selectedNodeId = null;
    state.selectedEdgeId = edgeId;
    render();
    try {
        await refreshSelectionRuntimeSlice();
    } catch (error) {
        showBanner(error.message, "error");
    }
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
selectionSummary?.addEventListener("click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }

    const groupedEventCard = target.closest("[data-grouped-event-id]");
    const alertCard = target.closest("[data-alert-id]");
    const linkedGroupedEventId = alertCard?.dataset.linkedGroupedEventId;
    const groupedEventId = groupedEventCard?.dataset.groupedEventId || linkedGroupedEventId;
    if (!groupedEventId) {
        return;
    }

    try {
        clearBanner();
        await loadEventDetails(Number(groupedEventId));
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
    void selectNode(Number(card.dataset.nodeId));
});
svg.addEventListener("click", () => {
    state.selectedNodeId = null;
    state.selectedEdgeId = null;
    render();
});

void refreshAll().then(() => {
    connectRealtimeStream();
});
window.addEventListener("beforeunload", disconnectRealtimeStream);
window.addEventListener("pagehide", disconnectRealtimeStream);
window.setInterval(refreshAll, POLL_INTERVAL_MS);


