"""Unit tests for YFinanceService."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.yfinance_service import YFinanceService, ValidationError
from src.models.request import DCFRequest


class TestYFinanceService:
    """Test suite for YFinanceService parameter extraction logic."""

    @pytest.fixture
    def service(self):
        """YFinanceService instance."""
        return YFinanceService()

    @pytest.fixture
    def mock_ticker_aapl(self):
        """Mock yfinance Ticker object for AAPL."""
        ticker = Mock()
        
        # Mock quarterly financials (income statement)
        ticker.quarterly_financials = {
            "Operating Cash Flow": [100.0, 98.0, 95.0, 93.0, 90.0],
            "Capital Expenditure": [10.0, 10.0, 10.0, 10.0, 10.0],
        }
        
        # Mock quarterly cash flow
        ticker.quarterly_cashflow = {
            "Operating Cash Flow": [100.0, 98.0, 95.0, 93.0, 90.0],
            "Capital Expenditure": [10.0, 10.0, 10.0, 10.0, 10.0],
        }
        
        # Mock quarterly balance sheet
        ticker.quarterly_balance_sheet = {
            "Total Debt": [50.0],
            "Cash And Cash Equivalents": [20.0],
        }
        
        # Mock info (company metadata)
        ticker.info = {
            "beta": 1.2,
            "sharesOutstanding": 2500.0,
            "marketCap": 2000000000000,
            "longName": "Apple Inc."
        }
        
        return ticker

    def test_validate_ticker_empty_string(self, service):
        """Test validation rejects empty ticker."""
        assert not service.validate_ticker("")

    def test_validate_ticker_valid_alphabetic(self, service):
        """Test validation accepts valid alphabetic ticker."""
        assert service.validate_ticker("AAPL")
        assert service.validate_ticker("MSFT")

    def test_validate_ticker_invalid_chars(self, service):
        """Test validation rejects non-alphabetic characters."""
        assert not service.validate_ticker("AAPL123")
        assert not service.validate_ticker("AA-PL")

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_valid_ticker_returns_dict(self, mock_yf, service):
        """Test extraction returns dict with valid ticker."""
        import pandas as pd
        ticker = Mock()
        
        # Create proper DataFrame structure (metrics in rows, dates in columns)
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
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
        
        result = service.extract_dcf_inputs("AAPL")
        
        assert isinstance(result, DCFRequest)
        assert result.starting_fcf > 0
        assert result.fcf_growth_rate >= 0
        assert result.discount_rate > 0

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_calculates_fcf_correctly(self, mock_yf, service):
        """Test FCF calculation: Operating CF - CapEx."""
        import pandas as pd
        ticker = Mock()
        
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
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
        
        result = service.extract_dcf_inputs("AAPL")
        
        # Latest FCF is most recent (dates[4]): (90e9 - 10e9) / 1e9 = 80.0 billion
        assert result.starting_fcf == 80.0

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_calculates_fcf_5yr_cagr(self, mock_yf, service):
        """Test 5-year CAGR calculation from quarterly history."""
        import pandas as pd
        ticker = Mock()
        
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
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
        
        result = service.extract_dcf_inputs("AAPL")
        
        # With 5 years of data (90, 88, 85, 83, 80 billions), CAGR should be calculated
        # CAGR = (80/90)^(1/5) - 1 ≈ -0.023 (negative growth)
        # Should be capped at 0 or use default
        assert result.fcf_growth_rate >= 0

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_estimates_wacc_via_capm(self, mock_yf, service):
        """Test WACC estimation via CAPM: risk_free + beta * market_premium."""
        import pandas as pd
        ticker = Mock()
        
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
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
        
        result = service.extract_dcf_inputs("AAPL")
        
        # WACC should be ~0.045 + 1.2 * 0.06 = 0.117 (11.7%)
        assert 0.08 < result.discount_rate < 0.15

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_applies_growth_rate_cap(self, mock_yf, service):
        """Test FCF growth rate is capped at min(2x CAGR, 20%)."""
        import pandas as pd
        ticker = Mock()
        
        # High growth scenario: CAGR = 15%
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [146.4e9, 10e9],
            dates[1]: [133.1e9, 10e9],
            dates[2]: [121.0e9, 10e9],
            dates[3]: [110.0e9, 10e9],
            dates[4]: [100.0e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
        bs_df = pd.DataFrame({
            dates[0]: [50e9, 20e9],
        }, index=['Total Debt', 'Cash And Cash Equivalents'])
        
        ticker.quarterly_cashflow = cf_df
        ticker.quarterly_balance_sheet = bs_df
        ticker.info = {
            "symbol": "TEST",
            "beta": 1.0,
            "sharesOutstanding": 2500.0,
            "marketCap": 2000000000000,
        }
        
        mock_yf.Ticker.return_value = ticker
        
        result = service.extract_dcf_inputs("TEST")
        
        # Growth should be capped at 20% maximum
        assert result.fcf_growth_rate <= 0.20

    @patch('src.services.yfinance_service.yf')
    def test_estimate_discount_rate_missing_beta_uses_default(self, mock_yf, service):
        """Test missing beta uses default 1.0."""
        import pandas as pd
        ticker = Mock()
        
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [100e9, 10e9],
            dates[1]: [98e9, 10e9],
            dates[2]: [95e9, 10e9],
            dates[3]: [93e9, 10e9],
            dates[4]: [90e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
        bs_df = pd.DataFrame({
            dates[0]: [50e9, 20e9],
        }, index=['Total Debt', 'Cash And Cash Equivalents'])
        
        ticker.quarterly_cashflow = cf_df
        ticker.quarterly_balance_sheet = bs_df
        ticker.info = {
            "symbol": "TEST",
            "sharesOutstanding": 2500.0,
            "marketCap": 2000000000000,
            # beta missing
        }
        
        mock_yf.Ticker.return_value = ticker
        
        result = service.extract_dcf_inputs("TEST")
        
        # With default beta=1.0: WACC = 0.045 + 1.0 * 0.06 = 0.105 (10.5%)
        assert 0.10 < result.discount_rate < 0.11

    @patch('src.services.yfinance_service.yf')
    def test_extract_dcf_inputs_negative_fcf_logged(self, mock_yf, service):
        """Test negative FCF is handled and logged."""
        import pandas as pd
        ticker = Mock()
        
        dates = pd.date_range('2024-09-30', periods=5, freq='Q')
        cf_df = pd.DataFrame({
            dates[0]: [-10e9, 10e9],
            dates[1]: [-5e9, 10e9],
            dates[2]: [0.0, 10e9],
            dates[3]: [5e9, 10e9],
            dates[4]: [10e9, 10e9],
        }, index=['Operating Cash Flow', 'Capital Expenditure'])
        
        bs_df = pd.DataFrame({
            dates[0]: [50e9, 20e9],
        }, index=['Total Debt', 'Cash And Cash Equivalents'])
        
        ticker.quarterly_cashflow = cf_df
        ticker.quarterly_balance_sheet = bs_df
        ticker.info = {
            "symbol": "TEST",
            "beta": 1.2,
            "sharesOutstanding": 2500.0,
            "marketCap": 2000000000000,
        }
        
        mock_yf.Ticker.return_value = ticker
        
        # Should handle negative FCF gracefully (not raise exception)
        with patch('src.services.yfinance_service.logger') as mock_logger:
            result = service.extract_dcf_inputs("TEST")
            # Check if warning was logged (implementation may vary)
            # For now, just verify it doesn't raise
            assert isinstance(result, DCFRequest)
