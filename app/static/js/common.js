export async function apiFetch(url, options = {}) {
    const config = {
        method: options.method || "GET",
        headers: {
            Accept: "application/json",
            ...(options.headers || {}),
        },
        credentials: "same-origin",
    };

    if (options.body !== undefined) {
        config.headers["Content-Type"] = "application/json";
        config.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, config);
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : null;

    if (!response.ok) {
        const message = payload?.error?.message || `request failed: ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
    }

    return payload;
}

export function showBanner(message, kind = "info") {
    const banner = document.getElementById("page-banner");
    if (!banner) {
        return;
    }

    banner.hidden = false;
    banner.className = `page-banner ${kind}`;
    banner.textContent = message;
}

export function clearBanner() {
    const banner = document.getElementById("page-banner");
    if (!banner) {
        return;
    }
    banner.hidden = true;
    banner.className = "page-banner";
    banner.textContent = "";
}

export function formatTimestamp(value) {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString("ko-KR", { hour12: false });
}

const ALERT_RESOLUTION_SOURCE_LABELS = {
    manual_operator: "수동",
    auto_recovery: "자동 복구",
    auto_policy_timeout: "정책 타임아웃",
    system_cleanup: "시스템 정리",
};

const ALERT_RESOLUTION_REASON_LABELS = {
    manual_resolved: "운영자가 수동으로 해결함",
    resolved_from_status_api: "상태 API로 해결 처리됨",
    threshold_cleared: "threshold가 해소됨",
    event_window_elapsed: "이벤트 반복 창이 종료됨",
    suppressed_by_precedence: "우선순위 규칙에 의해 정리됨",
    state_normalized: "상태가 정상화됨",
    superseded: "새 상태 평가로 대체됨",
};

export function formatAlertResolutionSource(value) {
    return ALERT_RESOLUTION_SOURCE_LABELS[value] || value || "-";
}

export function formatAlertResolutionReason(item) {
    const label =
        ALERT_RESOLUTION_REASON_LABELS[item?.resolution_reason] || item?.resolution_reason || item?.latest_message || "이유 없음";
    const metadata =
        item?.metadata && typeof item.metadata === "object" && !Array.isArray(item.metadata) ? item.metadata : null;
    const resolutionNote = item?.resolution_note || metadata?.resolution_note || "";
    return resolutionNote ? `${label} | ${resolutionNote}` : label;
}

function normalizeAlertExplanation(itemOrExplanation) {
    if (!itemOrExplanation || typeof itemOrExplanation !== "object") {
        return null;
    }
    if (itemOrExplanation.explanation && typeof itemOrExplanation.explanation === "object") {
        return itemOrExplanation.explanation;
    }
    return itemOrExplanation;
}

export function formatAlertExplanationRule(itemOrExplanation) {
    const explanation = normalizeAlertExplanation(itemOrExplanation);
    if (!explanation) {
        return "rule 정보 없음";
    }
    const ruleLabel = explanation.display_name || explanation.rule_key || "runtime alert";
    const valueKey = explanation.value_key || "-";
    const level = explanation.threshold_level || "-";
    return `${ruleLabel} | ${valueKey} | ${level}`;
}

export function formatAlertExplanationReason(itemOrExplanation) {
    const explanation = normalizeAlertExplanation(itemOrExplanation);
    if (explanation?.reason) {
        return explanation.reason;
    }
    if (itemOrExplanation?.latest_message) {
        return itemOrExplanation.latest_message;
    }
    return "판정 근거 없음";
}

export function formatAlertExplanationDecision(itemOrExplanation) {
    const explanation = normalizeAlertExplanation(itemOrExplanation);
    if (!explanation) {
        return "winner / suppressed 정보 없음";
    }
    const winnerLabel =
        explanation.winner_display_name ||
        explanation.display_name ||
        explanation.winner_rule_key ||
        explanation.rule_key ||
        "winner 없음";
    const suppressedNames = Array.isArray(explanation.suppressed_rule_display_names)
        ? explanation.suppressed_rule_display_names.filter((value) => typeof value === "string" && value.trim().length > 0)
        : [];
    const suppressedLabel = suppressedNames.length
        ? `suppressed ${suppressedNames.length}건: ${suppressedNames.join(", ")}`
        : "suppressed 없음";
    return `winner ${winnerLabel} | ${suppressedLabel}`;
}

function normalizeAlertWinnerTransitionSummary(itemOrSummary) {
    if (!itemOrSummary || typeof itemOrSummary !== "object") {
        return null;
    }
    if (
        itemOrSummary.winner_transition_summary &&
        typeof itemOrSummary.winner_transition_summary === "object"
    ) {
        return itemOrSummary.winner_transition_summary;
    }
    return itemOrSummary;
}

export function formatAlertWinnerTransitionRule(rule) {
    if (!rule || typeof rule !== "object") {
        return "rule 정보 없음";
    }
    return rule.display_name || rule.rule_key || "rule 정보 없음";
}

export function formatAlertWinnerTransitionSummary(itemOrSummary, options = {}) {
    const summary = normalizeAlertWinnerTransitionSummary(itemOrSummary);
    const winnerLabel = options.winnerLabel || "Current winner";
    const timelineAvailable = options.timelineAvailable ?? true;
    if (!summary) {
        return {
            opening: "Opened by -",
            winner: `${winnerLabel} -`,
            count: "Winner transitions 0",
            lastChange: "Last winner change -",
            timelineAvailable,
        };
    }

    const openingRule = formatAlertWinnerTransitionRule(summary.opening_rule);
    const winnerRule = formatAlertWinnerTransitionRule(summary.winner_rule);
    const transitionCount = Number(summary.transition_count) || 0;
    return {
        opening: `Opened by ${openingRule}`,
        winner: `${winnerLabel} ${winnerRule}`,
        count: `Winner transitions ${transitionCount}`,
        lastChange: `Last winner change ${formatTimestamp(summary.last_transition_at)}`,
        timelineAvailable,
    };
}

export function formatAlertWinnerTransitionLabel(item) {
    if (!item || typeof item !== "object") {
        return "winner transition 정보 없음";
    }
    const previousRule = formatAlertWinnerTransitionRule(item.previous_rule);
    const newRule = formatAlertWinnerTransitionRule(item.new_rule);
    return `${previousRule} -> ${newRule}`;
}

export function bindGlobalUi() {
    const logoutButton = document.getElementById("logout-button");
    if (!logoutButton) {
        return;
    }

    logoutButton.addEventListener("click", async () => {
        logoutButton.disabled = true;
        try {
            await apiFetch("/api/auth/logout", { method: "POST" });
            window.location.href = "/login";
        } catch (error) {
            showBanner(error.message, "error");
            logoutButton.disabled = false;
        }
    });
}

export function readNumber(input, fallback = 0) {
    const value = Number(input.value);
    return Number.isFinite(value) ? value : fallback;
}

export function slugify(value) {
    return String(value || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") || "item";
}
