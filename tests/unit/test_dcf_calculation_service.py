from src.services.dcf_calculation_service import DCFCalculationService
from src.models.request import DCFRequest
import pytest


def test_single_year_pv_calculation():
    req = DCFRequest(fcf=[100.0], discount_rate=0.10, net_debt=0.0)
    svc = DCFCalculationService()
    res = svc.calculate_dcf(req)

    expected_pv = 100.0 / 1.10
    assert pytest.approx(res.enterprise_value, rel=1e-9) == expected_pv
    assert pytest.approx(res.discounted_fcfs[0], rel=1e-9) == expected_pv
    assert res.discounted_terminal_value == 0.0
