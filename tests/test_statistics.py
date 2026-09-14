import pytest

from nexus.statistics import benjamini_hochberg, two_proportion_z_test


def test_known_equal_experiment():
    result = two_proportion_z_test(10, 100, 10, 100)
    assert result.absolute_uplift == 0
    assert result.p_value == 1
    assert result.decision == "Различие не доказано"


def test_empty_sample_is_nullable():
    result = two_proportion_z_test(0, 0, 1, 10)
    assert result.p_value is None
    assert result.decision == "Недостаточно данных"


def test_invalid_experiment_rejected():
    with pytest.raises(ValueError, match="не может превышать"):
        two_proportion_z_test(11, 10, 1, 10)


def test_benjamini_hochberg():
    assert benjamini_hochberg([0.001, 0.02, 0.2]) == [True, True, False]
