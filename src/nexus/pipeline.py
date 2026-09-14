"""Конвейер расчёта витрин и статических API-ответов."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from nexus.generator import generate
from nexus.metrics import arppu, arpu, drop_off, model_ltv, percent, safe_divide
from nexus.quality import read_table, validate
from nexus.statistics import two_proportion_z_test


def _dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build(data_dir: str | Path, api_dir: str | Path) -> dict[str, object]:
    """Проверяет данные, рассчитывает метрики и публикует JSON-витрины."""
    root, output = Path(data_dir), Path(api_dir)
    checks = validate(root)
    failed = [x for x in checks if x.severity == "Critical" and not x.passed]
    if failed:
        raise RuntimeError("Критические проверки качества данных не пройдены")
    users = read_table(root, "users.csv")
    events = read_table(root, "events.csv")
    subscriptions = read_table(root, "subscriptions.csv")
    payments = read_table(root, "payments.csv")
    spend = read_table(root, "marketing_spend.csv")
    assignments = read_table(root, "experiment_assignments.csv")
    registrations = {x["user_id"]: date.fromisoformat(x["registered_at"]) for x in users}
    user_events: dict[str, list[tuple[str, date]]] = defaultdict(list)
    daily: dict[date, set[str]] = defaultdict(set)
    feature_users: dict[str, set[str]] = defaultdict(set)
    active_names = {"project_created", "task_created", "meaningful_action"}
    for row in events:
        day = datetime.fromisoformat(row["event_at"]).date()
        user_events[row["user_id"]].append((row["event_name"], day))
        if row["event_name"] in active_names:
            daily[day].add(row["user_id"])
        if row["feature_name"]:
            feature_users[row["feature_name"]].add(row["user_id"])
    report_date = max(daily) if daily else None
    dau = len(daily.get(report_date, set())) if report_date else 0
    wau = set().union(*(daily.get(report_date - timedelta(days=i), set()) for i in range(7))) if report_date else set()
    mau = set().union(*(daily.get(report_date - timedelta(days=i), set()) for i in range(30))) if report_date else set()
    activated: set[str] = set()
    projects: set[str] = set()
    for uid, rows in user_events.items():
        registered = registrations[uid]
        project_days = [d for n, d in rows if n == "project_created" and registered <= d <= registered + timedelta(days=7)]
        task_days = [d for n, d in rows if n == "task_created" and registered <= d <= registered + timedelta(days=7)]
        if project_days:
            projects.add(uid)
        if any(p <= t for p in project_days for t in task_days):
            activated.add(uid)
    retention = {}
    for period in (1, 7, 14, 30):
        eligible = {u for u, r in registrations.items() if report_date and r <= report_date - timedelta(days=period)}
        returned = {u for u in eligible if any(n in active_names and d == registrations[u] + timedelta(days=period) for n, d in user_events[u])}
        retention[f"D{period}"] = percent(len(returned), len(eligible))
    gross = sum(float(x["gross_amount"]) for x in payments)
    net = sum(float(x["gross_amount"]) - float(x["refund_amount"]) for x in payments)
    paying = {x["user_id"] for x in payments if x["status"] == "Оплачен"}
    mrr = sum(float(x["monthly_amount"]) for x in subscriptions if x["status"] == "Активна")
    churn = safe_divide(sum(x["status"] == "Отменена" for x in subscriptions), len(subscriptions))
    arpu_value = arpu(net, len(mau))
    ltv = model_ltv(arpu_value, 0.82, churn)
    cac = safe_divide(sum(float(x["amount"]) for x in spend), len(paying))
    series = []
    if report_date:
        for offset in range(89, -1, -1):
            day = report_date - timedelta(days=offset)
            series.append({"date": day.isoformat(), "dau": len(daily.get(day, set()))})
    overview = {
        "meta": {"application_version": "1.0.0", "dataset_version": "1.0.0", "pipeline_version": "1.0.0", "metrics_version": "1.0.0", "synthetic": True, "report_date": report_date.isoformat() if report_date else None},
        "metrics": {"dau": dau, "wau": len(wau), "mau": len(mau), "stickiness": percent(dau, len(mau)), "activation_rate": percent(len(activated), len(users)), "gross_revenue": gross, "net_revenue": net, "mrr": mrr, "arpu": arpu_value, "arppu": arppu(net, len(paying)), "customer_churn": None if churn is None else churn * 100, "cac": cac, "ltv": ltv, "ltv_cac": safe_divide(ltv, cac)},
        "retention": retention,
        "activity_series": series,
        "insights": ["Тестовая группа активируется чаще контрольной; статистическое решение приведено в разделе экспериментов.", "Наблюдаемая связь использования функций и удержания не доказывает причинно-следственную связь."],
    }
    channel_counts = Counter(x["channel"] for x in users)
    user_channel = {x["user_id"]: x["channel"] for x in users}
    paid_channels = Counter(user_channel[u] for u in paying)
    acquisition = {"channels": [{"channel": c, "users": n, "paying_users": paid_channels[c], "paying_conversion": percent(paid_channels[c], n)} for c, n in channel_counts.items()]}
    funnel = {"steps": [{"name": "Регистрация", "users": len(users), "conversion": 100.0, "drop_off": 0.0}, {"name": "Создание проекта", "users": len(projects), "conversion": percent(len(projects), len(users)), "drop_off": drop_off(len(projects), len(users))}, {"name": "Создание задачи", "users": len(activated), "conversion": percent(len(activated), len(projects)), "drop_off": drop_off(len(activated), len(projects))}]}
    group = {x["user_id"]: x["variant"] for x in assignments}
    sizes, conversions = Counter(group.values()), Counter(group[u] for u in activated)
    experiment = two_proportion_z_test(conversions["Контрольная группа"], sizes["Контрольная группа"], conversions["Тестовая группа"], sizes["Тестовая группа"]).to_dict()
    experiment.update({"method": "Двусторонний z-тест разности независимых долей", "confidence_level": 0.95, "warning": "Причинный вывод допустим только при корректной случайной рандомизации."})
    features = {"features": [{"feature": n, "users": len(ids), "adoption": percent(len(ids), len(mau))} for n, ids in feature_users.items()]}
    payloads = {"overview.json": overview, "acquisition.json": acquisition, "funnel.json": funnel, "features.json": features, "experiment.json": experiment, "quality.json": {"checks": [x.to_dict() for x in checks], "critical_passed": not failed}, "health.json": {"status": "работает", "version": "1.0.0", "dataset": "синтетический"}}
    for name, payload in payloads.items():
        _dump(output / name, payload)
    return overview


def main() -> None:
    parser = argparse.ArgumentParser(description="Конвейер NEXUS")
    parser.add_argument("--data", default="data/processed")
    parser.add_argument("--api", default="site/api/v1")
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    if args.generate:
        generate(args.data)
    build(args.data, args.api)


if __name__ == "__main__":
    main()
