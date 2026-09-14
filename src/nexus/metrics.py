"""Переиспользуемые функции продуктовых и финансовых метрик."""

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def safe_divide(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """Возвращает отношение или NULL при отсутствии данных и делении на ноль."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def percent(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """Возвращает долю в процентах или NULL."""
    value = safe_divide(numerator, denominator)
    return None if value is None else value * 100


def unique_count(values: Iterable[T]) -> int:
    """Считает уникальные непустые значения."""
    return len({value for value in values if value is not None})


def drop_off(current_step: int, previous_step: int) -> float | None:
    """Вычисляет потери этапа в процентах."""
    conversion = safe_divide(current_step, previous_step)
    return None if conversion is None else (1 - conversion) * 100


def mrr(monthly_amounts: Iterable[float]) -> float:
    """Суммирует месячную регулярную выручку активных подписок."""
    return round(sum(monthly_amounts), 2)


def arpu(revenue: float, active_customers: int) -> float | None:
    """Вычисляет выручку на активного клиента."""
    value = safe_divide(revenue, active_customers)
    return None if value is None else round(value, 2)


def arppu(revenue: float, paying_customers: int) -> float | None:
    """Вычисляет выручку на платящего клиента."""
    value = safe_divide(revenue, paying_customers)
    return None if value is None else round(value, 2)


def model_ltv(arpu_value: float | None, gross_margin: float, monthly_churn: float | None) -> float | None:
    """Вычисляет модельный LTV; нулевой отток даёт NULL, а не бесконечность."""
    if arpu_value is None or monthly_churn is None or monthly_churn <= 0:
        return None
    return round(arpu_value * gross_margin / monthly_churn, 2)
