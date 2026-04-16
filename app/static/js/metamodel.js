import { apiFetch } from "./common.js";

const FALLBACK_PALETTE_GROUPS = [
    {
        code: "servers",
        label: "Servers",
        items: [
            {
                notation_code: "server.physical.rect",
                display_name: "Physical Server",
                semantic_type_code: "PhysicalServer",
                render_primitive: "rect",
                render_schema: {
                    primitive: "rect",
                    default_size: { width: 480, height: 260 },
                    anchors: ["top", "right", "bottom", "left"],
                },
            },
            {
                notation_code: "vm.logical.rect",
                display_name: "Virtual Machine",
                semantic_type_code: "VirtualMachine",
                render_primitive: "rect",
                render_schema: {
                    primitive: "rect",
                    default_size: { width: 360, height: 220 },
                    anchors: ["top", "right", "bottom", "left"],
                    modifiers: { dashed_border: true },
                },
            },
        ],
    },
    {
        code: "processes",
        label: "Processes",
        items: [
            {
                notation_code: "process.rounded_rect",
                display_name: "Software Process",
                semantic_type_code: "SoftwareProcess",
                render_primitive: "rounded_rect",
                render_schema: {
                    primitive: "rounded_rect",
                    default_size: { width: 180, height: 56 },
                    anchors: ["top", "right", "bottom", "left"],
                },
            },
        ],
    },
    {
        code: "monitoring",
        label: "Monitoring",
        items: [
            {
                notation_code: "agent.rounded_rect.double_border",
                display_name: "Monitoring Agent",
                semantic_type_code: "MonitoringAgent",
                render_primitive: "rounded_rect",
                render_schema: {
                    primitive: "rounded_rect",
                    default_size: { width: 170, height: 56 },
                    anchors: ["top", "right", "bottom", "left"],
                    modifiers: { double_border: true },
                },
            },
        ],
    },
    {
        code: "communication",
        label: "Communication",
        items: [
            {
                notation_code: "communication.line",
                display_name: "Communication Link",
                semantic_type_code: "CommunicationLink",
                render_primitive: "line",
                render_schema: {
                    primitive: "line",
                    anchors: ["top", "right", "bottom", "left"],
                },
            },
        ],
    },
];

const FALLBACK_SEMANTIC_TYPES = [
    { code: "PhysicalServer", display_name: "Physical Server", kind: "node", runtime_kind: "host", allows_runtime_binding: true, is_active: true, default_notation_code: "server.physical.rect" },
    { code: "VirtualMachine", display_name: "Virtual Machine", kind: "node", runtime_kind: "host", allows_runtime_binding: true, is_active: true, default_notation_code: "vm.logical.rect" },
    { code: "SoftwareProcess", display_name: "Software Process", kind: "node", runtime_kind: "process", allows_runtime_binding: true, is_active: true, default_notation_code: "process.rounded_rect" },
    { code: "MonitoringAgent", display_name: "Monitoring Agent", kind: "node", runtime_kind: "agent", allows_runtime_binding: true, is_active: true, default_notation_code: "agent.rounded_rect.double_border" },
    { code: "CommunicationLink", display_name: "Communication Link", kind: "edge", runtime_kind: null, allows_runtime_binding: false, is_active: true, default_notation_code: "communication.line" },
];

const FALLBACK_CONTAINMENT_RULES = [
    { parent_type_code: "PhysicalServer", child_type_code: "VirtualMachine" },
    { parent_type_code: "PhysicalServer", child_type_code: "SoftwareProcess" },
    { parent_type_code: "PhysicalServer", child_type_code: "MonitoringAgent" },
    { parent_type_code: "VirtualMachine", child_type_code: "SoftwareProcess" },
    { parent_type_code: "VirtualMachine", child_type_code: "MonitoringAgent" },
];

const FALLBACK_ASSOCIATIONS = [
    { code: "communicates_with", source_type_code: "SoftwareProcess", target_type_code: "SoftwareProcess", direction: "directed", semantics: { default_edge_type: "CommunicationLink" } },
    { code: "monitors", source_type_code: "MonitoringAgent", target_type_code: "SoftwareProcess", direction: "directed", semantics: { default_edge_type: "CommunicationLink" } },
];

function cloneJson(value) {
    return JSON.parse(JSON.stringify(value));
}

export function buildFallbackPaletteGroups() {
    return cloneJson(FALLBACK_PALETTE_GROUPS);
}

export function buildNotationDefinitionsByCode(items = []) {
    const map = new Map();
    for (const item of items) {
        map.set(item.code || item.notation_code, {
            id: item.id || item.notation_id || null,
            code: item.code || item.notation_code,
            display_name: item.display_name,
            semantic_type_code: item.semantic_type_code,
            render_primitive: item.render_primitive,
            render_schema: item.render_schema || {},
            style_tokens: item.style_tokens || {},
            kind: item.kind || null,
            palette_group_code: item.palette_group_code || null,
        });
    }
    return map;
}

export function buildSemanticTypesByCode(items = []) {
    const map = new Map();
    for (const item of items) {
        map.set(item.code || item.semantic_type_code, item);
    }
    return map;
}

function buildFallbackSemanticTypesByCode() {
    return buildSemanticTypesByCode(FALLBACK_SEMANTIC_TYPES);
}

function flattenPaletteNotationItems(paletteGroups) {
    return paletteGroups.flatMap((group) =>
        (group.items || []).map((item) => ({
            code: item.notation_code,
            display_name: item.display_name,
            semantic_type_code: item.semantic_type_code,
            render_primitive: item.render_primitive,
            render_schema: item.render_schema || {},
            style_tokens: item.style_tokens || {},
            palette_group_code: group.code,
        }))
    );
}

export async function loadMetamodelRegistry(versionCode) {
    if (!versionCode) {
        const fallbackPaletteGroups = buildFallbackPaletteGroups();
        return {
            versionId: null,
            versionCode: null,
            versionStatus: null,
            paletteGroups: fallbackPaletteGroups,
            notationDefinitionsByCode: buildNotationDefinitionsByCode(flattenPaletteNotationItems(fallbackPaletteGroups)),
            semanticTypesByCode: buildFallbackSemanticTypesByCode(),
            containmentRules: cloneJson(FALLBACK_CONTAINMENT_RULES),
            associations: cloneJson(FALLBACK_ASSOCIATIONS),
            usedFallback: true,
        };
    }

    try {
        const versionsPayload = await apiFetch("/api/metamodel/versions/published");
        const version = versionsPayload.items.find((item) => item.version_code === versionCode);
        if (!version) {
            throw new Error(`published metamodel version '${versionCode}' not found`);
        }

        const [palettePayload, notationPayload, semanticTypePayload, containmentPayload, associationPayload] = await Promise.all([
            apiFetch(`/api/metamodel/versions/${version.id}/palette`),
            apiFetch(`/api/metamodel/versions/${version.id}/notations`),
            apiFetch(`/api/metamodel/versions/${version.id}/semantic-types`),
            apiFetch(`/api/metamodel/versions/${version.id}/containment-rules`),
            apiFetch(`/api/metamodel/versions/${version.id}/associations`),
        ]);

        return {
            versionId: version.id,
            versionCode,
            versionStatus: version.status,
            paletteGroups: palettePayload.palette_groups || [],
            notationDefinitionsByCode: buildNotationDefinitionsByCode(notationPayload.items || []),
            semanticTypesByCode: buildSemanticTypesByCode(semanticTypePayload.items || []),
            containmentRules: containmentPayload.items || [],
            associations: associationPayload.items || [],
            usedFallback: false,
        };
    } catch (error) {
        console.error(error);
        const fallbackPaletteGroups = buildFallbackPaletteGroups();
        return {
            versionId: null,
            versionCode,
            versionStatus: null,
            paletteGroups: fallbackPaletteGroups,
            notationDefinitionsByCode: buildNotationDefinitionsByCode(flattenPaletteNotationItems(fallbackPaletteGroups)),
            semanticTypesByCode: buildFallbackSemanticTypesByCode(),
            containmentRules: cloneJson(FALLBACK_CONTAINMENT_RULES),
            associations: cloneJson(FALLBACK_ASSOCIATIONS),
            usedFallback: true,
        };
    }
}

export async function loadViewVersionMetamodel(viewVersionId, fallbackVersionCode) {
    try {
        const payload = await apiFetch(`/api/view-versions/${viewVersionId}/metamodel`);
        return {
            versionId: payload.metamodel.version.id,
            versionCode: payload.metamodel.version.version_code,
            versionStatus: payload.metamodel.version.status,
            paletteGroups: payload.metamodel.palette_groups || [],
            notationDefinitionsByCode: buildNotationDefinitionsByCode(payload.metamodel.notations || []),
            semanticTypesByCode: buildSemanticTypesByCode(payload.metamodel.semantic_types || []),
            containmentRules: payload.metamodel.containment_rules || [],
            associations: payload.metamodel.associations || [],
            usedFallback: false,
        };
    } catch (error) {
        console.error(error);
        return loadMetamodelRegistry(fallbackVersionCode);
    }
}
