"""YFinance data extraction service for auto DCF calculations."""
import logging
from typing import Optional, Tuple
import yfinance as yf
from src.models.request import DCFRequest

logger = logging.getLogger(__name__)

# Constants from research.md
RISK_FREE_RATE = 0.045  # 4.5%
MARKET_RISK_PREMIUM = 0.06  # 6%
DEFAULT_BETA = 1.0
TERMINAL_GROWTH_RATE = 0.025  # 2.5%
FCF_GROWTH_CAP = 0.20  # 20%
NETWORK_TIMEOUT = 10  # seconds
MINIMUM_DATA_QUARTERS = 4  # 1 year


class ValidationError(Exception):
    """Custom exception for validation errors."""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


class YFinanceService:
    """Extract financial data from yfinance and prepare DCFRequest inputs."""
    
    def validate_ticker(self, ticker: str) -> bool:
        """Validate ticker format (alphabetic only).
        
        Args:
            ticker: Stock ticker symbol.
            
        Returns:
            True if valid; False otherwise.
        """
        if not ticker:
            return False
        return ticker.isalpha()
    
    def validate_ticker_exists(self, ticker: str) -> Tuple[bool, Optional[dict]]:
        """Check if ticker exists in yfinance and return its info.
        
        Args:
            ticker: Stock ticker symbol.
            
        Returns:
            Tuple of (exists: bool, info: dict or None)
            
        Raises:
            ValidationError: If yfinance fails to fetch the ticker.
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info
            
            # Check if ticker exists
            if not info or 'symbol' not in info:
                return False, None
            
            return True, info
        except Exception as e:
            logger.error(f"YFINANCE_ERROR: Failed to fetch ticker {ticker}: {str(e)}")
            raise ValidationError("YFINANCE_ERROR", f"Failed to fetch ticker {ticker}: {str(e)}")
    
    def validate_historical_data(self, cash_flow: dict) -> bool:
        """Check if cash flow data meets minimum history requirement.
        
        Args:
            cash_flow: Quarterly cash flow DataFrame from yfinance.
            
        Returns:
            True if sufficient data; False otherwise.
        """
        if cash_flow is None:
            return False
        
        # Try to get Operating Cash Flow row
        try:
            if hasattr(cash_flow, 'loc'):
                # DataFrame: use .loc to access by row name
                ocf = cash_flow.loc['Operating Cash Flow']
            else:
                # Old dict structure
                ocf = cash_flow.get('Operating Cash Flow')
            
            if ocf is None:
                return False
            
            # Check if empty using pandas-aware method
            try:
                if hasattr(ocf, 'empty') and ocf.empty:
                    return False
            except (AttributeError, TypeError):
                pass
            
            # Count non-NaN values
            if hasattr(ocf, 'notna'):
                col_count = ocf.notna().sum()
            else:
                col_count = len(ocf) if hasattr(ocf, '__len__') else 0
            
            return col_count >= MINIMUM_DATA_QUARTERS
        except (KeyError, AttributeError, TypeError):
            return False
    
    def extract_dcf_inputs(self, ticker: str) -> DCFRequest:
        """Extract financial data and create DCFRequest.
        
        Args:
            ticker: Stock ticker symbol.
            
        Returns:
            DCFRequest object with extracted inputs.
            
        Raises:
            ValidationError: If ticker is invalid or data is insufficient.
        """
        # Validate ticker format
        if not self.validate_ticker(ticker):
            raise ValidationError("INVALID_TICKER", f"'{ticker}' is not a valid ticker symbol")
        
        # Fetch and validate ticker exists
        exists, info = self.validate_ticker_exists(ticker)
        if not exists:
            raise ValidationError("TICKER_NOT_FOUND", f"'{ticker}' not found in yfinance")
        
        # Extract financial data
        try:
            yf_ticker = yf.Ticker(ticker)
            cash_flow = yf_ticker.quarterly_cashflow
            
            # Check minimum data requirement
            if not self.validate_historical_data(cash_flow):
                try:
                    if hasattr(cash_flow, 'loc'):
                        ocf = cash_flow.loc['Operating Cash Flow']
                        col_count = ocf.notna().sum() if hasattr(ocf, 'notna') else len(ocf)
                    else:
                        ocf = cash_flow.get("Operating Cash Flow", [])
                        col_count = len(ocf) if hasattr(ocf, '__len__') else 0
                except (AttributeError, TypeError, KeyError):
                    col_count = 0
                raise ValidationError(
                    "INSUFFICIENT_HISTORY",
                    f"'{ticker}' has insufficient data (requires {MINIMUM_DATA_QUARTERS} quarters, found {col_count})"
                )
            
            # Extract latest FCF: Operating CF - CapEx
            # yfinance returns DataFrames with metrics in rows, dates in columns
            operating_cf = cash_flow.loc['Operating Cash Flow']
            capex = cash_flow.loc['Capital Expenditure']
            
            # Convert pandas Series to list (most recent first in yfinance - sort index descending)
            ocf_series = operating_cf.dropna().sort_index(ascending=False)
            capex_series = capex.dropna().sort_index(ascending=False)
            
            # Get first N quarters
            ocf_list = list(ocf_series.values)[:MINIMUM_DATA_QUARTERS]
            capex_list = list(capex_series.values)[:MINIMUM_DATA_QUARTERS]
            
            # Calculate FCF list (Operating CF - CapEx)
            fcf_list = [ocf - cap for ocf, cap in zip(ocf_list, capex_list)]
            
            # Latest FCF (first in list, most recent)
            latest_fcf = fcf_list[0] / 1e9  # Convert to billions
            
            # Log warning if FCF is negative
            if latest_fcf < 0:
                logger.warning(f"Negative FCF detected for {ticker}: {latest_fcf:.2f}B")
            
            # Calculate 5-year CAGR
            if len(fcf_list) >= 2:
                earliest_fcf = fcf_list[-1]
                years = (len(fcf_list) - 1) / 4  # Convert quarters to years
                
                # CAGR = (Ending / Beginning)^(1/years) - 1
                if earliest_fcf > 0:
                    cagr = (latest_fcf / (earliest_fcf / 1e9)) ** (1 / years) - 1
                else:
                    # If earliest FCF is negative, use conservative 0%
                    cagr = 0.0
            else:
                cagr = 0.0
            
            # Apply growth rate cap: min(2x CAGR, 20%)
            growth_rate = min(cagr * 2, FCF_GROWTH_CAP)
            growth_rate = max(growth_rate, 0)  # Floor at 0%
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract cash flow data for {ticker}: {str(e)}")
            raise ValidationError("YFINANCE_ERROR", f"Failed to extract cash flow data: {str(e)}")
        
        # Estimate discount rate (WACC) via CAPM
        discount_rate = self._estimate_discount_rate(info)
        
        # Extract balance sheet data for net debt
        try:
            balance_sheet = yf_ticker.quarterly_balance_sheet
            net_debt = 0.0
            
            if balance_sheet is not None and not (hasattr(balance_sheet, 'empty') and balance_sheet.empty):
                try:
                    total_debt = balance_sheet.loc['Total Debt']
                    total_debt_val = float(total_debt.dropna().iloc[0]) / 1e9 if len(total_debt.dropna()) > 0 else 0
                except (KeyError, IndexError, AttributeError, TypeError):
                    total_debt_val = 0.0
                
                try:
                    cash = balance_sheet.loc['Cash And Cash Equivalents']
                    cash_val = float(cash.dropna().iloc[0]) / 1e9 if len(cash.dropna()) > 0 else 0
                except (KeyError, IndexError, AttributeError, TypeError):
                    cash_val = 0.0
                
                # Net debt = Total Debt - Cash
                net_debt = total_debt_val - cash_val
        except Exception as e:
            logger.warning(f"Failed to extract debt data for {ticker}: {str(e)}")
            net_debt = 0.0
        
        # Get shares outstanding
        try:
            shares_outstanding = info.get('sharesOutstanding', 0) / 1e6  # Convert to millions
        except Exception as e:
            logger.warning(f"Failed to extract shares outstanding for {ticker}: {str(e)}")
            shares_outstanding = 0.0
        
        # Create and return DCFRequest
        return DCFRequest(
            starting_fcf=max(latest_fcf, 0.01),  # Minimum 0.01B to avoid zero
            fcf_growth_rate=growth_rate,
            years=10,  # Default 10-year forecast
            discount_rate=discount_rate,
            terminal_growth_rate=TERMINAL_GROWTH_RATE,
            net_debt=net_debt,
            number_of_shares=shares_outstanding
        )
    
    def _estimate_discount_rate(self, info: dict) -> float:
        """Estimate WACC using CAPM: Rf + beta * (Rm - Rf).
        
        Args:
            info: yfinance ticker info dict.
            
        Returns:
            Discount rate (WACC) as decimal.
        """
        try:
            beta = info.get('beta', DEFAULT_BETA)
            if beta is None or beta <= 0:
                beta = DEFAULT_BETA
        except Exception:
            logger.warning("Failed to extract beta, using default 1.0")
            beta = DEFAULT_BETA
        
        # WACC = Rf + beta * (Rm - Rf)
        wacc = RISK_FREE_RATE + beta * MARKET_RISK_PREMIUM
        
        return max(wacc, 0.01)  # Floor at 1% to avoid zero
