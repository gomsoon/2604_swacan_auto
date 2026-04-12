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
