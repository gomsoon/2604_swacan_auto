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
const metamodelValidationPanel = document.getElementById("metamodel-validation-panel");
const metamodelSemanticTypesList = document.getElementById("admin-metamodel-semantic-types-list");
const metamodelSemanticTypeCount = document.getElementById("metamodel-semantic-type-count");
const metamodelPropertiesList = document.getElementById("admin-metamodel-properties-list");
const metamodelPropertyCount = document.getElementById("metamodel-property-count");
const metamodelContainmentRulesList = document.getElementById("admin-metamodel-containment-rules-list");
const metamodelContainmentRuleCount = document.getElementById("metamodel-containment-rule-count");
const metamodelNotationsList = document.getElementById("admin-metamodel-notations-list");
const metamodelNotationCount = document.getElementById("metamodel-notation-count");
const metamodelAssociationsList = document.getElementById("admin-metamodel-associations-list");
const metamodelAssociationCount = document.getElementById("metamodel-association-count");
const metamodelWorkspaceSummary = document.getElementById("metamodel-workspace-summary");
const metamodelWorkspaceOutline = document.getElementById("metamodel-workspace-outline");
const metamodelWorkspaceCanvas = document.getElementById("metamodel-workspace-canvas");
const metamodelWorkspaceInspector = document.getElementById("metamodel-workspace-inspector");
const metamodelWorkspaceModeStatus = document.getElementById("metamodel-workspace-mode-status");
const metamodelWorkspaceSelectModeButton = document.getElementById("metamodel-workspace-select-mode");
const metamodelWorkspaceCreateContainmentModeButton = document.getElementById("metamodel-workspace-create-containment-mode");
const metamodelWorkspaceCreateAssociationModeButton = document.getElementById("metamodel-workspace-create-association-mode");
const metamodelSemanticTypeSection = document.getElementById("metamodel-semantic-type-form")?.closest(".admin-subcard, .card");
const metamodelPropertySection = document.getElementById("metamodel-property-form")?.closest(".admin-subcard, .card");
const metamodelContainmentRuleSection = document.getElementById("metamodel-containment-rule-form")?.closest(".admin-subcard, .card");
const metamodelNotationSection = document.getElementById("metamodel-notation-form")?.closest(".admin-subcard, .card");
const metamodelAssociationSection = document.getElementById("metamodel-association-form")?.closest(".admin-subcard, .card");
const alertRulesList = document.getElementById("admin-alert-rules-list");
const alertRuleCount = document.getElementById("alert-rule-count");
const alertRulePreviewPanel = document.getElementById("alert-rule-preview-panel");
const ingestList = document.getElementById("admin-ingest-list");
const latestStateList = document.getElementById("admin-latest-state-list");
const eventsList = document.getElementById("admin-events-list");
const eventDetailPanel = document.getElementById("admin-event-detail-panel");
const alertsList = document.getElementById("admin-alerts-list");
const alertHistoryList = document.getElementById("admin-alert-history-list");
const debugList = document.getElementById("admin-debug-list");
const cleanupList = document.getElementById("admin-cleanup-list");

const refreshAdminButton = document.getElementById("refresh-admin-button");
const refreshIngestButton = document.getElementById("refresh-ingest-button");
const refreshLatestStateButton = document.getElementById("refresh-latest-state-button");
const refreshEventsButton = document.getElementById("refresh-admin-events-button");
const refreshAlertsButton = document.getElementById("refresh-alerts-button");
const refreshAlertHistoryButton = document.getElementById("refresh-alert-history-button");
const refreshDebugButton = document.getElementById("refresh-debug-button");
const refreshCleanupButton = document.getElementById("refresh-cleanup-button");
const refreshMetamodelVersionsButton = document.getElementById("refresh-metamodel-versions-button");
const refreshMetamodelSemanticTypesButton = document.getElementById("refresh-metamodel-semantic-types-button");
const refreshMetamodelPropertiesButton = document.getElementById("refresh-metamodel-properties-button");
const refreshMetamodelContainmentRulesButton = document.getElementById("refresh-metamodel-containment-rules-button");
const refreshMetamodelNotationsButton = document.getElementById("refresh-metamodel-notations-button");
const refreshMetamodelAssociationsButton = document.getElementById("refresh-metamodel-associations-button");
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
const metamodelDraftVersionSelect = document.getElementById("metamodel-draft-version-select");
const metamodelSemanticTypeForm = document.getElementById("metamodel-semantic-type-form");
const metamodelSemanticTypeFormTitle = document.getElementById("metamodel-semantic-type-form-title");
const metamodelSemanticTypeFormMode = document.getElementById("metamodel-semantic-type-form-mode");
const metamodelSemanticTypeFormResetButton = document.getElementById("metamodel-semantic-type-form-reset");
const metamodelSemanticTypeIdInput = document.getElementById("metamodel-semantic-type-id");
const metamodelSemanticTypeCodeInput = document.getElementById("metamodel-semantic-type-code");
const metamodelSemanticTypeDisplayNameInput = document.getElementById("metamodel-semantic-type-display-name");
const metamodelSemanticTypeKindSelect = document.getElementById("metamodel-semantic-type-kind");
const metamodelSemanticTypeRuntimeKindInput = document.getElementById("metamodel-semantic-type-runtime-kind");
const metamodelSemanticTypeDescriptionInput = document.getElementById("metamodel-semantic-type-description");
const metamodelSemanticTypeGroupableInput = document.getElementById("metamodel-semantic-type-groupable");
const metamodelSemanticTypeRuntimeBindingInput = document.getElementById("metamodel-semantic-type-runtime-binding");
const metamodelSemanticTypeActiveInput = document.getElementById("metamodel-semantic-type-active");
const metamodelPropertyForm = document.getElementById("metamodel-property-form");
const metamodelPropertyFormTitle = document.getElementById("metamodel-property-form-title");
const metamodelPropertyFormMode = document.getElementById("metamodel-property-form-mode");
const metamodelPropertyFormResetButton = document.getElementById("metamodel-property-form-reset");
const metamodelPropertyIdInput = document.getElementById("metamodel-property-id");
const metamodelPropertySemanticTypeIdInput = document.getElementById("metamodel-property-semantic-type-id");
const metamodelPropertyCodeInput = document.getElementById("metamodel-property-code");
const metamodelPropertyDisplayNameInput = document.getElementById("metamodel-property-display-name");
const metamodelPropertyValueTypeSelect = document.getElementById("metamodel-property-value-type");
const metamodelPropertyUnitInput = document.getElementById("metamodel-property-unit");
const metamodelPropertySortOrderInput = document.getElementById("metamodel-property-sort-order");
const metamodelPropertyDefaultValueJsonInput = document.getElementById("metamodel-property-default-value-json");
const metamodelPropertyDescriptionInput = document.getElementById("metamodel-property-description");
const metamodelPropertyRequiredInput = document.getElementById("metamodel-property-required");
const metamodelPropertyRuntimeInput = document.getElementById("metamodel-property-runtime");
const metamodelPropertyUserEditableInput = document.getElementById("metamodel-property-user-editable");
const metamodelContainmentRuleForm = document.getElementById("metamodel-containment-rule-form");
const metamodelContainmentRuleFormTitle = document.getElementById("metamodel-containment-rule-form-title");
const metamodelContainmentRuleFormMode = document.getElementById("metamodel-containment-rule-form-mode");
const metamodelContainmentRuleFormResetButton = document.getElementById("metamodel-containment-rule-form-reset");
const metamodelContainmentRuleIdInput = document.getElementById("metamodel-containment-rule-id");
const metamodelContainmentRuleVersionIdInput = document.getElementById("metamodel-containment-rule-version-id");
const metamodelContainmentParentTypeIdInput = document.getElementById("metamodel-containment-parent-type-id");
const metamodelContainmentChildTypeIdInput = document.getElementById("metamodel-containment-child-type-id");
const metamodelContainmentMinCountInput = document.getElementById("metamodel-containment-min-count");
const metamodelContainmentMaxCountInput = document.getElementById("metamodel-containment-max-count");
const metamodelContainmentCardinalityScopeInput = document.getElementById("metamodel-containment-cardinality-scope");
const metamodelContainmentIsRequiredInput = document.getElementById("metamodel-containment-is-required");
const metamodelNotationForm = document.getElementById("metamodel-notation-form");
const metamodelNotationFormTitle = document.getElementById("metamodel-notation-form-title");
const metamodelNotationFormMode = document.getElementById("metamodel-notation-form-mode");
const metamodelNotationFormResetButton = document.getElementById("metamodel-notation-form-reset");
const metamodelNotationIdInput = document.getElementById("metamodel-notation-id");
const metamodelNotationSemanticTypeIdInput = document.getElementById("metamodel-notation-semantic-type-id");
const metamodelNotationPaletteGroupIdInput = document.getElementById("metamodel-notation-palette-group-id");
const metamodelNotationCodeInput = document.getElementById("metamodel-notation-code");
const metamodelNotationDisplayNameInput = document.getElementById("metamodel-notation-display-name");
const metamodelNotationKindInput = document.getElementById("metamodel-notation-kind");
const metamodelNotationRenderPrimitiveInput = document.getElementById("metamodel-notation-render-primitive");
const metamodelNotationSortOrderInput = document.getElementById("metamodel-notation-sort-order");
const metamodelNotationRenderSchemaJsonInput = document.getElementById("metamodel-notation-render-schema-json");
const metamodelNotationStyleTokensJsonInput = document.getElementById("metamodel-notation-style-tokens-json");
const metamodelNotationIsDefaultInput = document.getElementById("metamodel-notation-is-default");
const metamodelNotationIsVisibleInPaletteInput = document.getElementById("metamodel-notation-is-visible-in-palette");
const metamodelAssociationForm = document.getElementById("metamodel-association-form");
const metamodelAssociationFormTitle = document.getElementById("metamodel-association-form-title");
const metamodelAssociationFormMode = document.getElementById("metamodel-association-form-mode");
const metamodelAssociationFormResetButton = document.getElementById("metamodel-association-form-reset");
const metamodelAssociationIdInput = document.getElementById("metamodel-association-id");
const metamodelAssociationSourceTypeIdInput = document.getElementById("metamodel-association-source-type-id");
const metamodelAssociationTargetTypeIdInput = document.getElementById("metamodel-association-target-type-id");
const metamodelAssociationCodeInput = document.getElementById("metamodel-association-code");
const metamodelAssociationDisplayNameInput = document.getElementById("metamodel-association-display-name");
const metamodelAssociationDirectionInput = document.getElementById("metamodel-association-direction");
const metamodelAssociationMultiplicitySourceInput = document.getElementById("metamodel-association-multiplicity-source");
const metamodelAssociationMultiplicityTargetInput = document.getElementById("metamodel-association-multiplicity-target");
const metamodelAssociationDescriptionInput = document.getElementById("metamodel-association-description");
const metamodelAssociationSemanticsJsonInput = document.getElementById("metamodel-association-semantics-json");
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
const alertRuleObjectTypeFilter = document.getElementById("alert-rule-object-type-filter");
const alertRuleScopeFilter = document.getElementById("alert-rule-scope-filter");
const alertRuleStateFilter = document.getElementById("alert-rule-state-filter");
const alertRuleEnabledFilter = document.getElementById("alert-rule-enabled-filter");
const alertStatusFilter = document.getElementById("alert-status-filter");
const alertAckFilter = document.getElementById("alert-ack-filter");

let metamodelVersions = [];
let metamodelSemanticTypes = [];
let metamodelProperties = [];
let metamodelContainmentRules = [];
let metamodelPaletteGroups = [];
let metamodelNotations = [];
let metamodelAssociations = [];
let alertRules = [];
let monitoredObjects = [];
let selectedAlertRuleId = null;
let selectedAlertRulePreview = null;
let groupedEvents = [];
let selectedGroupedEventId = null;
let selectedGroupedEvent = null;
let selectedGroupedEventRawItems = [];
let selectedRawEventId = null;
let selectedMetamodelSemanticTypeId = null;
let selectedMetamodelPropertyId = null;
let selectedMetamodelContainmentRuleId = null;
let selectedMetamodelNotationId = null;
let selectedMetamodelAssociationId = null;
let selectedMetamodelValidation = null;
let selectedMetamodelWorkspace = null;
let metamodelEditorFocusTimer = null;
let metamodelWorkspaceInteractionMode = "select";
let metamodelWorkspacePendingTypeId = null;

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

function setTemporarySectionFocus(section) {
    if (!section) {
        return;
    }

    section.classList.add("is-focus-target");
    if (metamodelEditorFocusTimer) {
        window.clearTimeout(metamodelEditorFocusTimer);
    }
    metamodelEditorFocusTimer = window.setTimeout(() => {
        section.classList.remove("is-focus-target");
        metamodelEditorFocusTimer = null;
    }, 1800);
}

function scrollToMetamodelEditorSection(section, input) {
    if (!section) {
        return;
    }

    section.scrollIntoView({ behavior: "smooth", block: "start" });
    setTemporarySectionFocus(section);
    if (input && typeof input.focus === "function") {
        window.setTimeout(() => {
            input.focus({ preventScroll: true });
            if (typeof input.select === "function" && input.tagName === "INPUT") {
                input.select();
            }
        }, 160);
    }
}

function setMetamodelWorkspaceInteractionMode(mode) {
    metamodelWorkspaceInteractionMode = mode;
    metamodelWorkspacePendingTypeId = null;
    renderMetamodelWorkspaceModeControls();
}

function renderMetamodelWorkspaceModeControls() {
    const isSelect = metamodelWorkspaceInteractionMode === "select";
    const isContainment = metamodelWorkspaceInteractionMode === "create_containment";
    const isAssociation = metamodelWorkspaceInteractionMode === "create_association";
    const pendingSemanticType = metamodelSemanticTypes.find((item) => item.id === metamodelWorkspacePendingTypeId);

    if (metamodelWorkspaceModeStatus) {
        if (isContainment) {
            metamodelWorkspaceModeStatus.textContent = pendingSemanticType
                ? `Containment: ${pendingSemanticType.display_name} 다음 대상 선택`
                : "Containment 연결 모드";
        } else if (isAssociation) {
            metamodelWorkspaceModeStatus.textContent = pendingSemanticType
                ? `Association: ${pendingSemanticType.display_name} 다음 대상 선택`
                : "Association 연결 모드";
        } else {
            metamodelWorkspaceModeStatus.textContent = "선택 모드";
        }
    }

    metamodelWorkspaceSelectModeButton?.classList.toggle("is-active", isSelect);
    metamodelWorkspaceCreateContainmentModeButton?.classList.toggle("is-active", isContainment);
    metamodelWorkspaceCreateAssociationModeButton?.classList.toggle("is-active", isAssociation);
}

async function openContainmentCreateFromCanvas(parentTypeId, childTypeId) {
    const existingRule = metamodelContainmentRules.find(
        (item) =>
            Number(item.parent_type_id) === Number(parentTypeId) &&
            Number(item.child_type_id) === Number(childTypeId) &&
            Number(item.metamodel_version_id) === Number(metamodelDraftVersionSelect.value)
    );

    if (existingRule) {
        selectedMetamodelWorkspace = { kind: "containment_rule", id: existingRule.id };
        fillMetamodelContainmentRuleForm(existingRule);
        refreshMetamodelWorkspace();
        scrollToMetamodelEditorSection(metamodelContainmentRuleSection, metamodelContainmentParentTypeIdInput);
        showBanner("이미 존재하는 containment rule을 편집 모드로 열었습니다.", "success");
        return;
    }

    const versionId = Number(metamodelDraftVersionSelect.value);
    const payload = {
        parent_type_id: Number(parentTypeId),
        child_type_id: Number(childTypeId),
        min_count: 0,
        max_count: null,
        cardinality_scope: "group_total",
        is_required: false,
    };
    const createdPayload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/containment-rules`, {
        method: "POST",
        body: payload,
    });
    await Promise.all([loadMetamodelVersions(), loadMetamodelContainmentRules()]);
    const created = createdPayload.containment_rule;
    if (created) {
        selectedMetamodelWorkspace = { kind: "containment_rule", id: created.id };
        fillMetamodelContainmentRuleForm(created);
        refreshMetamodelWorkspace();
    }
    scrollToMetamodelEditorSection(metamodelContainmentRuleSection, metamodelContainmentParentTypeIdInput);
    showBanner("Containment rule을 canvas에서 생성했습니다.", "success");
}

async function openAssociationCreateFromCanvas(sourceTypeId, targetTypeId) {
    const existingAssociation = metamodelAssociations.find(
        (item) =>
            Number(item.source_type_id) === Number(sourceTypeId) &&
            Number(item.target_type_id) === Number(targetTypeId)
    );
    if (existingAssociation) {
        selectedMetamodelWorkspace = { kind: "association_definition", id: existingAssociation.id };
        fillMetamodelAssociationForm(existingAssociation);
        refreshMetamodelWorkspace();
        scrollToMetamodelEditorSection(metamodelAssociationSection, metamodelAssociationCodeInput);
        showBanner("이미 존재하는 association definition을 편집 모드로 열었습니다.", "success");
        return;
    }

    const sourceType = metamodelSemanticTypes.find((item) => Number(item.id) === Number(sourceTypeId));
    const targetType = metamodelSemanticTypes.find((item) => Number(item.id) === Number(targetTypeId));
    const edgeType = metamodelSemanticTypes.find((item) => item.kind === "edge" && item.is_active);
    const normalizeCodeToken = (value) =>
        String(value || "")
            .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
            .replace(/[^A-Za-z0-9]+/g, "_")
            .replace(/^_+|_+$/g, "")
            .toLowerCase();

    if (sourceType && targetType) {
        const versionId = Number(metamodelDraftVersionSelect.value);
        const payload = {
            source_type_id: Number(sourceTypeId),
            target_type_id: Number(targetTypeId),
            code: `${normalizeCodeToken(sourceType.code)}_to_${normalizeCodeToken(targetType.code)}`,
            display_name: `${sourceType.display_name} -> ${targetType.display_name}`,
            direction: "directed",
            multiplicity_source: "1",
            multiplicity_target: "0..n",
            description: `${sourceType.display_name}에서 ${targetType.display_name}로 향하는 association`,
            semantics_json: edgeType
                ? JSON.stringify({ default_edge_type: edgeType.code }, null, 2)
                : null,
        };
        const createdPayload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/associations`, {
            method: "POST",
            body: payload,
        });
        await Promise.all([loadMetamodelVersions(), loadMetamodelAssociations()]);
        const created = createdPayload.association_definition;
        if (created) {
            selectedMetamodelWorkspace = { kind: "association_definition", id: created.id };
            fillMetamodelAssociationForm(created);
            refreshMetamodelWorkspace();
        }
        showBanner("Association definition을 canvas에서 생성했습니다.", "success");
        if (edgeType) {
            metamodelAssociationSemanticsJsonInput.value = JSON.stringify({ default_edge_type: edgeType.code }, null, 2);
        }
    }
    scrollToMetamodelEditorSection(metamodelAssociationSection, metamodelAssociationCodeInput);
}

function openMetamodelEditorFromInspector(action, kind, id) {
    const numericId = Number(id);
    if (!numericId) {
        return;
    }

    if (kind === "semantic_type") {
        const item = metamodelSemanticTypes.find((entry) => entry.id === numericId);
        if (!item) {
            return;
        }

        if (action === "edit-semantic-type") {
            fillMetamodelSemanticTypeForm(item);
            scrollToMetamodelEditorSection(metamodelSemanticTypeSection, metamodelSemanticTypeCodeInput);
            return;
        }

        if (action === "create-property") {
            metamodelPropertySemanticTypeIdInput.value = String(item.id);
            resetMetamodelPropertyForm();
            metamodelPropertySemanticTypeIdInput.value = String(item.id);
            scrollToMetamodelEditorSection(metamodelPropertySection, metamodelPropertyCodeInput);
            return;
        }

        if (action === "create-notation") {
            metamodelNotationSemanticTypeIdInput.value = String(item.id);
            resetMetamodelNotationForm({ preserveSemanticType: true });
            metamodelNotationSemanticTypeIdInput.value = String(item.id);
            scrollToMetamodelEditorSection(metamodelNotationSection, metamodelNotationCodeInput);
        }

        return;
    }

    if (kind === "containment_rule") {
        const item = metamodelContainmentRules.find((entry) => entry.id === numericId);
        if (!item) {
            return;
        }

        fillMetamodelContainmentRuleForm(item);
        scrollToMetamodelEditorSection(metamodelContainmentRuleSection, metamodelContainmentParentTypeIdInput);
        return;
    }

    if (kind === "notation_definition") {
        const item = metamodelNotations.find((entry) => entry.id === numericId);
        if (!item) {
            return;
        }

        fillMetamodelNotationForm(item);
        scrollToMetamodelEditorSection(metamodelNotationSection, metamodelNotationCodeInput);
        return;
    }

    if (kind === "association_definition") {
        const item = metamodelAssociations.find((entry) => entry.id === numericId);
        if (!item) {
            return;
        }

        fillMetamodelAssociationForm(item);
        scrollToMetamodelEditorSection(metamodelAssociationSection, metamodelAssociationCodeInput);
    }
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
        ["grouped event", `${payload.retention_policy.grouped_events_days}일`],
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
            <p class="admin-meta">raw event ${escapeHtml(payload.last_cleanup.raw_events_deleted)} | grouped event ${escapeHtml(payload.last_cleanup.grouped_events_deleted)} | debug payload ${escapeHtml(payload.last_cleanup.debug_payload_logs_deleted)} | inbox ${escapeHtml(payload.last_cleanup.ingest_inbox_deleted)}</p>
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
    groupedEvents = items;
    if (items.length === 0) {
        eventsList.innerHTML = '<p class="section-copy">최근 event가 없습니다.</p>';
        return;
    }

    eventsList.innerHTML = items
        .map(
            (event) => `
                <article class="event-item event-summary-item is-interactive${selectedGroupedEventId === event.id ? " is-selected" : ""}" data-grouped-event-id="${escapeHtml(event.id)}">
                    <h3>${escapeHtml(event.event_type)}</h3>
                    <p>${escapeHtml(event.latest_message || event.message || "메시지 없음")}</p>
                    <p>${escapeHtml(event.target_id)} | ${escapeHtml(event.severity)} | 반복 ${escapeHtml(event.repeat_count ?? 1)}회</p>
                    <p>${escapeHtml(formatTimestamp(event.last_occurred_at || event.occurred_at))}</p>
                </article>
            `
        )
        .join("");
}

function renderEventDetailPanel() {
    if (!selectedGroupedEvent) {
        eventDetailPanel.innerHTML = '<p class="section-copy">grouped event를 선택하면 raw event 상세를 확인할 수 있습니다.</p>';
        return;
    }

    const header = `
        <div class="section-header">
            <h3>${escapeHtml(selectedGroupedEvent.event_type)}</h3>
            <span class="meta-pill">반복 ${escapeHtml(selectedGroupedEvent.repeat_count ?? 1)}회</span>
        </div>
        <p class="admin-meta">${escapeHtml(selectedGroupedEvent.target_id || "-")} | ${escapeHtml(selectedGroupedEvent.severity)} | ${escapeHtml(formatTimestamp(selectedGroupedEvent.last_occurred_at || selectedGroupedEvent.occurred_at))}</p>
    `;

    if (selectedGroupedEventRawItems.length === 0) {
        eventDetailPanel.innerHTML = `
            ${header}
            <p class="section-copy">조건에 맞는 raw event가 없습니다.</p>
        `;
        return;
    }

    const selectedRawEvent =
        selectedGroupedEventRawItems.find((event) => event.id === selectedRawEventId) ||
        selectedGroupedEventRawItems[0];
    selectedRawEventId = selectedRawEvent.id;
    const payloadJson =
        selectedRawEvent.event !== undefined
            ? JSON.stringify(selectedRawEvent.event, null, 2)
            : null;

    eventDetailPanel.innerHTML = `
        ${header}
        <div class="event-drilldown-layout">
            <div class="event-list raw-event-list">
                ${selectedGroupedEventRawItems
                    .map(
                        (event) => `
                            <article class="event-item raw-event-item is-interactive${event.id === selectedRawEventId ? " is-selected" : ""}" data-raw-event-id="${escapeHtml(event.id)}">
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

function renderAlerts(items) {
    if (items.length === 0) {
        alertsList.innerHTML = '<p class="section-copy">표시할 alert가 없습니다.</p>';
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
                            <span class="meta-pill">${escapeHtml(item.status)}</span>
                            ${item.is_acknowledged ? '<span class="meta-pill">ACK</span>' : ""}
                            <button class="button ghost small toggle-alert-ack-button" type="button" data-alert-id="${escapeHtml(item.id)}" data-acknowledged="${item.is_acknowledged ? "true" : "false"}" data-ack-note="${escapeHtml(item.ack_note || "")}">${item.is_acknowledged ? "ACK 해제" : "ACK"}</button>
                            ${item.status !== "resolved" ? `<button class="button ghost small resolve-alert-button" type="button" data-alert-id="${escapeHtml(item.id)}" data-resolution-reason="${escapeHtml(item.status_note || "")}">해결 처리</button>` : ""}
                            ${buildAlertStatusButtons(item)}
                        </div>
                    </div>
                    <p class="admin-meta">object=${escapeHtml(item.monitored_object_id)} | binding=${escapeHtml(item.runtime_binding_key || "-")} | type=${escapeHtml(item.semantic_type_code || "-")}</p>
                    <p class="admin-meta">rule=${escapeHtml(item.source_rule_metric_key || item.alert_code)} | target=${escapeHtml(item.source_rule_target_label || "-")}</p>
                    <p class="admin-meta">반복 ${escapeHtml(item.repeat_count)}회 | 최근 ${escapeHtml(formatTimestamp(item.last_occurred_at))}</p>
                    <p class="admin-meta">${escapeHtml(item.latest_message || "메시지 없음")}</p>
                      ${
                          item.is_acknowledged
                              ? `<p class="admin-meta">ACK ${escapeHtml(item.acknowledged_by_username || "-")} | ${escapeHtml(formatTimestamp(item.acknowledged_at))}${item.ack_note ? ` | ${escapeHtml(item.ack_note)}` : ""}</p>`
                              : '<p class="admin-meta">ACK 대기 중</p>'
                      }
                      <p class="admin-meta">상태 업데이트 ${escapeHtml(item.status_updated_by_username || "-")} | ${escapeHtml(formatTimestamp(item.status_updated_at))}${item.status_note ? ` | ${escapeHtml(item.status_note)}` : ""}</p>
                      ${
                          item.resolved_at
                              ? `<p class="admin-meta">해결 ${escapeHtml(item.resolved_by_username || "-")} | ${escapeHtml(formatTimestamp(item.resolved_at))}</p>`
                              : ""
                      }
                </article>
            `
        )
        .join("");
}

function buildAlertStatusButtons(item) {
    const buttonSpecs = [];
    if (item.status !== "open") {
        buttonSpecs.push(["open", "재오픈"]);
    }
    if (item.status !== "in_progress") {
        buttonSpecs.push(["in_progress", "처리중"]);
    }
    if (item.status !== "suppressed") {
        buttonSpecs.push(["suppressed", "억제"]);
    }

    return buttonSpecs
        .map(
            ([nextStatus, label]) =>
                `<button class="button ghost small change-alert-status-button" type="button" data-alert-id="${escapeHtml(item.id)}" data-next-status="${escapeHtml(nextStatus)}" data-status-note="${escapeHtml(item.status_note || "")}">${escapeHtml(label)}</button>`
        )
        .join("");
}

function renderAlertHistoryArchive(items) {
    if (items.length === 0) {
        alertHistoryList.innerHTML = '<p class="section-copy">종료된 alert 이력이 없습니다.</p>';
        return;
    }

    alertHistoryList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item compact-admin-item">
                    <div class="section-header">
                        <h3>${escapeHtml(item.display_name || item.runtime_binding_key || item.alert_code)}</h3>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${escapeHtml(item.alert_code)}</span>
                            <span class="meta-pill">${escapeHtml(item.final_severity)}</span>
                            <span class="meta-pill">${escapeHtml(item.resolution_source)}</span>
                        </div>
                    </div>
                    <p class="admin-meta">opened=${escapeHtml(formatTimestamp(item.opened_at))} | resolved=${escapeHtml(formatTimestamp(item.resolved_at))}</p>
                    <p class="admin-meta">repeat ${escapeHtml(item.repeat_count)}회 | ack ${item.was_acknowledged ? "yes" : "no"}</p>
                    <p class="admin-meta">resolved by ${escapeHtml(item.resolved_by_username || "-")} | target ${escapeHtml(item.source_rule_target_label || item.semantic_type_code || "-")}</p>
                    <p class="admin-meta">${escapeHtml(item.resolution_reason || item.latest_message || "이유 없음")}</p>
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
                    <p class="admin-meta">raw event ${escapeHtml(item.raw_events_deleted)} | grouped event ${escapeHtml(item.grouped_events_deleted)} | debug payload ${escapeHtml(item.debug_payload_logs_deleted)} | inbox ${escapeHtml(item.ingest_inbox_deleted)}</p>
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

    const draftVersions = metamodelVersions.filter((item) => item.status === "draft");
    const currentDraftVersionId = metamodelDraftVersionSelect.value;
    const defaultDraftVersionId = draftVersions[0] ? String(draftVersions[0].id) : "";
    const selectedDraftVersionId = draftVersions.some((item) => String(item.id) === currentDraftVersionId)
        ? currentDraftVersionId
        : defaultDraftVersionId;
    metamodelDraftVersionSelect.innerHTML = draftVersions.length
        ? draftVersions
              .map(
                  (item) => `
                      <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedDraftVersionId) ? "selected" : ""}>
                          ${escapeHtml(item.namespace_code)} / ${escapeHtml(item.version_code)}
                      </option>
                  `
              )
              .join("")
        : '<option value="">draft 없음</option>';
    metamodelDraftVersionSelect.disabled = draftVersions.length === 0;
}

function renderMetamodelVersions(items) {
    metamodelVersions = items;
    metamodelVersionCount.textContent = `${items.length}개`;
    renderMetamodelSelectOptions();
    renderContainmentVersionOptions(metamodelContainmentRuleVersionIdInput.value || metamodelDraftVersionSelect.value);

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
                            ${canPublish ? `<button class="button ghost small validate-metamodel-button" type="button" data-version-id="${escapeHtml(item.id)}">Validate</button>` : ""}
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

function renderMetamodelValidationPanel() {
    if (!selectedMetamodelValidation) {
        metamodelValidationPanel.innerHTML =
            '<p class="section-copy">draft version의 validation 결과를 확인하면 publish 전 문제를 빠르게 파악할 수 있습니다.</p>';
        return;
    }

    const { version, validation } = selectedMetamodelValidation;
    const summary = validation.summary || {};
    const issues = validation.issues || [];

    metamodelValidationPanel.innerHTML = `
        <div class="section-header">
            <h3>${escapeHtml(version.namespace_code)} / ${escapeHtml(version.version_code)} validation</h3>
            <span class="meta-pill">${validation.is_valid ? "valid" : "invalid"}</span>
        </div>
        <div class="summary-metrics">
            ${renderMetaPills([
                ["semantic type", summary.semantic_type_count ?? 0],
                ["containment", summary.containment_rule_count ?? 0],
                ["association", summary.association_count ?? 0],
                ["error", summary.error_count ?? 0],
                ["warning", summary.warning_count ?? 0],
            ])}
        </div>
        ${
            issues.length === 0
                ? '<p class="section-copy">현재 publish를 막는 validation issue가 없습니다.</p>'
                : `<div class="admin-list compact-admin-list">
                    ${issues
                        .map(
                            (issue) => `
                                <article class="admin-item compact-admin-item">
                                    <div class="section-header">
                                        <h4>${escapeHtml(issue.code)}</h4>
                                        <span class="meta-pill">${escapeHtml(issue.severity)}</span>
                                    </div>
                                    <p class="admin-meta">${escapeHtml(issue.message || "설명 없음")}</p>
                                </article>
                            `
                        )
                        .join("")}
                </div>`
        }
    `;
}

function isSelectedMetamodelWorkspace(kind, id) {
    return (
        selectedMetamodelWorkspace &&
        selectedMetamodelWorkspace.kind === kind &&
        Number(selectedMetamodelWorkspace.id) === Number(id)
    );
}

function ensureMetamodelWorkspaceSelection() {
    if (
        selectedMetamodelWorkspace &&
        (
            (selectedMetamodelWorkspace.kind === "semantic_type" &&
                metamodelSemanticTypes.some((item) => item.id === selectedMetamodelWorkspace.id)) ||
            (selectedMetamodelWorkspace.kind === "containment_rule" &&
                metamodelContainmentRules.some((item) => item.id === selectedMetamodelWorkspace.id)) ||
            (selectedMetamodelWorkspace.kind === "association_definition" &&
                metamodelAssociations.some((item) => item.id === selectedMetamodelWorkspace.id)) ||
            (selectedMetamodelWorkspace.kind === "notation_definition" &&
                metamodelNotations.some((item) => item.id === selectedMetamodelWorkspace.id))
        )
    ) {
        return;
    }

    selectedMetamodelWorkspace = metamodelSemanticTypes[0]
        ? { kind: "semantic_type", id: metamodelSemanticTypes[0].id }
        : null;
}

function renderMetamodelWorkspaceOutline() {
    ensureMetamodelWorkspaceSelection();
    metamodelWorkspaceSummary.textContent = `${metamodelSemanticTypes.length} type`;

    const sections = [
        {
            title: "Semantic Types",
            items: metamodelSemanticTypes.map((item) => ({
                kind: "semantic_type",
                id: item.id,
                title: item.display_name,
                meta: `${item.code} | ${item.kind}`,
            })),
        },
        {
            title: "Containment",
            items: metamodelContainmentRules.map((item) => ({
                kind: "containment_rule",
                id: item.id,
                title: `${item.parent_type_display_name} -> ${item.child_type_display_name}`,
                meta: `${item.cardinality_scope} | min ${item.min_count ?? "-"} / max ${item.max_count ?? "-"}`,
            })),
        },
        {
            title: "Associations",
            items: metamodelAssociations.map((item) => ({
                kind: "association_definition",
                id: item.id,
                title: item.display_name,
                meta: `${item.source_type_code} -> ${item.target_type_code} | ${item.direction}`,
            })),
        },
        {
            title: "Notations",
            items: metamodelNotations.map((item) => ({
                kind: "notation_definition",
                id: item.id,
                title: item.display_name,
                meta: `${item.code} | ${item.render_primitive}`,
            })),
        },
    ].filter((section) => section.items.length > 0);

    if (sections.length === 0) {
        metamodelWorkspaceOutline.innerHTML =
            '<p class="section-copy">draft version을 선택하면 메타모델 구조를 여기에서 확인할 수 있습니다.</p>';
        return;
    }

    metamodelWorkspaceOutline.innerHTML = sections
        .map(
            (section) => `
                <section class="workspace-outline-section">
                    <div class="section-header">
                        <h4>${escapeHtml(section.title)}</h4>
                        <span class="meta-pill">${escapeHtml(section.items.length)}</span>
                    </div>
                    ${section.items
                        .map(
                            (item) => `
                                <article
                                    class="workspace-outline-item ${isSelectedMetamodelWorkspace(item.kind, item.id) ? "is-selected" : ""}"
                                    data-workspace-kind="${escapeHtml(item.kind)}"
                                    data-workspace-id="${escapeHtml(item.id)}"
                                >
                                    <h4>${escapeHtml(item.title)}</h4>
                                    <p class="admin-meta">${escapeHtml(item.meta)}</p>
                                </article>
                            `
                        )
                        .join("")}
                </section>
            `
        )
        .join("");
}

function buildNotationPreviewSvg(notation, semanticType) {
    const title = notation?.display_name || semanticType?.display_name || "Preview";
    const primitive = notation?.render_primitive || "rounded_rect";
    const doubleBorder =
        notation?.code?.includes("double_border") ||
        Boolean(notation?.render_schema?.double_border);
    const dashedBorder =
        notation?.code?.includes("dashed") ||
        notation?.render_schema?.border_style === "dashed" ||
        notation?.render_schema?.stroke_style === "dashed";

    if (primitive === "line") {
        return `
            <svg viewBox="0 0 240 140" role="img" aria-label="Notation preview">
                <line x1="40" y1="70" x2="200" y2="70" stroke="#50606d" stroke-width="4" ${dashedBorder ? 'stroke-dasharray="8 4"' : ""}></line>
                <text x="120" y="48" text-anchor="middle" font-size="14" font-weight="700" fill="#1f2a33">${escapeHtml(title)}</text>
            </svg>
        `;
    }

    const rx = primitive === "rounded_rect" ? 24 : 10;
    return `
        <svg viewBox="0 0 240 140" role="img" aria-label="Notation preview">
            <rect x="34" y="32" width="172" height="76" rx="${rx}" ry="${rx}" fill="#fffdfa" stroke="#405162" stroke-width="3" ${dashedBorder ? 'stroke-dasharray="8 4"' : ""}></rect>
            ${doubleBorder ? `<rect x="44" y="42" width="152" height="56" rx="${Math.max(rx - 8, 8)}" ry="${Math.max(rx - 8, 8)}" fill="none" stroke="#405162" stroke-width="1.4" ${dashedBorder ? 'stroke-dasharray="8 4"' : ""}></rect>` : ""}
            <text x="120" y="64" text-anchor="middle" font-size="16" font-weight="700" fill="#1f2a33">${escapeHtml(title)}</text>
            <text x="120" y="86" text-anchor="middle" font-size="11" fill="#58636b">${escapeHtml(semanticType?.code || notation?.code || "-")}</text>
        </svg>
    `;
}

function renderMetamodelWorkspaceInspector() {
    ensureMetamodelWorkspaceSelection();
    if (!selectedMetamodelWorkspace) {
        metamodelWorkspaceInspector.innerHTML =
            '<p class="section-copy">semantic type, containment, association, notation을 선택하면 우측 inspector에서 상세를 확인할 수 있습니다.</p>';
        return;
    }

    if (selectedMetamodelWorkspace.kind === "semantic_type") {
        const item = metamodelSemanticTypes.find((entry) => entry.id === selectedMetamodelWorkspace.id);
        if (!item) {
            metamodelWorkspaceInspector.innerHTML = '<p class="section-copy">선택한 semantic type을 찾을 수 없습니다.</p>';
            return;
        }
        const propertyCount =
            String(metamodelPropertySemanticTypeIdInput.value) === String(item.id) ? metamodelProperties.length : "-";
        const notationCount = metamodelNotations.filter((entry) => entry.semantic_type_id === item.id).length;
        const childCount = metamodelContainmentRules.filter((entry) => entry.parent_type_id === item.id).length;
        const parentCount = metamodelContainmentRules.filter((entry) => entry.child_type_id === item.id).length;
        const sourceAssocCount = metamodelAssociations.filter((entry) => entry.source_type_id === item.id).length;
        const targetAssocCount = metamodelAssociations.filter((entry) => entry.target_type_id === item.id).length;
        const defaultNotation = metamodelNotations.find((entry) => entry.semantic_type_id === item.id && entry.is_default);

        metamodelWorkspaceInspector.innerHTML = `
            <div class="section-header">
                <h3>${escapeHtml(item.display_name)}</h3>
                <span class="meta-pill">${escapeHtml(item.kind)}</span>
            </div>
            <p class="admin-meta">${escapeHtml(item.code)} | runtime ${escapeHtml(item.runtime_kind || "-")}</p>
            <div class="toolbar-inline inspector-actions">
                <button class="button ghost small" type="button" data-inspector-action="edit-semantic-type" data-workspace-kind="semantic_type" data-workspace-id="${escapeHtml(item.id)}">Semantic Type 편집</button>
                <button class="button ghost small" type="button" data-inspector-action="create-property" data-workspace-kind="semantic_type" data-workspace-id="${escapeHtml(item.id)}">새 Property</button>
                <button class="button ghost small" type="button" data-inspector-action="create-notation" data-workspace-kind="semantic_type" data-workspace-id="${escapeHtml(item.id)}">새 Notation</button>
            </div>
            <div class="summary-metrics">
                ${renderMetaPills([
                    ["property", propertyCount],
                    ["notation", notationCount],
                    ["contains", childCount],
                    ["parent", parentCount],
                    ["assoc out", sourceAssocCount],
                    ["assoc in", targetAssocCount],
                ])}
            </div>
            <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
            ${
                defaultNotation
                    ? `<div class="metamodel-notation-preview">
                        <h4>Default Notation Preview</h4>
                        ${buildNotationPreviewSvg(defaultNotation, item)}
                        <p class="admin-meta">${escapeHtml(defaultNotation.code)} | ${escapeHtml(defaultNotation.render_primitive)}</p>
                    </div>`
                    : '<p class="section-copy">default notation이 아직 지정되지 않았습니다.</p>'
            }
        `;
        return;
    }

    if (selectedMetamodelWorkspace.kind === "containment_rule") {
        const item = metamodelContainmentRules.find((entry) => entry.id === selectedMetamodelWorkspace.id);
        if (!item) {
            metamodelWorkspaceInspector.innerHTML = '<p class="section-copy">선택한 containment rule을 찾을 수 없습니다.</p>';
            return;
        }
        metamodelWorkspaceInspector.innerHTML = `
            <div class="section-header">
                <h3>${escapeHtml(item.parent_type_display_name)} -> ${escapeHtml(item.child_type_display_name)}</h3>
                <span class="meta-pill">${escapeHtml(item.cardinality_scope)}</span>
            </div>
            <p class="admin-meta">${escapeHtml(item.parent_type_code)} -> ${escapeHtml(item.child_type_code)}</p>
            <div class="toolbar-inline inspector-actions">
                <button class="button ghost small" type="button" data-inspector-action="edit-containment-rule" data-workspace-kind="containment_rule" data-workspace-id="${escapeHtml(item.id)}">Containment 편집</button>
            </div>
            <div class="summary-metrics">
                ${renderMetaPills([
                    ["min", item.min_count ?? "-"],
                    ["max", item.max_count ?? "-"],
                    ["required", item.is_required ? "yes" : "no"],
                ])}
            </div>
        `;
        return;
    }

    if (selectedMetamodelWorkspace.kind === "association_definition") {
        const item = metamodelAssociations.find((entry) => entry.id === selectedMetamodelWorkspace.id);
        if (!item) {
            metamodelWorkspaceInspector.innerHTML = '<p class="section-copy">선택한 association definition을 찾을 수 없습니다.</p>';
            return;
        }
        metamodelWorkspaceInspector.innerHTML = `
            <div class="section-header">
                <h3>${escapeHtml(item.display_name)}</h3>
                <span class="meta-pill">${escapeHtml(item.direction)}</span>
            </div>
            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.source_type_code)} -> ${escapeHtml(item.target_type_code)}</p>
            <div class="toolbar-inline inspector-actions">
                <button class="button ghost small" type="button" data-inspector-action="edit-association-definition" data-workspace-kind="association_definition" data-workspace-id="${escapeHtml(item.id)}">Association 편집</button>
            </div>
            <div class="summary-metrics">
                ${renderMetaPills([
                    ["source", item.multiplicity_source || "-"],
                    ["target", item.multiplicity_target || "-"],
                ])}
            </div>
            <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
            ${
                item.semantics_json
                    ? `<details class="state-payload-block" open><summary>Semantics JSON</summary><pre>${escapeHtml(JSON.stringify(item.semantics || {}, null, 2))}</pre></details>`
                    : '<p class="section-copy">semantics JSON이 없습니다.</p>'
            }
        `;
        return;
    }

    if (selectedMetamodelWorkspace.kind === "notation_definition") {
        const item = metamodelNotations.find((entry) => entry.id === selectedMetamodelWorkspace.id);
        if (!item) {
            metamodelWorkspaceInspector.innerHTML = '<p class="section-copy">선택한 notation definition을 찾을 수 없습니다.</p>';
            return;
        }
        const semanticType = metamodelSemanticTypes.find((entry) => entry.id === item.semantic_type_id);
        metamodelWorkspaceInspector.innerHTML = `
            <div class="section-header">
                <h3>${escapeHtml(item.display_name)}</h3>
                <span class="meta-pill">${escapeHtml(item.render_primitive)}</span>
            </div>
            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.kind)} | ${escapeHtml(item.semantic_type_code)}</p>
            <div class="toolbar-inline inspector-actions">
                <button class="button ghost small" type="button" data-inspector-action="edit-notation-definition" data-workspace-kind="notation_definition" data-workspace-id="${escapeHtml(item.id)}">Notation 편집</button>
            </div>
            <div class="summary-metrics">
                ${renderMetaPills([
                    ["default", item.is_default ? "yes" : "no"],
                    ["palette", item.is_visible_in_palette ? "visible" : "hidden"],
                    ["sort", item.sort_order ?? 0],
                ])}
            </div>
            <div class="metamodel-notation-preview">
                <h4>Notation Preview</h4>
                ${buildNotationPreviewSvg(item, semanticType)}
            </div>
        `;
    }
}

function renderMetamodelWorkspaceCanvas() {
    ensureMetamodelWorkspaceSelection();
    if (metamodelSemanticTypes.length === 0) {
        metamodelWorkspaceCanvas.setAttribute("viewBox", "0 0 1200 560");
        metamodelWorkspaceCanvas.innerHTML =
            '<text x="40" y="60" font-size="18" fill="#58636b">draft version을 선택하면 semantic type graph를 확인할 수 있습니다.</text>';
        return;
    }

    const layoutTypes = [...metamodelSemanticTypes];
    const columns = Math.min(3, Math.max(layoutTypes.length, 1));
    const startX = 80;
    const startY = 80;
    const colGap = 340;
    const rowGap = 180;
    const width = 240;
    const height = 92;
    const positions = new Map();

    layoutTypes.forEach((item, index) => {
        const col = index % columns;
        const row = Math.floor(index / columns);
        positions.set(item.id, {
            x: startX + col * colGap,
            y: startY + row * rowGap,
            width,
            height,
        });
    });

    const rows = Math.max(1, Math.ceil(layoutTypes.length / columns));
    const viewWidth = Math.max(1200, startX + (columns - 1) * colGap + width + 120);
    const viewHeight = Math.max(560, startY + (rows - 1) * rowGap + height + 140);

    const containmentSvg = metamodelContainmentRules
        .map((item) => {
            const source = positions.get(item.parent_type_id);
            const target = positions.get(item.child_type_id);
            if (!source || !target) {
                return "";
            }
            const x1 = source.x + source.width / 2;
            const y1 = source.y + source.height;
            const x2 = target.x + target.width / 2;
            const y2 = target.y;
            const labelX = (x1 + x2) / 2;
            const labelY = (y1 + y2) / 2 - 8;
            return `
                <g data-workspace-kind="containment_rule" data-workspace-id="${escapeHtml(item.id)}">
                    <path class="metamodel-link containment ${isSelectedMetamodelWorkspace("containment_rule", item.id) ? "is-selected" : ""}" d="M ${x1} ${y1} C ${x1} ${y1 + 50}, ${x2} ${y2 - 50}, ${x2} ${y2}"></path>
                    <text class="metamodel-link-label" x="${labelX}" y="${labelY}" text-anchor="middle">${escapeHtml(item.cardinality_scope)}</text>
                </g>
            `;
        })
        .join("");

    const associationSvg = metamodelAssociations
        .map((item) => {
            const source = positions.get(item.source_type_id);
            const target = positions.get(item.target_type_id);
            if (!source || !target) {
                return "";
            }
            const x1 = source.x + source.width;
            const y1 = source.y + source.height / 2;
            const x2 = target.x;
            const y2 = target.y + target.height / 2;
            const labelX = (x1 + x2) / 2;
            const labelY = (y1 + y2) / 2 - 8;
            return `
                <g data-workspace-kind="association_definition" data-workspace-id="${escapeHtml(item.id)}">
                    <path class="metamodel-link association ${isSelectedMetamodelWorkspace("association_definition", item.id) ? "is-selected" : ""}" d="M ${x1} ${y1} C ${x1 + 40} ${y1}, ${x2 - 40} ${y2}, ${x2} ${y2}"></path>
                    <text class="metamodel-link-label" x="${labelX}" y="${labelY}" text-anchor="middle">${escapeHtml(item.code)}</text>
                </g>
            `;
        })
        .join("");

    const nodeSvg = layoutTypes
        .map((item) => {
            const pos = positions.get(item.id);
            const nodeClass = item.kind === "runtime-only" ? "runtime-only" : item.kind;
            return `
                <g class="diagram-node metamodel-node kind-${escapeHtml(nodeClass)} ${isSelectedMetamodelWorkspace("semantic_type", item.id) ? "is-selected" : ""}" data-workspace-kind="semantic_type" data-workspace-id="${escapeHtml(item.id)}">
                    <rect class="node-shape" x="${pos.x}" y="${pos.y}" width="${pos.width}" height="${pos.height}" rx="${item.kind === "container" ? 22 : 14}" ry="${item.kind === "container" ? 22 : 14}"></rect>
                    <text class="node-label" x="${pos.x + 20}" y="${pos.y + 36}">${escapeHtml(item.display_name)}</text>
                    <text class="node-meta" x="${pos.x + 20}" y="${pos.y + 58}">${escapeHtml(item.code)} | ${escapeHtml(item.kind)}</text>
                    <text class="node-meta" x="${pos.x + 20}" y="${pos.y + 76}">default notation ${escapeHtml(item.default_notation_code || "-")}</text>
                </g>
            `;
        })
        .join("");

    metamodelWorkspaceCanvas.setAttribute("viewBox", `0 0 ${viewWidth} ${viewHeight}`);
    metamodelWorkspaceCanvas.innerHTML = `
        ${containmentSvg}
        ${associationSvg}
        ${nodeSvg}
    `;
}

function refreshMetamodelWorkspace() {
    ensureMetamodelWorkspaceSelection();
    renderMetamodelWorkspaceOutline();
    renderMetamodelWorkspaceCanvas();
    renderMetamodelWorkspaceInspector();
    renderMetamodelWorkspaceModeControls();
}

function resetMetamodelSemanticTypeForm() {
    metamodelSemanticTypeForm.reset();
    metamodelSemanticTypeIdInput.value = "";
    metamodelSemanticTypeKindSelect.value = "node";
    metamodelSemanticTypeGroupableInput.checked = false;
    metamodelSemanticTypeRuntimeBindingInput.checked = true;
    metamodelSemanticTypeActiveInput.checked = true;
    metamodelSemanticTypeFormTitle.textContent = "Semantic Type 생성";
    metamodelSemanticTypeFormMode.textContent = "create";
    selectedMetamodelSemanticTypeId = null;
}

function renderMetamodelPropertySemanticTypeOptions(selectedId = "") {
    const items = metamodelSemanticTypes
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedId) ? "selected" : ""}>
                    ${escapeHtml(item.display_name)} (${escapeHtml(item.code)})
                </option>
            `
        )
        .join("");

    metamodelPropertySemanticTypeIdInput.innerHTML = items
        ? items
        : '<option value="">선택 가능한 semantic type이 없습니다.</option>';
}

function renderContainmentVersionOptions(selectedId = "") {
    const draftVersions = metamodelVersions.filter((item) => item.status === "draft");
    metamodelContainmentRuleVersionIdInput.innerHTML = draftVersions.length
        ? draftVersions
              .map(
                  (item) => `
                      <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedId) ? "selected" : ""}>
                          ${escapeHtml(item.namespace_code)} / ${escapeHtml(item.version_code)}
                      </option>
                  `
              )
              .join("")
        : '<option value="">선택 가능한 draft version이 없습니다.</option>';
    metamodelContainmentRuleVersionIdInput.disabled = draftVersions.length === 0;
}

function renderContainmentSemanticTypeOptions(selectedParentId = "", selectedChildId = "") {
    const options = metamodelSemanticTypes
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}">
                    ${escapeHtml(item.display_name)} (${escapeHtml(item.code)})
                </option>
            `
        )
        .join("");

    const emptyOption = '<option value="">선택 가능한 semantic type이 없습니다.</option>';
    metamodelContainmentParentTypeIdInput.innerHTML = options || emptyOption;
    metamodelContainmentChildTypeIdInput.innerHTML = options || emptyOption;
    if (options) {
        metamodelContainmentParentTypeIdInput.value = String(selectedParentId || metamodelSemanticTypes[0]?.id || "");
        metamodelContainmentChildTypeIdInput.value = String(selectedChildId || metamodelSemanticTypes[1]?.id || metamodelSemanticTypes[0]?.id || "");
    }
}

function renderMetamodelNotationSemanticTypeOptions(selectedId = "") {
    const options = metamodelSemanticTypes
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedId) ? "selected" : ""}>
                    ${escapeHtml(item.display_name)} (${escapeHtml(item.code)})
                </option>
            `
        )
        .join("");

    metamodelNotationSemanticTypeIdInput.innerHTML = options
        ? options
        : '<option value="">선택 가능한 semantic type이 없습니다.</option>';
}

function renderMetamodelPaletteGroupOptions(selectedId = "") {
    const options = metamodelPaletteGroups
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedId) ? "selected" : ""}>
                    ${escapeHtml(item.label)} (${escapeHtml(item.code)})
                </option>
            `
        )
        .join("");

    metamodelNotationPaletteGroupIdInput.innerHTML = `
        <option value="">없음</option>
        ${options}
    `;
}

function renderMetamodelAssociationTypeOptions(selectedSourceId = "", selectedTargetId = "") {
    const options = metamodelSemanticTypes
        .map(
            (item) => `
                <option value="${escapeHtml(item.id)}">
                    ${escapeHtml(item.display_name)} (${escapeHtml(item.code)})
                </option>
            `
        )
        .join("");

    const emptyOption = '<option value="">선택 가능한 semantic type이 없습니다.</option>';
    metamodelAssociationSourceTypeIdInput.innerHTML = options || emptyOption;
    metamodelAssociationTargetTypeIdInput.innerHTML = options || emptyOption;
    if (options) {
        metamodelAssociationSourceTypeIdInput.value = String(selectedSourceId || metamodelSemanticTypes[0]?.id || "");
        metamodelAssociationTargetTypeIdInput.value = String(
            selectedTargetId || metamodelSemanticTypes[1]?.id || metamodelSemanticTypes[0]?.id || ""
        );
    }
}

function fillMetamodelSemanticTypeForm(item) {
    metamodelSemanticTypeIdInput.value = String(item.id);
    metamodelDraftVersionSelect.value = String(item.metamodel_version_id);
    metamodelSemanticTypeCodeInput.value = item.code || "";
    metamodelSemanticTypeDisplayNameInput.value = item.display_name || "";
    metamodelSemanticTypeKindSelect.value = item.kind;
    metamodelSemanticTypeRuntimeKindInput.value = item.runtime_kind || "";
    metamodelSemanticTypeDescriptionInput.value = item.description || "";
    metamodelSemanticTypeGroupableInput.checked = Boolean(item.is_groupable);
    metamodelSemanticTypeRuntimeBindingInput.checked = Boolean(item.allows_runtime_binding);
    metamodelSemanticTypeActiveInput.checked = Boolean(item.is_active);
    metamodelSemanticTypeFormTitle.textContent = `Semantic Type 수정 #${item.id}`;
    metamodelSemanticTypeFormMode.textContent = "edit";
    selectedMetamodelSemanticTypeId = item.id;
}

function resetMetamodelPropertyForm({ preserveSemanticType = true } = {}) {
    const currentSemanticTypeId = preserveSemanticType ? metamodelPropertySemanticTypeIdInput.value : "";
    metamodelPropertyForm.reset();
    metamodelPropertyIdInput.value = "";
    metamodelPropertyValueTypeSelect.value = "string";
    metamodelPropertySortOrderInput.value = "0";
    metamodelPropertyUserEditableInput.checked = true;
    metamodelPropertyRequiredInput.checked = false;
    metamodelPropertyRuntimeInput.checked = false;
    metamodelPropertyFormTitle.textContent = "Property Definition 생성";
    metamodelPropertyFormMode.textContent = "create";
    selectedMetamodelPropertyId = null;
    renderMetamodelPropertySemanticTypeOptions(currentSemanticTypeId);
}

function resetMetamodelContainmentRuleForm() {
    metamodelContainmentRuleForm.reset();
    metamodelContainmentRuleIdInput.value = "";
    metamodelContainmentCardinalityScopeInput.value = "group_total";
    metamodelContainmentIsRequiredInput.checked = false;
    metamodelContainmentRuleFormTitle.textContent = "Containment Rule 생성";
    metamodelContainmentRuleFormMode.textContent = "create";
    selectedMetamodelContainmentRuleId = null;
    renderContainmentVersionOptions(metamodelDraftVersionSelect.value);
    renderContainmentSemanticTypeOptions();
}

function resetMetamodelNotationForm({ preserveSemanticType = true } = {}) {
    const currentSemanticTypeId = preserveSemanticType ? metamodelNotationSemanticTypeIdInput.value : "";
    const currentPaletteGroupId = metamodelNotationPaletteGroupIdInput.value;
    metamodelNotationForm.reset();
    metamodelNotationIdInput.value = "";
    metamodelNotationKindInput.value = "node";
    metamodelNotationRenderPrimitiveInput.value = "rounded_rect";
    metamodelNotationSortOrderInput.value = "0";
    metamodelNotationIsDefaultInput.checked = false;
    metamodelNotationIsVisibleInPaletteInput.checked = true;
    metamodelNotationFormTitle.textContent = "Notation Definition 생성";
    metamodelNotationFormMode.textContent = "create";
    selectedMetamodelNotationId = null;
    renderMetamodelNotationSemanticTypeOptions(currentSemanticTypeId);
    renderMetamodelPaletteGroupOptions(currentPaletteGroupId);
}

function resetMetamodelAssociationForm() {
    metamodelAssociationForm.reset();
    metamodelAssociationIdInput.value = "";
    metamodelAssociationDirectionInput.value = "directed";
    metamodelAssociationFormTitle.textContent = "Association Definition 생성";
    metamodelAssociationFormMode.textContent = "create";
    selectedMetamodelAssociationId = null;
    renderMetamodelAssociationTypeOptions();
}

function fillMetamodelPropertyForm(item) {
    metamodelPropertyIdInput.value = String(item.id);
    metamodelPropertySemanticTypeIdInput.value = String(item.semantic_type_id);
    metamodelPropertyCodeInput.value = item.code || "";
    metamodelPropertyDisplayNameInput.value = item.display_name || "";
    metamodelPropertyValueTypeSelect.value = item.value_type;
    metamodelPropertyUnitInput.value = item.unit || "";
    metamodelPropertySortOrderInput.value = String(item.sort_order ?? 0);
    metamodelPropertyDefaultValueJsonInput.value = item.default_value_json || "";
    metamodelPropertyDescriptionInput.value = item.description || "";
    metamodelPropertyRequiredInput.checked = Boolean(item.is_required);
    metamodelPropertyRuntimeInput.checked = Boolean(item.is_runtime);
    metamodelPropertyUserEditableInput.checked = Boolean(item.is_user_editable);
    metamodelPropertyFormTitle.textContent = `Property Definition 수정 #${item.id}`;
    metamodelPropertyFormMode.textContent = "edit";
    selectedMetamodelPropertyId = item.id;
}

function fillMetamodelContainmentRuleForm(item) {
    metamodelContainmentRuleIdInput.value = String(item.id);
    metamodelContainmentRuleVersionIdInput.value = String(item.metamodel_version_id);
    renderContainmentSemanticTypeOptions(item.parent_type_id, item.child_type_id);
    metamodelContainmentMinCountInput.value = item.min_count ?? "";
    metamodelContainmentMaxCountInput.value = item.max_count ?? "";
    metamodelContainmentCardinalityScopeInput.value = item.cardinality_scope;
    metamodelContainmentIsRequiredInput.checked = Boolean(item.is_required);
    metamodelContainmentRuleFormTitle.textContent = `Containment Rule 수정 #${item.id}`;
    metamodelContainmentRuleFormMode.textContent = "edit";
    selectedMetamodelContainmentRuleId = item.id;
}

function fillMetamodelNotationForm(item) {
    metamodelNotationIdInput.value = String(item.id);
    renderMetamodelNotationSemanticTypeOptions(item.semantic_type_id);
    renderMetamodelPaletteGroupOptions(item.palette_group_id ?? "");
    metamodelNotationCodeInput.value = item.code || "";
    metamodelNotationDisplayNameInput.value = item.display_name || "";
    metamodelNotationKindInput.value = item.kind || "node";
    metamodelNotationRenderPrimitiveInput.value = item.render_primitive || "rounded_rect";
    metamodelNotationSortOrderInput.value = String(item.sort_order ?? 0);
    metamodelNotationRenderSchemaJsonInput.value = item.render_schema_json || "";
    metamodelNotationStyleTokensJsonInput.value = item.style_tokens_json || "";
    metamodelNotationIsDefaultInput.checked = Boolean(item.is_default);
    metamodelNotationIsVisibleInPaletteInput.checked = Boolean(item.is_visible_in_palette);
    metamodelNotationFormTitle.textContent = `Notation Definition 수정 #${item.id}`;
    metamodelNotationFormMode.textContent = "edit";
    selectedMetamodelNotationId = item.id;
}

function fillMetamodelAssociationForm(item) {
    metamodelAssociationIdInput.value = String(item.id);
    renderMetamodelAssociationTypeOptions(item.source_type_id, item.target_type_id);
    metamodelAssociationCodeInput.value = item.code || "";
    metamodelAssociationDisplayNameInput.value = item.display_name || "";
    metamodelAssociationDirectionInput.value = item.direction || "directed";
    metamodelAssociationMultiplicitySourceInput.value = item.multiplicity_source || "";
    metamodelAssociationMultiplicityTargetInput.value = item.multiplicity_target || "";
    metamodelAssociationDescriptionInput.value = item.description || "";
    metamodelAssociationSemanticsJsonInput.value = item.semantics_json || "";
    metamodelAssociationFormTitle.textContent = `Association Definition 수정 #${item.id}`;
    metamodelAssociationFormMode.textContent = "edit";
    selectedMetamodelAssociationId = item.id;
}

function renderMetamodelSemanticTypes(items) {
    metamodelSemanticTypes = items;
    metamodelSemanticTypeCount.textContent = `${items.length}개`;
    const previousSemanticTypeId = selectedMetamodelSemanticTypeId ?? metamodelPropertySemanticTypeIdInput.value;
    const nextSemanticTypeId = items.some((item) => String(item.id) === String(previousSemanticTypeId))
        ? String(previousSemanticTypeId)
        : (items[0] ? String(items[0].id) : "");
    renderMetamodelPropertySemanticTypeOptions(nextSemanticTypeId);
    renderContainmentSemanticTypeOptions(
        metamodelContainmentParentTypeIdInput.value,
        metamodelContainmentChildTypeIdInput.value
    );
    renderMetamodelNotationSemanticTypeOptions(
        metamodelNotationSemanticTypeIdInput.value || nextSemanticTypeId
    );
    renderMetamodelAssociationTypeOptions(
        metamodelAssociationSourceTypeIdInput.value,
        metamodelAssociationTargetTypeIdInput.value
    );
    if (selectedMetamodelSemanticTypeId && !items.some((item) => item.id === selectedMetamodelSemanticTypeId)) {
        selectedMetamodelSemanticTypeId = null;
    }

    if (items.length === 0) {
        metamodelSemanticTypesList.innerHTML = '<p class="section-copy">선택한 draft version에 semantic type이 없습니다.</p>';
        refreshMetamodelWorkspace();
        return;
    }

    metamodelSemanticTypesList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item ${item.is_active ? "" : "is-disabled"}">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.display_name)}</h3>
                            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.kind)} | runtime ${escapeHtml(item.runtime_kind || "-")}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${item.is_active ? "active" : "inactive"}</span>
                            <span class="meta-pill">${item.allows_runtime_binding ? "binding" : "no-binding"}</span>
                            <button class="button ghost small edit-metamodel-semantic-type-button" type="button" data-semantic-type-id="${escapeHtml(item.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">groupable=${item.is_groupable ? "true" : "false"} | default notation=${escapeHtml(item.default_notation_code || "-")}</p>
                    <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
                </article>
            `
        )
        .join("");
    refreshMetamodelWorkspace();
}

function renderMetamodelContainmentRules(items) {
    metamodelContainmentRules = items;
    metamodelContainmentRuleCount.textContent = `${items.length}개`;

    if (items.length === 0) {
        metamodelContainmentRulesList.innerHTML = '<p class="section-copy">선택한 draft version에 containment rule이 없습니다.</p>';
        refreshMetamodelWorkspace();
        return;
    }

    metamodelContainmentRulesList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.parent_type_display_name)} -> ${escapeHtml(item.child_type_display_name)}</h3>
                            <p class="admin-meta">${escapeHtml(item.parent_type_code)} -> ${escapeHtml(item.child_type_code)}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${escapeHtml(item.cardinality_scope)}</span>
                            <span class="meta-pill">${item.is_required ? "required" : "optional"}</span>
                            <button class="button ghost small edit-metamodel-containment-rule-button" type="button" data-containment-rule-id="${escapeHtml(item.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">min=${escapeHtml(item.min_count ?? "-")} | max=${escapeHtml(item.max_count ?? "-")}</p>
                </article>
            `
        )
        .join("");
    refreshMetamodelWorkspace();
}

function renderMetamodelNotations(items) {
    metamodelNotations = items;
    metamodelNotationCount.textContent = `${items.length}개`;

    if (items.length === 0) {
        metamodelNotationsList.innerHTML = '<p class="section-copy">선택한 semantic type에 notation definition이 없습니다.</p>';
        refreshMetamodelWorkspace();
        return;
    }

    metamodelNotationsList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item ${item.is_visible_in_palette ? "" : "is-disabled"}">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.display_name)}</h3>
                            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.kind)} | ${escapeHtml(item.render_primitive)}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${item.is_default ? "default" : "secondary"}</span>
                            <span class="meta-pill">${item.is_visible_in_palette ? "palette" : "hidden"}</span>
                            <button class="button ghost small edit-metamodel-notation-button" type="button" data-notation-id="${escapeHtml(item.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">palette=${escapeHtml(item.palette_group_label || "-")} | sort=${escapeHtml(item.sort_order)}</p>
                    <p class="admin-meta">schema=${escapeHtml(item.render_schema_json || "-")}</p>
                </article>
            `
        )
        .join("");
    refreshMetamodelWorkspace();
}

function renderMetamodelAssociations(items) {
    metamodelAssociations = items;
    metamodelAssociationCount.textContent = `${items.length}개`;

    if (items.length === 0) {
        metamodelAssociationsList.innerHTML = '<p class="section-copy">선택한 draft version에 association definition이 없습니다.</p>';
        refreshMetamodelWorkspace();
        return;
    }

    metamodelAssociationsList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.display_name)}</h3>
                            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.direction)}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${escapeHtml(item.multiplicity_source || "-")}</span>
                            <span class="meta-pill">${escapeHtml(item.multiplicity_target || "-")}</span>
                            <button class="button ghost small edit-metamodel-association-button" type="button" data-association-id="${escapeHtml(item.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">${escapeHtml(item.source_type_code)} -> ${escapeHtml(item.target_type_code)}</p>
                    <p class="admin-meta">semantics=${escapeHtml(item.semantics_json || "-")}</p>
                    <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
                </article>
            `
        )
        .join("");
    refreshMetamodelWorkspace();
}

function renderMetamodelProperties(items) {
    metamodelProperties = items;
    metamodelPropertyCount.textContent = `${items.length}개`;

    if (items.length === 0) {
        metamodelPropertiesList.innerHTML = '<p class="section-copy">선택한 semantic type에 property definition이 없습니다.</p>';
        refreshMetamodelWorkspace();
        return;
    }

    metamodelPropertiesList.innerHTML = items
        .map(
            (item) => `
                <article class="admin-item ${item.is_user_editable ? "" : "is-disabled"}">
                    <div class="section-header">
                        <div>
                            <h3>${escapeHtml(item.display_name)}</h3>
                            <p class="admin-meta">${escapeHtml(item.code)} | ${escapeHtml(item.value_type)} | sort ${escapeHtml(item.sort_order)}</p>
                        </div>
                        <div class="toolbar-inline">
                            <span class="meta-pill">${item.is_required ? "required" : "optional"}</span>
                            <span class="meta-pill">${item.is_runtime ? "runtime" : "design"}</span>
                            <button class="button ghost small edit-metamodel-property-button" type="button" data-property-id="${escapeHtml(item.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">unit=${escapeHtml(item.unit || "-")} | user_editable=${item.is_user_editable ? "true" : "false"}</p>
                    <p class="admin-meta">default=${escapeHtml(item.default_value_json || "-")}</p>
                    <p class="admin-meta">${escapeHtml(item.description || "설명 없음")}</p>
                </article>
            `
        )
        .join("");
    refreshMetamodelWorkspace();
}

function renderMonitoredObjectOptions(selectedId = "") {
    const optionItems = monitoredObjects.map(
        (item) => `
            <option value="${escapeHtml(item.id)}" ${String(item.id) === String(selectedId) ? "selected" : ""}>
                ${escapeHtml(item.display_name)} [${escapeHtml(item.object_type)}] · view ${escapeHtml(item.active_view_count)} · node ${escapeHtml(item.active_node_count)}
            </option>
        `
    );

    alertRuleMonitoredObjectIdInput.innerHTML = `
        <option value="">선택하세요</option>
        ${optionItems.join("")}
    `;

    const objectTypes = [...new Set(monitoredObjects.map((item) => item.object_type))].sort();
    const currentObjectTypeFilter = alertRuleObjectTypeFilter.value;
    alertRuleObjectTypeFilter.innerHTML = `
        <option value="">전체</option>
        ${objectTypes
            .map(
                (item) => `<option value="${escapeHtml(item)}" ${item === currentObjectTypeFilter ? "selected" : ""}>${escapeHtml(item)}</option>`
            )
            .join("")}
    `;
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
    renderMonitoredObjectOptions();
}

function fillAlertRuleForm(rule) {
    alertRuleIdInput.value = String(rule.id);
    alertRuleScopeTypeSelect.value = rule.scope_type;
    alertRuleStateTypeSelect.value = rule.state_type;
    alertRuleObjectTypeInput.value = rule.object_type || "";
    renderMonitoredObjectOptions(rule.monitored_object_id ?? "");
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
                            <button class="button ghost small preview-alert-rule-button" type="button" data-rule-id="${escapeHtml(rule.id)}">미리보기</button>
                            <button class="button ghost small toggle-alert-rule-button" type="button" data-rule-id="${escapeHtml(rule.id)}" data-enabled="${rule.is_enabled ? "true" : "false"}">${rule.is_enabled ? "비활성화" : "활성화"}</button>
                            <button class="button ghost small edit-alert-rule-button" type="button" data-rule-id="${escapeHtml(rule.id)}">수정</button>
                        </div>
                    </div>
                    <p class="admin-meta">warning=${escapeHtml(rule.warning_threshold ?? "-")} | critical=${escapeHtml(rule.critical_threshold ?? "-")}</p>
                    <p class="admin-meta">target=${escapeHtml(rule.target_display_name || rule.object_type || "-")} | binding=${escapeHtml(rule.target_runtime_binding_key || "-")} | monitored_object_id=${escapeHtml(rule.monitored_object_id ?? "-")}</p>
                    <p class="admin-meta">${escapeHtml(rule.description || "설명 없음")}</p>
                </article>
            `
        )
        .join("");
}

function renderAlertRulePreviewPanel() {
    if (!selectedAlertRulePreview) {
        alertRulePreviewPanel.innerHTML = '<p class="section-copy">rule의 적용 대상을 확인하려면 미리보기를 선택하세요.</p>';
        return;
    }

    const { rule, summary, items } = selectedAlertRulePreview;
    const header = `
        <div class="section-header">
            <h3>${escapeHtml(rule.metric_key)}</h3>
            <div class="toolbar-inline">
                <span class="meta-pill">${escapeHtml(rule.scope_type)}</span>
                <span class="meta-pill">${escapeHtml(rule.state_type)}</span>
                <span class="meta-pill">${rule.is_enabled ? "enabled" : "disabled"}</span>
            </div>
        </div>
        <p class="admin-meta">warning=${escapeHtml(rule.warning_threshold ?? "-")} | critical=${escapeHtml(rule.critical_threshold ?? "-")} | comparison=${escapeHtml(rule.comparison)}</p>
    `;

    const summaryBlock = `
        <div class="summary-metrics">
            ${renderMetaPills([
                ["matched object", summary?.matched_object_count ?? 0],
                ["active view", summary?.active_view_count ?? 0],
                ["active node", summary?.active_node_count ?? 0],
                ["active alert", summary?.open_alert_count ?? 0],
                ["rule alert", summary?.source_rule_open_alert_count ?? 0],
                ["metric available", summary?.metric_available_count ?? 0],
                ["warning match", summary?.warning_match_count ?? 0],
                ["critical match", summary?.critical_match_count ?? 0],
            ])}
        </div>
    `;

    if (items.length === 0) {
        alertRulePreviewPanel.innerHTML = `
            ${header}
            ${summaryBlock}
            <p class="section-copy">현재 이 rule에 매칭되는 monitored object가 없습니다.</p>
        `;
        return;
    }

    alertRulePreviewPanel.innerHTML = `
        ${header}
        ${summaryBlock}
        <div class="admin-list compact-admin-list">
            ${items
                .map(
                    (item) => `
                        <article class="admin-item compact-admin-item">
                            <div class="section-header">
                                <h4>${escapeHtml(item.display_name)}</h4>
                                <div class="toolbar-inline">
                                    <span class="meta-pill">active alert ${escapeHtml(item.open_alert_count)}</span>
                                    <span class="meta-pill">rule alert ${escapeHtml(item.source_rule_open_alert_count)}</span>
                                    <span class="meta-pill">${escapeHtml(item.threshold_level)}</span>
                                </div>
                            </div>
                            <p class="admin-meta">object=${escapeHtml(item.monitored_object_id)} | type=${escapeHtml(item.object_type)}</p>
                            <p class="admin-meta">binding=${escapeHtml(item.runtime_binding_key || "-")}</p>
                            <p class="admin-meta">active view ${escapeHtml(item.active_view_count)} | active node ${escapeHtml(item.active_node_count)}</p>
                            <p class="admin-meta">latest state ${escapeHtml(item.latest_state_status || "-")} | latest severity ${escapeHtml(item.latest_state_severity || "-")} | received ${escapeHtml(formatTimestamp(item.latest_received_at))}</p>
                            <p class="admin-meta">current metric ${escapeHtml(rule.metric_key)}=${escapeHtml(item.current_metric_value ?? "-")}</p>
                        </article>
                    `
                )
                .join("")}
        </div>
    `;
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
    const payload = await apiFetch("/api/admin/grouped-events?limit=10");
    renderEvents(payload.items);
    if (selectedGroupedEventId && payload.items.some((item) => item.id === selectedGroupedEventId)) {
        await loadGroupedEventDetails(selectedGroupedEventId);
        return;
    }
    selectedGroupedEventId = null;
    selectedGroupedEvent = null;
    selectedGroupedEventRawItems = [];
    selectedRawEventId = null;
    renderEventDetailPanel();
}

async function loadAlerts() {
    const params = new URLSearchParams({ limit: "10", status: alertStatusFilter?.value || "active" });
    if (alertAckFilter.value) {
        params.set("is_acknowledged", alertAckFilter.value);
    }
    const payload = await apiFetch(`/api/admin/alerts?${params.toString()}`);
    renderAlerts(payload.items);
}

async function loadAlertHistoryArchive() {
    const payload = await apiFetch("/api/admin/alert-history?limit=10");
    renderAlertHistoryArchive(payload.items);
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

async function loadMetamodelValidation(versionId) {
    const payload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/validation`);
    selectedMetamodelValidation = payload;
    renderMetamodelValidationPanel();
}

async function loadMetamodelSemanticTypes() {
    const versionId = metamodelDraftVersionSelect.value;
    if (!versionId) {
        metamodelSemanticTypes = [];
        renderMetamodelSemanticTypes([]);
        renderMetamodelProperties([]);
        renderMetamodelNotations([]);
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/semantic-types`);
    renderMetamodelSemanticTypes(payload.items);
}

async function loadMetamodelProperties() {
    const semanticTypeId = metamodelPropertySemanticTypeIdInput.value;
    if (!semanticTypeId) {
        metamodelProperties = [];
        renderMetamodelProperties([]);
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/semantic-types/${semanticTypeId}/properties`);
    renderMetamodelProperties(payload.items);
}

async function loadMetamodelContainmentRules() {
    const versionId = metamodelContainmentRuleVersionIdInput.value || metamodelDraftVersionSelect.value;
    if (!versionId) {
        metamodelContainmentRules = [];
        renderMetamodelContainmentRules([]);
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/containment-rules`);
    renderMetamodelContainmentRules(payload.items);
}

async function loadMetamodelPaletteGroups() {
    const versionId = metamodelDraftVersionSelect.value;
    if (!versionId) {
        metamodelPaletteGroups = [];
        renderMetamodelPaletteGroupOptions("");
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/palette-groups`);
    metamodelPaletteGroups = payload.items;
    renderMetamodelPaletteGroupOptions(metamodelNotationPaletteGroupIdInput.value);
}

async function loadMetamodelNotations() {
    const semanticTypeId = metamodelNotationSemanticTypeIdInput.value;
    if (!semanticTypeId) {
        metamodelNotations = [];
        renderMetamodelNotations([]);
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/semantic-types/${semanticTypeId}/notations`);
    renderMetamodelNotations(payload.items);
}

async function loadMetamodelAssociations() {
    const versionId = metamodelDraftVersionSelect.value;
    if (!versionId) {
        metamodelAssociations = [];
        renderMetamodelAssociations([]);
        return;
    }
    const payload = await apiFetch(`/api/admin/metamodel/versions/${versionId}/associations`);
    renderMetamodelAssociations(payload.items);
}

async function loadMonitoredObjects() {
    const payload = await apiFetch("/api/admin/monitored-objects?limit=100");
    monitoredObjects = payload.items;
    renderMonitoredObjectOptions(alertRuleMonitoredObjectIdInput.value);
}

async function loadAlertRules() {
    const params = new URLSearchParams();
    if (alertRuleScopeFilter.value) {
        params.set("scope_type", alertRuleScopeFilter.value);
    }
    if (alertRuleStateFilter.value) {
        params.set("state_type", alertRuleStateFilter.value);
    }
    if (alertRuleEnabledFilter.value) {
        params.set("is_enabled", alertRuleEnabledFilter.value);
    }
    if (alertRuleObjectTypeFilter.value) {
        params.set("object_type", alertRuleObjectTypeFilter.value);
    }
    const query = params.toString();
    const payload = await apiFetch(`/api/admin/alert-rules${query ? `?${query}` : ""}`);
    renderAlertRules(payload.items);
    if (selectedAlertRuleId && payload.items.some((item) => item.id === selectedAlertRuleId)) {
        await loadAlertRulePreview(selectedAlertRuleId);
        return;
    }
    selectedAlertRuleId = null;
    selectedAlertRulePreview = null;
    renderAlertRulePreviewPanel();
}

async function loadAlertRulePreview(ruleId) {
    const payload = await apiFetch(`/api/admin/alert-rules/${ruleId}/targets-preview?limit=20`);
    selectedAlertRuleId = ruleId;
    selectedAlertRulePreview = payload;
    renderAlertRulePreviewPanel();
}

async function toggleAlertRule(ruleId, isEnabled) {
    await apiFetch(`/api/admin/alert-rules/${ruleId}`, {
        method: "PATCH",
        body: { is_enabled: !isEnabled },
    });
}

async function loadGroupedEventDetails(groupedEventId) {
    const payload = await apiFetch(`/api/admin/grouped-events/${groupedEventId}/raw-events?limit=20`);
    selectedGroupedEventId = groupedEventId;
    selectedGroupedEvent = payload.grouped_event;
    selectedGroupedEventRawItems = payload.items;
    selectedRawEventId = payload.items[0]?.id ?? null;
    renderEvents(groupedEvents);
    renderEventDetailPanel();
}

async function selectMetamodelWorkspaceItem(kind, id) {
    const numericId = Number(id);

    if (metamodelWorkspaceInteractionMode !== "select") {
        if (kind !== "semantic_type") {
            showBanner("생성 모드에서는 semantic type을 선택하세요.", "error");
            return;
        }

        if (!metamodelWorkspacePendingTypeId) {
            metamodelWorkspacePendingTypeId = numericId;
            selectedMetamodelWorkspace = { kind: "semantic_type", id: numericId };
            refreshMetamodelWorkspace();
            return;
        }

        if (Number(metamodelWorkspacePendingTypeId) === numericId) {
            showBanner("다른 semantic type을 선택하세요.", "error");
            return;
        }

        if (metamodelWorkspaceInteractionMode === "create_containment") {
            await openContainmentCreateFromCanvas(metamodelWorkspacePendingTypeId, numericId);
        } else if (metamodelWorkspaceInteractionMode === "create_association") {
            await openAssociationCreateFromCanvas(metamodelWorkspacePendingTypeId, numericId);
        }

        setMetamodelWorkspaceInteractionMode("select");
        refreshMetamodelWorkspace();
        return;
    }

    selectedMetamodelWorkspace = { kind, id: numericId };

    if (kind === "semantic_type") {
        const item = metamodelSemanticTypes.find((entry) => entry.id === numericId);
        if (item) {
            fillMetamodelSemanticTypeForm(item);
        }
        metamodelPropertySemanticTypeIdInput.value = String(id);
        metamodelNotationSemanticTypeIdInput.value = String(id);
        await Promise.all([loadMetamodelProperties(), loadMetamodelNotations()]);
        scrollToMetamodelEditorSection(metamodelSemanticTypeSection, metamodelSemanticTypeCodeInput);
        return;
    }

    if (kind === "containment_rule") {
        const item = metamodelContainmentRules.find((entry) => entry.id === numericId);
        if (item) {
            fillMetamodelContainmentRuleForm(item);
            refreshMetamodelWorkspace();
            scrollToMetamodelEditorSection(metamodelContainmentRuleSection, metamodelContainmentParentTypeIdInput);
        }
        return;
    }

    if (kind === "notation_definition") {
        const item = metamodelNotations.find((entry) => entry.id === numericId);
        if (item) {
            fillMetamodelNotationForm(item);
            refreshMetamodelWorkspace();
            scrollToMetamodelEditorSection(metamodelNotationSection, metamodelNotationCodeInput);
        }
        return;
    }

    if (kind === "association_definition") {
        const item = metamodelAssociations.find((entry) => entry.id === numericId);
        if (item) {
            fillMetamodelAssociationForm(item);
            refreshMetamodelWorkspace();
            scrollToMetamodelEditorSection(metamodelAssociationSection, metamodelAssociationCodeInput);
        }
        return;
    }

    refreshMetamodelWorkspace();
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
        await Promise.all([loadMetamodelVersions(), loadMetamodelSemanticTypes()]);
        await loadMetamodelProperties();
        await loadMetamodelPaletteGroups();
        await loadMetamodelNotations();
        resetMetamodelSemanticTypeForm();
        resetMetamodelPropertyForm();
        resetMetamodelContainmentRuleForm();
        resetMetamodelNotationForm({ preserveSemanticType: false });
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
        await Promise.all([loadMetamodelVersions(), loadMetamodelSemanticTypes()]);
        await loadMetamodelProperties();
        await loadMetamodelContainmentRules();
        await loadMetamodelPaletteGroups();
        await loadMetamodelNotations();
        await loadMetamodelAssociations();
        selectedMetamodelValidation = null;
        renderMetamodelValidationPanel();
        resetMetamodelSemanticTypeForm();
        resetMetamodelPropertyForm();
        resetMetamodelContainmentRuleForm();
        resetMetamodelNotationForm({ preserveSemanticType: false });
        resetMetamodelAssociationForm();
        showBanner("메타모델 버전을 publish했습니다.", "success");
    } catch (error) {
        if (error.payload?.version && error.payload?.validation) {
            selectedMetamodelValidation = {
                version: error.payload.version,
                validation: error.payload.validation,
            };
            renderMetamodelValidationPanel();
        }
        showBanner(error.message, "error");
    }
}

async function saveMetamodelSemanticType(event) {
    event.preventDefault();
    clearBanner();

    const versionId = Number(metamodelDraftVersionSelect.value);
    if (!versionId) {
        showBanner("편집할 draft version을 먼저 선택하세요.", "error");
        return;
    }

    const semanticTypeId = metamodelSemanticTypeIdInput.value ? Number(metamodelSemanticTypeIdInput.value) : null;
    const payload = {
        code: metamodelSemanticTypeCodeInput.value.trim(),
        display_name: metamodelSemanticTypeDisplayNameInput.value.trim(),
        kind: metamodelSemanticTypeKindSelect.value,
        runtime_kind: metamodelSemanticTypeRuntimeKindInput.value.trim() || null,
        description: metamodelSemanticTypeDescriptionInput.value.trim() || null,
        is_groupable: metamodelSemanticTypeGroupableInput.checked,
        allows_runtime_binding: metamodelSemanticTypeRuntimeBindingInput.checked,
        is_active: metamodelSemanticTypeActiveInput.checked,
    };

    try {
        if (semanticTypeId) {
            await apiFetch(`/api/admin/metamodel/semantic-types/${semanticTypeId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("semantic type을 수정했습니다.", "success");
        } else {
            await apiFetch(`/api/admin/metamodel/versions/${versionId}/semantic-types`, {
                method: "POST",
                body: payload,
            });
            showBanner("semantic type을 생성했습니다.", "success");
        }

        await Promise.all([loadMetamodelVersions(), loadMetamodelSemanticTypes()]);
        if (semanticTypeId) {
            metamodelPropertySemanticTypeIdInput.value = String(semanticTypeId);
            metamodelNotationSemanticTypeIdInput.value = String(semanticTypeId);
        }
        await loadMetamodelProperties();
        await loadMetamodelNotations();
        await loadMetamodelAssociations();
        resetMetamodelSemanticTypeForm();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveMetamodelProperty(event) {
    event.preventDefault();
    clearBanner();

    const semanticTypeId = Number(metamodelPropertySemanticTypeIdInput.value);
    if (!semanticTypeId) {
        showBanner("편집할 semantic type을 먼저 선택하세요.", "error");
        return;
    }

    const propertyId = metamodelPropertyIdInput.value ? Number(metamodelPropertyIdInput.value) : null;
    const payload = {
        code: metamodelPropertyCodeInput.value.trim(),
        display_name: metamodelPropertyDisplayNameInput.value.trim(),
        value_type: metamodelPropertyValueTypeSelect.value,
        unit: metamodelPropertyUnitInput.value.trim() || null,
        default_value_json: metamodelPropertyDefaultValueJsonInput.value.trim() || null,
        description: metamodelPropertyDescriptionInput.value.trim() || null,
        is_required: metamodelPropertyRequiredInput.checked,
        is_runtime: metamodelPropertyRuntimeInput.checked,
        is_user_editable: metamodelPropertyUserEditableInput.checked,
        sort_order: Number.parseInt(metamodelPropertySortOrderInput.value || "0", 10),
    };

    try {
        if (propertyId) {
            await apiFetch(`/api/admin/metamodel/properties/${propertyId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("property definition을 수정했습니다.", "success");
        } else {
            await apiFetch(`/api/admin/metamodel/semantic-types/${semanticTypeId}/properties`, {
                method: "POST",
                body: payload,
            });
            showBanner("property definition을 생성했습니다.", "success");
        }

        await Promise.all([loadMetamodelVersions(), loadMetamodelProperties()]);
        resetMetamodelPropertyForm();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveMetamodelContainmentRule(event) {
    event.preventDefault();
    clearBanner();

    const versionId = Number(metamodelContainmentRuleVersionIdInput.value || metamodelDraftVersionSelect.value);
    if (!versionId) {
        showBanner("편집할 draft version을 먼저 선택하세요.", "error");
        return;
    }

    const ruleId = metamodelContainmentRuleIdInput.value ? Number(metamodelContainmentRuleIdInput.value) : null;
    const payload = {
        parent_type_id: Number(metamodelContainmentParentTypeIdInput.value),
        child_type_id: Number(metamodelContainmentChildTypeIdInput.value),
        min_count: metamodelContainmentMinCountInput.value === "" ? null : Number.parseInt(metamodelContainmentMinCountInput.value, 10),
        max_count: metamodelContainmentMaxCountInput.value === "" ? null : Number.parseInt(metamodelContainmentMaxCountInput.value, 10),
        cardinality_scope: metamodelContainmentCardinalityScopeInput.value,
        is_required: metamodelContainmentIsRequiredInput.checked,
    };

    try {
        if (ruleId) {
            await apiFetch(`/api/admin/metamodel/containment-rules/${ruleId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("containment rule을 수정했습니다.", "success");
        } else {
            await apiFetch(`/api/admin/metamodel/versions/${versionId}/containment-rules`, {
                method: "POST",
                body: payload,
            });
            showBanner("containment rule을 생성했습니다.", "success");
        }

        await Promise.all([loadMetamodelVersions(), loadMetamodelContainmentRules()]);
        resetMetamodelContainmentRuleForm();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveMetamodelNotation(event) {
    event.preventDefault();
    clearBanner();

    const semanticTypeId = Number(metamodelNotationSemanticTypeIdInput.value);
    if (!semanticTypeId) {
        showBanner("편집할 semantic type을 먼저 선택하세요.", "error");
        return;
    }

    const notationId = metamodelNotationIdInput.value ? Number(metamodelNotationIdInput.value) : null;
    const payload = {
        semantic_type_id: semanticTypeId,
        palette_group_id: toOptionalNumberValue(metamodelNotationPaletteGroupIdInput.value),
        code: metamodelNotationCodeInput.value.trim(),
        display_name: metamodelNotationDisplayNameInput.value.trim(),
        kind: metamodelNotationKindInput.value,
        render_primitive: metamodelNotationRenderPrimitiveInput.value,
        sort_order: Number.parseInt(metamodelNotationSortOrderInput.value || "0", 10),
        render_schema_json: metamodelNotationRenderSchemaJsonInput.value.trim(),
        style_tokens_json: metamodelNotationStyleTokensJsonInput.value.trim() || null,
        is_default: metamodelNotationIsDefaultInput.checked,
        is_visible_in_palette: metamodelNotationIsVisibleInPaletteInput.checked,
    };

    try {
        if (notationId) {
            await apiFetch(`/api/admin/metamodel/notations/${notationId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("notation definition을 수정했습니다.", "success");
        } else {
            await apiFetch(`/api/admin/metamodel/semantic-types/${semanticTypeId}/notations`, {
                method: "POST",
                body: payload,
            });
            showBanner("notation definition을 생성했습니다.", "success");
        }

        await Promise.all([loadMetamodelVersions(), loadMetamodelNotations()]);
        resetMetamodelNotationForm();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveMetamodelAssociation(event) {
    event.preventDefault();
    clearBanner();

    const versionId = Number(metamodelDraftVersionSelect.value);
    if (!versionId) {
        showBanner("편집할 draft version을 먼저 선택하세요.", "error");
        return;
    }

    const associationId = metamodelAssociationIdInput.value ? Number(metamodelAssociationIdInput.value) : null;
    const payload = {
        source_type_id: Number(metamodelAssociationSourceTypeIdInput.value),
        target_type_id: Number(metamodelAssociationTargetTypeIdInput.value),
        code: metamodelAssociationCodeInput.value.trim(),
        display_name: metamodelAssociationDisplayNameInput.value.trim(),
        direction: metamodelAssociationDirectionInput.value,
        multiplicity_source: metamodelAssociationMultiplicitySourceInput.value.trim() || null,
        multiplicity_target: metamodelAssociationMultiplicityTargetInput.value.trim() || null,
        description: metamodelAssociationDescriptionInput.value.trim() || null,
        semantics_json: metamodelAssociationSemanticsJsonInput.value.trim() || null,
    };

    try {
        if (associationId) {
            await apiFetch(`/api/admin/metamodel/associations/${associationId}`, {
                method: "PATCH",
                body: payload,
            });
            showBanner("association definition을 수정했습니다.", "success");
        } else {
            await apiFetch(`/api/admin/metamodel/versions/${versionId}/associations`, {
                method: "POST",
                body: payload,
            });
            showBanner("association definition을 생성했습니다.", "success");
        }

        await Promise.all([loadMetamodelVersions(), loadMetamodelAssociations()]);
        resetMetamodelAssociationForm();
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

async function updateAlertAcknowledgement(alertId, acknowledged, currentNote) {
    const ackNote = acknowledged ? window.prompt("ACK 메모를 입력하세요.", currentNote || "") : "";
    if (acknowledged && ackNote === null) {
        return;
    }

    await apiFetch(`/api/admin/alerts/${alertId}`, {
        method: "PATCH",
        body: {
            acknowledged,
            ack_note: acknowledged ? ackNote : null,
        },
    });
}

async function updateAlertStatus(alertId, nextStatus, currentNote) {
    const statusNote = window.prompt("상태 메모를 입력하세요.", currentNote || "");
    if (statusNote === null) {
        return;
    }

    await apiFetch(`/api/admin/alerts/${alertId}/status`, {
        method: "PATCH",
        body: {
            status: nextStatus,
            status_note: statusNote,
        },
    });
}

async function resolveAlert(alertId, currentReason) {
    const resolutionReason = window.prompt("해결 사유를 입력하세요.", currentReason || "");
    if (resolutionReason === null) {
        return;
    }

    await apiFetch(`/api/admin/alerts/${alertId}/resolve`, {
        method: "POST",
        body: {
            resolution_reason: resolutionReason,
        },
    });
}

async function refreshAll() {
    clearBanner();
    try {
        await Promise.all([
            loadMetamodelVersions(),
            loadMetamodelSemanticTypes(),
            loadMonitoredObjects(),
            loadAlertRules(),
            loadSummary(),
            loadIngest(),
            loadLatestStates(),
            loadEvents(),
            loadAlerts(),
            loadAlertHistoryArchive(),
            loadDebug(),
            loadCleanupRuns(),
        ]);
        await loadMetamodelProperties();
        await loadMetamodelContainmentRules();
        await loadMetamodelPaletteGroups();
        await loadMetamodelNotations();
        await loadMetamodelAssociations();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

refreshAdminButton?.addEventListener("click", refreshAll);
refreshIngestButton?.addEventListener("click", loadIngest);
refreshLatestStateButton?.addEventListener("click", loadLatestStates);
refreshEventsButton?.addEventListener("click", loadEvents);
refreshAlertsButton?.addEventListener("click", loadAlerts);
refreshAlertHistoryButton?.addEventListener("click", loadAlertHistoryArchive);
refreshDebugButton?.addEventListener("click", loadDebug);
refreshCleanupButton?.addEventListener("click", loadCleanupRuns);
refreshMetamodelVersionsButton?.addEventListener("click", loadMetamodelVersions);
refreshMetamodelSemanticTypesButton?.addEventListener("click", () => {
    loadMetamodelSemanticTypes()
        .then(async () => {
            await loadMetamodelProperties();
            await loadMetamodelContainmentRules();
            await loadMetamodelNotations();
            await loadMetamodelAssociations();
        })
        .catch((error) => showBanner(error.message, "error"));
});
refreshMetamodelPropertiesButton?.addEventListener("click", loadMetamodelProperties);
refreshMetamodelContainmentRulesButton?.addEventListener("click", loadMetamodelContainmentRules);
refreshMetamodelNotationsButton?.addEventListener("click", loadMetamodelNotations);
refreshMetamodelAssociationsButton?.addEventListener("click", loadMetamodelAssociations);
refreshAlertRulesButton?.addEventListener("click", loadAlertRules);
alertRuleScopeFilter?.addEventListener("change", loadAlertRules);
alertRuleStateFilter?.addEventListener("change", loadAlertRules);
alertRuleEnabledFilter?.addEventListener("change", loadAlertRules);
alertRuleObjectTypeFilter?.addEventListener("change", loadAlertRules);
alertStatusFilter?.addEventListener("change", loadAlerts);
alertAckFilter?.addEventListener("change", loadAlerts);
eventsList?.addEventListener("click", async (event) => {
    const card = event.target instanceof Element ? event.target.closest("[data-grouped-event-id]") : null;
    if (!card) {
        return;
    }

    try {
        clearBanner();
        await loadGroupedEventDetails(Number(card.dataset.groupedEventId));
    } catch (error) {
        showBanner(error.message, "error");
    }
});
eventDetailPanel?.addEventListener("click", (event) => {
    const card = event.target instanceof Element ? event.target.closest("[data-raw-event-id]") : null;
    if (!card) {
        return;
    }
    selectedRawEventId = Number(card.dataset.rawEventId);
    renderEventDetailPanel();
});
metamodelVersionForm?.addEventListener("submit", createMetamodelVersion);
metamodelNamespaceSelect?.addEventListener("change", renderMetamodelSelectOptions);
metamodelDraftVersionSelect?.addEventListener("change", () => {
    selectedMetamodelWorkspace = null;
    resetMetamodelSemanticTypeForm();
    resetMetamodelPropertyForm({ preserveSemanticType: false });
    resetMetamodelContainmentRuleForm();
    resetMetamodelNotationForm({ preserveSemanticType: false });
    resetMetamodelAssociationForm();
    loadMetamodelSemanticTypes()
        .then(async () => {
            await loadMetamodelProperties();
            await loadMetamodelContainmentRules();
            await loadMetamodelPaletteGroups();
            await loadMetamodelNotations();
            await loadMetamodelAssociations();
        })
        .catch((error) => showBanner(error.message, "error"));
});
metamodelSemanticTypeForm?.addEventListener("submit", saveMetamodelSemanticType);
metamodelSemanticTypeFormResetButton?.addEventListener("click", resetMetamodelSemanticTypeForm);
metamodelPropertyForm?.addEventListener("submit", saveMetamodelProperty);
metamodelPropertyFormResetButton?.addEventListener("click", () => resetMetamodelPropertyForm());
metamodelContainmentRuleForm?.addEventListener("submit", saveMetamodelContainmentRule);
metamodelContainmentRuleFormResetButton?.addEventListener("click", resetMetamodelContainmentRuleForm);
metamodelNotationForm?.addEventListener("submit", saveMetamodelNotation);
metamodelNotationFormResetButton?.addEventListener("click", () => resetMetamodelNotationForm());
metamodelAssociationForm?.addEventListener("submit", saveMetamodelAssociation);
metamodelAssociationFormResetButton?.addEventListener("click", resetMetamodelAssociationForm);
metamodelContainmentRuleVersionIdInput?.addEventListener("change", () => {
    loadMetamodelContainmentRules().catch((error) => showBanner(error.message, "error"));
});
metamodelPropertySemanticTypeIdInput?.addEventListener("change", () => {
    resetMetamodelPropertyForm();
    loadMetamodelProperties().catch((error) => showBanner(error.message, "error"));
});
metamodelNotationSemanticTypeIdInput?.addEventListener("change", () => {
    resetMetamodelNotationForm({ preserveSemanticType: true });
    loadMetamodelNotations().catch((error) => showBanner(error.message, "error"));
});
metamodelWorkspaceOutline?.addEventListener("click", (event) => {
    const item = event.target instanceof Element ? event.target.closest("[data-workspace-kind][data-workspace-id]") : null;
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem(item.dataset.workspaceKind, item.dataset.workspaceId).catch((error) => showBanner(error.message, "error"));
});
metamodelWorkspaceCanvas?.addEventListener("click", (event) => {
    const item = event.target instanceof Element ? event.target.closest("[data-workspace-kind][data-workspace-id]") : null;
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem(item.dataset.workspaceKind, item.dataset.workspaceId).catch((error) => showBanner(error.message, "error"));
});
metamodelWorkspaceInspector?.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-inspector-action][data-workspace-kind][data-workspace-id]") : null;
    if (!button) {
        return;
    }

    openMetamodelEditorFromInspector(
        button.dataset.inspectorAction,
        button.dataset.workspaceKind,
        button.dataset.workspaceId
    );
});
metamodelWorkspaceSelectModeButton?.addEventListener("click", () => {
    setMetamodelWorkspaceInteractionMode("select");
});
metamodelWorkspaceCreateContainmentModeButton?.addEventListener("click", () => {
    setMetamodelWorkspaceInteractionMode("create_containment");
});
metamodelWorkspaceCreateAssociationModeButton?.addEventListener("click", () => {
    setMetamodelWorkspaceInteractionMode("create_association");
});
alertRuleForm?.addEventListener("submit", saveAlertRule);
alertRuleFormResetButton?.addEventListener("click", resetAlertRuleForm);
alertRuleScopeTypeSelect?.addEventListener("change", toggleAlertRuleScopeFields);
metamodelVersionsList?.addEventListener("click", async (event) => {
    const validateButton = event.target instanceof HTMLElement ? event.target.closest(".validate-metamodel-button") : null;
    if (validateButton) {
        const versionId = Number(validateButton.dataset.versionId);
        if (!versionId) {
            return;
        }

        try {
            clearBanner();
            await loadMetamodelValidation(versionId);
            showBanner("메타모델 validation 결과를 갱신했습니다.", "success");
        } catch (error) {
            showBanner(error.message, "error");
        }
        return;
    }

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
metamodelSemanticTypesList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-metamodel-semantic-type-button") : null;
    if (!button) {
        return;
    }
    const typeId = Number(button.dataset.semanticTypeId);
    const item = metamodelSemanticTypes.find((entry) => entry.id === typeId);
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem("semantic_type", item.id).catch((error) => showBanner(error.message, "error"));
});
metamodelContainmentRulesList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-metamodel-containment-rule-button") : null;
    if (!button) {
        return;
    }
    const ruleId = Number(button.dataset.containmentRuleId);
    const item = metamodelContainmentRules.find((entry) => entry.id === ruleId);
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem("containment_rule", item.id).catch((error) => showBanner(error.message, "error"));
});
metamodelPropertiesList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-metamodel-property-button") : null;
    if (!button) {
        return;
    }
    const propertyId = Number(button.dataset.propertyId);
    const item = metamodelProperties.find((entry) => entry.id === propertyId);
    if (!item) {
        return;
    }
    fillMetamodelPropertyForm(item);
});
metamodelNotationsList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-metamodel-notation-button") : null;
    if (!button) {
        return;
    }
    const notationId = Number(button.dataset.notationId);
    const item = metamodelNotations.find((entry) => entry.id === notationId);
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem("notation_definition", item.id).catch((error) => showBanner(error.message, "error"));
});
metamodelAssociationsList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-metamodel-association-button") : null;
    if (!button) {
        return;
    }
    const associationId = Number(button.dataset.associationId);
    const item = metamodelAssociations.find((entry) => entry.id === associationId);
    if (!item) {
        return;
    }
    selectMetamodelWorkspaceItem("association_definition", item.id).catch((error) => showBanner(error.message, "error"));
});
alertRulesList?.addEventListener("click", (event) => {
    const button = event.target instanceof HTMLElement ? event.target.closest(".edit-alert-rule-button") : null;
    if (button) {
        const ruleId = Number(button.dataset.ruleId);
        const rule = alertRules.find((item) => item.id === ruleId);
        if (!rule) {
            return;
        }

        fillAlertRuleForm(rule);
        return;
    }

    const previewButton = event.target instanceof HTMLElement ? event.target.closest(".preview-alert-rule-button") : null;
    if (previewButton) {
        const ruleId = Number(previewButton.dataset.ruleId);
        loadAlertRulePreview(ruleId).catch((error) => showBanner(error.message, "error"));
        return;
    }

    const toggleButton = event.target instanceof HTMLElement ? event.target.closest(".toggle-alert-rule-button") : null;
    if (!toggleButton) {
        return;
    }

    const ruleId = Number(toggleButton.dataset.ruleId);
    const isEnabled = toggleButton.dataset.enabled === "true";
    toggleAlertRule(ruleId, isEnabled)
        .then(async () => {
            await Promise.all([loadAlertRules(), loadSummary()]);
            showBanner(`alert rule을 ${isEnabled ? "비활성화" : "활성화"}했습니다.`, "success");
        })
        .catch((error) => showBanner(error.message, "error"));
});

alertsList?.addEventListener("click", (event) => {
    const ackButton = event.target instanceof HTMLElement ? event.target.closest(".toggle-alert-ack-button") : null;
    if (ackButton) {
        const alertId = Number(ackButton.dataset.alertId);
        const acknowledged = ackButton.dataset.acknowledged !== "true";
        const currentNote = ackButton.dataset.ackNote || "";
        updateAlertAcknowledgement(alertId, acknowledged, currentNote)
            .then(async () => {
                await Promise.all([loadAlerts(), loadAlertHistoryArchive(), loadSummary()]);
                showBanner(`alert를 ${acknowledged ? "ACK" : "ACK 해제"}했습니다.`, "success");
            })
            .catch((error) => showBanner(error.message, "error"));
        return;
    }

    const resolveButton = event.target instanceof HTMLElement ? event.target.closest(".resolve-alert-button") : null;
    if (resolveButton) {
        const alertId = Number(resolveButton.dataset.alertId);
        const currentReason = resolveButton.dataset.resolutionReason || "";
        resolveAlert(alertId, currentReason)
            .then(async () => {
                await Promise.all([loadAlerts(), loadAlertHistoryArchive(), loadSummary()]);
                showBanner("alert를 수동 해결 처리했습니다.", "success");
            })
            .catch((error) => showBanner(error.message, "error"));
        return;
    }

    const statusButton = event.target instanceof HTMLElement ? event.target.closest(".change-alert-status-button") : null;
    if (!statusButton) {
        return;
    }

    const alertId = Number(statusButton.dataset.alertId);
    const nextStatus = statusButton.dataset.nextStatus || "open";
    const currentNote = statusButton.dataset.statusNote || "";
    updateAlertStatus(alertId, nextStatus, currentNote)
        .then(async () => {
            await Promise.all([loadAlerts(), loadAlertHistoryArchive(), loadSummary()]);
            showBanner(`alert 상태를 ${nextStatus}(으)로 변경했습니다.`, "success");
        })
        .catch((error) => showBanner(error.message, "error"));
});

ingestStatusFilter?.addEventListener("change", loadIngest);
latestStateTypeFilter?.addEventListener("change", loadLatestStates);
latestStateStatusFilter?.addEventListener("change", loadLatestStates);
debugDirectionFilter?.addEventListener("change", loadDebug);

resetAlertRuleForm();
resetMetamodelPropertyForm({ preserveSemanticType: false });
resetMetamodelContainmentRuleForm();
resetMetamodelNotationForm({ preserveSemanticType: false });
resetMetamodelAssociationForm();
renderMetamodelValidationPanel();
refreshAll();
