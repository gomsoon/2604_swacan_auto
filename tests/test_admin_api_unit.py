from __future__ import annotations

from datetime import datetime

from app.admin_api import (
    build_alert_rule_publish_warnings,
    build_default_alert_rule_display_name,
    build_default_alert_rule_key,
    ensure_alert_rule_key_unique,
    get_payload_item_count,
    parse_alert_status_filter,
    parse_boolean_query_param,
    parse_json_or_text,
    parse_limit,
    parse_optional_bool,
    parse_optional_float,
    parse_optional_string,
    preview_metric_value,
    preview_threshold_level,
    suggest_clone_display_name,
    suggest_next_rule_key,
    validate_alert_rule_payload,
    validate_rule_key_value,
)
from app.db import get_db


def test_admin_parser_helpers_cover_small_branches(seeded_app) -> None:
    assert parse_json_or_text(None) is None
    assert parse_json_or_text('{"items":[1,2]}') == {"items": [1, 2]}
    assert parse_json_or_text("not-json") == "not-json"
    assert get_payload_item_count('{"items":[1,2,3]}') == 3
    assert get_payload_item_count('{"items":"bad"}') is None
    assert get_payload_item_count('"plain text"') is None

    assert preview_metric_value({"cpu_usage": "88.5"}, "cpu_usage") == 88.5
    assert preview_metric_value({"memory_total": 200, "memory_used": 50}, "memory_used_ratio") == 25.0
    assert preview_metric_value({"memory_total": 0, "memory_used": 50}, "memory_used_ratio") is None
    assert preview_metric_value({"memory_total": "bad", "memory_used": 50}, "memory_used_ratio") is None
    assert preview_metric_value({"cpu_usage": "bad"}, "cpu_usage") is None
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:20.100+09:00")
    with seeded_app.app_context():
        assert preview_metric_value(
            {"heartbeat_time": "2026-04-10T10:20:00.100+09:00"},
            "heartbeat_age_seconds",
        ) == 20.0

    assert preview_threshold_level(None, "gte", 80.0, 90.0) == "unknown"
    assert preview_threshold_level(95.0, "gte", 80.0, 90.0) == "critical"
    assert preview_threshold_level(85.0, "gte", 80.0, 90.0) == "warning"
    assert preview_threshold_level(75.0, "gte", 80.0, 90.0) == "normal"
    assert preview_threshold_level(5.0, "lte", 20.0, 10.0) == "critical"
    assert preview_threshold_level(15.0, "lte", 20.0, 10.0) == "warning"

    assert parse_optional_float(None) is None
    assert parse_optional_float("") is None
    assert parse_optional_float("12.5") == 12.5
    try:
        parse_optional_float("bad")
    except ValueError as exc:
        assert str(exc) == "threshold must be a number"
    else:
        raise AssertionError("expected ValueError")

    assert parse_optional_bool(True) is True
    assert parse_optional_bool(0) is False
    try:
        parse_optional_bool("yes")
    except ValueError as exc:
        assert str(exc) == "is_enabled must be a boolean"
    else:
        raise AssertionError("expected ValueError")

    assert parse_optional_string(None, field_name="description") is None
    assert parse_optional_string("  ", field_name="description") is None
    assert parse_optional_string("  trimmed  ", field_name="description") == "trimmed"
    try:
        parse_optional_string(10, field_name="description")
    except ValueError as exc:
        assert str(exc) == "description must be a string"
    else:
        raise AssertionError("expected ValueError")
    try:
        parse_optional_string("abcdef", field_name="description", max_length=5)
    except ValueError as exc:
        assert str(exc) == "description must be at most 5 characters"
    else:
        raise AssertionError("expected ValueError")

    with seeded_app.app_context():
        true_value, true_error = parse_boolean_query_param("true", field_name="is_enabled")
        false_value, false_error = parse_boolean_query_param("0", field_name="is_enabled")
        invalid_value, invalid_error = parse_boolean_query_param("maybe", field_name="is_enabled")
        active_value, active_error = parse_alert_status_filter(None)
        open_value, open_error = parse_alert_status_filter("open")
        invalid_status, invalid_status_error = parse_alert_status_filter("bad")

    assert (true_value, true_error) == (True, None)
    assert (false_value, false_error) == (False, None)
    assert invalid_value is None and invalid_error[1] == 400
    assert (active_value, active_error) == ("active", None)
    assert (open_value, open_error) == ("open", None)
    assert invalid_status == "bad" and invalid_status_error[1] == 400

    with seeded_app.test_request_context("/api/admin/raw-events?limit=7"):
        limit, error = parse_limit()
    assert (limit, error) == (7, None)

    with seeded_app.test_request_context("/api/admin/raw-events?limit=bad"):
        limit, error = parse_limit()
    assert limit is None and error[1] == 400


def test_admin_rule_naming_helpers_cover_uniqueness_and_warnings(seeded_app) -> None:
    with seeded_app.app_context():
        row = get_db().execute("SELECT id, rule_key FROM alert_rules ORDER BY id LIMIT 1").fetchone()
        assert validate_rule_key_value("threshold.process.cpu_usage.process-cpu-high") is None
        assert validate_rule_key_value("Threshold.Bad") == "rule_key can use only lowercase letters, digits, '.', '-', and '_'"
        assert validate_rule_key_value(".bad.rule") == "rule_key cannot start or end with a separator"
        assert validate_rule_key_value("bad..rule") == "rule_key cannot contain an empty segment between '.' separators"

        assert ensure_alert_rule_key_unique(row["rule_key"])[1] == 400
        assert ensure_alert_rule_key_unique(row["rule_key"], exclude_rule_id=row["id"]) is None

        next_key = suggest_next_rule_key(row["rule_key"])

    assert next_key.startswith(f"{row['rule_key']}-")
    assert suggest_clone_display_name("Process CPU High") == "Process CPU High (Copy)"
    assert suggest_clone_display_name("Process CPU High (Copy)") == "Process CPU High (Copy) 2"
    assert build_default_alert_rule_display_name(
        {"description": None, "state_type": "process", "metric_key": "cpu_usage"}
    ) == "Legacy Process Cpu Usage Threshold"
    assert build_default_alert_rule_key(
        {"display_name": "Legacy Process Cpu Usage Threshold", "state_type": "process", "metric_key": "cpu_usage"}
    ) == "threshold.process.cpu_usage.legacy-process-cpu-usage-threshold"
    assert build_alert_rule_publish_warnings(
        {
            "warning_threshold": 80.0,
            "critical_threshold": None,
            "display_name": "Process CPU High (Copy)",
        }
    ) == [
        {"message": "This rule only emits a single severity level."},
        {"message": "display_name still contains the '(Copy)' suffix."},
    ]


def test_validate_alert_rule_payload_covers_success_and_negative_matrix(seeded_app) -> None:
    with seeded_app.app_context():
        payload, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "object_type": "SoftwareProcess",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "critical_threshold": 95,
                "is_enabled": True,
            }
        )
        assert error is None
        assert payload["display_name"] == "Legacy Process Cpu Usage Threshold"
        assert payload["rule_key"] == "threshold.process.cpu_usage.legacy-process-cpu-usage-threshold"

        monitored_payload, monitored_error = validate_alert_rule_payload(
            {
                "scope_type": "monitored_object",
                "monitored_object_id": 1302,
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "is_enabled": True,
            }
        )
        assert monitored_error is None
        assert monitored_payload["object_type"] is None

        _, error = validate_alert_rule_payload({"status": "bad"}, partial=True)
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "object_type": "SoftwareProcess",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "critical_threshold": 95,
                "is_enabled": True,
                "rule_key": "Bad Key",
                "display_name": "Bad",
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "critical_threshold": 95,
                "is_enabled": True,
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "monitored_object",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "critical_threshold": 95,
                "is_enabled": True,
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "monitored_object",
                "monitored_object_id": 999999,
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 80,
                "critical_threshold": 95,
                "is_enabled": True,
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "object_type": "SoftwareProcess",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "is_enabled": True,
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "object_type": "SoftwareProcess",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "gte",
                "warning_threshold": 90,
                "critical_threshold": 80,
                "is_enabled": True,
            }
        )
        assert error[1] == 400

        _, error = validate_alert_rule_payload(
            {
                "scope_type": "object_type",
                "object_type": "SoftwareProcess",
                "state_type": "process",
                "metric_key": "cpu_usage",
                "comparison": "lte",
                "warning_threshold": 10,
                "critical_threshold": 20,
                "is_enabled": True,
            }
        )
        assert error[1] == 400
