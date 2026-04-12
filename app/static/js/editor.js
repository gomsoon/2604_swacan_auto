import { apiFetch, clearBanner, readNumber, showBanner, slugify } from "./common.js";
import { clientToSvg, renderDiagram } from "./diagram.js";

const appRoot = document.getElementById("editor-app");
const svg = document.getElementById("editor-canvas");
const selectionKind = document.getElementById("selection-kind");
const revisionLabel = document.getElementById("editor-revision-label");
const statusLabel = document.getElementById("editor-status-label");
const nodeForm = document.getElementById("node-form");
const edgeSummary = document.getElementById("edge-summary");
const edgeIdText = document.getElementById("edge-id-text");
const edgeLinkText = document.getElementById("edge-link-text");

const state = {
    viewId: Number(appRoot.dataset.viewId),
    viewName: "",
    revision: 0,
    nodes: [],
    edges: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    connectSourceId: null,
    drag: null,
    lastDragAt: 0,
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

function updateRevision(revision) {
    state.revision = revision;
    revisionLabel.textContent = `revision ${revision}`;
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

function getDefaultNodePayload(nodeType) {
    if (nodeType === "PhysicalServer") {
        const serverCount = state.nodes.filter((node) => node.node_type === "PhysicalServer").length;
        return {
            parent_node_id: null,
            display_name: `Host ${String.fromCharCode(65 + serverCount)}`,
            target_id: null,
            x: 60 + serverCount * 80,
            y: 60 + serverCount * 40,
            width: 480,
            height: 260,
            style: { shape: "rect" },
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
    const displayName = nodeType === "MonitoringAgent" ? "Monitoring Agent" : "App Process";
    const targetPrefix = nodeType === "MonitoringAgent" ? "agent" : "process";

    return {
        parent_node_id: parentId,
        display_name: displayName,
        target_id: nextTargetId(targetPrefix, displayName),
        x: baseX,
        y: baseY,
        width: nodeType === "MonitoringAgent" ? 170 : 180,
        height: 56,
        style:
            nodeType === "MonitoringAgent"
                ? { shape: "rounded-rect", variant: "double-border" }
                : { shape: "rounded-rect" },
    };
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
    clearBanner();
    try {
        const payload = await apiFetch(`/api/views/${state.viewId}`);
        state.viewName = payload.view.name;
        state.nodes = payload.nodes;
        state.edges = payload.edges;
        state.selectedNodeId = null;
        state.selectedEdgeId = null;
        state.connectSourceId = null;
        updateRevision(payload.view.revision);
        render();
        setStatus("뷰가 준비되었습니다.");
    } catch (error) {
        showBanner(error.message, "error");
        setStatus("뷰를 불러오지 못했습니다.");
    }
}

async function addNode(nodeType) {
    clearBanner();
    try {
        const payload = await apiFetch(`/api/views/${state.viewId}/nodes`, {
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
    if (!state.connectSourceId || state.connectSourceId === targetNodeId) {
        state.connectSourceId = null;
        render();
        return;
    }

    clearBanner();
    try {
        const payload = await apiFetch(`/api/views/${state.viewId}/edges`, {
            method: "POST",
            body: {
                revision: state.revision,
                edge_type: "CommunicationLink",
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
    clearBanner();
    try {
        if (state.selectedNodeId) {
            await apiFetch(`/api/views/${state.viewId}/nodes/${state.selectedNodeId}`, {
                method: "DELETE",
                body: { revision: state.revision },
            });
            await loadView();
            setStatus("노드가 삭제되었습니다.");
            return;
        }

        if (state.selectedEdgeId) {
            const edgeId = state.selectedEdgeId;
            const payload = await apiFetch(`/api/views/${state.viewId}/edges/${edgeId}`, {
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
    const node = getNode(state.selectedNodeId);
    if (!node) {
        return;
    }

    clearBanner();
    try {
        const payload = await apiFetch(`/api/views/${state.viewId}/nodes/${node.id}`, {
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
    if (event.button !== 0 || state.connectSourceId) {
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
    const payload = await apiFetch(`/api/views/${state.viewId}`, {
        method: "PUT",
        body: {
            revision: state.revision,
            nodes: state.nodes,
            edges: state.edges,
        },
    });
    updateRevision(payload.revision);
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

document.getElementById("add-server-button")?.addEventListener("click", () => addNode("PhysicalServer"));
document.getElementById("add-process-button")?.addEventListener("click", () => addNode("SoftwareProcess"));
document.getElementById("add-agent-button")?.addEventListener("click", () => addNode("MonitoringAgent"));
document.getElementById("start-connect-button")?.addEventListener("click", startConnectMode);
document.getElementById("delete-selected-button")?.addEventListener("click", deleteSelected);
document.getElementById("reload-view-button")?.addEventListener("click", loadView);
nodeForm?.addEventListener("submit", saveSelectedNode);

loadView();
