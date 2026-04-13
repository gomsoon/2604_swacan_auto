from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class OutboxItem:
    payload_type: str
    target_id: str
    occurred_at: str
    payload: dict[str, object]

    def to_json(self) -> str:
        return json.dumps(
            {
                "payload_type": self.payload_type,
                "target_id": self.target_id,
                "occurred_at": self.occurred_at,
                "payload": self.payload,
            },
            ensure_ascii=False,
        )
