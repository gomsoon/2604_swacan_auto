from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Blueprint, abort, g, redirect, render_template, url_for

from .db import get_db

bp = Blueprint("web", __name__)


def page_login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped_view(*args: Any, **kwargs: Any):
        if g.get("user") is None:
            return redirect(url_for("web.login_page"))
        return view(*args, **kwargs)

    return wrapped_view


def page_admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    @page_login_required
    def wrapped_view(*args: Any, **kwargs: Any):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def get_owned_view(view_id: int):
    row = get_db().execute(
        """
        SELECT id, name, description, owner_user_id, revision, updated_at
        FROM views
        WHERE id = ?
        """,
        (view_id,),
    ).fetchone()

    if row is None or row["owner_user_id"] != g.user["id"]:
        abort(404)

    return row


@bp.app_context_processor
def inject_template_context() -> dict[str, Any]:
    return {"current_user": g.get("user")}


@bp.get("/")
def index():
    if g.get("user") is None:
        return redirect(url_for("web.login_page"))
    return redirect(url_for("web.views_page"))


@bp.get("/login")
def login_page():
    if g.get("user") is not None:
        return redirect(url_for("web.views_page"))

    return render_template(
        "login.html",
        page_title="로그인",
        page_key="login",
    )


@bp.get("/views")
@page_login_required
def views_page():
    return render_template(
        "views.html",
        page_title="뷰 목록",
        page_key="views",
    )


@bp.get("/views/<int:view_id>/edit")
@page_login_required
def editor_page(view_id: int):
    view_row = get_owned_view(view_id)
    return render_template(
        "editor.html",
        page_title=f"{view_row['name']} 편집",
        page_key="editor",
        view_id=view_row["id"],
        view_name=view_row["name"],
        view_revision=view_row["revision"],
    )


@bp.get("/views/<int:view_id>/monitor")
@page_login_required
def monitor_page(view_id: int):
    view_row = get_owned_view(view_id)
    return render_template(
        "monitor.html",
        page_title=f"{view_row['name']} 모니터링",
        page_key="monitor",
        view_id=view_row["id"],
        view_name=view_row["name"],
    )


@bp.get("/admin")
@page_admin_required
def admin_page():
    return render_template(
        "admin.html",
        page_title="관리 화면",
        page_key="admin",
    )
