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
const outlineSummary = document.getElementById("outline-summary");
const outlineTreeRoot = document.getElementById("editor-outline-tree");
const outlineSearchInput = document.getElementById("outline-search-input");
const outlineExpandAllButton = document.getElementById("outline-expand-all-button");
const outlineCollapseAllButton = document.getElementById("outline-collapse-all-button");
const nodeForm = document.getElementById("node-form");
const dynamicPropertiesPanel = document.getElementById("node-dynamic-properties");
const dynamicPropertiesFields = document.getElementById("node-dynamic-properties-fields");
const runtimeBindingPanel = document.getElementById("runtime-binding-panel");
const runtimeBindingSummary = document.getElementById("runtime-binding-summary");
const runtimeBindingQueryInput = document.getElementById("runtime-binding-query");
const runtimeBindingSearchButton = document.getElementById("runtime-binding-search-button");
const runtimeBindingClearButton = document.getElementById("runtime-binding-clear-button");
const runtimeBindingResults = document.getElementById("runtime-binding-results");
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
    propertyDefinitionsByType: new Map(),
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
    previewCreateNodeType: null,
    outlineQuery: "",
    collapsedOutlineNodeIds: new Set(),
    outlineSelectionNeedsScroll: false,
    bindingSearch: {
        activeNodeId: null,
        query: "",
        items: [],
        currentBinding: null,
        loading: false,
        lastRequestSignature: null,
        token: 0,
        pendingSelection: null,
    },
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

const RESERVED_NODE_PROPERTY_CODES = new Set([
    "display_name",
    "target_id",
    "instance_mode",
    "cardinality_scope",
    "expected_min",
    "expected_max",
]);

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

function getEditablePropertyDefinitions(nodeTypeCode) {
    return (state.propertyDefinitionsByType.get(nodeTypeCode) || []).filter(
        (item) => item.is_user_editable && !item.is_runtime && !RESERVED_NODE_PROPERTY_CODES.has(item.code)
    );
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

function getRootNodes() {
    return state.nodes.filter((node) => node.parent_node_id === null);
}

function getDescendantIds(nodeId) {
    const result = [nodeId];
    for (const child of getChildren(nodeId)) {
        result.push(...getDescendantIds(child.id));
    }
    return result;
}

function markOutlineSelectionForScroll() {
    state.outlineSelectionNeedsScroll = true;
}

function expandOutlineAncestors(nodeId) {
    let current = getNode(nodeId);
    while (current?.parent_node_id) {
        state.collapsedOutlineNodeIds.delete(current.parent_node_id);
        current = getNode(current.parent_node_id);
    }
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
    const propertyDefinitions = getEditablePropertyDefinitions(nodeType);
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
            properties: Object.fromEntries(
                propertyDefinitions
                    .filter((property) => property.default_value !== null && property.default_value !== undefined)
                    .map((property) => [property.code, property.default_value])
            ),
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
        properties: Object.fromEntries(
            propertyDefinitions
                .filter((property) => property.default_value !== null && property.default_value !== undefined)
                .map((property) => [property.code, property.default_value])
        ),
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

function getContainmentPreviewGuide() {
    const nodeType = state.previewCreateNodeType;
    if (!nodeType || !isNodeSemanticType(nodeType)) {
        return {
            previewNodeType: null,
            candidateIds: new Set(),
            recommendedParentId: null,
        };
    }

    const allowedParentTypeCodes = getAllowedParentTypeCodes(nodeType);
    if (allowedParentTypeCodes.length === 0) {
        return {
            previewNodeType: nodeType,
            candidateIds: new Set(),
            recommendedParentId: null,
        };
    }

    const candidateIds = new Set(
        state.nodes
            .filter((node) => allowedParentTypeCodes.includes(node.semantic_type_code || node.node_type))
            .map((node) => node.id)
    );

    return {
        previewNodeType: nodeType,
        candidateIds,
        recommendedParentId: findCandidateParentId(nodeType),
    };
}

function getConnectGuide() {
    if (!state.connectSourceId) {
        return {
            sourceNode: null,
            candidateIds: new Set(),
            blockedIds: new Set(),
        };
    }

    const sourceNode = getNode(state.connectSourceId);
    if (!sourceNode) {
        return {
            sourceNode: null,
            candidateIds: new Set(),
            blockedIds: new Set(),
        };
    }

    const candidateIds = new Set();
    const blockedIds = new Set();

    for (const node of state.nodes) {
        if (node.id === sourceNode.id) {
            continue;
        }
        const edgePlan = resolveEdgeCreationPlan(sourceNode, node);
        if (edgePlan?.association) {
            candidateIds.add(node.id);
        } else {
            blockedIds.add(node.id);
        }
    }

    return { sourceNode, candidateIds, blockedIds };
}

function clearPalettePreview(nodeType = null) {
    if (nodeType && state.previewCreateNodeType !== nodeType) {
        return;
    }
    if (!state.previewCreateNodeType) {
        return;
    }
    state.previewCreateNodeType = null;
    render();
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
            button.addEventListener("mouseenter", () => {
                state.previewCreateNodeType = item.semantic_type_code;
                render();
            });
            button.addEventListener("focus", () => {
                state.previewCreateNodeType = item.semantic_type_code;
                render();
            });
            button.addEventListener("mouseleave", () => clearPalettePreview(item.semantic_type_code));
            button.addEventListener("blur", () => clearPalettePreview(item.semantic_type_code));
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

function refreshPalettePreviewState() {
    const paletteButtons = paletteGroupsRoot?.querySelectorAll(".palette-button") || [];
    paletteButtons.forEach((button) => {
        button.classList.toggle("is-previewing", button.dataset.semanticType === state.previewCreateNodeType);
    });
}

function sortNodesForOutline(nodes) {
    return [...nodes].sort((left, right) => {
        const leftLayer = Number(left.layer_order || 0);
        const rightLayer = Number(right.layer_order || 0);
        if (leftLayer !== rightLayer) {
            return leftLayer - rightLayer;
        }
        return left.id - right.id;
    });
}

function getOutlineSearchTerm() {
    return state.outlineQuery.trim().toLowerCase();
}

function nodeMatchesOutlineSearch(node) {
    const query = getOutlineSearchTerm();
    if (!query) {
        return true;
    }
    const semanticType = getSemanticType(node.semantic_type_code || node.node_type);
    const searchableParts = [
        node.display_name,
        node.target_id,
        node.semantic_type_code,
        node.node_type,
        semanticType?.display_name,
    ];
    return searchableParts.some((item) => String(item || "").toLowerCase().includes(query));
}

function branchMatchesOutlineSearch(node) {
    if (nodeMatchesOutlineSearch(node)) {
        return true;
    }
    return getChildren(node.id).some((child) => branchMatchesOutlineSearch(child));
}

function getOutlineNodesWithChildren() {
    return new Set(
        state.nodes
            .filter((node) => getChildren(node.id).length > 0)
            .map((node) => node.id)
    );
}

function isOutlineNodeCollapsed(nodeId) {
    return !getOutlineSearchTerm() && state.collapsedOutlineNodeIds.has(nodeId);
}

function collapseAllOutlineBranches() {
    state.collapsedOutlineNodeIds = getOutlineNodesWithChildren();
    render();
    setStatus("Outline을 모두 접었습니다.");
}

function expandAllOutlineBranches() {
    state.collapsedOutlineNodeIds = new Set();
    render();
    setStatus("Outline을 모두 펼쳤습니다.");
}

function countIncidentEdges(nodeId) {
    return state.edges.filter((edge) => edge.source_node_id === nodeId || edge.target_node_id === nodeId).length;
}

function renderOutlineNode(node, depth = 0, guides = {}) {
    const semanticType = getSemanticType(node.semantic_type_code || node.node_type);
    const childCount = getChildren(node.id).length;
    const isCollapsed = isOutlineNodeCollapsed(node.id);
    const item = document.createElement("button");
    item.type = "button";
    item.className = "outline-item";
    item.dataset.nodeId = String(node.id);
    item.dataset.depth = String(depth);
    if (childCount > 0) {
        item.dataset.collapsed = isCollapsed ? "true" : "false";
    }
    if (node.id === state.selectedNodeId) {
        item.classList.add("is-selected");
    }
    if (node.id === state.connectSourceId) {
        item.classList.add("is-connect-source");
    }
    if (guides.connectCandidateIds?.has(node.id)) {
        item.classList.add("is-connect-candidate");
    }
    if (guides.connectBlockedIds?.has(node.id)) {
        item.classList.add("is-connect-blocked");
    }
    if (guides.containmentCandidateIds?.has(node.id)) {
        item.classList.add("is-containment-candidate");
    }
    if (guides.recommendedParentId === node.id) {
        item.classList.add("is-containment-target");
    }
    item.style.setProperty("--outline-depth", String(depth));

    const main = document.createElement("span");
    main.className = "outline-item-main";

    const name = document.createElement("span");
    name.className = "outline-item-name";
    name.textContent = node.display_name || semanticType?.display_name || node.node_type;
    main.appendChild(name);

    const type = document.createElement("span");
    type.className = "outline-item-type";
    type.textContent = semanticType?.display_name || node.node_type;
    main.appendChild(type);

    const meta = document.createElement("span");
    meta.className = "outline-item-meta";

    if (childCount > 0) {
        const childBadge = document.createElement("span");
        childBadge.className = "outline-badge";
        childBadge.textContent = isCollapsed ? `자식 ${childCount} · 접힘` : `자식 ${childCount}`;
        meta.appendChild(childBadge);
    }

    const edgeCount = countIncidentEdges(node.id);
    if (edgeCount > 0) {
        const edgeBadge = document.createElement("span");
        edgeBadge.className = "outline-badge";
        edgeBadge.textContent = `관계 ${edgeCount}`;
        meta.appendChild(edgeBadge);
    }

    if (node.target_id) {
        const bindingBadge = document.createElement("span");
        bindingBadge.className = "outline-badge binding";
        bindingBadge.textContent = "binding";
        meta.appendChild(bindingBadge);
    }

    if (guides.recommendedParentId === node.id) {
        const targetBadge = document.createElement("span");
        targetBadge.className = "outline-badge ok";
        targetBadge.textContent = "추가 위치";
        meta.appendChild(targetBadge);
    } else if (guides.containmentCandidateIds?.has(node.id)) {
        const candidateBadge = document.createElement("span");
        candidateBadge.className = "outline-badge ok";
        candidateBadge.textContent = "허용 parent";
        meta.appendChild(candidateBadge);
    }

    if (guides.connectCandidateIds?.has(node.id)) {
        const connectBadge = document.createElement("span");
        connectBadge.className = "outline-badge ok";
        connectBadge.textContent = "연결 가능";
        meta.appendChild(connectBadge);
    } else if (guides.connectBlockedIds?.has(node.id)) {
        const blockedBadge = document.createElement("span");
        blockedBadge.className = "outline-badge warning";
        blockedBadge.textContent = "연결 불가";
        meta.appendChild(blockedBadge);
    }

    item.appendChild(main);
    item.appendChild(meta);
    item.addEventListener("click", () => {
        state.selectedNodeId = node.id;
        state.selectedEdgeId = null;
        state.connectSourceId = null;
        expandOutlineAncestors(node.id);
        markOutlineSelectionForScroll();
        render();
        setStatus(`${node.display_name || node.node_type}을(를) outline에서 선택했습니다.`);
    });
    return item;
}

function renderOutlineBranch(nodes, depth = 0, guides = {}) {
    const fragment = document.createDocumentFragment();
    for (const node of sortNodesForOutline(nodes)) {
        if (!branchMatchesOutlineSearch(node)) {
            continue;
        }
        fragment.appendChild(renderOutlineNode(node, depth, guides));
        const children = getChildren(node.id);
        if (children.length > 0 && !isOutlineNodeCollapsed(node.id)) {
            fragment.appendChild(renderOutlineBranch(children, depth + 1, guides));
        }
    }
    return fragment;
}

function renderOutline(guides = {}) {
    if (!outlineTreeRoot) {
        return;
    }

    outlineTreeRoot.replaceChildren();

    const visibleNodeCount = state.nodes.filter((node) => branchMatchesOutlineSearch(node)).length;
    const searchTerm = getOutlineSearchTerm();
    if (outlineSummary) {
        outlineSummary.textContent = searchTerm
            ? `${state.viewVersionCode || "draft"} · 검색 ${visibleNodeCount}/${state.nodes.length}개 · 관계선 ${state.edges.length}개`
            : `${state.viewVersionCode || "draft"} · 노드 ${state.nodes.length}개 · 관계선 ${state.edges.length}개`;
    }

    const root = document.createElement("div");
    root.className = "outline-root-card";

    const rootTitle = document.createElement("div");
    rootTitle.className = "outline-root-title";
    rootTitle.textContent = state.viewName || "Draft View Version";
    root.appendChild(rootTitle);

    const rootMeta = document.createElement("div");
    rootMeta.className = "outline-root-meta";
    rootMeta.textContent = `${state.viewVersionCode || "draft"} / ${state.viewVersionStatus || "-"}`;
    root.appendChild(rootMeta);

    outlineTreeRoot.appendChild(root);
    const branch = renderOutlineBranch(getRootNodes(), 0, guides);
    if (!branch.childNodes.length) {
        const empty = document.createElement("div");
        empty.className = "outline-empty-state";
        empty.textContent = "검색 조건에 맞는 객체가 없습니다.";
        outlineTreeRoot.appendChild(empty);
    } else {
        outlineTreeRoot.appendChild(branch);
    }

    if (state.outlineSelectionNeedsScroll && state.selectedNodeId) {
        const selectedItem = outlineTreeRoot.querySelector(`.outline-item[data-node-id="${state.selectedNodeId}"]`);
        selectedItem?.scrollIntoView({ block: "nearest" });
        state.outlineSelectionNeedsScroll = false;
    }
}

async function loadPalette(metamodelVersionCode) {
    const registry = await loadViewVersionMetamodel(state.viewVersionId, metamodelVersionCode);
    state.metamodelVersionId = registry.versionId;
    state.metamodelVersionCode = registry.versionCode;
    state.semanticTypesByCode = registry.semanticTypesByCode;
    state.propertyDefinitionsByType = registry.propertyDefinitionsByType || new Map();
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

function createDynamicPropertyField(property, value) {
    const label = document.createElement("label");
    label.className = "field";
    label.dataset.propertyField = property.code;

    const title = document.createElement("span");
    title.textContent = property.display_name;
    label.appendChild(title);

    let input;
    if (property.value_type === "boolean") {
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = Boolean(value);
    } else if (property.value_type === "json") {
        input = document.createElement("textarea");
        input.rows = 3;
        input.value = value === undefined ? "" : JSON.stringify(value, null, 2);
    } else {
        input = document.createElement("input");
        input.type = property.value_type === "number" || property.value_type === "integer" ? "number" : "text";
        if (property.value_type === "number") {
            input.step = "any";
        }
        if (property.value_type === "integer") {
            input.step = "1";
        }
        input.value = value ?? "";
    }

    input.dataset.propertyInputCode = property.code;
    input.dataset.valueType = property.value_type;
    label.appendChild(input);

    if (property.description) {
        const hint = document.createElement("small");
        hint.className = "field-hint";
        hint.textContent = property.description;
        label.appendChild(hint);
    }

    return label;
}

function renderDynamicPropertyFields(node) {
    if (!dynamicPropertiesPanel || !dynamicPropertiesFields) {
        return;
    }

    dynamicPropertiesFields.replaceChildren();
    const propertyDefinitions = getEditablePropertyDefinitions(node.semantic_type_code || node.node_type);
    if (propertyDefinitions.length === 0) {
        dynamicPropertiesPanel.hidden = true;
        return;
    }

    const currentProperties = node.properties || {};
    for (const property of propertyDefinitions) {
        const value = Object.prototype.hasOwnProperty.call(currentProperties, property.code)
            ? currentProperties[property.code]
            : property.default_value;
        dynamicPropertiesFields.appendChild(createDynamicPropertyField(property, value));
    }
    dynamicPropertiesPanel.hidden = false;
}

function collectDynamicProperties(node) {
    const propertyDefinitions = getEditablePropertyDefinitions(node.semantic_type_code || node.node_type);
    const nextProperties = {};

    for (const property of propertyDefinitions) {
        const input = dynamicPropertiesFields?.querySelector(`[data-property-input-code="${property.code}"]`);
        if (!input) {
            continue;
        }

        let value;
        if (property.value_type === "boolean") {
            value = Boolean(input.checked);
        } else if (property.value_type === "json") {
            const raw = input.value.trim();
            value = raw === "" ? null : JSON.parse(raw);
        } else if (property.value_type === "integer") {
            const raw = input.value.trim();
            value = raw === "" ? null : Number.parseInt(raw, 10);
        } else if (property.value_type === "number") {
            const raw = input.value.trim();
            value = raw === "" ? null : Number(raw);
        } else {
            const raw = input.value.trim();
            value = raw === "" ? null : raw;
        }

        if (value !== null) {
            nextProperties[property.code] = value;
        }
    }

    return nextProperties;
}

function getRuntimeBindingRequestSignature(node) {
    return JSON.stringify({
        nodeId: node?.id || null,
        targetId: node?.target_id || "",
        query: state.bindingSearch.query.trim(),
    });
}

function getRuntimeBindingDisplay(item) {
    if (!item) {
        return "";
    }
    return item.runtime_binding_key || item.display_name || `object #${item.id}`;
}

function renderRuntimeBindingPanel(node, semanticType) {
    if (!runtimeBindingPanel || !runtimeBindingSummary || !runtimeBindingResults) {
        return;
    }

    const allowsRuntimeBinding = semanticType?.allows_runtime_binding !== false;
    runtimeBindingPanel.hidden = !allowsRuntimeBinding;
    if (!allowsRuntimeBinding) {
        runtimeBindingResults.replaceChildren();
        return;
    }

    const editable = isEditableVersion();
    runtimeBindingQueryInput.disabled = !editable;
    runtimeBindingSearchButton.disabled = !editable;
    runtimeBindingClearButton.disabled = !editable;
    runtimeBindingQueryInput.value = state.bindingSearch.query;

    const pendingSelection = state.bindingSearch.pendingSelection;
    const currentBinding = state.bindingSearch.currentBinding;
    const targetIdValue = formFields.targetId.value.trim();
    const isPendingSelection =
        pendingSelection && pendingSelection.runtime_binding_key === targetIdValue && targetIdValue !== (node.target_id || "");

    if (state.bindingSearch.loading) {
        runtimeBindingSummary.textContent = "Runtime binding 후보를 불러오는 중입니다.";
    } else if (isPendingSelection) {
        runtimeBindingSummary.textContent = `저장 전 선택됨: ${pendingSelection.display_name} · ${getRuntimeBindingDisplay(pendingSelection)}`;
    } else if (currentBinding) {
        runtimeBindingSummary.textContent = `현재 binding: ${currentBinding.display_name} · ${getRuntimeBindingDisplay(currentBinding)} · open alert ${currentBinding.open_alert_count}`;
    } else if (node.target_id) {
        runtimeBindingSummary.textContent = `현재 target_id는 매핑되지 않았습니다: ${node.target_id}`;
    } else {
        runtimeBindingSummary.textContent = "현재 binding이 없습니다.";
    }

    runtimeBindingResults.replaceChildren();
    const items = state.bindingSearch.items || [];
    if (items.length === 0) {
        const empty = document.createElement("p");
        empty.className = "runtime-binding-empty";
        empty.textContent = state.bindingSearch.loading
            ? "검색 중입니다..."
            : "표시할 runtime binding 후보가 없습니다.";
        runtimeBindingResults.appendChild(empty);
        return;
    }

    for (const item of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "runtime-binding-item";
        const selectedTargetId = targetIdValue || node.target_id || "";
        if (item.runtime_binding_key && item.runtime_binding_key === selectedTargetId) {
            button.classList.add("is-selected");
        }

        const title = document.createElement("strong");
        title.textContent = item.display_name;
        button.appendChild(title);

        const meta = document.createElement("span");
        meta.className = "runtime-binding-item-meta";
        meta.textContent = [
            item.object_type,
            getRuntimeBindingDisplay(item),
            `open alert ${item.open_alert_count}`,
        ]
            .filter(Boolean)
            .join(" · ");
        button.appendChild(meta);

        button.addEventListener("click", () => {
            formFields.targetId.value = item.runtime_binding_key || "";
            state.bindingSearch.pendingSelection = item;
            renderRuntimeBindingPanel(node, semanticType);
            setStatus(`${item.display_name} runtime binding을 적용했습니다. 저장하면 반영됩니다.`);
        });
        runtimeBindingResults.appendChild(button);
    }
}

async function loadRuntimeBindingCandidates(node, { force = false } = {}) {
    const semanticType = getSemanticType(node?.semantic_type_code || node?.node_type);
    if (!node || semanticType?.allows_runtime_binding === false) {
        return;
    }

    const signature = getRuntimeBindingRequestSignature(node);
    if (!force && state.bindingSearch.lastRequestSignature === signature) {
        return;
    }

    state.bindingSearch.loading = true;
    state.bindingSearch.lastRequestSignature = signature;
    const token = state.bindingSearch.token + 1;
    state.bindingSearch.token = token;
    renderRuntimeBindingPanel(node, semanticType);

    try {
        const params = new URLSearchParams();
        const query = state.bindingSearch.query.trim();
        if (query) {
            params.set("query", query);
        }
        if (node.target_id) {
            params.set("current_target_id", node.target_id);
        }
        params.set("limit", "8");

        const payload = await apiFetch(`${getVersionApiBase()}/monitored-objects?${params.toString()}`);
        if (state.bindingSearch.token !== token || state.selectedNodeId !== node.id) {
            return;
        }
        state.bindingSearch.items = payload.items || [];
        state.bindingSearch.currentBinding = payload.current_binding || null;
    } catch (error) {
        if (state.bindingSearch.token === token && state.selectedNodeId === node.id) {
            showBanner(error.message, "error");
            state.bindingSearch.items = [];
            state.bindingSearch.currentBinding = null;
        }
    } finally {
        if (state.bindingSearch.token === token && state.selectedNodeId === node.id) {
            state.bindingSearch.loading = false;
            renderRuntimeBindingPanel(node, semanticType);
        }
    }
}

function resetRuntimeBindingPanel(node = null) {
    const nextTargetId = node?.target_id || "";
    const sameNode = state.bindingSearch.activeNodeId === node?.id;
    const existingSelected = state.bindingSearch.pendingSelection;
    const keepPendingSelection =
        sameNode &&
        existingSelected &&
        existingSelected.runtime_binding_key === formFields.targetId.value.trim() &&
        existingSelected.runtime_binding_key !== nextTargetId;

    state.bindingSearch.activeNodeId = node?.id || null;
    state.bindingSearch.query = "";
    state.bindingSearch.items = [];
    state.bindingSearch.currentBinding = null;
    state.bindingSearch.loading = false;
    state.bindingSearch.lastRequestSignature = null;
    state.bindingSearch.pendingSelection = keepPendingSelection ? existingSelected : null;
    if (runtimeBindingQueryInput) {
        runtimeBindingQueryInput.value = "";
    }
}

function syncSelectionPanel() {
    const node = getNode(state.selectedNodeId);
    if (node) {
        const semanticType = getSemanticType(node.semantic_type_code || node.node_type);
        const previousActiveNodeId = state.bindingSearch.activeNodeId;
        const previousTargetId = previousActiveNodeId === node.id ? (state.bindingSearch.currentBinding?.runtime_binding_key || node.target_id || "") : "";
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
        renderDynamicPropertyFields(node);
        if (previousActiveNodeId !== node.id || previousTargetId !== (node.target_id || "")) {
            resetRuntimeBindingPanel(node);
        }
        renderRuntimeBindingPanel(node, semanticType);
        if (allowsRuntimeBinding) {
            loadRuntimeBindingCandidates(node);
        }
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
        if (runtimeBindingPanel) {
            runtimeBindingPanel.hidden = true;
        }
        edgeIdText.textContent = String(edge.id);
        edgeLinkText.textContent = `${sourceNode?.display_name || edge.source_node_id} -> ${targetNode?.display_name || edge.target_node_id}`;
        return;
    }

    selectionKind.textContent = "선택된 항목이 없습니다.";
    nodeForm.hidden = true;
    edgeSummary.hidden = true;
    resetRuntimeBindingPanel();
    if (runtimeBindingPanel) {
        runtimeBindingPanel.hidden = true;
    }
    if (dynamicPropertiesPanel) {
        dynamicPropertiesPanel.hidden = true;
    }
}

function render() {
    const containmentGuide = getContainmentPreviewGuide();
    const connectGuide = getConnectGuide();
    renderDiagram(svg, {
        nodes: state.nodes,
        edges: state.edges,
        notationDefinitionsByCode: state.notationDefinitionsByCode,
        selectedNodeId: state.selectedNodeId,
        selectedEdgeId: state.selectedEdgeId,
        connectSourceId: state.connectSourceId,
        connectCandidateIds: connectGuide.candidateIds,
        connectBlockedIds: connectGuide.blockedIds,
        containmentCandidateIds: containmentGuide.candidateIds,
        containmentRecommendedParentId: containmentGuide.recommendedParentId,
        onNodeClick: handleNodeClick,
        onNodePointerDown: handleNodePointerDown,
        onEdgeClick: handleEdgeClick,
    });
    syncSelectionPanel();
    renderOutline({
        connectCandidateIds: connectGuide.candidateIds,
        connectBlockedIds: connectGuide.blockedIds,
        containmentCandidateIds: containmentGuide.candidateIds,
        recommendedParentId: containmentGuide.recommendedParentId,
    });
    refreshPaletteInteractivity();
    refreshPalettePreviewState();
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
        state.previewCreateNodeType = null;
        state.collapsedOutlineNodeIds = new Set();
        resetRuntimeBindingPanel();
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
        state.previewCreateNodeType = null;
        expandOutlineAncestors(payload.node.id);
        markOutlineSelectionForScroll();
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
    state.previewCreateNodeType = null;
    state.selectedEdgeId = null;
    const connectGuide = getConnectGuide();
    if (connectGuide.candidateIds.size === 0) {
        state.connectSourceId = null;
        render();
        showBanner("현재 메타모델 기준으로 연결 가능한 대상이 없습니다.", "error");
        return;
    }
    render();
    setStatus(`연결 가능한 대상 ${connectGuide.candidateIds.size}개를 표시했습니다.`);
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
        if (!matchedAssociation) {
            throw new Error("현재 메타모델 기준으로 연결할 수 없는 조합입니다.");
        }
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
                properties: collectDynamicProperties(node),
                x: readNumber(formFields.x, node.x),
                y: readNumber(formFields.y, node.y),
                width: readNumber(formFields.width, node.width),
                height: readNumber(formFields.height, node.height),
            },
        });
        state.nodes = state.nodes.map((item) => (item.id === node.id ? payload.node : item));
        state.bindingSearch.pendingSelection = null;
        state.bindingSearch.lastRequestSignature = null;
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
        const connectGuide = getConnectGuide();
        if (!connectGuide.candidateIds.has(node.id)) {
            showBanner("현재 메타모델 기준으로 연결할 수 없는 대상입니다.", "error");
            setStatus("연결 가능한 대상만 강조 표시됩니다.");
            render();
            return;
        }
        createEdge(node.id);
        return;
    }

    state.selectedNodeId = node.id;
    state.selectedEdgeId = null;
    expandOutlineAncestors(node.id);
    markOutlineSelectionForScroll();
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
    state.previewCreateNodeType = null;
    render();
});

startConnectButton?.addEventListener("click", startConnectMode);
document.getElementById("delete-selected-button")?.addEventListener("click", deleteSelected);
document.getElementById("reload-view-button")?.addEventListener("click", loadView);
nodeForm?.addEventListener("submit", saveSelectedNode);
publishVersionButton?.addEventListener("click", publishCurrentVersion);
activateVersionButton?.addEventListener("click", activateCurrentVersion);
outlineSearchInput?.addEventListener("input", (event) => {
    state.outlineQuery = event.target.value || "";
    render();
});
runtimeBindingQueryInput?.addEventListener("input", (event) => {
    state.bindingSearch.query = event.target.value || "";
    state.bindingSearch.lastRequestSignature = null;
    const node = getNode(state.selectedNodeId);
    if (node) {
        loadRuntimeBindingCandidates(node, { force: true });
    }
});
runtimeBindingSearchButton?.addEventListener("click", () => {
    const node = getNode(state.selectedNodeId);
    if (node) {
        state.bindingSearch.lastRequestSignature = null;
        loadRuntimeBindingCandidates(node, { force: true });
    }
});
runtimeBindingClearButton?.addEventListener("click", () => {
    const node = getNode(state.selectedNodeId);
    formFields.targetId.value = "";
    state.bindingSearch.pendingSelection = null;
    if (node) {
        renderRuntimeBindingPanel(node, getSemanticType(node.semantic_type_code || node.node_type));
        setStatus("Runtime binding을 제거했습니다. 저장하면 반영됩니다.");
    }
});
outlineExpandAllButton?.addEventListener("click", expandAllOutlineBranches);
outlineCollapseAllButton?.addEventListener("click", collapseAllOutlineBranches);

loadView();
