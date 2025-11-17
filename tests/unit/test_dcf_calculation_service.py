from src.services.dcf_calculation_service import DCFCalculationService
from src.models.request import DCFRequest
import pytest


def test_single_year_pv_calculation():
    # The current `DCFRequest` model uses `starting_fcf` (last historical year),
    # `fcf_growth_rate` (percent) and `years`. To produce a single forecasted
    # FCF of 100.0 in year 1 with a 10% growth rate, set `starting_fcf` to 100/1.1.
    req = DCFRequest(
        starting_fcf=100.0 / 1.10,
        fcf_growth_rate=10.0,
        years=1,
        discount_rate=10.0,
        net_debt=0.0,
    )
    svc = DCFCalculationService()
    res = svc.calculate_dcf(req)

    expected_pv = 100.0 / 1.10
    assert pytest.approx(res.enterprise_value, rel=1e-9) == expected_pv
    assert pytest.approx(res.discounted_fcfs[0], rel=1e-9) == expected_pv
    assert res.discounted_terminal_value == 0.0
