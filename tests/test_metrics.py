from nexus.metrics import arppu, arpu, drop_off, model_ltv, percent, safe_divide


def test_safe_divide_returns_none_for_zero_and_missing():
    assert safe_divide(3, 0) is None
    assert safe_divide(None, 2) is None


def test_golden_business_metrics():
    assert percent(25, 100) == 25
    assert drop_off(75, 100) == 25
    assert arpu(1000, 4) == 250
    assert arppu(1200, 3) == 400
    assert model_ltv(100, 0.8, 0.05) == 1600


def test_zero_churn_is_not_infinity():
    assert model_ltv(100, 0.8, 0) is None


def test_missing_and_empty_denominators_return_none():
    assert percent(0, 0) is None
    assert drop_off(0, 0) is None
    assert arpu(0, 0) is None
    assert arppu(0, 0) is None


def test_zero_revenue_with_existing_customer_is_zero():
    assert arpu(0, 3) == 0
    assert arppu(0, 2) == 0
