import { apiFetch, clearBanner, readNumber, showBanner, slugify } from "./common.js";
import { clientToSvg, renderDiagram } from "./diagram.js";
import { loadMetamodelRegistry } from "./metamodel.js";
const appRoot = document.getElementById("editor-app");
const svg = document.getElementById("editor-canvas");
const selectionKind = document.getElementById("selection-kind");
const revisionLabel = document.getElementById("editor-revision-label");
const statusLabel = document.getElementById("editor-status-label");
const versionCodeLabel = document.getElementById("editor-version-code-label");
const versionStatusLabel = document.getElementById("editor-version-status-label");
const paletteStatusLabel = document.getElementById("palette-status-label");
const paletteGroupsRoot = document.getElementById("palette-groups");
const nodeForm = document.getElementById("node-form");
const edgeSummary = document.getElementById("edge-summary");
const edgeIdText = document.getElementById("edge-id-text");
const edgeLinkText = document.getElementById("edge-link-text");
const startConnectButton = document.getElementById("start-connect-button");
const publishVersionButton = document.getElementById("publish-version-button");
const activateVersionButton = document.getElementById("activate-version-button");

const state = {
    viewId: Number(appRoot.dataset.viewId),
    viewVersionId: null,
    viewVersionCode: null,
    viewVersionStatus: null,
    viewName: "",
    revision: 0,
    metamodelVersionCode: null,
    metamodelVersionId: null,
    paletteGroups: [],
    notationDefinitionsByCode: new Map(),
    paletteItemsByType: new Map(),
    edgeToolLabel: "통신선 시작",
    nodes: [],
    edges: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    connectSourceId: null,
    drag: null,
    lastDragAt: 0,
};

const SUPPORTED_NODE_TYPES = new Set(["PhysicalServer", "SoftwareProcess", "MonitoringAgent"]);
const SUPPORTED_EDGE_TYPES = new Set(["CommunicationLink"]);
const NODE_BUTTON_ID_BY_TYPE = {
    PhysicalServer: "add-server-button",
    SoftwareProcess: "add-process-button",
    MonitoringAgent: "add-agent-button",
};
const NODE_BUTTON_LABEL_BY_TYPE = {
    PhysicalServer: "물리 서버 추가",
    SoftwareProcess: "프로세스 추가",
    MonitoringAgent: "에이전트 추가",
};
const EDGE_BUTTON_LABEL_BY_TYPE = {
    CommunicationLink: "통신선 시작",
};
const DEFAULT_DISPLAY_NAME_BY_TYPE = {
    PhysicalServer: "Physical Server",
    SoftwareProcess: "Software Process",
    MonitoringAgent: "Monitoring Agent",
};
const DEFAULT_TARGET_PREFIX_BY_TYPE = {
    SoftwareProcess: "process",
    MonitoringAgent: "agent",
};
const DEFAULT_NOTATION_BY_TYPE = {
    PhysicalServer: "server.physical.rect",
    SoftwareProcess: "process.rounded_rect",
    MonitoringAgent: "agent.rounded_rect.double_border",
    CommunicationLink: "communication.line",
};

const formFields = {
    displayName: document.getElementById("node-display-name"),
    targetId: document.getElementById("node-target-id"),
    x: document.getElementById("node-x"),
    y: document.getElementById("node-y"),
    width: document.getElementById("node-width"),
    height: document.getElementById("node-height"),
};

function setStatus(message) {
    statusLabel.textContent = message;
}

function setPaletteStatus(message) {
    if (paletteStatusLabel) {
        paletteStatusLabel.textContent = message;
    }
}

function updateRevision(revision) {
    state.revision = revision;
    revisionLabel.textContent = `revision ${revision}`;
}

function getVersionApiBase() {
    return `/api/view-versions/${state.viewVersionId}`;
}

function isEditableVersion() {
    return state.viewVersionStatus === "draft";
}

function refreshVersionPills() {
    if (versionCodeLabel) {
        versionCodeLabel.textContent = `version ${state.viewVersionCode || "-"}`;
    }
    if (versionStatusLabel) {
        versionStatusLabel.textContent = `status ${state.viewVersionStatus || "-"}`;
    }
}

function updateEditorMode() {
    const editable = isEditableVersion();
    const paletteButtons = paletteGroupsRoot?.querySelectorAll("button") || [];
    paletteButtons.forEach((button) => {
        button.disabled = !editable;
    });
    if (startConnectButton) {
        startConnectButton.disabled = !editable;
    }
    const deleteSelectedButton = document.getElementById("delete-selected-button");
    if (deleteSelectedButton) {
        deleteSelectedButton.disabled = !editable;
    }
    const saveSelectedButton = nodeForm?.querySelector('button[type="submit"]');
    if (saveSelectedButton) {
        saveSelectedButton.disabled = !editable;
    }
    nodeForm?.querySelectorAll("input").forEach((input) => {
        input.disabled = !editable;
    });
    if (publishVersionButton) {
        publishVersionButton.hidden = state.viewVersionStatus !== "draft";
        publishVersionButton.disabled = !editable;
    }
    if (activateVersionButton) {
        activateVersionButton.hidden = state.viewVersionStatus !== "published";
        activateVersionButton.disabled = state.viewVersionStatus !== "published";
    }
    refreshVersionPills();
}

function ensureEditableVersion(actionLabel) {
    if (!isEditableVersion()) {
        showBanner(`${actionLabel}은 draft 버전에서만 가능합니다.`, "error");
        return false;
    }
    return true;
}

function getNode(nodeId) {
    return state.nodes.find((node) => node.id === nodeId) || null;
}

function getChildren(parentId) {
    return state.nodes.filter((node) => node.parent_node_id === parentId);
}

function getDescendantIds(nodeId) {
    const result = [nodeId];
    for (const child of getChildren(nodeId)) {
        result.push(...getDescendantIds(child.id));
    }
    return result;
}

function getSelectedServerId() {
    const selectedNode = getNode(state.selectedNodeId);
    if (selectedNode?.node_type === "PhysicalServer") {
        return selectedNode.id;
    }
    if (selectedNode?.parent_node_id) {
        return selectedNode.parent_node_id;
    }
    const firstServer = state.nodes.find((node) => node.node_type === "PhysicalServer");
    return firstServer?.id || null;
}

function nextTargetId(prefix, displayName) {
    return `${prefix}_${slugify(displayName)}_${Date.now()}`;
}

function renderStyleFromPaletteItem(item) {
    if (!item) {
        return {};
    }
    if (item.render_primitive === "rect") {
        return { shape: "rect" };
    }
    if (item.render_primitive === "rounded_rect") {
        const style = { shape: "rounded-rect" };
        if (item.render_schema?.modifiers?.double_border) {
            style.variant = "double-border";
        }
        return style;
    }
    return {};
}

function getDefaultSizeFromPaletteItem(item, fallbackWidth, fallbackHeight) {
    const defaultSize = item?.render_schema?.default_size;
    return {
        width: defaultSize?.width ?? fallbackWidth,
        height: defaultSize?.height ?? fallbackHeight,
    };
}

function getPaletteItemByType(nodeType) {
    return state.paletteItemsByType.get(nodeType) || null;
}

function getNodeButtonLabel(nodeType, item) {
    return NODE_BUTTON_LABEL_BY_TYPE[nodeType] || item?.display_name || nodeType;
}

function getDefaultNodePayload(nodeType, item = getPaletteItemByType(nodeType)) {
    if (nodeType === "PhysicalServer") {
        const serverCount = state.nodes.filter((node) => node.node_type === "PhysicalServer").length;
        const size = getDefaultSizeFromPaletteItem(item, 480, 260);
        return {
            parent_node_id: null,
            semantic_type_code: item?.semantic_type_code || nodeType,
            notation_code: item?.notation_code || DEFAULT_NOTATION_BY_TYPE[nodeType],
            display_name: `Host ${String.fromCharCode(65 + serverCount)}`,
            target_id: null,
            x: 60 + serverCount * 80,
            y: 60 + serverCount * 40,
            width: size.width,
            height: size.height,
            style: renderStyleFromPaletteItem(item),
        };
    }

    const parentId = getSelectedServerId();
    if (!parentId) {
        throw new Error("프로세스와 에이전트는 서버를 먼저 선택한 뒤 생성해야 합니다.");
    }

    const parent = getNode(parentId);
    const siblings = state.nodes.filter((node) => node.parent_node_id === parentId).length;
    const baseX = parent.x + 40;
    const baseY = parent.y + 80 + siblings * 74;
    const defaultSize = getDefaultSizeFromPaletteItem(item, nodeType === "MonitoringAgent" ? 170 : 180, 56);
    const displayName = item?.display_name || DEFAULT_DISPLAY_NAME_BY_TYPE[nodeType] || nodeType;
    const targetPrefix = DEFAULT_TARGET_PREFIX_BY_TYPE[nodeType] || "node";

    return {
        parent_node_id: parentId,
        semantic_type_code: item?.semantic_type_code || nodeType,
        notation_code: item?.notation_code || DEFAULT_NOTATION_BY_TYPE[nodeType],
        display_name: displayName,
        target_id: nextTargetId(targetPrefix, displayName),
        x: baseX,
        y: baseY,
        width: defaultSize.width,
        height: defaultSize.height,
        style: renderStyleFromPaletteItem(item),
    };
}

function isSupportedPaletteItem(item) {
    return SUPPORTED_NODE_TYPES.has(item.semantic_type_code) || SUPPORTED_EDGE_TYPES.has(item.semantic_type_code);
}

function renderPalette() {
    if (!paletteGroupsRoot) {
        return;
    }

    paletteGroupsRoot.replaceChildren();
    state.paletteItemsByType = new Map();

    const supportedGroups = state.paletteGroups
        .map((group) => ({
            ...group,
            items: group.items.filter(isSupportedPaletteItem),
        }))
        .filter((group) => group.items.length > 0);

    for (const group of supportedGroups) {
        const groupEl = document.createElement("section");
        groupEl.className = "palette-group";

        const title = document.createElement("h2");
        title.className = "palette-group-title";
        title.textContent = group.label;
        groupEl.appendChild(title);

        const itemsEl = document.createElement("div");
        itemsEl.className = "palette-items";

        for (const item of group.items) {
            state.paletteItemsByType.set(item.semantic_type_code, item);

            if (!SUPPORTED_NODE_TYPES.has(item.semantic_type_code)) {
                continue;
            }

            const button = document.createElement("button");
            button.type = "button";
            button.className = `button ${item.semantic_type_code === "PhysicalServer" ? "primary" : "ghost"} palette-button`;
            button.dataset.semanticType = item.semantic_type_code;
            button.dataset.notationCode = item.notation_code;
            button.dataset.primitive = item.render_primitive;
            button.id = NODE_BUTTON_ID_BY_TYPE[item.semantic_type_code] || "";
            button.textContent = getNodeButtonLabel(item.semantic_type_code, item);
            button.addEventListener("click", () => addNode(item.semantic_type_code));
            itemsEl.appendChild(button);
        }

        if (itemsEl.children.length > 0) {
            groupEl.appendChild(itemsEl);
            paletteGroupsRoot.appendChild(groupEl);
        }
    }

    state.edgeToolLabel = EDGE_BUTTON_LABEL_BY_TYPE.CommunicationLink;
    if (startConnectButton) {
        startConnectButton.textContent = state.edgeToolLabel;
    }

    setPaletteStatus(
        supportedGroups.length > 0
            ? `${state.metamodelVersionCode || "metamodel"} palette가 준비되었습니다.`
            : "현재 editor에서 사용할 수 있는 palette 항목이 없습니다."
    );
}

async function loadPalette(metamodelVersionCode) {
    const registry = await loadMetamodelRegistry(metamodelVersionCode);
    state.metamodelVersionId = registry.versionId;
    state.metamodelVersionCode = registry.versionCode;
    state.paletteGroups = registry.paletteGroups;
    state.notationDefinitionsByCode = registry.notationDefinitionsByCode;
    renderPalette();

    if (!metamodelVersionCode) {
        setPaletteStatus("metamodel version 정보가 없어 기본 palette를 사용합니다.");
        return;
    }

    if (registry.usedFallback) {
        setPaletteStatus("metamodel palette 조회에 실패해 기본 palette를 사용합니다.");
    }
    updateEditorMode();
}

function syncSelectionPanel() {
    const node = getNode(state.selectedNodeId);
    if (node) {
        selectionKind.textContent = `${node.node_type} #${node.id}`;
        nodeForm.hidden = false;
        edgeSummary.hidden = true;
        formFields.displayName.value = node.display_name || "";
        formFields.targetId.value = node.target_id || "";
        formFields.x.value = node.x;
        formFields.y.value = node.y;
        formFields.width.value = node.width;
        formFields.height.value = node.height;
        return;
    }

    const edge = state.edges.find((item) => item.id === state.selectedEdgeId);
    if (edge) {
        selectionKind.textContent = `CommunicationLink #${edge.id}`;
        nodeForm.hidden = true;
        edgeSummary.hidden = false;
        edgeIdText.textContent = String(edge.id);
        edgeLinkText.textContent = `${edge.source_node_id} -> ${edge.target_node_id}`;
        return;
    }

    selectionKind.textContent = "선택된 항목이 없습니다.";
    nodeForm.hidden = true;
    edgeSummary.hidden = true;
}

function render() {
    renderDiagram(svg, {
        nodes: state.nodes,
        edges: state.edges,
        notationDefinitionsByCode: state.notationDefinitionsByCode,
        selectedNodeId: state.selectedNodeId,
        selectedEdgeId: state.selectedEdgeId,
        connectSourceId: state.connectSourceId,
        onNodeClick: handleNodeClick,
        onNodePointerDown: handleNodePointerDown,
        onEdgeClick: handleEdgeClick,
    });
    syncSelectionPanel();
}

async function loadView() {
    setStatus("뷰를 불러오는 중입니다.");
    setPaletteStatus("메타모델 palette를 불러오는 중입니다.");
    clearBanner();
    try {
        let payload;
        try {
            payload = await apiFetch(`/api/views/${state.viewId}/draft`);
        } catch (error) {
            if (error.status === 404) {
                try {
                    payload = await apiFetch(`/api/views/${state.viewId}/drafts`, {
                        method: "POST",
                        body: { description: "Editor auto-created draft" },
                    });
                    payload = {
                        view: { id: state.viewId, name: appRoot.querySelector("h1")?.textContent || "Draft View" },
                        version: payload.version,
                        nodes: payload.nodes,
                        edges: payload.edges,
                    };
                } catch (draftCreateError) {
                    if (draftCreateError.status === 409) {
                        payload = await apiFetch(`/api/views/${state.viewId}/draft`);
                    } else {
                        throw draftCreateError;
                    }
                }
            } else {
                throw error;
            }
        }

        state.viewName = payload.view.name;
        state.viewVersionId = payload.version.id;
        state.viewVersionCode = payload.version.version_code;
        state.viewVersionStatus = payload.version.status;

        const metamodelVersionCode = payload.version?.metamodel_version_code || payload.view.metamodel_version;
        if (state.metamodelVersionCode !== metamodelVersionCode || state.paletteGroups.length === 0) {
            await loadPalette(metamodelVersionCode);
        }
        state.nodes = payload.nodes;
        state.edges = payload.edges;
        state.selectedNodeId = null;
        state.selectedEdgeId = null;
        state.connectSourceId = null;
        updateRevision(payload.version.revision);
        updateEditorMode();
        render();
        setStatus(`${payload.version.version_code} draft가 준비되었습니다.`);
    } catch (error) {
        showBanner(error.message, "error");
        setStatus("뷰를 불러오지 못했습니다.");
    }
}

async function addNode(nodeType) {
    if (!ensureEditableVersion("노드 추가")) {
        return;
    }
    clearBanner();
    try {
        const payload = await apiFetch(`${getVersionApiBase()}/nodes`, {
            method: "POST",
            body: {
                revision: state.revision,
                node_type: nodeType,
                ...getDefaultNodePayload(nodeType),
            },
        });
        state.nodes.push(payload.node);
        state.selectedNodeId = payload.node.id;
        state.selectedEdgeId = null;
        updateRevision(payload.revision);
        render();
        setStatus(`${nodeType}가 추가되었습니다.`);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

function startConnectMode() {
    if (!ensureEditableVersion("통신선 생성")) {
        return;
    }
    if (!state.selectedNodeId) {
        showBanner("먼저 연결의 시작점이 될 노드를 선택해 주세요.", "error");
        return;
    }
    state.connectSourceId = state.selectedNodeId;
    state.selectedEdgeId = null;
    render();
    setStatus(`노드 ${state.connectSourceId} 에서 시작하는 통신선을 기다리는 중입니다.`);
}

async function createEdge(targetNodeId) {
    if (!ensureEditableVersion("통신선 생성")) {
        state.connectSourceId = null;
        render();
        return;
    }
    if (!state.connectSourceId || state.connectSourceId === targetNodeId) {
        state.connectSourceId = null;
        render();
        return;
    }

    clearBanner();
    try {
        const edgeItem = getPaletteItemByType("CommunicationLink");
        const payload = await apiFetch(`${getVersionApiBase()}/edges`, {
            method: "POST",
            body: {
                revision: state.revision,
                edge_type: "CommunicationLink",
                semantic_type_code: edgeItem?.semantic_type_code || "CommunicationLink",
                notation_code: edgeItem?.notation_code || DEFAULT_NOTATION_BY_TYPE.CommunicationLink,
                source_node_id: state.connectSourceId,
                target_node_id: targetNodeId,
                source_anchor: "right",
                target_anchor: "left",
                label: "communication",
                control_points: [],
                style: { strokeStyle: "solid" },
            },
        });
        state.edges.push(payload.edge);
        state.selectedEdgeId = payload.edge.id;
        state.selectedNodeId = null;
        state.connectSourceId = null;
        updateRevision(payload.revision);
        render();
        setStatus("통신선이 추가되었습니다.");
    } catch (error) {
        showBanner(error.message, "error");
        state.connectSourceId = null;
        render();
    }
}

async function deleteSelected() {
    if (!ensureEditableVersion("삭제")) {
        return;
    }
    clearBanner();
    try {
        if (state.selectedNodeId) {
            await apiFetch(`${getVersionApiBase()}/nodes/${state.selectedNodeId}`, {
                method: "DELETE",
                body: { revision: state.revision },
            });
            await loadView();
            setStatus("노드가 삭제되었습니다.");
            return;
        }

        if (state.selectedEdgeId) {
            const edgeId = state.selectedEdgeId;
            const payload = await apiFetch(`${getVersionApiBase()}/edges/${edgeId}`, {
                method: "DELETE",
                body: { revision: state.revision },
            });
            state.edges = state.edges.filter((edge) => edge.id !== edgeId);
            state.selectedEdgeId = null;
            updateRevision(payload.revision);
            render();
            setStatus("통신선이 삭제되었습니다.");
            return;
        }

        showBanner("삭제할 항목을 먼저 선택해 주세요.", "error");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function saveSelectedNode(event) {
    event.preventDefault();
    if (!ensureEditableVersion("저장")) {
        return;
    }
    const node = getNode(state.selectedNodeId);
    if (!node) {
        return;
    }

    clearBanner();
    try {
        const payload = await apiFetch(`${getVersionApiBase()}/nodes/${node.id}`, {
            method: "PATCH",
            body: {
                revision: state.revision,
                display_name: formFields.displayName.value.trim() || node.display_name,
                target_id: formFields.targetId.value.trim() || null,
                x: readNumber(formFields.x, node.x),
                y: readNumber(formFields.y, node.y),
                width: readNumber(formFields.width, node.width),
                height: readNumber(formFields.height, node.height),
            },
        });
        state.nodes = state.nodes.map((item) => (item.id === node.id ? payload.node : item));
        updateRevision(payload.revision);
        render();
        setStatus("노드가 저장되었습니다.");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

function handleEdgeClick(edge, event) {
    event.stopPropagation();
    state.selectedEdgeId = edge.id;
    state.selectedNodeId = null;
    state.connectSourceId = null;
    render();
    setStatus(`통신선 ${edge.id} 선택됨`);
}

function handleNodeClick(node, event) {
    event.stopPropagation();
    if (Date.now() - state.lastDragAt < 120) {
        return;
    }

    if (state.connectSourceId && state.connectSourceId !== node.id) {
        createEdge(node.id);
        return;
    }

    state.selectedNodeId = node.id;
    state.selectedEdgeId = null;
    render();
    setStatus(`노드 ${node.id} 선택됨`);
}

function handleNodePointerDown(node, event) {
    if (event.button !== 0 || state.connectSourceId || !isEditableVersion()) {
        return;
    }

    event.stopPropagation();
    const origin = clientToSvg(svg, event.clientX, event.clientY);
    const affectedIds = node.node_type === "PhysicalServer" ? getDescendantIds(node.id) : [node.id];
    const startPositions = new Map(
        affectedIds.map((nodeId) => {
            const current = getNode(nodeId);
            return [nodeId, { x: current.x, y: current.y }];
        })
    );

    state.selectedNodeId = node.id;
    state.selectedEdgeId = null;
    state.drag = {
        anchor: origin,
        affectedIds,
        startPositions,
        moved: false,
    };
    render();
}

async function persistLayout() {
    if (!ensureEditableVersion("레이아웃 저장")) {
        return;
    }
    const payload = await apiFetch(getVersionApiBase(), {
        method: "PUT",
        body: {
            revision: state.revision,
            nodes: state.nodes,
            edges: state.edges,
        },
    });
    updateRevision(payload.revision);
}

async function publishCurrentVersion() {
    if (!ensureEditableVersion("발행")) {
        return;
    }
    clearBanner();
    try {
        const payload = await apiFetch(`${getVersionApiBase()}/publish`, {
            method: "POST",
            body: { revision: state.revision },
        });
        state.viewVersionCode = payload.version.version_code;
        state.viewVersionStatus = payload.version.status;
        updateRevision(payload.version.revision);
        updateEditorMode();
        setStatus(`${payload.version.version_code} 버전이 발행되었습니다.`);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

async function activateCurrentVersion() {
    if (state.viewVersionStatus !== "published") {
        showBanner("운영 반영은 published 버전에서만 가능합니다.", "error");
        return;
    }
    clearBanner();
    try {
        const payload = await apiFetch(`${getVersionApiBase()}/activate`, {
            method: "POST",
            body: { revision: state.revision },
        });
        state.viewVersionCode = payload.version.version_code;
        state.viewVersionStatus = payload.version.status;
        updateRevision(payload.version.revision);
        updateEditorMode();
        setStatus(`${payload.version.version_code} 버전이 운영 반영되었습니다.`);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

svg.addEventListener("pointermove", (event) => {
    if (!state.drag) {
        return;
    }

    const point = clientToSvg(svg, event.clientX, event.clientY);
    const dx = point.x - state.drag.anchor.x;
    const dy = point.y - state.drag.anchor.y;
    if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
        state.drag.moved = true;
    }

    state.nodes = state.nodes.map((node) => {
        if (!state.drag.affectedIds.includes(node.id)) {
            return node;
        }
        const start = state.drag.startPositions.get(node.id);
        return { ...node, x: Math.round(start.x + dx), y: Math.round(start.y + dy) };
    });
    render();
});

svg.addEventListener("pointerup", async () => {
    if (!state.drag) {
        return;
    }

    const drag = state.drag;
    state.drag = null;
    if (!drag.moved) {
        return;
    }

    state.lastDragAt = Date.now();
    setStatus("레이아웃을 저장하는 중입니다.");
    try {
        await persistLayout();
        setStatus("레이아웃이 저장되었습니다.");
    } catch (error) {
        showBanner(error.message, "error");
        await loadView();
    }
});

svg.addEventListener("click", () => {
    state.selectedNodeId = null;
    state.selectedEdgeId = null;
    state.connectSourceId = null;
    render();
});

startConnectButton?.addEventListener("click", startConnectMode);
document.getElementById("delete-selected-button")?.addEventListener("click", deleteSelected);
document.getElementById("reload-view-button")?.addEventListener("click", loadView);
nodeForm?.addEventListener("submit", saveSelectedNode);
publishVersionButton?.addEventListener("click", publishCurrentVersion);
activateVersionButton?.addEventListener("click", activateCurrentVersion);

loadView();
