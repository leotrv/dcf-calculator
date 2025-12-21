"""Pytest configuration and shared fixtures."""
import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_yfinance_ticker_aapl():
    """Mock yfinance Ticker object for AAPL with realistic data."""
    ticker = Mock()
    
    # 5 years of quarterly cash flow (yfinance returns DataFrame with .values)
    # yfinance returns most recent first
    import pandas as pd
    
    ocf_data = pd.Series([100.0, 98.0, 95.0, 93.0, 90.0], index=range(5))
    capex_data = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0], index=range(5))
    debt_data = pd.Series([50.0], index=range(1))
    cash_data = pd.Series([20.0], index=range(1))
    
    ticker.quarterly_financials = {}
    
    # 5 years of quarterly cash flow
    cash_flow_dict = Mock()
    cash_flow_dict.get = Mock(side_effect=lambda key, default=None: {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }.get(key, default))
    cash_flow_dict.__getitem__ = Mock(side_effect=lambda key: {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }[key])
    cash_flow_dict.columns = range(5)
    
    ticker.quarterly_cashflow = {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }
    
    # Latest balance sheet data
    ticker.quarterly_balance_sheet = {
        "Total Debt": debt_data,
        "Cash And Cash Equivalents": cash_data,
    }
    
    # Company metadata
    ticker.info = {
        "symbol": "AAPL",  # Required for existence check
        "beta": 1.2,
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
        "longName": "Apple Inc.",
        "currency": "USD",
    }
    
    return ticker


@pytest.fixture
def mock_yfinance_ticker_invalid():
    """Mock yfinance Ticker for invalid/missing ticker (returns None)."""
    return None


@pytest.fixture
def mock_yfinance_ticker_insufficient_data():
    """Mock yfinance Ticker with insufficient history (<1 year)."""
    import pandas as pd
    
    ticker = Mock()
    
    # Only 1 quarter of data (insufficient)
    ocf_data = pd.Series([100.0], index=range(1))
    capex_data = pd.Series([10.0], index=range(1))
    debt_data = pd.Series([50.0], index=range(1))
    cash_data = pd.Series([20.0], index=range(1))
    
    ticker.quarterly_financials = {}
    
    ticker.quarterly_cashflow = {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }
    
    ticker.quarterly_balance_sheet = {
        "Total Debt": debt_data,
        "Cash And Cash Equivalents": cash_data,
    }
    
    ticker.info = {
        "symbol": "TEST",
        "beta": 1.2,
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
    }
    
    return ticker


@pytest.fixture
def mock_yfinance_ticker_high_growth():
    """Mock yfinance Ticker with high growth rate (tests growth cap)."""
    import pandas as pd
    
    ticker = Mock()
    
    # Exponential growth: 15% CAGR over 5 years
    ocf_data = pd.Series([146.4, 133.1, 121.0, 110.0, 100.0], index=range(5))
    capex_data = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0], index=range(5))
    debt_data = pd.Series([50.0], index=range(1))
    cash_data = pd.Series([20.0], index=range(1))
    
    ticker.quarterly_financials = {}
    ticker.quarterly_cashflow = {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }
    
    ticker.quarterly_balance_sheet = {
        "Total Debt": debt_data,
        "Cash And Cash Equivalents": cash_data,
    }
    
    ticker.info = {
        "symbol": "TEST",
        "beta": 1.0,
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
    }
    
    return ticker


@pytest.fixture
def mock_yfinance_ticker_negative_fcf():
    """Mock yfinance Ticker with negative FCF (unprofitable company)."""
    import pandas as pd
    
    ticker = Mock()
    
    # Negative and declining FCF
    ocf_data = pd.Series([-10.0, -5.0, 0.0, 5.0, 10.0], index=range(5))
    capex_data = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0], index=range(5))
    debt_data = pd.Series([50.0], index=range(1))
    cash_data = pd.Series([20.0], index=range(1))
    
    ticker.quarterly_financials = {}
    ticker.quarterly_cashflow = {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }
    
    ticker.quarterly_balance_sheet = {
        "Total Debt": debt_data,
        "Cash And Cash Equivalents": cash_data,
    }
    
    ticker.info = {
        "symbol": "TEST",
        "beta": 1.2,
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
    }
    
    return ticker


@pytest.fixture
def mock_yfinance_ticker_missing_beta():
    """Mock yfinance Ticker with missing beta (tests default value)."""
    import pandas as pd
    
    ticker = Mock()
    
    ocf_data = pd.Series([100.0, 98.0, 95.0, 93.0, 90.0], index=range(5))
    capex_data = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0], index=range(5))
    debt_data = pd.Series([50.0], index=range(1))
    cash_data = pd.Series([20.0], index=range(1))
    
    ticker.quarterly_financials = {}
    ticker.quarterly_cashflow = {
        "Operating Cash Flow": ocf_data,
        "Capital Expenditure": capex_data,
    }
    
    ticker.quarterly_balance_sheet = {
        "Total Debt": debt_data,
        "Cash And Cash Equivalents": cash_data,
    }
    
    ticker.info = {
        "symbol": "TEST",
        # beta is missing
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
    }
    
    return ticker
