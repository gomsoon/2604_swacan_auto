import { apiFetch, clearBanner, formatTimestamp, showBanner } from "./common.js";

const summaryCards = document.getElementById("admin-summary-cards");
const generatedAt = document.getElementById("admin-generated-at");
const debugStatus = document.getElementById("admin-debug-status");
const ingestStatus = document.getElementById("admin-ingest-status");
const ingestList = document.getElementById("admin-ingest-list");
const eventsList = document.getElementById("admin-events-list");
const debugList = document.getElementById("admin-debug-list");
const refreshAdminButton = document.getElementById("refresh-admin-button");
const refreshIngestButton = document.getElementById("refresh-ingest-button");
const refreshEventsButton = document.getElementById("refresh-admin-events-button");
const refreshDebugButton = document.getElementById("refresh-debug-button");
const ingestStatusFilter = document.getElementById("ingest-status-filter");
const debugDirectionFilter = document.getElementById("debug-direction-filter");

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('\"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatJson(value) {
    return JSON.stringify(value, null, 2);
}

function renderSummary(payload) {
    generatedAt.textContent = `기준 ${formatTimestamp(payload.generated_at)}`;
    debugStatus.textContent = payload.debug_payload_logging_enabled ? "debug mode 활성" : "debug mode 비활성";

    const cards = [
        ["서비스 상태", payload.service_status],
        ["사용자", payload.counts.users],
        ["뷰", payload.counts.views],
        ["노드", payload.counts.view_nodes],
        ["엣지", payload.counts.view_edges],
        ["latest state", payload.counts.latest_states],
        ["raw event", payload.counts.raw_events],
        ["debug payload", payload.counts.debug_payload_logs],
    ];

    summaryCards.innerHTML = cards
        .map(
            ([label, value]) => `
                <article class="stat-card">
                    <span class="stat-label">${escapeHtml(label)}</span>
                    <strong class="stat-value">${escapeHtml(value)}</strong>
                </article>
            `
        )
        .join("");

    ingestStatus.innerHTML = Object.entries(payload.ingest_inbox.status_counts)
        .map(
            ([status, count]) => `<span class="meta-pill">${escapeHtml(status)} ${escapeHtml(count)}</span>`
        )
        .join("");
}

function renderIngest(items) {
    if (items.length === 0) {
        ingestList.innerHTML = '<p class="section-copy">표시할 ingest batch가 없습니다.</p>';
        return;
    }

    ingestList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <h3>${escapeHtml(item.agent_id)} | ${escapeHtml(item.status)}</h3>
                        <span class="meta-pill">seq ${escapeHtml(item.seq_start)}-${escapeHtml(item.seq_end)}</span>
                    </div>
                    <p class="admin-meta">boot=${escapeHtml(item.boot_id)} | items=${escapeHtml(item.item_count ?? "-")}</p>
                    <p class="admin-meta">received=${escapeHtml(formatTimestamp(item.received_at))}</p>
                    <p class="admin-meta">processed=${escapeHtml(formatTimestamp(item.processed_at))}</p>
                    ${item.error_message ? `<p class="inline-error">${escapeHtml(item.error_message)}</p>` : ""}
                </article>
            `
        )
        .join("");
}

function renderEvents(items) {
    if (items.length === 0) {
        eventsList.innerHTML = '<p class="section-copy">최근 event가 없습니다.</p>';
        return;
    }

    eventsList.innerHTML = items
        .map(
            (event) => `
                <article class="event-item">
                    <h3>${escapeHtml(event.event_type)}</h3>
                    <p>${escapeHtml(event.message || "메시지 없음")}</p>
                    <p>${escapeHtml(event.target_id)} ? ${escapeHtml(event.severity)} ? ${escapeHtml(formatTimestamp(event.occurred_at))}</p>
                </article>
            `
        )
        .join("");
}

function renderDebug(payload) {
    if (payload.items.length === 0) {
        debugList.innerHTML = payload.debug_payload_logging_enabled
            ? '<p class="section-copy">표시할 debug payload가 없습니다.</p>'
            : '<p class="section-copy">debug mode가 비활성화되어 있습니다.</p>';
        return;
    }

    debugList.innerHTML = payload.items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <h3>${escapeHtml(item.channel)} | ${escapeHtml(item.direction)}</h3>
                        <span class="meta-pill">${escapeHtml(formatTimestamp(item.occurred_at))}</span>
                    </div>
                    <p class="admin-meta">endpoint=${escapeHtml(item.endpoint_or_topic)} | agent=${escapeHtml(item.agent_id || "-")}</p>
                    <p class="admin-meta">trace=${escapeHtml(item.trace_id || "-")} | user=${escapeHtml(item.username || "-")} | status=${escapeHtml(item.status_code ?? "-")}</p>
                    <pre class="payload-preview">${escapeHtml(formatJson(item.payload))}</pre>
                </article>
            `
        )
        .join("");
}

async function loadSummary() {
    const payload = await apiFetch("/api/admin/summary");
    renderSummary(payload);
}

async function loadIngest() {
    const params = new URLSearchParams({ limit: "10" });
    if (ingestStatusFilter.value) {
        params.set("status", ingestStatusFilter.value);
    }
    const payload = await apiFetch(`/api/admin/ingest-inbox?${params.toString()}`);
    renderIngest(payload.items);
}

async function loadEvents() {
    const payload = await apiFetch("/api/admin/raw-events?limit=10");
    renderEvents(payload.items);
}

async function loadDebug() {
    const params = new URLSearchParams({ limit: "10" });
    if (debugDirectionFilter.value) {
        params.set("direction", debugDirectionFilter.value);
    }
    const payload = await apiFetch(`/api/admin/debug-payloads?${params.toString()}`);
    renderDebug(payload);
}

async function refreshAll() {
    clearBanner();
    try {
        await Promise.all([loadSummary(), loadIngest(), loadEvents(), loadDebug()]);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

refreshAdminButton?.addEventListener("click", refreshAll);
refreshIngestButton?.addEventListener("click", loadIngest);
ingestStatusFilter?.addEventListener("change", loadIngest);
refreshEventsButton?.addEventListener("click", loadEvents);
refreshDebugButton?.addEventListener("click", loadDebug);
debugDirectionFilter?.addEventListener("change", loadDebug);

refreshAll();
