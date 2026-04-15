import { apiFetch, clearBanner, formatTimestamp, showBanner } from "./common.js";

const summaryCards = document.getElementById("admin-summary-cards");
const generatedAt = document.getElementById("admin-generated-at");
const debugStatus = document.getElementById("admin-debug-status");
const ingestStatus = document.getElementById("admin-ingest-status");
const runtimeStatus = document.getElementById("admin-runtime-status");
const retentionPolicy = document.getElementById("admin-retention-policy");
const staleAgents = document.getElementById("admin-stale-agents");
const cleanupSummary = document.getElementById("admin-cleanup-summary");
const metamodelVersionsList = document.getElementById("admin-metamodel-versions-list");
const metamodelVersionCount = document.getElementById("metamodel-version-count");
const alertRulesList = document.getElementById("admin-alert-rules-list");
const alertRuleCount = document.getElementById("alert-rule-count");
const ingestList = document.getElementById("admin-ingest-list");
const latestStateList = document.getElementById("admin-latest-state-list");
const eventsList = document.getElementById("admin-events-list");
const alertsList = document.getElementById("admin-alerts-list");
const debugList = document.getElementById("admin-debug-list");
const cleanupList = document.getElementById("admin-cleanup-list");

const refreshAdminButton = document.getElementById("refresh-admin-button");
const refreshIngestButton = document.getElementById("refresh-ingest-button");
const refreshLatestStateButton = document.getElementById("refresh-latest-state-button");
const refreshEventsButton = document.getElementById("refresh-admin-events-button");
const refreshAlertsButton = document.getElementById("refresh-alerts-button");
const refreshDebugButton = document.getElementById("refresh-debug-button");
const refreshCleanupButton = document.getElementById("refresh-cleanup-button");
const refreshMetamodelVersionsButton = document.getElementById("refresh-metamodel-versions-button");
const refreshAlertRulesButton = document.getElementById("refresh-alert-rules-button");

const ingestStatusFilter = document.getElementById("ingest-status-filter");
const latestStateTypeFilter = document.getElementById("latest-state-type-filter");
const latestStateStatusFilter = document.getElementById("latest-state-status-filter");
const debugDirectionFilter = document.getElementById("debug-direction-filter");
const metamodelVersionForm = document.getElementById("metamodel-version-form");
const metamodelNamespaceSelect = document.getElementById("metamodel-namespace-select");
const metamodelBaseVersionSelect = document.getElementById("metamodel-base-version-select");
const metamodelVersionCodeInput = document.getElementById("metamodel-version-code");
const metamodelVersionDescriptionInput = document.getElementById("metamodel-version-description");
const alertRuleForm = document.getElementById("alert-rule-form");
const alertRuleFormTitle = document.getElementById("alert-rule-form-title");
const alertRuleFormMode = document.getElementById("alert-rule-form-mode");
const alertRuleFormResetButton = document.getElementById("alert-rule-form-reset");
const alertRuleIdInput = document.getElementById("alert-rule-id");
const alertRuleScopeTypeSelect = document.getElementById("alert-rule-scope-type");
const alertRuleStateTypeSelect = document.getElementById("alert-rule-state-type");
const alertRuleObjectTypeInput = document.getElementById("alert-rule-object-type");
const alertRuleMonitoredObjectIdInput = document.getElementById("alert-rule-monitored-object-id");
const alertRuleMetricKeyInput = document.getElementById("alert-rule-metric-key");
const alertRuleComparisonSelect = document.getElementById("alert-rule-comparison");
const alertRuleWarningThresholdInput = document.getElementById("alert-rule-warning-threshold");
const alertRuleCriticalThresholdInput = document.getElementById("alert-rule-critical-threshold");
const alertRuleDescriptionInput = document.getElementById("alert-rule-description");
const alertRuleEnabledInput = document.getElementById("alert-rule-enabled");

let metamodelVersions = [];
let alertRules = [];

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatJson(value) {
    return JSON.stringify(value, null, 2);
}

function formatNumber(value, fractionDigits = 1) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "-";
    }
    return Number(value).toFixed(fractionDigits);
}

function formatBytes(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "-";
    }

    const numeric = Number(value);
    if (numeric >= 1024 * 1024 * 1024) {
        return `${(numeric / (1024 * 1024 * 1024)).toFixed(1)} GiB`;
    }
    if (numeric >= 1024 * 1024) {
        return `${(numeric / (1024 * 1024)).toFixed(1)} MiB`;
    }
    if (numeric >= 1024) {
        return `${(numeric / 1024).toFixed(1)} KiB`;
    }
    return `${numeric} B`;
}

function toOptionalNumberValue(value) {
    if (value === "" || value === null || value === undefined) {
        return null;
    }
    return Number(value);
}

function renderMetaPills(entries) {
    return entries
        .map(
            ([label, value]) =>
                `<span class="meta-pill">${escapeHtml(label)} ${escapeHtml(value)}</span>`
        )
        .join("");
}

function buildStateSummary(item) {
    const state = item.state || {};
    if (item.state_type === "agent") {
        return [
            `연결 ${state.backend_connection_status || "-"}`,
            `outbox ${state.outbox_queue_depth ?? "-"}`,
            `ack ${state.last_ack_seq ?? "-"}`,
            `heartbeat ${formatNumber(state.heartbeat_age_seconds, 1)}s`,
        ];
    }

    if (item.state_type === "host") {
        return [
            `host ${state.hostname || "-"}`,
            `CPU ${formatNumber(state.cpu_usage)}%`,
            `Load ${formatNumber(state.loadavg_1, 2)}/${formatNumber(state.loadavg_5, 2)}`,
            `Mem ${formatBytes(state.memory_used)}/${formatBytes(state.memory_total)}`,
        ];
    }

    return [
        `상태 ${state.state || "-"}`,
        `CPU ${formatNumber(state.cpu_usage)}%`,
        `RSS ${formatBytes(state.memory_rss)}`,
        `threads ${state.thread_count ?? "-"}`,
    ];
}

function renderSummary(payload) {
    generatedAt.textContent = `기준 ${formatTimestamp(payload.generated_at)}`;
    debugStatus.textContent = payload.debug_payload_logging_enabled
        ? "debug mode 활성"
        : "debug mode 비활성";

    const cards = [
        ["서비스 상태", payload.service_status],
        ["사용자", payload.counts.users],
        ["뷰", payload.counts.views],
        ["노드", payload.counts.view_nodes],
        ["엣지", payload.counts.view_edges],
        ["latest state", payload.counts.latest_states],
        ["raw event", payload.counts.raw_events],
        ["open alert", payload.counts.open_alerts],
        ["alert rule", payload.counts.alert_rules],
        ["debug payload", payload.counts.debug_payload_logs],
        ["cleanup run", payload.counts.cleanup_runs],
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

    ingestStatus.innerHTML = renderMetaPills(
        Object.entries(payload.ingest_inbox.status_counts).map(([status, count]) => [status, count])
    );

    runtimeStatus.innerHTML = renderMetaPills([
        ["agent", payload.runtime.state_type_counts.agent],
        ["host", payload.runtime.state_type_counts.host],
        ["process", payload.runtime.state_type_counts.process],
        ["up", payload.runtime.status_counts.up],
        ["warning", payload.runtime.status_counts.warning],
        ["down", payload.runtime.status_counts.down],
        ["stale agent", payload.runtime.stale_agent_count],
    ]);

    retentionPolicy.innerHTML = renderMetaPills([
        ["raw event", `${payload.retention_policy.raw_events_days}일`],
        ["debug payload", `${payload.retention_policy.debug_payload_hours}시간`],
        ["ingest inbox", `${payload.retention_policy.ingest_inbox_days}일`],
    ]);

    if (payload.stale_agents.length === 0) {
        staleAgents.innerHTML = '<p class="section-copy">현재 주의가 필요한 agent가 없습니다.</p>';
    } else {
        staleAgents.innerHTML = payload.stale_agents
            .map((item) => {
                const state = item.state || {};
                return `
                    <article class="admin-item compact-admin-item">
                        <div class="section-header">
                            <h3>${escapeHtml(item.target_id)}</h3>
                            <span class="meta-pill">${escapeHtml(item.status)}</span>
                        </div>
                        <p class="admin-meta">연결 ${escapeHtml(state.backend_connection_status || "-")} | outbox ${escapeHtml(state.outbox_queue_depth ?? "-")} | ack ${escapeHtml(state.last_ack_seq ?? "-")}</p>
                        <p class="admin-meta">heartbeat age ${escapeHtml(formatNumber(state.heartbeat_age_seconds, 1))}s | ${escapeHtml(state.heartbeat_timeout_message || "정상")}</p>
                    </article>
                `;
            })
            .join("");
    }

    if (!payload.last_cleanup) {
        cleanupSummary.innerHTML = '<p class="section-copy">아직 cleanup 실행 기록이 없습니다.</p>';
        return;
    }

    cleanupSummary.innerHTML = `
        <article class="admin-item compact-admin-item">
            <div class="section-header">
                <h3>최근 실행</h3>
                <span class="meta-pill">${escapeHtml(formatTimestamp(payload.last_cleanup.finished_at))}</span>
            </div>
            <p class="admin-meta">raw event ${escapeHtml(payload.last_cleanup.raw_events_deleted)} | debug payload ${escapeHtml(payload.last_cleanup.debug_payload_logs_deleted)} | inbox ${escapeHtml(payload.last_cleanup.ingest_inbox_deleted)}</p>
            <p class="admin-meta">started=${escapeHtml(formatTimestamp(payload.last_cleanup.started_at))}</p>
        </article>
    `;
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

function renderLatestStates(items) {
    if (items.length === 0) {
        latestStateList.innerHTML = '<p class="section-copy">조건에 맞는 latest state가 없습니다.</p>';
        return;
    }

    latestStateList.innerHTML = items
        .map((item) => {
            const lines = buildStateSummary(item);
            return `
                <article class="admin-item">
                    <div class="section-header">
                        <h3>${escapeHtml(item.target_id)}</h3>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${escapeHtml(item.state_type)}</span>
                            <span class="meta-pill">${escapeHtml(item.status)}</span>
                        </div>
                    </div>
                    <p class="admin-meta">severity=${escapeHtml(item.severity)} | received=${escapeHtml(formatTimestamp(item.received_at))}</p>
                    <p class="admin-meta">${lines.map(escapeHtml).join(" | ")}</p>
                </article>
            `;
        })
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
                    <p>${escapeHtml(event.target_id)} | ${escapeHtml(event.severity)} | ${escapeHtml(formatTimestamp(event.occurred_at))}</p>
                </article>
            `
        )
        .join("");
}

function renderAlerts(items) {
    if (items.length === 0) {
        alertsList.innerHTML = '<p class="section-copy">현재 열린 alert가 없습니다.</p>';
        return;
    }

    alertsList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <h3>${escapeHtml(item.display_name || item.runtime_binding_key || item.alert_code)}</h3>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${escapeHtml(item.alert_code)}</span>
                            <span class="meta-pill">${escapeHtml(item.severity)}</span>
                        </div>
                    </div>
                    <p class="admin-meta">object=${escapeHtml(item.monitored_object_id)} | binding=${escapeHtml(item.runtime_binding_key || "-")} | type=${escapeHtml(item.semantic_type_code || "-")}</p>
                    <p class="admin-meta">반복 ${escapeHtml(item.repeat_count)}회 | 최근 ${escapeHtml(formatTimestamp(item.last_occurred_at))}</p>
                    <p class="admin-meta">${escapeHtml(item.latest_message || "메시지 없음")}</p>
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

function renderCleanupRuns(items) {
    if (items.length === 0) {
        cleanupList.innerHTML = '<p class="section-copy">최근 cleanup 기록이 없습니다.</p>';
        return;
    }

    cleanupList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <h3>cleanup #${escapeHtml(item.id)}</h3>
                        <span class="meta-pill">${escapeHtml(formatTimestamp(item.finished_at))}</span>
                    </div>
                    <p class="admin-meta">raw event ${escapeHtml(item.raw_events_deleted)} | debug payload ${escapeHtml(item.debug_payload_logs_deleted)} | inbox ${escapeHtml(item.ingest_inbox_deleted)}</p>
                    <p class="admin-meta">started=${escapeHtml(formatTimestamp(item.started_at))}</p>
                </article>
            `
        )
        .join("");
}

function renderMetamodelSelectOptions() {
    const namespaceCodes = [...new Set(metamodelVersions.map((item) => item.namespace_code))];
    const currentNamespace = metamodelNamespaceSelect.value || namespaceCodes[0] || "";

    metamodelNamespaceSelect.innerHTML = namespaceCodes
        .map(
            (code) => `
                <option value="${escapeHtml(code)}" ${code === currentNamespace ? "selected" : ""}>
                    ${escapeHtml(code)}
                </option>
            `
        )
        .join("");

    const baseVersions = metamodelVersions.filter((item) => item.namespace_code === (metamodelNamespaceSelect.value || currentNamespace));
    metamodelBaseVersionSelect.innerHTML = baseVersions
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}" ${item.status === "published" ? "selected" : ""}>
                    ${escapeHtml(item.version_code)} (${escapeHtml(item.status)})
                </option>
            `
        )
        .join("");
}

function renderMetamodelVersions(items) {
    metamodelVersions = items;
    metamodelVersionCount.textContent = `${items.length}개`;
    renderMetamodelSelectOptions();

    if (items.length === 0) {
        metamodelVersionsList.innerHTML = '<p class="section-copy">등록된 메타모델 버전이 없습니다.</p>';
        return;
    }

    metamodelVersionsList.innerHTML = items
        .map((item) => {
            const canPublish = item.status === "draft";
            return `
                <article class="admin-item">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.namespace_code)} / ${escapeHtml(item.version_code)}</h3>
                            <p class="admin-meta">상태 ${escapeHtml(item.status)} | 생성 ${escapeHtml(formatTimestamp(item.created_at))}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">type ${escapeHtml(item.semantic_type_count)}</span>
                            <span class="meta-pill">notation ${escapeHtml(item.notation_count)}</span>
                            <span class="meta-pill">palette ${escapeHtml(item.palette_group_count)}</span>
                            ${canPublish ? `<button class="button small primary publish-metamodel-button" type="button" data-version-id="${escapeHtml(item.id)}">Publish</button>` : ""}
                        </div>
                    </div>
                    <p class="admin-meta">기준 버전 ${escapeHtml(item.based_on_version_id ?? "-")} | published ${escapeHtml(formatTimestamp(item.published_at))}</p>
                    <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
                </article>
            `;
        })
        .join("");
}

function toggleAlertRuleScopeFields() {
    const isObjectType = alertRuleScopeTypeSelect.value === "object_type";
    alertRuleObjectTypeInput.disabled = !isObjectType;
    alertRuleMonitoredObjectIdInput.disabled = isObjectType;
}

function resetAlertRuleForm() {
    alertRuleForm.reset();
    alertRuleIdInput.value = "";
    alertRuleScopeTypeSelect.value = "object_type";
    alertRuleStateTypeSelect.value = "process";
    alertRuleComparisonSelect.value = "gte";
    alertRuleEnabledInput.checked = true;
    alertRuleFormTitle.textContent = "Alert Rule 생성";
    alertRuleFormMode.textContent = "create";
    toggleAlertRuleScopeFields();
}

function fillAlertRuleForm(rule) {
    alertRuleIdInput.value = String(rule.id);
    alertRuleScopeTypeSelect.value = rule.scope_type;
    alertRuleStateTypeSelect.value = rule.state_type;
    alertRuleObjectTypeInput.value = rule.object_type || "";
    alertRuleMonitoredObjectIdInput.value = rule.monitored_object_id ?? "";
    alertRuleMetricKeyInput.value = rule.metric_key || "";
    alertRuleComparisonSelect.value = rule.comparison;
    alertRuleWarningThresholdInput.value = rule.warning_threshold ?? "";
    alertRuleCriticalThresholdInput.value = rule.critical_threshold ?? "";
    alertRuleDescriptionInput.value = rule.description || "";
    alertRuleEnabledInput.checked = Boolean(rule.is_enabled);
    alertRuleFormTitle.textContent = `Alert Rule 수정 #${rule.id}`;
    alertRuleFormMode.textContent = "edit";
    toggleAlertRuleScopeFields();
}

function renderAlertRules(items) {
    alertRules = items;
    alertRuleCount.textContent = `${items.length}개`;

    if (items.length === 0) {
        alertRulesList.innerHTML = '<p class="section-copy">등록된 alert rule이 없습니다.</p>';
        return;
    }

    alertRulesList.innerHTML = items
        .map(
            (rule) => `
                <article class="admin-item ${rule.is_enabled ? "" : "is-disabled"}">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(rule.metric_key)}</h3>
                            <p class="admin-meta">${escapeHtml(rule.scope_type)} | ${escapeHtml(rule.state_type)} | ${escapeHtml(rule.comparison)}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${rule.is_enabled ? "enabled" : "disabled"}</span>
                            <button class="button ghost small edit-alert-rule-button" type="button" data-rule-id="${escapeHtml(rule.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">warning=${escapeHtml(rule.warning_threshold ?? "-")} | critical=${escapeHtml(rule.critical_threshold ?? "-")}</p>
                    <p class="admin-meta">object_type=${escapeHtml(rule.object_type || "-")} | monitored_object_id=${escapeHtml(rule.monitored_object_id ?? "-")}</p>
                    <p class="admin-meta">${escapeHtml(rule.description || "설명 없음")}</p>
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

async function loadLatestStates() {
    const params = new URLSearchParams({ limit: "10" });
    if (latestStateTypeFilter.value) {
        params.set("state_type", latestStateTypeFilter.value);
    }
    if (latestStateStatusFilter.value) {
        params.set("status", latestStateStatusFilter.value);
    }
    const payload = await apiFetch(`/api/admin/latest-states?${params.toString()}`);
    renderLatestStates(payload.items);
}

async function loadEvents() {
    const payload = await apiFetch("/api/admin/raw-events?limit=10");
    renderEvents(payload.items);
}

async function loadAlerts() {
    const payload = await apiFetch("/api/admin/alerts?limit=10&status=open");
    renderAlerts(payload.items);
}

async function loadDebug() {
    const params = new URLSearchParams({ limit: "10" });
    if (debugDirectionFilter.value) {
        params.set("direction", debugDirectionFilter.value);
    }
    const payload = await apiFetch(`/api/admin/debug-payloads?${params.toString()}`);
    renderDebug(payload);
}

async function loadCleanupRuns() {
    const payload = await apiFetch("/api/admin/cleanup-runs?limit=10");
    renderCleanupRuns(payload.items);
}

async function loadMetamodelVersions() {
    const payload = await apiFetch("/api/admin/metamodel/versions");
    renderMetamodelVersions(payload.items);
}

async function loadAlertRules() {
    const payload = await apiFetch("/api/admin/alert-rules");
    renderAlertRules(payload.items);
}

async function createMetamodelVersion(event) {
    event.preventDefault();
    clearBanner();

    try {
        const payload = {
            namespace_code: metamodelNamespaceSelect.value,
            based_on_version_id: Number(metamodelBaseVersionSelect.value),
            version_code: metamodelVersionCodeInput.value.trim(),
            description: metamodelVersionDescriptionInput.value.trim() || null,
        };

        await apiFetch("/api/admin/metamodel/versions", {
            method: "POST",
            body: payload,
        });

        metamodelVersionForm.reset();
        await loadMetamodelVersions();
        showBanner("메타모델 draft 버전을 생성했습니다.", "success");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function publishMetamodelVersion(versionId) {
    clearBanner();

    try {
        await apiFetch(`/api/admin/metamodel/versions/${versionId}/publish`, {
            method: "POST",
        });
        await loadMetamodelVersions();
        showBanner("메타모델 버전을 publish했습니다.", "success");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveAlertRule(event) {
    event.preventDefault();
    clearBanner();

    const ruleId = alertRuleIdInput.value ? Number(alertRuleIdInput.value) : null;
    const payload = {
        scope_type: alertRuleScopeTypeSelect.value,
        state_type: alertRuleStateTypeSelect.value,
        object_type: alertRuleObjectTypeInput.value.trim() || null,
        monitored_object_id: toOptionalNumberValue(alertRuleMonitoredObjectIdInput.value),
        metric_key: alertRuleMetricKeyInput.value.trim(),
        comparison: alertRuleComparisonSelect.value,
        warning_threshold: toOptionalNumberValue(alertRuleWarningThresholdInput.value),
        critical_threshold: toOptionalNumberValue(alertRuleCriticalThresholdInput.value),
        description: alertRuleDescriptionInput.value.trim() || null,
        is_enabled: alertRuleEnabledInput.checked,
    };

    try {
        if (ruleId) {
            await apiFetch(`/api/admin/alert-rules/${ruleId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("alert rule을 수정했습니다.", "success");
        } else {
            await apiFetch("/api/admin/alert-rules", {
                method: "POST",
                body: payload,
            });
            showBanner("alert rule을 생성했습니다.", "success");
        }

        await Promise.all([loadAlertRules(), loadSummary()]);
        resetAlertRuleForm();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function refreshAll() {
    clearBanner();
    try {
        await Promise.all([
            loadMetamodelVersions(),
            loadAlertRules(),
            loadSummary(),
            loadIngest(),
            loadLatestStates(),
            loadEvents(),
            loadAlerts(),
            loadDebug(),
            loadCleanupRuns(),
        ]);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

refreshAdminButton?.addEventListener("click", refreshAll);
refreshIngestButton?.addEventListener("click", loadIngest);
refreshLatestStateButton?.addEventListener("click", loadLatestStates);
refreshEventsButton?.addEventListener("click", loadEvents);
refreshAlertsButton?.addEventListener("click", loadAlerts);
refreshDebugButton?.addEventListener("click", loadDebug);
refreshCleanupButton?.addEventListener("click", loadCleanupRuns);
refreshMetamodelVersionsButton?.addEventListener("click", loadMetamodelVersions);
refreshAlertRulesButton?.addEventListener("click", loadAlertRules);
metamodelVersionForm?.addEventListener("submit", createMetamodelVersion);
metamodelNamespaceSelect?.addEventListener("change", renderMetamodelSelectOptions);
alertRuleForm?.addEventListener("submit", saveAlertRule);
alertRuleFormResetButton?.addEventListener("click", resetAlertRuleForm);
alertRuleScopeTypeSelect?.addEventListener("change", toggleAlertRuleScopeFields);
metamodelVersionsList?.addEventListener("click", async (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".publish-metamodel-button") : null;
    if (!button) {
        return;
    }

    const versionId = Number(button.dataset.versionId);
    if (!versionId) {
        return;
    }

    await publishMetamodelVersion(versionId);
});
alertRulesList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-alert-rule-button") : null;
    if (!button) {
        return;
    }

    const ruleId = Number(button.dataset.ruleId);
    const rule = alertRules.find((item) => item.id === ruleId);
    if (!rule) {
        return;
    }

    fillAlertRuleForm(rule);
});

ingestStatusFilter?.addEventListener("change", loadIngest);
latestStateTypeFilter?.addEventListener("change", loadLatestStates);
latestStateStatusFilter?.addEventListener("change", loadLatestStates);
debugDirectionFilter?.addEventListener("change", loadDebug);

resetAlertRuleForm();
refreshAll();
