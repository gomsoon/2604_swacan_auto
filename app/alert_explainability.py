from __future__ import annotations

from typing import Any

from .alert_rule_evaluator import (
    EVENT_SIGNAL_TYPE_GROUPED_REPEAT,
    LATEST_STATE_SIGNAL_TYPE,
    alert_rule_value_key,
)


def build_threshold_reason(rule: dict[str, Any], metric_value: float, level: str) -> str:
    condition_mode = rule.get("condition_mode") or rule.get("cond_mode") or "scalar"
    metric_label = rule.get("metric_key") or "metric"
    if condition_mode == "compound":
        trace = rule.get("_winning_condition_trace") or rule.get("winning_condition_trace") or {}
        logical_operator = trace.get("logical_operator")
        matched_clause_indexes = trace.get("matched_clause_indexes") or []
        if logical_operator == "and":
            clause_label = ", ".join(str(index + 1) for index in matched_clause_indexes) or "1"
            return (
                f"{metric_label}={metric_value:.3f} matched {level} condition "
                f"(and, clauses {clause_label})"
            )
        clause_index = matched_clause_indexes[0] + 1 if matched_clause_indexes else 1
        operator_label = logical_operator or "single"
        return (
            f"{metric_label}={metric_value:.3f} matched {level} condition "
            f"({operator_label}, clause {clause_index})"
        )

    threshold = rule["critical_threshold"] if level == "critical" else rule["warning_threshold"]
    if rule["comparison"] == "lte":
        return f"{metric_label}={metric_value:.3f} met {level} lower threshold {float(threshold):.3f}"
    return f"{metric_label}={metric_value:.3f} met {level} threshold {float(threshold):.3f}"


def build_event_reason(rule: dict[str, Any], repeat_count: float, level: str) -> str:
    threshold = rule["critical_threshold"] if level == "critical" else rule["warning_threshold"]
    signal_key = rule.get("signal_key") or "event"
    return f"{signal_key} repeat count {repeat_count:.0f} met {level} threshold {float(threshold):.0f}"


def build_alert_rule_reason(
    rule: dict[str, Any],
    *,
    threshold_level: str | None,
    metric_value: float | None = None,
    grouped_event: dict[str, Any] | None = None,
) -> str | None:
    if threshold_level not in {"warning", "critical"}:
        return None

    signal_type = rule.get("signal_type") or LATEST_STATE_SIGNAL_TYPE
    if signal_type == EVENT_SIGNAL_TYPE_GROUPED_REPEAT:
        if grouped_event is not None:
            try:
                repeat_count = float(grouped_event["repeat_count"])
            except (KeyError, TypeError, ValueError):
                return None
        elif metric_value is not None:
            repeat_count = float(metric_value)
        else:
            return None
        return build_event_reason(rule, repeat_count, threshold_level)

    if metric_value is None:
        return None
    return build_threshold_reason(rule, metric_value, threshold_level)


def build_alert_explanation(
    *,
    rule_key: str | None,
    display_name: str | None,
    signal_type: str | None,
    value_key: str | None,
    threshold_level: str | None,
    reason: str | None,
    winning_condition_trace: dict[str, Any] | None,
    family_key: list[Any] | tuple[Any, ...] | None,
    winner_rule_key: str | None,
    winner_display_name: str | None,
    suppressed_rule_keys: list[str] | None,
    suppressed_rule_display_names: list[str] | None,
    resolution_reason: str | None,
) -> dict[str, Any]:
    normalized_family_key = list(family_key) if isinstance(family_key, tuple) else family_key
    normalized_suppressed_rule_keys = [
        value
        for value in (suppressed_rule_keys or [])
        if isinstance(value, str) and value
    ]
    normalized_suppressed_rule_display_names = [
        value
        for value in (suppressed_rule_display_names or [])
        if isinstance(value, str) and value
    ]
    return {
        "rule_key": rule_key,
        "display_name": display_name,
        "signal_type": signal_type or LATEST_STATE_SIGNAL_TYPE,
        "value_key": value_key,
        "threshold_level": threshold_level,
        "reason": reason,
        "winning_condition_trace": winning_condition_trace,
        "family_key": normalized_family_key,
        "winner_rule_key": winner_rule_key,
        "winner_display_name": winner_display_name,
        "suppressed_rule_keys": normalized_suppressed_rule_keys,
        "suppressed_rule_display_names": normalized_suppressed_rule_display_names,
        "resolution_reason": resolution_reason,
    }


def build_alert_rule_explanation(
    rule: dict[str, Any] | None,
    *,
    threshold_level: str | None,
    reason: str | None,
    winning_condition_trace: dict[str, Any] | None,
    family_key: list[Any] | tuple[Any, ...] | None,
    winner_rule_key: str | None,
    winner_display_name: str | None,
    suppressed_rule_keys: list[str] | None,
    suppressed_rule_display_names: list[str] | None,
    resolution_reason: str | None,
) -> dict[str, Any]:
    safe_rule = rule or {}
    return build_alert_explanation(
        rule_key=safe_rule.get("rule_key"),
        display_name=safe_rule.get("display_name"),
        signal_type=safe_rule.get("signal_type"),
        value_key=alert_rule_value_key(safe_rule),
        threshold_level=threshold_level,
        reason=reason,
        winning_condition_trace=winning_condition_trace,
        family_key=family_key,
        winner_rule_key=winner_rule_key,
        winner_display_name=winner_display_name,
        suppressed_rule_keys=suppressed_rule_keys,
        suppressed_rule_display_names=suppressed_rule_display_names,
        resolution_reason=resolution_reason,
    )


def build_alert_explanation_from_metadata(
    metadata: Any,
    *,
    fallback_rule_key: str | None = None,
    fallback_display_name: str | None = None,
    fallback_reason: str | None = None,
    resolution_reason: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        if not any([fallback_rule_key, fallback_display_name, fallback_reason, resolution_reason]):
            return None
        return build_alert_explanation(
            rule_key=fallback_rule_key,
            display_name=fallback_display_name,
            signal_type=LATEST_STATE_SIGNAL_TYPE,
            value_key=None,
            threshold_level=None,
            reason=fallback_reason,
            winning_condition_trace=None,
            family_key=None,
            winner_rule_key=fallback_rule_key,
            winner_display_name=fallback_display_name,
            suppressed_rule_keys=[],
            suppressed_rule_display_names=[],
            resolution_reason=resolution_reason,
        )

    rule_key = metadata.get("rule_key") if isinstance(metadata.get("rule_key"), str) else fallback_rule_key
    display_name = (
        metadata.get("display_name") if isinstance(metadata.get("display_name"), str) else fallback_display_name
    )
    signal_type = metadata.get("signal_type") if isinstance(metadata.get("signal_type"), str) else LATEST_STATE_SIGNAL_TYPE
    value_key = None
    if isinstance(metadata.get("signal_key"), str) and metadata.get("signal_key"):
        value_key = metadata.get("signal_key")
    elif isinstance(metadata.get("metric_key"), str) and metadata.get("metric_key"):
        value_key = metadata.get("metric_key")

    family_key = metadata.get("family_key")
    suppressed_rule_keys = metadata.get("suppressed_rule_keys")
    if not isinstance(suppressed_rule_keys, list):
        suppressed_rule_keys = []
    suppressed_rule_display_names = metadata.get("suppressed_rule_display_names")
    if not isinstance(suppressed_rule_display_names, list):
        suppressed_rule_display_names = []
    winner_rule_key = metadata.get("winner_rule_key")
    if not isinstance(winner_rule_key, str) or not winner_rule_key:
        winner_rule_key = rule_key
    winner_display_name = metadata.get("winner_display_name")
    if not isinstance(winner_display_name, str) or not winner_display_name:
        winner_display_name = display_name
    return build_alert_explanation(
        rule_key=rule_key,
        display_name=display_name,
        signal_type=signal_type,
        value_key=value_key,
        threshold_level=metadata.get("threshold_level") if isinstance(metadata.get("threshold_level"), str) else None,
        reason=metadata.get("reason") if isinstance(metadata.get("reason"), str) else fallback_reason,
        winning_condition_trace=metadata.get("winning_condition_trace")
        if isinstance(metadata.get("winning_condition_trace"), dict)
        else None,
        family_key=family_key if isinstance(family_key, (list, tuple)) else None,
        winner_rule_key=winner_rule_key,
        winner_display_name=winner_display_name,
        suppressed_rule_keys=suppressed_rule_keys,
        suppressed_rule_display_names=suppressed_rule_display_names,
        resolution_reason=resolution_reason,
    )
