import { apiFetch, clearBanner, formatTimestamp, showBanner } from "./common.js";

const listRoot = document.getElementById("views-list");
const countRoot = document.getElementById("views-count");
const createForm = document.getElementById("create-view-form");
const refreshButton = document.getElementById("refresh-views-button");

function renderViews(items) {
    countRoot.textContent = String(items.length);
    if (items.length === 0) {
        listRoot.innerHTML = '<p class="section-copy">아직 저장된 뷰가 없습니다.</p>';
        return;
    }

    listRoot.innerHTML = items
        .map(
            (item) => `
            <article class="view-card">
                <div>
                    <h3>${item.name}</h3>
                    <p>${item.description || "설명이 없습니다."}</p>
                </div>
                <div class="view-actions">
                    <span class="meta-pill">revision ${item.revision}</span>
                    <span class="meta-pill">${formatTimestamp(item.updated_at)}</span>
                    <a class="button ghost small" href="/views/${item.id}/edit">편집</a>
                    <a class="button ghost small" href="/views/${item.id}/monitor">모니터링</a>
                </div>
            </article>
        `
        )
        .join("");
}

async function loadViews() {
    clearBanner();
    try {
        const payload = await apiFetch("/api/views");
        renderViews(payload.items);
    } catch (error) {
        showBanner(error.message, "error");
    }
}

createForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearBanner();

    const formData = new FormData(createForm);
    const name = String(formData.get("name") || "").trim();
    const description = String(formData.get("description") || "").trim();

    try {
        const payload = await apiFetch("/api/views", {
            method: "POST",
            body: { name, description },
        });
        window.location.href = `/views/${payload.view.id}/edit`;
    } catch (error) {
        showBanner(error.message, "error");
    }
});

refreshButton?.addEventListener("click", loadViews);

loadViews();
