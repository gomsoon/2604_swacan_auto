from __future__ import annotations

from .alert_rule_evaluator import EVENT_SIGNAL_TYPE_GROUPED_REPEAT, LATEST_STATE_SIGNAL_TYPE

ALERT_IDENTITY_KIND_RULE = "rule"
ALERT_IDENTITY_KIND_FAMILY = "family"


def build_rule_identity_key(*, source_rule_id: int | None, alert_code: str | None) -> str:
    if isinstance(source_rule_id, int):
        return f"rule:{source_rule_id}"
    return f"code:{alert_code or '-'}"


def build_threshold_family_identity_key(
    *,
    monitored_object_id: int,
    state_type: str | None,
    metric_key: str | None,
    comparison: str | None,
) -> str:
    return (
        f"threshold:{monitored_object_id}:{state_type or '-'}:{metric_key or '-'}:{comparison or '-'}"
    )


def build_threshold_family_identity_key_from_family_key(
    *,
    monitored_object_id: int,
    family_key: tuple[str, str | None, str | None, str | None],
) -> str:
    _, state_type, metric_key, comparison = family_key
    return build_threshold_family_identity_key(
        monitored_object_id=monitored_object_id,
        state_type=state_type,
        metric_key=metric_key,
        comparison=comparison,
    )


def derive_alert_identity(
    *,
    monitored_object_id: int | None,
    alert_code: str | None,
    source_rule_id: int | None,
    signal_type: str | None,
    state_type: str | None,
    metric_key: str | None,
    comparison: str | None,
) -> tuple[str, str]:
    normalized_signal_type = signal_type or LATEST_STATE_SIGNAL_TYPE
    if (
        monitored_object_id is not None
        and normalized_signal_type != EVENT_SIGNAL_TYPE_GROUPED_REPEAT
        and state_type
        and metric_key
        and comparison
    ):
        return (
            ALERT_IDENTITY_KIND_FAMILY,
            build_threshold_family_identity_key(
                monitored_object_id=monitored_object_id,
                state_type=state_type,
                metric_key=metric_key,
                comparison=comparison,
            ),
        )
    return (
        ALERT_IDENTITY_KIND_RULE,
        build_rule_identity_key(source_rule_id=source_rule_id, alert_code=alert_code),
    )
