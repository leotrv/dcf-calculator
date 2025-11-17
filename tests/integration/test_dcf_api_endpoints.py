from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_post_dcf_calculate_basic():
    # Use the current request model: `starting_fcf` is the last historical FCF
    # Forecasted FCF for year 1 = starting_fcf * (1 + fcf_growth_rate)
    payload = {
        "starting_fcf": 100.0,
        "fcf_growth_rate": 10.0,  # percent (10% -> growth to 110)
        "years": 3,
        "discount_rate": 10.0,    # percent (10% WACC)
        "terminal_growth_rate": 2.0,
        "net_debt": 50.0
    }
    r = client.post('/dcf/calculate', json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert 'enterprise_value' in body
    assert 'equity_value' in body
    assert 'discounted_fcfs' in body
    assert 'discounted_terminal_value' in body
