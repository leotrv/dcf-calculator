"""Integration tests for auto-DCF endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import pandas as pd
from src.main import app


class TestAutoDCFEndpoint:
    """Test suite for POST /dcf/auto-calculate endpoint."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @patch('src.services.yfinance_service.yf')
    def test_auto_dcf_endpoint_valid_ticker_aapl(self, mock_yf, client):
        """Test endpoint with valid ticker returns DCFResponse structure."""
        # Mock yfinance Ticker with proper DataFrame structure
        # yfinance returns DataFrames with metrics in rows, dates in columns
        ticker = Mock()
        
        # Create cash flow DataFrame: rows are metrics, columns are dates
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
        # Create balance sheet DataFrame
        bs_df = pd.DataFrame({
            dates[0]: [50e9, 20e9],
        }, index=['Total Debt', 'Cash And Cash Equivalents'])
        
        ticker.quarterly_cashflow = cf_df
        ticker.quarterly_balance_sheet = bs_df
        ticker.info = {
            "symbol": "AAPL",
            "beta": 1.2,
            "sharesOutstanding": 2500.0,
            "marketCap": 2000000000000,
        }
        
        mock_yf.Ticker.return_value = ticker
        
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
