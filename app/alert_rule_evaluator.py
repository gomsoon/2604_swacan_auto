from __future__ import annotations

from datetime import datetime
from typing import Any

THRESHOLD_FIRING_LEVELS = {"warning", "critical"}
THRESHOLD_SEVERITY_RANK = {"critical": 2, "warning": 1}


def metric_value_for_state(state: dict[str, Any], metric_key: str) -> float | None:
    if metric_key == "memory_used_ratio":
        total = state.get("memory_total")
        used = state.get("memory_used")
        try:
            total_value = float(total)
            used_value = float(used)
        except (TypeError, ValueError):
            return None
        if total_value <= 0:
            return None
        return (used_value / total_value) * 100.0

    value = state.get(metric_key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def threshold_clause_matches(metric_value: float, clause: dict[str, Any]) -> bool:
    comparison = clause.get("comparison")
    value = clause.get("value")
    if comparison not in {"gt", "gte", "lt", "lte"}:
        return False
    if value is None:
        return False
    try:
        threshold_value = float(value)
    except (TypeError, ValueError):
        return False

    if comparison == "gt":
        return metric_value > threshold_value
    if comparison == "gte":
        return metric_value >= threshold_value
    if comparison == "lt":
        return metric_value < threshold_value
    return metric_value <= threshold_value


def _build_scalar_condition_group(rule: dict[str, Any], field_prefix: str) -> dict[str, Any] | None:
    comparison = rule.get("comparison")
    value = rule.get(field_prefix)
    if comparison not in {"gte", "lte"} or value is None:
        return None
    return {
        "logical_operator": None,
        "clauses": [{"comparison": comparison, "value": float(value)}],
    }


def normalize_rule_conditions(rule: dict[str, Any]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    condition_mode = rule.get("condition_mode") or rule.get("cond_mode") or "scalar"
    if condition_mode == "compound":
        return condition_mode, rule.get("warning_condition"), rule.get("critical_condition")
    return (
        "scalar",
        rule.get("warning_condition") or _build_scalar_condition_group(rule, "warning_threshold"),
        rule.get("critical_condition") or _build_scalar_condition_group(rule, "critical_threshold"),
    )


def evaluate_condition_group(
    metric_value: float | None,
    *,
    condition_mode: str,
    condition_group: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if metric_value is None or not isinstance(condition_group, dict):
        return None

    clauses = condition_group.get("clauses")
    if not isinstance(clauses, list) or not clauses:
        return None

    matched_clause_indexes = [
        index
        for index, clause in enumerate(clauses)
        if isinstance(clause, dict) and threshold_clause_matches(metric_value, clause)
    ]

    if condition_mode == "compound":
        logical_operator = condition_group.get("logical_operator")
        if logical_operator == "and" and len(matched_clause_indexes) == len(clauses):
            return {
                "condition_mode": "compound",
                "logical_operator": "and",
                "matched_clause_indexes": matched_clause_indexes,
            }
        if logical_operator == "or" and matched_clause_indexes:
            return {
                "condition_mode": "compound",
                "logical_operator": "or",
                "matched_clause_indexes": matched_clause_indexes,
            }
        return None

    if matched_clause_indexes:
        return {
            "condition_mode": "scalar",
            "logical_operator": None,
            "matched_clause_indexes": [0],
        }
    return None


def evaluate_threshold_rule(metric_value: float | None, rule: dict[str, Any]) -> dict[str, Any]:
    if metric_value is None:
        return {"threshold_level": "unknown", "winning_condition_trace": None}

    condition_mode, warning_condition, critical_condition = normalize_rule_conditions(rule)
    critical_trace = evaluate_condition_group(
        metric_value,
        condition_mode=condition_mode,
        condition_group=critical_condition,
    )
    if critical_trace is not None:
        return {
            "threshold_level": "critical",
            "winning_condition_trace": {
                "severity": "critical",
                **critical_trace,
            },
        }

    warning_trace = evaluate_condition_group(
        metric_value,
        condition_mode=condition_mode,
        condition_group=warning_condition,
    )
    if warning_trace is not None:
        return {
            "threshold_level": "warning",
            "winning_condition_trace": {
                "severity": "warning",
                **warning_trace,
            },
        }

    return {"threshold_level": "normal", "winning_condition_trace": None}


def alert_rule_specificity_rank(rule: dict[str, Any]) -> int:
    return 2 if rule.get("scope_type") == "monitored_object" else 1


def alert_rule_candidate_identity(rule: dict[str, Any]) -> str:
    rule_key = rule.get("rule_key")
    if isinstance(rule_key, str) and rule_key:
        return rule_key
    rule_id = rule.get("id")
    if isinstance(rule_id, int):
        return f"rule:{rule_id}"
    display_name = rule.get("display_name")
    if isinstance(display_name, str) and display_name:
        return f"name:{display_name}"
    return f"preview:{rule.get('scope_type')}:{rule.get('metric_key')}"


def threshold_family_key(rule: dict[str, Any]) -> tuple[str, str | None, str | None, str | None]:
    return (
        "threshold",
        rule.get("state_type"),
        rule.get("metric_key"),
        rule.get("comparison"),
    )


def evaluate_threshold_candidates(
    metric_value: float | None,
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for rule in rules:
        threshold_evaluation = evaluate_threshold_rule(metric_value, rule)
        candidates.append(
            {
                **rule,
                "_threshold_level": threshold_evaluation["threshold_level"],
                "_winning_condition_trace": threshold_evaluation["winning_condition_trace"],
            }
        )
    return candidates


def _rule_recency_rank(rule: dict[str, Any]) -> float:
    if rule.get("_origin") == "current_preview":
        return float("inf")

    for field_name in ("updated_at", "created_at"):
        value = rule.get(field_name)
        if not isinstance(value, str) or not value:
            continue
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            continue

    rule_id = rule.get("id")
    if isinstance(rule_id, int):
        return float(rule_id)
    return 0.0


def summarize_threshold_decision(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    decision = {
        "candidate_rule_count": len(candidates),
        "winner_rule_id": None,
        "winner_rule_key": None,
        "winner_display_name": None,
        "winner_scope_type": None,
        "winner_rule_origin": None,
        "winner_threshold_level": None,
        "winner_rule": None,
        "suppressed_rule_count": 0,
        "suppressed_rule_ids": [],
        "suppressed_rule_display_names": [],
        "suppressed_rules": [],
        "firing_rule_ids": [],
    }

    firing_rules = [
        candidate for candidate in candidates if candidate.get("_threshold_level") in THRESHOLD_FIRING_LEVELS
    ]
    if not firing_rules:
        return decision

    firing_rules.sort(
        key=lambda item: (
            -alert_rule_specificity_rank(item),
            -THRESHOLD_SEVERITY_RANK.get(item["_threshold_level"], 0),
            -_rule_recency_rank(item),
            -(item.get("id") if isinstance(item.get("id"), int) else 0),
            item.get("rule_key") or "",
        )
    )

    winner = firing_rules[0]
    suppressed_rules = firing_rules[1:]
    decision.update(
        {
            "winner_rule_id": winner.get("id"),
            "winner_rule_key": winner.get("rule_key"),
            "winner_display_name": winner.get("display_name") or winner.get("rule_key"),
            "winner_scope_type": winner.get("scope_type"),
            "winner_rule_origin": winner.get("_origin"),
            "winner_threshold_level": winner.get("_threshold_level"),
            "winner_rule": winner,
            "suppressed_rule_count": len(suppressed_rules),
            "suppressed_rule_ids": [
                item.get("id") for item in suppressed_rules if isinstance(item.get("id"), int)
            ],
            "suppressed_rule_display_names": [
                item.get("display_name") or item.get("rule_key") or "unnamed rule"
                for item in suppressed_rules
            ],
            "suppressed_rules": suppressed_rules,
            "firing_rule_ids": [
                item.get("id") for item in firing_rules if isinstance(item.get("id"), int)
            ],
        }
    )
    return decision
