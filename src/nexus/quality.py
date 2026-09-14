"""Проверки схемы, целостности и диапазонов аналитических данных."""

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    severity: str
    passed: bool
    details: str

    def to_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def read_table(directory: Path, name: str) -> list[dict[str, str]]:
    with (directory / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate(directory: str | Path) -> list[Check]:
    """Запускает критические проверки; вызывающая сторона останавливает конвейер при сбое."""
    root = Path(directory)
    required = {"users.csv", "events.csv", "subscriptions.csv", "payments.csv", "marketing_spend.csv", "experiment_assignments.csv"}
    missing = sorted(name for name in required if not (root / name).exists())
    checks = [Check("Обязательные таблицы", "Critical", not missing, "Отсутствуют: " + ", ".join(missing) if missing else "Все таблицы присутствуют")]
    if missing:
        return checks
    users, events = read_table(root, "users.csv"), read_table(root, "events.csv")
    subscriptions, payments = read_table(root, "subscriptions.csv"), read_table(root, "payments.csv")
    spend, assignments = read_table(root, "marketing_spend.csv"), read_table(root, "experiment_assignments.csv")
    tables = {"Пользователи": (users, "user_id"), "События": (events, "event_id"), "Подписки": (subscriptions, "subscription_id"), "Платежи": (payments, "payment_id"), "Расходы": (spend, "spend_id")}
    for label, (rows, key) in tables.items():
        ids = [row[key] for row in rows]
        checks.append(Check(f"Уникальность: {label}", "Critical", len(ids) == len(set(ids)) and all(ids), f"Строк: {len(ids)}"))
    user_ids = {row["user_id"] for row in users}
    sub_ids = {row["subscription_id"] for row in subscriptions}
    checks.append(Check("Связи событий", "Critical", all(row["user_id"] in user_ids for row in events), "События ссылаются на пользователей"))
    checks.append(Check("Связи подписок", "Critical", all(row["user_id"] in user_ids for row in subscriptions), "Подписки ссылаются на пользователей"))
    checks.append(Check("Связи платежей", "Critical", all(row["user_id"] in user_ids and row["subscription_id"] in sub_ids for row in payments), "Платежи ссылаются на пользователей и подписки"))
    checks.append(Check("Связи эксперимента", "Critical", all(row["user_id"] in user_ids for row in assignments), "Назначения ссылаются на пользователей"))
    known_events = {"registration", "project_created", "task_created", "meaningful_action"}
    checks.append(Check("Допустимые события", "Critical", all(row["event_name"] in known_events for row in events), "Неизвестных событий нет"))
    amount_valid = all(float(row["gross_amount"]) >= 0 and 0 <= float(row["refund_amount"]) <= float(row["gross_amount"]) for row in payments)
    checks.append(Check("Диапазоны платежей", "Critical", amount_valid, "Суммы неотрицательны, возврат не превышает платёж"))
    date_valid = True
    try:
        for row in users:
            date.fromisoformat(row["registered_at"])
        for row in events:
            datetime.fromisoformat(row["event_at"])
    except ValueError:
        date_valid = False
    checks.append(Check("Форматы дат", "Critical", date_valid, "Используется ISO 8601"))
    checks.append(Check("Пустой набор пользователей", "Warning", bool(users), f"Пользователей: {len(users)}"))
    return checks
