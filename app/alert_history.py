from __future__ import annotations

import json
from typing import Any


def record_alert_history(
    db_conn,
    *,
    alert_instance_id: int,
    action_type: str,
    created_at: str,
    performed_by_user_id: int | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    previous_acknowledged: bool | None = None,
    new_acknowledged: bool | None = None,
    note: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db_conn.execute(
        """
        INSERT INTO alert_history (
            alert_instance_id,
            action_type,
            previous_status,
            new_status,
            previous_acknowledged,
            new_acknowledged,
            performed_by_user_id,
            note,
            payload_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert_instance_id,
            action_type,
            previous_status,
            new_status,
            None if previous_acknowledged is None else int(previous_acknowledged),
            None if new_acknowledged is None else int(new_acknowledged),
            performed_by_user_id,
            note,
            json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            created_at,
        ),
    )
