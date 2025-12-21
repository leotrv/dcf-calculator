"""Integration tests for auto-DCF endpoint."""
import pytest
from fastapi.testclient import TestClient
from src.main import app


class TestAutoDCFEndpoint:
    """Test suite for POST /dcf/auto-calculate endpoint."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    def test_auto_dcf_endpoint_valid_ticker_aapl(self, client):
        """Test endpoint with valid ticker returns DCFResponse structure."""
        response = client.post(
            "/dcf/auto-calculate",
            json={"ticker": "AAPL"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure matches DCFResponse model
        assert "enterprise_value" in data
        assert "equity_value" in data
        assert "value_per_share" in data
        assert "discounted_fcfs" in data
        assert "discounted_terminal_value" in data
        
        # Verify types
        assert isinstance(data["enterprise_value"], (int, float))
        assert isinstance(data["equity_value"], (int, float))
        assert isinstance(data["discounted_fcfs"], list)
        assert isinstance(data["discounted_terminal_value"], (int, float))
