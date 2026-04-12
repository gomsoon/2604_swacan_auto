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
            <p><strong>${node.display_name}</strong></p>
            <p>아직 runtime state가 없습니다.</p>
        `;
        return;
    }

    selectionSummary.innerHTML = `
        <p><strong>${node.display_name}</strong></p>
        <p>상태: ${stateRow.status}</p>
        <p>심각도: ${stateRow.severity || "-"}</p>
        <p>발생 시각: ${formatTimestamp(stateRow.occurred_at)}</p>
        <p>수신 시각: ${formatTimestamp(stateRow.received_at)}</p>
        <pre>${JSON.stringify(stateRow.state, null, 2)}</pre>
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
