"""Детерминированная генерация обезличенного набора SaaS-данных."""

import csv
import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

SEED = 20260914
CHANNELS = ("Органический поиск", "Партнёрства", "Контекстная реклама", "Сообщества")
PLANS = ("Бесплатный", "Командный", "Профессиональный")
FEATURES = ("Отчёты", "Совместная работа", "Автоматизация", "Экспорт")


def _id(kind: str, number: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"nexus:{SEED}:{kind}:{number}"))


def _write(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate(output_dir: str | Path, users_count: int = 720) -> dict[str, int]:
    """Создаёт взаимосвязанные таблицы с фиксированным seed."""
    rng = random.Random(SEED)
    output = Path(output_dir)
    start = date(2025, 9, 1)
    end = date(2026, 8, 31)
    users: list[dict[str, object]] = []
    events: list[dict[str, object]] = []
    subscriptions: list[dict[str, object]] = []
    payments: list[dict[str, object]] = []
    assignments: list[dict[str, object]] = []
    event_number = payment_number = subscription_number = 0

    for index in range(users_count):
        user_id = _id("user", index)
        registered = start + timedelta(days=rng.randrange((end - start).days + 1))
        channel = rng.choices(CHANNELS, weights=(35, 20, 30, 15))[0]
        segment = rng.choices(("Малый бизнес", "Средний бизнес", "Самозанятый"), (45, 30, 25))[0]
        users.append({"user_id": user_id, "registered_at": registered.isoformat(), "channel": channel, "segment": segment, "country": "Синтетическая страна"})
        variant = "Контрольная группа" if index % 2 == 0 else "Тестовая группа"
        assignments.append({"experiment_id": "onboarding-2026-01", "user_id": user_id, "variant": variant, "assigned_at": registered.isoformat()})

        def add_event(name: str, day: date, feature: str = "", current_user_id: str = user_id) -> None:
            nonlocal event_number
            stamp = datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=rng.randrange(8, 21), minutes=rng.randrange(60))
            events.append({"event_id": _id("event", event_number), "user_id": current_user_id, "event_name": name, "event_at": stamp.isoformat(), "feature_name": feature})
            event_number += 1

        add_event("registration", registered)
        project_probability = 0.68 + (0.08 if variant == "Тестовая группа" else 0)
        activated = rng.random() < project_probability and registered <= end - timedelta(days=7)
        if activated:
            project_day = registered + timedelta(days=rng.randrange(0, 4))
            task_day = project_day + timedelta(days=rng.randrange(0, 4))
            if task_day <= registered + timedelta(days=7):
                add_event("project_created", project_day)
                add_event("task_created", task_day)
        activity_probability = 0.62 if activated else 0.18
        for offset in range(1, min(91, (end - registered).days + 1)):
            decay = max(0.08, activity_probability * (0.986**offset))
            if rng.random() < decay:
                add_event("meaningful_action", registered + timedelta(days=offset), rng.choice(FEATURES))

        paid_probability = 0.27 if activated else 0.04
        if rng.random() < paid_probability and registered <= end - timedelta(days=14):
            plan = rng.choice(PLANS[1:])
            monthly = 1990 if plan == "Командный" else 4990
            sub_start = registered + timedelta(days=rng.randrange(7, 15))
            possible_months = max(1, (end.year - sub_start.year) * 12 + end.month - sub_start.month + 1)
            duration = rng.randint(1, possible_months)
            cancelled = duration < possible_months and rng.random() < 0.72
            sub_end = min(end, sub_start + timedelta(days=30 * duration)) if cancelled else ""
            subscription_id = _id("subscription", subscription_number)
            subscriptions.append({"subscription_id": subscription_id, "user_id": user_id, "plan": plan, "started_at": sub_start.isoformat(), "ended_at": sub_end.isoformat() if isinstance(sub_end, date) else "", "monthly_amount": monthly, "status": "Отменена" if cancelled else "Активна"})
            subscription_number += 1
            payment_day = sub_start
            for _ in range(duration):
                if payment_day > end:
                    break
                refunded = rng.random() < 0.025
                payments.append({"payment_id": _id("payment", payment_number), "subscription_id": subscription_id, "user_id": user_id, "paid_at": payment_day.isoformat(), "gross_amount": monthly, "refund_amount": monthly if refunded else 0, "currency": "RUB", "status": "Возврат" if refunded else "Оплачен"})
                payment_number += 1
                payment_day += timedelta(days=30)

    spend: list[dict[str, object]] = []
    cursor = date(2025, 9, 1)
    while cursor <= end:
        for channel in CHANNELS:
            base = {"Органический поиск": 0, "Партнёрства": 18000, "Контекстная реклама": 52000, "Сообщества": 9000}[channel]
            spend.append({"spend_id": _id("spend", len(spend)), "month": cursor.strftime("%Y-%m"), "channel": channel, "amount": base + (rng.randrange(-2500, 2501) if base else 0), "currency": "RUB"})
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)

    tables = {
        "users.csv": (users, ["user_id", "registered_at", "channel", "segment", "country"]),
        "events.csv": (events, ["event_id", "user_id", "event_name", "event_at", "feature_name"]),
        "subscriptions.csv": (subscriptions, ["subscription_id", "user_id", "plan", "started_at", "ended_at", "monthly_amount", "status"]),
        "payments.csv": (payments, ["payment_id", "subscription_id", "user_id", "paid_at", "gross_amount", "refund_amount", "currency", "status"]),
        "marketing_spend.csv": (spend, ["spend_id", "month", "channel", "amount", "currency"]),
        "experiment_assignments.csv": (assignments, ["experiment_id", "user_id", "variant", "assigned_at"]),
    }
    for name, (rows, fields) in tables.items():
        _write(output / name, rows, fields)
    manifest = {"dataset_version": "1.0.0", "seed": SEED, "synthetic": True, "rows": {name: len(rows) for name, (rows, _) in tables.items()}}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest["rows"]
