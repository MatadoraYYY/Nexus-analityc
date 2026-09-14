"""Статистические функции для бинарных A/B-экспериментов."""

from dataclasses import asdict, dataclass
from math import erf, sqrt


@dataclass(frozen=True)
class ExperimentResult:
    """Результат двустороннего z-теста разности долей."""

    control_size: int
    control_conversions: int
    treatment_size: int
    treatment_conversions: int
    control_rate: float | None
    treatment_rate: float | None
    absolute_uplift: float | None
    relative_uplift: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    decision: str

    def to_dict(self) -> dict[str, int | float | str | None]:
        return asdict(self)


def _normal_cdf(value: float) -> float:
    return (1 + erf(value / sqrt(2))) / 2


def two_proportion_z_test(control_conversions: int, control_size: int, treatment_conversions: int, treatment_size: int, alpha: float = 0.05) -> ExperimentResult:
    """Сравнивает две независимые доли и строит 95% интервал разности."""
    values = (control_conversions, control_size, treatment_conversions, treatment_size)
    if any(value < 0 for value in values):
        raise ValueError("Размеры выборок и конверсии не могут быть отрицательными")
    if control_conversions > control_size or treatment_conversions > treatment_size:
        raise ValueError("Число конверсий не может превышать размер выборки")
    if control_size == 0 or treatment_size == 0:
        return ExperimentResult(*values, *(None,) * 7, "Недостаточно данных")
    p_control = control_conversions / control_size
    p_treatment = treatment_conversions / treatment_size
    difference = p_treatment - p_control
    pooled = (control_conversions + treatment_conversions) / (control_size + treatment_size)
    pooled_se = sqrt(pooled * (1 - pooled) * (1 / control_size + 1 / treatment_size))
    unpooled_se = sqrt(p_control * (1 - p_control) / control_size + p_treatment * (1 - p_treatment) / treatment_size)
    p_value = 1.0 if pooled_se == 0 else 2 * (1 - _normal_cdf(abs(difference / pooled_se)))
    z_critical = 1.959963984540054
    ci_low, ci_high = difference - z_critical * unpooled_se, difference + z_critical * unpooled_se
    relative = None if p_control == 0 else difference / p_control
    decision = "Статистически значимое различие" if p_value < alpha else "Различие не доказано"
    return ExperimentResult(control_size, control_conversions, treatment_size, treatment_conversions, p_control, p_treatment, difference, relative, ci_low, ci_high, p_value, decision)


def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """Контролирует ожидаемую долю ложных открытий для нескольких гипотез."""
    if any(not 0 <= value <= 1 for value in p_values):
        raise ValueError("p-значения должны находиться в диапазоне от 0 до 1")
    ranked = sorted(enumerate(p_values), key=lambda item: item[1])
    cutoff = -1
    total = len(ranked)
    for rank, (_, value) in enumerate(ranked, start=1):
        if value <= alpha * rank / total:
            cutoff = rank
    accepted = [False] * total
    if cutoff > 0:
        for index, _ in ranked[:cutoff]:
            accepted[index] = True
    return accepted
