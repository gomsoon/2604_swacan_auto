from __future__ import annotations

from app.alert_rule_evaluator import evaluate_threshold_candidates, summarize_threshold_decision


def test_threshold_decision_prefers_monitored_object_specificity_over_general_severity() -> None:
    candidates = evaluate_threshold_candidates(
        88.0,
        [
            {
                "id": 1501,
                "rule_key": "threshold.process.cpu_usage.general",
                "display_name": "General CPU High",
                "scope_type": "object_type",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 70.0,
                "critical_threshold": 85.0,
                "updated_at": "2026-05-10T10:00:00+09:00",
                "_origin": "published_rule",
            },
            {
                "id": 1901,
                "rule_key": "threshold.process.cpu_usage.specific",
                "display_name": "Specific CPU Override",
                "scope_type": "monitored_object",
                "monitored_object_id": 1302,
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80.0,
                "critical_threshold": 95.0,
                "updated_at": "2026-05-10T09:00:00+09:00",
                "_origin": "published_rule",
            },
        ],
    )

    decision = summarize_threshold_decision(candidates)

    assert decision["winner_rule_id"] == 1901
    assert decision["winner_display_name"] == "Specific CPU Override"
    assert decision["winner_threshold_level"] == "warning"
    assert decision["suppressed_rule_ids"] == [1501]


def test_threshold_decision_uses_recency_when_specificity_and_severity_match() -> None:
    candidates = evaluate_threshold_candidates(
        88.0,
        [
            {
                "id": 1501,
                "rule_key": "threshold.process.cpu_usage.general-old",
                "display_name": "General CPU High Old",
                "scope_type": "object_type",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80.0,
                "critical_threshold": 95.0,
                "updated_at": "2026-05-10T09:00:00+09:00",
                "_origin": "published_rule",
            },
            {
                "id": 1502,
                "rule_key": "threshold.process.cpu_usage.general-new",
                "display_name": "General CPU High New",
                "scope_type": "object_type",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80.0,
                "critical_threshold": 95.0,
                "updated_at": "2026-05-10T10:00:00+09:00",
                "_origin": "published_rule",
            },
        ],
    )

    decision = summarize_threshold_decision(candidates)

    assert decision["winner_rule_id"] == 1502
    assert decision["suppressed_rule_ids"] == [1501]
