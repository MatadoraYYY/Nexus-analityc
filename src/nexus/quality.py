"""Проверки схемы, целостности и диапазонов аналитических данных."""

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class Check:
    """Результат одной воспроизводимой проверки качества."""

    name: str
    severity: str
    passed: bool
    details: str

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


SCHEMAS = {
    "users.csv": {"user_id", "registered_at", "channel", "segment", "country"},
    "events.csv": {"event_id", "user_id", "event_name", "event_at", "feature_name"},
    "subscriptions.csv": {"subscription_id", "user_id", "plan", "started_at", "ended_at", "monthly_amount", "status"},
    "payments.csv": {"payment_id", "subscription_id", "user_id", "paid_at", "gross_amount", "refund_amount", "currency", "status"},
    "marketing_spend.csv": {"spend_id", "month", "channel", "amount", "currency"},
    "experiment_assignments.csv": {"experiment_id", "user_id", "variant", "assigned_at"},
}


def read_table(directory: Path, name: str) -> list[dict[str, str]]:
    """Читает CSV-таблицу в список строк."""
    with (directory / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _check(name: str, passed: bool, ok: str, error: str, severity: str = "Critical") -> Check:
    return Check(name, severity, passed, ok if passed else error)


def _parse_dates(rows: list[dict[str, str]], fields: tuple[str, ...], with_time: bool = False) -> bool:
    try:
        parser = datetime.fromisoformat if with_time else date.fromisoformat
        for row in rows:
            for field in fields:
                if row[field]:
                    parser(row[field])
    except (KeyError, ValueError):
        return False
    return True


def validate(directory: str | Path) -> list[Check]:
    """Проверяет данные; критические ошибки должны останавливать конвейер."""
    root = Path(directory)
    missing = sorted(name for name in SCHEMAS if not (root / name).is_file())
    checks = [_check("Обязательные таблицы", not missing, "Все таблицы присутствуют", f"Отсутствуют: {', '.join(missing)}")]
    if missing:
        return checks

    headers: dict[str, set[str]] = {}
    for name in SCHEMAS:
        with (root / name).open(encoding="utf-8", newline="") as stream:
            headers[name] = set(next(csv.reader(stream), []))
    invalid_schemas = [name for name, expected in SCHEMAS.items() if headers[name] != expected]
    checks.append(_check("Схема таблиц", not invalid_schemas, "Поля соответствуют словарю данных", f"Неверная схема: {', '.join(invalid_schemas)}"))
    if invalid_schemas:
        return checks

    users = read_table(root, "users.csv")
    events = read_table(root, "events.csv")
    subscriptions = read_table(root, "subscriptions.csv")
    payments = read_table(root, "payments.csv")
    spend = read_table(root, "marketing_spend.csv")
    assignments = read_table(root, "experiment_assignments.csv")
    tables = {
        "Пользователи": (users, "user_id"),
        "События": (events, "event_id"),
        "Подписки": (subscriptions, "subscription_id"),
        "Платежи": (payments, "payment_id"),
        "Расходы": (spend, "spend_id"),
    }
    for label, (rows, key) in tables.items():
        ids = [row[key] for row in rows]
        checks.append(_check(f"Первичный ключ: {label}", len(ids) == len(set(ids)) and all(ids), f"Уникальных строк: {len(ids)}", "Обнаружен пустой или повторяющийся ключ"))

    required_values = {
        "users": (users, ("user_id", "registered_at", "channel", "segment", "country")),
        "events": (events, ("event_id", "user_id", "event_name", "event_at")),
        "subscriptions": (subscriptions, ("subscription_id", "user_id", "plan", "started_at", "monthly_amount", "status")),
        "payments": (payments, ("payment_id", "subscription_id", "user_id", "paid_at", "gross_amount", "refund_amount", "currency", "status")),
        "marketing_spend": (spend, ("spend_id", "month", "channel", "amount", "currency")),
        "experiment_assignments": (assignments, ("experiment_id", "user_id", "variant", "assigned_at")),
    }
    null_tables = [name for name, (rows, fields) in required_values.items() if any(not row[field] for row in rows for field in fields)]
    checks.append(_check("Обязательные значения", not null_tables, "Обязательные значения заполнены", f"Пустые значения: {', '.join(null_tables)}"))

    user_ids = {row["user_id"] for row in users}
    sub_ids = {row["subscription_id"] for row in subscriptions}
    checks.extend([
        _check("Связи событий", all(row["user_id"] in user_ids for row in events), "События ссылаются на пользователей", "Обнаружены события неизвестных пользователей"),
        _check("Связи подписок", all(row["user_id"] in user_ids for row in subscriptions), "Подписки ссылаются на пользователей", "Обнаружены подписки неизвестных пользователей"),
        _check("Связи платежей", all(row["user_id"] in user_ids and row["subscription_id"] in sub_ids for row in payments), "Платежи ссылаются на пользователей и подписки", "Обнаружены потерянные связи платежей"),
        _check("Связи эксперимента", all(row["user_id"] in user_ids for row in assignments), "Назначения ссылаются на пользователей", "Обнаружены назначения неизвестных пользователей"),
    ])

    allowed = {
        "События": (events, "event_name", {"registration", "project_created", "task_created", "meaningful_action"}),
        "Каналы пользователей": (users, "channel", {"Органический поиск", "Партнёрства", "Контекстная реклама", "Сообщества"}),
        "Сегменты": (users, "segment", {"Малый бизнес", "Средний бизнес", "Самозанятый"}),
        "Планы": (subscriptions, "plan", {"Командный", "Профессиональный"}),
        "Статусы подписок": (subscriptions, "status", {"Активна", "Отменена"}),
        "Статусы платежей": (payments, "status", {"Оплачен", "Возврат"}),
        "Варианты эксперимента": (assignments, "variant", {"Контрольная группа", "Тестовая группа"}),
    }
    invalid_enums = [label for label, (rows, field, values) in allowed.items() if any(row[field] not in values for row in rows)]
    checks.append(_check("Допустимые значения", not invalid_enums, "Перечисления соответствуют белым спискам", f"Неверные перечисления: {', '.join(invalid_enums)}"))

    dates_valid = all((_parse_dates(users, ("registered_at",)), _parse_dates(events, ("event_at",), with_time=True), _parse_dates(subscriptions, ("started_at", "ended_at")), _parse_dates(payments, ("paid_at",)), _parse_dates(assignments, ("assigned_at",))))
    try:
        dates_valid = dates_valid and all(date.fromisoformat(row["month"] + "-01") for row in spend)
    except ValueError:
        dates_valid = False
    checks.append(_check("Форматы дат", dates_valid, "Используется ISO 8601", "Обнаружена некорректная дата"))

    order_valid = dates_valid and all(not row["ended_at"] or date.fromisoformat(row["ended_at"]) >= date.fromisoformat(row["started_at"]) for row in subscriptions)
    checks.append(_check("Порядок дат подписок", order_valid, "Окончание не предшествует началу", "Нарушен порядок дат подписок"))
    try:
        payment_ranges = all(float(row["gross_amount"]) >= 0 and 0 <= float(row["refund_amount"]) <= float(row["gross_amount"]) for row in payments)
        spend_ranges = all(float(row["amount"]) >= 0 for row in spend)
        subscription_ranges = all(float(row["monthly_amount"]) >= 0 for row in subscriptions)
    except ValueError:
        payment_ranges = spend_ranges = subscription_ranges = False
    checks.extend([
        _check("Диапазоны платежей", payment_ranges, "Суммы и возвраты допустимы", "Некорректная сумма или возврат"),
        _check("Диапазоны расходов", spend_ranges, "Расходы неотрицательны", "Обнаружен отрицательный или некорректный расход"),
        _check("Диапазоны подписок", subscription_ranges, "Стоимость подписки неотрицательна", "Некорректная стоимость подписки"),
        _check("Пустой набор пользователей", bool(users), f"Пользователей: {len(users)}", "Набор пользователей пуст", "Warning"),
    ])
    return checks
