"""YFinance data extraction service for auto DCF calculations."""
import logging
import math
from typing import List, Optional, Any
import pandas as pd
import numpy as np
import yfinance as yf
from src.models.request import DCFRequest

logger = logging.getLogger(__name__)

# --- Constants ---
RISK_FREE_RATE = 0.042       # 4.2%
MARKET_RISK_PREMIUM = 0.055  # 5.5%
DEFAULT_BETA = 1.0
TERMINAL_GROWTH_RATE = 0.03 
MIN_GROWTH_FLOOR = 0.03      # Inflation floor
FCF_GROWTH_CAP = 0.15        # Cap growth at 15%
PROJECTION_YEARS = 10        # Standard 10-year DCF

class ValidationError(Exception):
    """Custom exception for validation errors in yfinance data extraction."""
    def __init__(self, message: str, error_code: str = 'YFINANCE_ERROR'):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class YFinanceService:
    def extract_dcf_inputs(self, ticker: str) -> DCFRequest:
        if not ticker or not ticker.isalpha():
            raise ValidationError(f"Invalid ticker: {ticker}", 'INVALID_TICKER')
            
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info 
            if not info or 'symbol' not in info:
                raise ValidationError(f"Ticker {ticker} not found", 'TICKER_NOT_FOUND')
            
            # 1. Calculate Base FCF (TTM)
            q_cash_flow = yf_ticker.quarterly_cashflow
            raw_ttm_fcf = self._calculate_ttm_fcf(q_cash_flow, ticker)
            ttm_fcf = self._sanitize(raw_ttm_fcf, 0.0)
            
            # 2. Calculate Growth Rate
            a_cash_flow = yf_ticker.cashflow
            raw_growth = self._calculate_historical_growth(a_cash_flow, ttm_fcf)
            # Apply floor and sanitize
            growth_rate = self._sanitize(max(raw_growth, MIN_GROWTH_FLOOR), MIN_GROWTH_FLOOR)

            # 3. Estimate WACC
            discount_rate = self._sanitize(self._estimate_wacc(info), 0.10)
            
            # 4. Net Debt & Shares
            net_debt = self._sanitize(self._calculate_net_debt(yf_ticker.quarterly_balance_sheet), 0.0)
            
            shares = info.get('sharesOutstanding')
            if not shares:
                # Handle cases where marketCap or currentPrice might be None
                mcap = self._sanitize(info.get('marketCap'), 0.0)
                price = self._sanitize(info.get('currentPrice'), 1.0) # Default price 1.0 to avoid zero div
                shares = mcap / price if price > 0 else 0.0
            
            shares = self._sanitize(shares, 0.0)

            # 5. Robust Projection Logic (Decay Model)
            projected_fcf = []
            current_value = ttm_fcf
            
            for i in range(PROJECTION_YEARS):
                # Calculate step growth
                step_growth = growth_rate - ((growth_rate - TERMINAL_GROWTH_RATE) * (i / PROJECTION_YEARS))
                step_growth = self._sanitize(step_growth, MIN_GROWTH_FLOOR)
                
                current_value = current_value * (1 + step_growth)
                projected_fcf.append(self._sanitize(current_value, 0.0))

            logger.info(f"{ticker} Inputs: FCF_TTM={ttm_fcf:.2f}B, Growth={growth_rate:.2%}, WACC={discount_rate:.2%}")

            return DCFRequest(
                starting_fcf=ttm_fcf,
                fcf_growth_rate=growth_rate,
                years=PROJECTION_YEARS,
                discount_rate=discount_rate,
                terminal_growth_rate=TERMINAL_GROWTH_RATE,
                net_debt=net_debt,
                number_of_shares=shares,
                fcf=projected_fcf 
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error processing {ticker}: {str(e)}")
            raise ValidationError(f"Error fetching data for {ticker}: {str(e)}", 'YFINANCE_ERROR')

    def _sanitize(self, value: Any, default: float = 0.0) -> float:
        """Ensures value is a clean JSON-compliant float (no NaN, no Inf)."""
        try:
            if value is None:
                return default
            
            float_val = float(value)
            
            if math.isnan(float_val) or math.isinf(float_val):
                return default
                
            return float_val
        except (ValueError, TypeError):
            return default

    def _calculate_ttm_fcf(self, cash_flow_df: pd.DataFrame, ticker: str) -> float:
        """Sums last 4 quarters for Trailing Twelve Months FCF."""
        if cash_flow_df is None or cash_flow_df.empty:
            raise ValidationError("No quarterly cash flow data found")

        try:
            # Handle field name variations
            ocf = cash_flow_df.loc['Operating Cash Flow'] if 'Operating Cash Flow' in cash_flow_df.index else cash_flow_df.loc['Total Cash From Operating Activities']
            
            if 'Capital Expenditure' in cash_flow_df.index:
                capex = cash_flow_df.loc['Capital Expenditure']
            else:
                capex = pd.Series([0]*len(ocf), index=ocf.index)

            # FCF = OCF + CapEx (assuming CapEx is negative)
            quarterly_fcf = ocf + capex 
            quarterly_fcf = quarterly_fcf.sort_index(ascending=False)
            
            # Sanitize series before summation to avoid propagating NaNs
            quarterly_fcf = quarterly_fcf.fillna(0.0)

            if len(quarterly_fcf) < 4:
                ttm_val = quarterly_fcf.iloc[0] * 4 
            else:
                ttm_val = quarterly_fcf.iloc[:4].sum()

            return float(ttm_val) / 1e9 

        except KeyError:
            return 0.1

    def _calculate_historical_growth(self, annual_cf_df: pd.DataFrame, current_ttm: float) -> float:
        """Calculates CAGR based on Annual Cash Flows + Current TTM."""
        if annual_cf_df is None or annual_cf_df.empty:
            return MIN_GROWTH_FLOOR

        try:
            ocf = annual_cf_df.loc['Operating Cash Flow'] if 'Operating Cash Flow' in annual_cf_df.index else annual_cf_df.loc['Total Cash From Operating Activities']
            capex = annual_cf_df.loc['Capital Expenditure'] if 'Capital Expenditure' in annual_cf_df.index else 0
            
            annual_fcf = (ocf + capex).sort_index(ascending=False).fillna(0.0)
            values = annual_fcf.values
            
            years_back = min(len(values), 5)
            if years_back < 2: return MIN_GROWTH_FLOOR

            past_fcf = float(values[years_back-1]) / 1e9 
            
            if past_fcf <= 0 or current_ttm <= 0: return MIN_GROWTH_FLOOR
            
            # Simple check to avoid complex number errors in power
            if (current_ttm / past_fcf) < 0:
                 return MIN_GROWTH_FLOOR

            cagr = (current_ttm / past_fcf) ** (1 / years_back) - 1
            
            return min(cagr, FCF_GROWTH_CAP)
        except Exception:
            return MIN_GROWTH_FLOOR

    def _calculate_net_debt(self, balance_sheet_df: pd.DataFrame) -> float:
        """Total Debt - (Cash + Investments)"""
        if balance_sheet_df is None or balance_sheet_df.empty: return 0.0
        try:
            latest = balance_sheet_df.iloc[:, 0]
            
            total_debt = latest.get('Total Debt', 0)
            
            cash_investments = latest.get('Cash Cash Equivalents And Short Term Investments', 0)
            
            if pd.isna(cash_investments) or cash_investments == 0:
                c = latest.get('Cash And Cash Equivalents', 0)
                sti = latest.get('Other Short Term Investments', 0)
                
                c = 0 if pd.isna(c) else c
                sti = 0 if pd.isna(sti) else sti
                cash_investments = c + sti

            # Convert to float and handle potential None/NaN immediately
            td_val = 0.0 if pd.isna(total_debt) else float(total_debt)
            ci_val = 0.0 if pd.isna(cash_investments) else float(cash_investments)

            return (td_val - ci_val) / 1e9
        except Exception: return 0.0

    def _estimate_wacc(self, info: dict) -> float:
        beta = info.get('beta', DEFAULT_BETA)
        # Handle None or NaN beta
        if not beta or pd.isna(beta) or beta < 0.5 or beta > 3.0: 
            beta = DEFAULT_BETA
        return round(RISK_FREE_RATE + beta * MARKET_RISK_PREMIUM, 4)