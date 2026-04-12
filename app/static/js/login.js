import { apiFetch } from "./common.js";

const form = document.getElementById("login-form");
const errorBox = document.getElementById("login-error");

form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
        await apiFetch("/api/auth/login", {
            method: "POST",
            body: { username, password },
        });
        window.location.href = "/views";
    } catch (error) {
        errorBox.hidden = false;
        errorBox.textContent = error.message;
    }
});
