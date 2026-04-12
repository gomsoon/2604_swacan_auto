from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def error_response(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped_view(*args: Any, **kwargs: Any):
        if g.get("user") is None:
            return error_response("unauthorized", "login required", 401)
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    @login_required
    def wrapped_view(*args: Any, **kwargs: Any):
        if g.user["role"] != "admin":
            return error_response("forbidden", "admin access required", 403)
        return view(*args, **kwargs)

    return wrapped_view


def load_logged_in_user() -> None:
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def init_app(app) -> None:
    app.before_request(load_logged_in_user)


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return error_response("validation_error", "username and password are required", 400)

    user = get_db().execute(
        "SELECT id, username, role, is_active, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return error_response("invalid_credentials", "invalid username or password", 401)

    if user["is_active"] != 1:
        return error_response("inactive_user", "inactive user", 403)

    session.clear()
    session["user_id"] = user["id"]

    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


@bp.post("/logout")
def logout():
    session.clear()
    return {"ok": True}
