import csv
from pathlib import Path

from nexus.generator import generate
from nexus.quality import validate


def _rewrite(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_full_generated_dataset_passes_critical_quality(tmp_path):
    generate(tmp_path, users_count=40)
    checks = validate(tmp_path)
    assert len(checks) >= 19
    assert all(check.passed for check in checks if check.severity == "Critical")


def test_missing_table_is_critical(tmp_path):
    generate(tmp_path, users_count=20)
    (tmp_path / "payments.csv").unlink()
    checks = validate(tmp_path)
    assert checks[0].severity == "Critical"
    assert checks[0].passed is False


def test_duplicate_primary_key_is_rejected(tmp_path):
    generate(tmp_path, users_count=20)
    path = tmp_path / "users.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[1]["user_id"] = rows[0]["user_id"]
    _rewrite(path, rows)
    duplicate = next(check for check in validate(tmp_path) if check.name == "Первичный ключ: Пользователи")
    assert duplicate.passed is False


def test_unknown_event_is_rejected(tmp_path):
    generate(tmp_path, users_count=20)
    path = tmp_path / "events.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["event_name"] = "unknown_event"
    _rewrite(path, rows)
    enums = next(check for check in validate(tmp_path) if check.name == "Допустимые значения")
    assert enums.passed is False


def test_invalid_subscription_dates_are_rejected(tmp_path):
    generate(tmp_path, users_count=100)
    path = tmp_path / "subscriptions.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["ended_at"] = "2020-01-01"
    _rewrite(path, rows)
    order = next(check for check in validate(tmp_path) if check.name == "Порядок дат подписок")
    assert order.passed is False
