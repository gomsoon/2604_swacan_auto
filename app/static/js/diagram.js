const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(name, attrs = {}) {
    const element = document.createElementNS(SVG_NS, name);
    Object.entries(attrs).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
            element.setAttribute(key, String(value));
        }
    });
    return element;
}

function notationForCode(notationCode, notationDefinitionsByCode) {
    if (!notationCode || !(notationDefinitionsByCode instanceof Map)) {
        return null;
    }
    return notationDefinitionsByCode.get(notationCode) || null;
}

function nodeRenderDescriptor(node, notationDefinitionsByCode) {
    const notation = notationForCode(node.notation_code, notationDefinitionsByCode);
    const renderSchema = notation?.render_schema || {};
    const primitive =
        notation?.render_primitive ||
        renderSchema.primitive ||
        (node.style?.shape === "rect" ? "rect" : "rounded_rect");
    const modifiers = renderSchema.modifiers || {};
    const hasDoubleBorder = Boolean(modifiers.double_border || node.style?.variant === "double-border");
    const hasDashedBorder = Boolean(modifiers.dashed_border || node.style?.variant === "dashed-border");
    const radius = primitive === "rect" ? 4 : renderSchema.corner_radius ?? 18;

    return {
        notation,
        primitive,
        modifiers,
        hasDoubleBorder,
        hasDashedBorder,
        radius,
    };
}

function valueForRenderSource(source, node, latestState) {
    if (!source) {
        return null;
    }
    if (source === "display_name") {
        return node.display_name;
    }
    if (source === "target_id") {
        return node.target_id;
    }
    if (source === "node_type") {
        return node.node_type;
    }
    if (source === "runtime.status") {
        return latestState?.status || null;
    }
    if (source.startsWith("runtime.")) {
        return latestState?.state?.[source.slice("runtime.".length)] ?? null;
    }
    return null;
}

function runtimeStateForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId) {
    if (node.monitored_object_id && latestStatesByMonitoredObjectId instanceof Map) {
        const byObject = latestStatesByMonitoredObjectId.get(node.monitored_object_id);
        if (byObject) {
            return byObject;
        }
    }
    if (node.target_id && latestStatesByTargetId instanceof Map) {
        return latestStatesByTargetId.get(node.target_id) || null;
    }
    return null;
}

function resolveNodeTextContent(node, renderDescriptor, latestState) {
    const labelSlots = renderDescriptor.notation?.render_schema?.label_slots || [];
    const title = valueForRenderSource(labelSlots[0]?.source, node, latestState) || node.display_name;
    const subtitle =
        valueForRenderSource(labelSlots[1]?.source, node, latestState) ||
        node.target_id ||
        node.node_type;
    return { title, subtitle };
}

function resolveAnchorPoint(node, anchor) {
    const midX = node.x + node.width / 2;
    const midY = node.y + node.height / 2;
    switch (anchor) {
        case "left":
            return { x: node.x, y: midY };
        case "right":
            return { x: node.x + node.width, y: midY };
        case "top":
            return { x: midX, y: node.y };
        case "bottom":
            return { x: midX, y: node.y + node.height };
        default:
            return { x: midX, y: midY };
    }
}

function statusClassForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId) {
    const state = runtimeStateForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId);
    if (!state) {
        return "";
    }

    if (state.status === "down" || state.severity === "critical") {
        return "status-down";
    }
    if (state.status === "warning" || state.severity === "warning") {
        return "status-warning";
    }
    if (state.status === "up" || state.status === "healthy" || state.severity === "info") {
        return "status-up";
    }
    return "";
}

function agentBadgeTextForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId) {
    if (node.node_type !== "MonitoringAgent") {
        return null;
    }

    const state = runtimeStateForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId);
    if (!state) {
        return "미수신";
    }

    const payload = state.state || {};
    if (payload.heartbeat_timeout_level === "down") {
        return "heartbeat 끊김";
    }
    if (payload.heartbeat_timeout_level === "warning") {
        return "heartbeat 지연";
    }
    const connection = payload.backend_connection_status || state.status || "unknown";
    const queueDepth = Number(payload.outbox_queue_depth);
    if (Number.isFinite(queueDepth) && queueDepth > 0) {
        return `${connection} · q${queueDepth}`;
    }
    return connection;
}

function alertCountForNode(node, alertsByMonitoredObjectId) {
    if (!node.monitored_object_id || !(alertsByMonitoredObjectId instanceof Map)) {
        return 0;
    }
    return alertsByMonitoredObjectId.get(node.monitored_object_id)?.length || 0;
}

function buildViewBox(nodes) {
    if (nodes.length === 0) {
        return "0 0 1200 800";
    }

    const minX = Math.min(...nodes.map((node) => node.x)) - 80;
    const minY = Math.min(...nodes.map((node) => node.y)) - 80;
    const maxX = Math.max(...nodes.map((node) => node.x + node.width)) + 120;
    const maxY = Math.max(...nodes.map((node) => node.y + node.height)) + 120;
    return `${minX} ${minY} ${Math.max(1200, maxX - minX)} ${Math.max(800, maxY - minY)}`;
}

export function renderDiagram(svg, options) {
    const {
        nodes,
        edges,
        selectedNodeId = null,
        selectedEdgeId = null,
        connectSourceId = null,
        latestStatesByTargetId = new Map(),
        latestStatesByMonitoredObjectId = new Map(),
        alertsByMonitoredObjectId = new Map(),
        notationDefinitionsByCode = new Map(),
        onNodeClick,
        onNodePointerDown,
        onEdgeClick,
    } = options;

    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const sortedEdges = [...edges].sort((left, right) => {
        return (left.layer_order ?? 0) - (right.layer_order ?? 0) || left.id - right.id;
    });
    const sortedNodes = [...nodes].sort((left, right) => {
        const layerDiff = (left.layer_order ?? 0) - (right.layer_order ?? 0);
        if (layerDiff !== 0) {
            return layerDiff;
        }
        const leftRank = left.parent_node_id === null ? 0 : 1;
        const rightRank = right.parent_node_id === null ? 0 : 1;
        return leftRank - rightRank || left.id - right.id;
    });

    svg.replaceChildren();
    svg.setAttribute("viewBox", buildViewBox(nodes));

    const defs = svgEl("defs");
    const marker = svgEl("marker", {
        id: "edge-arrow",
        markerWidth: 10,
        markerHeight: 10,
        refX: 8,
        refY: 3,
        orient: "auto",
        markerUnits: "strokeWidth",
    });
    marker.appendChild(svgEl("path", { d: "M0,0 L0,6 L9,3 z", fill: "#50606d" }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    const edgeLayer = svgEl("g");
    const nodeLayer = svgEl("g");

    for (const edge of sortedEdges) {
        const sourceNode = nodeMap.get(edge.source_node_id);
        const targetNode = nodeMap.get(edge.target_node_id);
        if (!sourceNode || !targetNode) {
            continue;
        }

        const source = resolveAnchorPoint(sourceNode, edge.source_anchor);
        const target = resolveAnchorPoint(targetNode, edge.target_anchor);
        const path = svgEl("path", {
            d: `M ${source.x} ${source.y} L ${target.x} ${target.y}`,
            class: `diagram-edge${edge.id === selectedEdgeId ? " is-selected" : ""}`,
            "marker-end": "url(#edge-arrow)",
        });
        path.dataset.edgeId = String(edge.id);
        path.dataset.edgeType = edge.edge_type;
        path.dataset.notationCode = edge.notation_code || "";
        if (typeof onEdgeClick === "function") {
            path.addEventListener("click", (event) => onEdgeClick(edge, event));
        }
        edgeLayer.appendChild(path);

        if (edge.label) {
            const label = svgEl("text", {
                x: (source.x + target.x) / 2,
                y: (source.y + target.y) / 2 - 8,
                "text-anchor": "middle",
                class: "node-meta",
            });
            label.textContent = edge.label;
            edgeLayer.appendChild(label);
        }
    }

    for (const node of sortedNodes) {
        const latestState = runtimeStateForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId);
        const statusClass = statusClassForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId);
        const classes = ["diagram-node"];
        const renderDescriptor = nodeRenderDescriptor(node, notationDefinitionsByCode);
        const textContent = resolveNodeTextContent(node, renderDescriptor, latestState);
        classes.push(renderDescriptor.primitive === "rect" ? "node-primitive-rect" : "node-primitive-rounded");
        classes.push(node.node_type === "PhysicalServer" ? "node-physical" : "node-process");
        if (node.node_type === "MonitoringAgent") {
            classes.push("node-agent");
        }
        if (renderDescriptor.hasDashedBorder) {
            classes.push("has-dashed-border");
        }
        if (node.id === selectedNodeId) {
            classes.push("is-selected");
        }
        if (node.id === connectSourceId) {
            classes.push("is-connect-source");
        }
        if (statusClass) {
            classes.push(statusClass);
        }

        const group = svgEl("g", {
            class: classes.join(" "),
            transform: `translate(${node.x}, ${node.y})`,
        });
        group.dataset.nodeId = String(node.id);
        group.dataset.nodeType = node.node_type;
        group.dataset.semanticType = node.semantic_type_code || node.node_type;
        group.dataset.notationCode = node.notation_code || "";

        group.appendChild(
            svgEl("rect", {
                class: "node-shape",
                x: 0,
                y: 0,
                width: node.width,
                height: node.height,
                rx: renderDescriptor.radius,
                ry: renderDescriptor.radius,
            })
        );

        if (renderDescriptor.hasDoubleBorder) {
            group.appendChild(
                svgEl("rect", {
                    class: "node-double-border",
                    x: 6,
                    y: 6,
                    width: Math.max(node.width - 12, 0),
                    height: Math.max(node.height - 12, 0),
                    rx: Math.max(renderDescriptor.radius - 4, 2),
                    ry: Math.max(renderDescriptor.radius - 4, 2),
                })
            );
        }

        const label = svgEl("text", {
            class: "node-label",
            x: node.width / 2,
            y: node.node_type === "PhysicalServer" ? 28 : node.height / 2 - 2,
            "text-anchor": "middle",
        });
        label.textContent = textContent.title;
        group.appendChild(label);

        const meta = svgEl("text", {
            class: "node-meta",
            x: node.width / 2,
            y: node.node_type === "PhysicalServer" ? 48 : node.height / 2 + 18,
            "text-anchor": "middle",
        });
        meta.textContent = textContent.subtitle;
        group.appendChild(meta);

        const agentBadgeText = agentBadgeTextForNode(node, latestStatesByTargetId, latestStatesByMonitoredObjectId);
        const alertCount = alertCountForNode(node, alertsByMonitoredObjectId);
        if (agentBadgeText) {
            const badgeWidth = Math.min(Math.max(agentBadgeText.length * 7 + 18, 78), Math.max(node.width - 16, 78));
            const badgeGroup = svgEl("g", {
                class: "node-badge",
                transform: `translate(${node.width - badgeWidth - 8}, 8)`,
            });
            badgeGroup.appendChild(
                svgEl("rect", {
                    class: "node-badge-shape",
                    x: 0,
                    y: 0,
                    width: badgeWidth,
                    height: 24,
                    rx: 12,
                    ry: 12,
                })
            );
            const badgeText = svgEl("text", {
                class: "node-badge-text",
                x: badgeWidth / 2,
                y: 16,
                "text-anchor": "middle",
            });
            badgeText.textContent = agentBadgeText;
            badgeGroup.appendChild(badgeText);
            group.appendChild(badgeGroup);
        }

        if (alertCount > 0) {
            const alertBadge = svgEl("g", {
                class: "node-alert-badge",
                transform: `translate(12, 12)`,
            });
            alertBadge.appendChild(
                svgEl("circle", {
                    class: "node-alert-badge-shape",
                    cx: 0,
                    cy: 0,
                    r: 11,
                })
            );
            const alertText = svgEl("text", {
                class: "node-alert-badge-text",
                x: 0,
                y: 4,
                "text-anchor": "middle",
            });
            alertText.textContent = String(Math.min(alertCount, 99));
            alertBadge.appendChild(alertText);
            group.appendChild(alertBadge);
        }

        if (typeof onNodeClick === "function") {
            group.addEventListener("click", (event) => onNodeClick(node, event));
        }
        if (typeof onNodePointerDown === "function") {
            group.addEventListener("pointerdown", (event) => onNodePointerDown(node, event));
        }

        nodeLayer.appendChild(group);
    }

    svg.append(edgeLayer, nodeLayer);
}

export function clientToSvg(svg, clientX, clientY) {
    const point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
}



