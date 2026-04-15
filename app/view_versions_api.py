from __future__ import annotations

from flask import Blueprint, g, request

from .auth import error_response, login_required
from .view_versioning import (
    create_draft_view_version,
    fetch_version_detail,
    get_active_view_version,
    get_owned_view,
    get_owned_view_version,
    list_view_versions,
)

bp = Blueprint("view_versions_api", __name__, url_prefix="/api")


@bp.get("/views/<int:view_id>/versions")
@login_required
def list_versions(view_id: int):
    view_row = get_owned_view(view_id, g.user["id"])
    if view_row is None:
        return error_response("not_found", "view not found", 404)

    return {"items": list_view_versions(view_id)}


@bp.get("/views/<int:view_id>/active")
@login_required
def get_active_version(view_id: int):
    view_row = get_owned_view(view_id, g.user["id"])
    if view_row is None:
        return error_response("not_found", "view not found", 404)

    active_row = get_active_view_version(view_id)
    if active_row is None:
        return error_response("not_found", "active version not found", 404)

    detail = fetch_version_detail(active_row["id"])
    if detail is None:
        return error_response("not_found", "active version not found", 404)

    version, nodes, edges = detail
    return {"view": {"id": view_row["id"], "name": view_row["name"]}, "version": version, "nodes": nodes, "edges": edges}


@bp.post("/views/<int:view_id>/drafts")
@login_required
def create_draft(view_id: int):
    view_row = get_owned_view(view_id, g.user["id"])
    if view_row is None:
        return error_response("not_found", "view not found", 404)

    payload = request.get_json(silent=True) or {}
    based_on_version_id = payload.get("based_on_version_id")
    description = payload.get("description")

    if based_on_version_id is not None and not isinstance(based_on_version_id, int):
        return error_response("validation_error", "based_on_version_id must be an integer", 400)

    try:
        version_id = create_draft_view_version(
            view_row=view_row,
            user_id=g.user["id"],
            based_on_version_id=based_on_version_id,
            description=description,
        )
    except ValueError:
        return error_response("draft_conflict", "draft version already exists for view", 409)
    except LookupError:
        return error_response("validation_error", "based_on_version_id is invalid", 400)
    except RuntimeError:
        return error_response("version_state_conflict", "based_on_version_id must reference published, active or deprecated version", 409)

    detail = fetch_version_detail(version_id)
    assert detail is not None
    version, nodes, edges = detail
    return {"version": version, "nodes": nodes, "edges": edges}, 201


@bp.get("/view-versions/<int:version_id>")
@login_required
def get_version_detail(version_id: int):
    version_row = get_owned_view_version(version_id, g.user["id"])
    if version_row is None:
        return error_response("not_found", "view version not found", 404)

    detail = fetch_version_detail(version_id)
    if detail is None:
        return error_response("not_found", "view version not found", 404)

    version, nodes, edges = detail
    return {"version": version, "nodes": nodes, "edges": edges}
