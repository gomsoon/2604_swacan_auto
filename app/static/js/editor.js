import { apiFetch, clearBanner, readNumber, showBanner, slugify } from "./common.js";
import { clientToSvg, renderDiagram } from "./diagram.js";
import { loadViewVersionMetamodel } from "./metamodel.js";
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
    semanticTypesByCode: new Map(),
    paletteGroups: [],
    containmentRules: [],
    associations: [],
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

const NODE_BUTTON_LABEL_BY_TYPE = {
    PhysicalServer: "물리 서버 추가",
    VirtualMachine: "가상 머신 추가",
    SoftwareProcess: "프로세스 추가",
    MonitoringAgent: "에이전트 추가",
};
const EDGE_TOOL_LABEL_BY_TYPE = {
    CommunicationLink: "통신선 시작",
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

function getSemanticType(code) {
    return state.semanticTypesByCode.get(code) || null;
}

function isNodeSemanticType(code) {
    const semanticType = getSemanticType(code);
    return Boolean(semanticType && semanticType.is_active && semanticType.kind !== "edge");
}

function isEdgeSemanticType(code) {
    const semanticType = getSemanticType(code);
    return Boolean(semanticType && semanticType.is_active && semanticType.kind === "edge");
}

function getAllowedParentTypeCodes(childTypeCode) {
    return state.containmentRules
        .filter((rule) => rule.child_type_code === childTypeCode)
        .map((rule) => rule.parent_type_code);
}

function findCandidateParentId(childTypeCode) {
    const allowedParentTypeCodes = getAllowedParentTypeCodes(childTypeCode);
    if (allowedParentTypeCodes.length === 0) {
        return null;
    }

    const selectedNode = getNode(state.selectedNodeId);
    if (selectedNode && allowedParentTypeCodes.includes(selectedNode.semantic_type_code || selectedNode.node_type)) {
        return selectedNode.id;
    }

    const candidate = state.nodes.find((node) =>
        allowedParentTypeCodes.includes(node.semantic_type_code || node.node_type)
    );
    return candidate?.id || null;
}

function resolveEdgeCreationPlan(sourceNode, targetNode) {
    if (!sourceNode || !targetNode) {
        return null;
    }

    const sourceTypeCode = sourceNode.semantic_type_code || sourceNode.node_type;
    const targetTypeCode = targetNode.semantic_type_code || targetNode.node_type;
    const exactAssociation = state.associations.find(
        (item) =>
            item.source_type_code === sourceTypeCode &&
            item.target_type_code === targetTypeCode
    );
    if (exactAssociation) {
        return {
            association: exactAssociation,
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            autoOriented: false,
        };
    }

    const reverseAssociation = state.associations.find(
        (item) =>
            item.source_type_code === targetTypeCode &&
            item.target_type_code === sourceTypeCode
    );
    if (!reverseAssociation) {
        return {
            association: null,
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            autoOriented: false,
        };
    }

    if (reverseAssociation.direction === "undirected") {
        return {
            association: reverseAssociation,
            sourceNodeId: sourceNode.id,
            targetNodeId: targetNode.id,
            autoOriented: false,
        };
    }

    return {
        association: reverseAssociation,
        sourceNodeId: targetNode.id,
        targetNodeId: sourceNode.id,
        autoOriented: true,
    };
}

function getFirstEdgePaletteItem() {
    return state.paletteGroups
        .flatMap((group) => group.items || [])
        .find((item) => isEdgeSemanticType(item.semantic_type_code)) || null;
}

function getNodePaletteItems() {
    return state.paletteGroups.flatMap((group) =>
        (group.items || []).filter((item) => isNodeSemanticType(item.semantic_type_code))
    );
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

function refreshPaletteInteractivity() {
    const paletteButtons = paletteGroupsRoot?.querySelectorAll(".palette-button") || [];
    paletteButtons.forEach((button) => {
        const availability = getNodeCreationAvailability(button.dataset.semanticType);
        button.disabled = !isEditableVersion() || !availability.enabled;
        button.title = availability.reason;
    });
}

function updateEditorMode() {
    const editable = isEditableVersion();
    refreshPaletteInteractivity();
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
    return NODE_BUTTON_LABEL_BY_TYPE[nodeType] || `${item?.display_name || nodeType} 추가`;
}

function getEdgeToolLabel(edgeType, item) {
    return EDGE_TOOL_LABEL_BY_TYPE[edgeType] || `${item?.display_name || edgeType} 시작`;
}

function getNodeCreationAvailability(nodeType) {
    if (!isNodeSemanticType(nodeType)) {
        return {
            enabled: false,
            reason: "현재 메타모델에서 사용할 수 없는 semantic type입니다.",
        };
    }
    const semanticType = getSemanticType(nodeType);
    const allowedParentTypeCodes = getAllowedParentTypeCodes(nodeType);
    if (allowedParentTypeCodes.length === 0) {
        return { enabled: true, reason: `${semanticType?.display_name || nodeType}을(를) 루트 요소로 추가합니다.` };
    }
    const parentId = findCandidateParentId(nodeType);
    if (parentId) {
        const parentNode = getNode(parentId);
        return {
            enabled: true,
            reason: `${parentNode?.display_name || parentNode?.node_type || "상위 요소"} 안에 ${semanticType?.display_name || nodeType}을(를) 추가합니다.`,
        };
    }
    return {
        enabled: false,
        reason: `${semanticType?.display_name || nodeType}을(를) 배치할 수 있는 상위 요소를 먼저 선택하거나 생성해 주세요.`,
    };
}

function getDefaultNodePayload(nodeType, item = getPaletteItemByType(nodeType)) {
    const semanticType = getSemanticType(nodeType);
    const allowedParentTypeCodes = getAllowedParentTypeCodes(nodeType);
    const parentId = findCandidateParentId(nodeType);
    const displayName = item?.display_name || semanticType?.display_name || nodeType;
    const runtimePrefix = semanticType?.runtime_kind ? slugify(semanticType.runtime_kind) : slugify(nodeType);

    if (allowedParentTypeCodes.length === 0) {
        const rootCount = state.nodes.filter((node) => node.parent_node_id === null).length;
        const size = getDefaultSizeFromPaletteItem(item, 360, 220);
        return {
            parent_node_id: null,
            semantic_type_code: item?.semantic_type_code || nodeType,
            notation_code: item?.notation_code || semanticType?.default_notation_code || null,
            display_name: displayName,
            target_id: null,
            x: 60 + rootCount * 80,
            y: 60 + rootCount * 40,
            width: size.width,
            height: size.height,
            style: renderStyleFromPaletteItem(item),
        };
    }

    if (!parentId) {
        throw new Error(`${displayName}을(를) 배치할 수 있는 상위 요소가 없습니다.`);
    }

    const parent = getNode(parentId);
    const siblings = state.nodes.filter((node) => node.parent_node_id === parentId).length;
    const baseX = parent.x + 40;
    const baseY = parent.y + 80 + siblings * 74;
    const defaultSize = getDefaultSizeFromPaletteItem(item, 180, 72);

    return {
        parent_node_id: parentId,
        semantic_type_code: item?.semantic_type_code || nodeType,
        notation_code: item?.notation_code || semanticType?.default_notation_code || null,
        display_name: displayName,
        target_id: semanticType?.allows_runtime_binding ? nextTargetId(runtimePrefix || "node", displayName) : null,
        x: baseX,
        y: baseY,
        width: defaultSize.width,
        height: defaultSize.height,
        style: renderStyleFromPaletteItem(item),
    };
}

function canCreateNodeType(nodeType) {
    if (!isNodeSemanticType(nodeType)) {
        return false;
    }
    const allowedParentTypeCodes = getAllowedParentTypeCodes(nodeType);
    if (allowedParentTypeCodes.length === 0) {
        return true;
    }
    return Boolean(findCandidateParentId(nodeType));
}

function renderPalette() {
    if (!paletteGroupsRoot) {
        return;
    }

    paletteGroupsRoot.replaceChildren();
    state.paletteItemsByType = new Map();
    state.paletteGroups.forEach((group) => {
        (group.items || []).forEach((item) => {
            state.paletteItemsByType.set(item.semantic_type_code, item);
        });
    });

    const supportedGroups = state.paletteGroups
        .map((group) => ({
            ...group,
            items: (group.items || []).filter((item) => isNodeSemanticType(item.semantic_type_code)),
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
            const button = document.createElement("button");
            button.type = "button";
            button.className = `button ${item.semantic_type_code === "PhysicalServer" ? "primary" : "ghost"} palette-button`;
            button.dataset.semanticType = item.semantic_type_code;
            button.dataset.notationCode = item.notation_code;
            button.dataset.primitive = item.render_primitive;
            button.textContent = getNodeButtonLabel(item.semantic_type_code, item);
            button.disabled = !canCreateNodeType(item.semantic_type_code) || !isEditableVersion();
            button.addEventListener("click", () => addNode(item.semantic_type_code));
            itemsEl.appendChild(button);
        }

        if (itemsEl.children.length > 0) {
            groupEl.appendChild(itemsEl);
            paletteGroupsRoot.appendChild(groupEl);
        }
    }

    const edgePaletteItem = getFirstEdgePaletteItem();
    state.edgeToolLabel = edgePaletteItem
        ? getEdgeToolLabel(edgePaletteItem.semantic_type_code, edgePaletteItem)
        : "관계선 시작";
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
    const registry = await loadViewVersionMetamodel(state.viewVersionId, metamodelVersionCode);
    state.metamodelVersionId = registry.versionId;
    state.metamodelVersionCode = registry.versionCode;
    state.semanticTypesByCode = registry.semanticTypesByCode;
    state.paletteGroups = registry.paletteGroups;
    state.containmentRules = registry.containmentRules;
    state.associations = registry.associations;
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
        const semanticType = getSemanticType(node.semantic_type_code || node.node_type);
        selectionKind.textContent = `${semanticType?.display_name || node.node_type} #${node.id}`;
        nodeForm.hidden = false;
        edgeSummary.hidden = true;
        formFields.displayName.value = node.display_name || "";
        formFields.targetId.value = node.target_id || "";
        const allowsRuntimeBinding = semanticType?.allows_runtime_binding !== false;
        formFields.targetId.disabled = !isEditableVersion() || !allowsRuntimeBinding;
        formFields.targetId.placeholder = allowsRuntimeBinding ? "" : "이 semantic type은 runtime binding을 사용하지 않습니다.";
        formFields.x.value = node.x;
        formFields.y.value = node.y;
        formFields.width.value = node.width;
        formFields.height.value = node.height;
        return;
    }

    const edge = state.edges.find((item) => item.id === state.selectedEdgeId);
    if (edge) {
        const association = edge.association_code
            ? state.associations.find((item) => item.code === edge.association_code)
            : null;
        const sourceNode = getNode(edge.source_node_id);
        const targetNode = getNode(edge.target_node_id);
        selectionKind.textContent = `${association?.display_name || edge.edge_type} #${edge.id}`;
        nodeForm.hidden = true;
        edgeSummary.hidden = false;
        edgeIdText.textContent = String(edge.id);
        edgeLinkText.textContent = `${sourceNode?.display_name || edge.source_node_id} -> ${targetNode?.display_name || edge.target_node_id}`;
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
    refreshPaletteInteractivity();
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
        if (
            state.metamodelVersionCode !== metamodelVersionCode ||
            state.metamodelVersionId !== payload.version.metamodel_version_id ||
            state.paletteGroups.length === 0
        ) {
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
    const availability = getNodeCreationAvailability(nodeType);
    if (!availability.enabled) {
        showBanner(availability.reason, "error");
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
        const sourceNode = getNode(state.connectSourceId);
        const targetNode = getNode(targetNodeId);
        const edgePlan = resolveEdgeCreationPlan(sourceNode, targetNode);
        const matchedAssociation = edgePlan?.association || null;
        const matchedEdgeType = matchedAssociation?.semantics?.default_edge_type;
        const edgeItem = getPaletteItemByType(matchedEdgeType) || getFirstEdgePaletteItem();
        if (!edgeItem) {
            throw new Error("현재 메타모델에는 생성 가능한 관계선이 없습니다.");
        }
        const payload = await apiFetch(`${getVersionApiBase()}/edges`, {
            method: "POST",
            body: {
                revision: state.revision,
                edge_type: edgeItem.semantic_type_code,
                association_code: matchedAssociation?.code || null,
                semantic_type_code: edgeItem.semantic_type_code,
                notation_code: edgeItem.notation_code,
                source_node_id: edgePlan?.sourceNodeId || state.connectSourceId,
                target_node_id: edgePlan?.targetNodeId || targetNodeId,
                source_anchor: "right",
                target_anchor: "left",
                label: matchedAssociation?.display_name || edgeItem.display_name || "communication",
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
        setStatus(
            edgePlan?.autoOriented
                ? `${edgeItem.display_name || "관계선"}이 추가되었습니다. 메타모델 정의에 맞춰 방향을 자동 조정했습니다.`
                : `${edgeItem.display_name || "관계선"}이 추가되었습니다.`
        );
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
