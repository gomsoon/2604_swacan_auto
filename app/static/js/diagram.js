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

function statusClassForNode(node, latestStatesByTargetId) {
    if (!node.target_id) {
        return "";
    }

    const state = latestStatesByTargetId.get(node.target_id);
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

function agentBadgeTextForNode(node, latestStatesByTargetId) {
    if (node.node_type !== "MonitoringAgent" || !node.target_id) {
        return null;
    }

    const state = latestStatesByTargetId.get(node.target_id);
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
        const statusClass = statusClassForNode(node, latestStatesByTargetId);
        const classes = ["diagram-node"];
        classes.push(node.node_type === "PhysicalServer" ? "node-physical" : "node-process");
        if (node.node_type === "MonitoringAgent") {
            classes.push("node-agent");
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

        const radius = node.node_type === "PhysicalServer" ? 4 : 18;
        group.appendChild(
            svgEl("rect", {
                class: "node-shape",
                x: 0,
                y: 0,
                width: node.width,
                height: node.height,
                rx: radius,
                ry: radius,
            })
        );

        if (node.node_type === "MonitoringAgent") {
            group.appendChild(
                svgEl("rect", {
                    class: "node-double-border",
                    x: 6,
                    y: 6,
                    width: Math.max(node.width - 12, 0),
                    height: Math.max(node.height - 12, 0),
                    rx: Math.max(radius - 4, 2),
                    ry: Math.max(radius - 4, 2),
                })
            );
        }

        const label = svgEl("text", {
            class: "node-label",
            x: node.width / 2,
            y: node.node_type === "PhysicalServer" ? 28 : node.height / 2 - 2,
            "text-anchor": "middle",
        });
        label.textContent = node.display_name;
        group.appendChild(label);

        const meta = svgEl("text", {
            class: "node-meta",
            x: node.width / 2,
            y: node.node_type === "PhysicalServer" ? 48 : node.height / 2 + 18,
            "text-anchor": "middle",
        });
        meta.textContent = node.target_id || node.node_type;
        group.appendChild(meta);

        const agentBadgeText = agentBadgeTextForNode(node, latestStatesByTargetId);
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



