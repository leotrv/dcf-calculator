from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_post_dcf_calculate_basic():
    payload = {
        "fcf": [100.0, 110.0, 120.0],
        "discount_rate": 0.10,
        "terminal_growth_rate": 0.02,
        "net_debt": 50.0
    }
    r = client.post('/dcf/calculate', json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert 'enterprise_value' in body
    assert 'equity_value' in body
    assert 'discounted_fcfs' in body
    assert 'discounted_terminal_value' in body
