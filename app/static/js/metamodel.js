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
                display_name: "통신선 시작",
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
            palette_group_code: item.palette_group_code || null,
        });
    }
    return map;
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
            paletteGroups: fallbackPaletteGroups,
            notationDefinitionsByCode: buildNotationDefinitionsByCode(flattenPaletteNotationItems(fallbackPaletteGroups)),
            usedFallback: true,
        };
    }

    try {
        const versionsPayload = await apiFetch("/api/metamodel/versions/published");
        const version = versionsPayload.items.find((item) => item.version_code === versionCode);
        if (!version) {
            throw new Error(`published metamodel version '${versionCode}' not found`);
        }

        const [palettePayload, notationPayload] = await Promise.all([
            apiFetch(`/api/metamodel/versions/${version.id}/palette`),
            apiFetch(`/api/metamodel/versions/${version.id}/notations`),
        ]);

        return {
            versionId: version.id,
            versionCode,
            paletteGroups: palettePayload.palette_groups || [],
            notationDefinitionsByCode: buildNotationDefinitionsByCode(notationPayload.items || []),
            usedFallback: false,
        };
    } catch (error) {
        console.error(error);
        const fallbackPaletteGroups = buildFallbackPaletteGroups();
        return {
            versionId: null,
            versionCode,
            paletteGroups: fallbackPaletteGroups,
            notationDefinitionsByCode: buildNotationDefinitionsByCode(flattenPaletteNotationItems(fallbackPaletteGroups)),
            usedFallback: true,
        };
    }
}
