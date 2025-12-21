"""Pytest configuration and shared fixtures."""
import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_yfinance_ticker_aapl():
    """Mock yfinance Ticker object for AAPL with realistic data.
    
    yfinance returns DataFrames with metrics in rows and dates in columns.
    """
    ticker = Mock()
    
    # Create cash flow DataFrame with metrics in rows, dates in columns
    dates = pd.date_range('2024-09-30', periods=5, freq='Q')
    cf_df = pd.DataFrame({
        dates[0]: [100.0e9, 10.0e9],
        dates[1]: [98.0e9, 10.0e9],
        dates[2]: [95.0e9, 10.0e9],
        dates[3]: [93.0e9, 10.0e9],
        dates[4]: [90.0e9, 10.0e9],
    }, index=['Operating Cash Flow', 'Capital Expenditure'])
    
    # Create balance sheet DataFrame
    bs_df = pd.DataFrame({
        dates[0]: [50.0e9, 20.0e9],
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    ticker.quarterly_cashflow = cf_df
    ticker.quarterly_balance_sheet = bs_df
    
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
    ticker = Mock()
    
    # Only 1 quarter of data (insufficient, needs 4)
    dates = pd.date_range('2024-09-30', periods=1, freq='Q')
    cf_df = pd.DataFrame({
        dates[0]: [100.0e9, 10.0e9],
    }, index=['Operating Cash Flow', 'Capital Expenditure'])
    
    bs_df = pd.DataFrame({
        dates[0]: [50.0e9, 20.0e9],
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    ticker.quarterly_cashflow = cf_df
    ticker.quarterly_balance_sheet = bs_df
    
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
    ticker = Mock()
    
    # Exponential growth: 15% CAGR over 5 years
    dates = pd.date_range('2024-09-30', periods=5, freq='Q')
    cf_df = pd.DataFrame({
        dates[0]: [146.4e9, 10.0e9],
        dates[1]: [133.1e9, 10.0e9],
        dates[2]: [121.0e9, 10.0e9],
        dates[3]: [110.0e9, 10.0e9],
        dates[4]: [100.0e9, 10.0e9],
    }, index=['Operating Cash Flow', 'Capital Expenditure'])
    
    bs_df = pd.DataFrame({
        dates[0]: [50.0e9, 20.0e9],
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    ticker.quarterly_cashflow = cf_df
    ticker.quarterly_balance_sheet = bs_df
    
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
    ticker = Mock()
    
    # Negative and declining FCF
    dates = pd.date_range('2024-09-30', periods=5, freq='Q')
    cf_df = pd.DataFrame({
        dates[0]: [-10.0e9, 10.0e9],
        dates[1]: [-5.0e9, 10.0e9],
        dates[2]: [0.0e9, 10.0e9],
        dates[3]: [5.0e9, 10.0e9],
        dates[4]: [10.0e9, 10.0e9],
    }, index=['Operating Cash Flow', 'Capital Expenditure'])
    
    bs_df = pd.DataFrame({
        dates[0]: [50.0e9, 20.0e9],
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    ticker.quarterly_cashflow = cf_df
    ticker.quarterly_balance_sheet = bs_df
    
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
    ticker = Mock()
    
    dates = pd.date_range('2024-09-30', periods=5, freq='Q')
    cf_df = pd.DataFrame({
        dates[0]: [100.0e9, 10.0e9],
        dates[1]: [98.0e9, 10.0e9],
        dates[2]: [95.0e9, 10.0e9],
        dates[3]: [93.0e9, 10.0e9],
        dates[4]: [90.0e9, 10.0e9],
    }, index=['Operating Cash Flow', 'Capital Expenditure'])
    
    bs_df = pd.DataFrame({
        dates[0]: [50.0e9, 20.0e9],
    }, index=['Total Debt', 'Cash And Cash Equivalents'])
    
    ticker.quarterly_cashflow = cf_df
    ticker.quarterly_balance_sheet = bs_df
    
    ticker.info = {
        "symbol": "TEST",
        # beta is missing
        "sharesOutstanding": 2500.0,
        "marketCap": 2000000000000,
    }
    
    return ticker

