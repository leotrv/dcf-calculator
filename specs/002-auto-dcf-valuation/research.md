# Research: Auto-DCF Valuation Endpoint

**Phase**: 0 - Outline & Research  
**Feature**: [spec.md](spec.md)  
**Plan**: [plan.md](plan.md)

## Overview

This document consolidates research findings for implementing the auto-DCF endpoint using yfinance. Key questions addressed: how to extract DCF parameters from yfinance data, best practices for financial data transformation, and error handling patterns.

---

## Research Task 1: yfinance Data Extraction Best Practices

**Question**: How should financial data be extracted from yfinance to populate DCF parameters?

### Findings

**yfinance API Overview**:
- `yf.download()`: Returns historical price data (OHLCV)
- `Ticker()` object: Provides access to fundamentals, balance sheet, cash flow statements
- Available financial data:
  - `ticker.quarterly_financials`: Income statement (revenue, operating income, net income)
  - `ticker.quarterly_cashflow`: Cash flow statement (operating CF, capital expenditure)
  - `ticker.quarterly_balance_sheet`: Balance sheet (total debt, cash, shares outstanding)
  - `ticker.info`: Company metadata including beta, sector, industry

**Historical Data Requirements**:
- Free cash flow: Calculate as Operating Cash Flow - Capital Expenditure
- Growth rate estimation: Use 5-year historical CAGR of revenue or FCF (requires ≥1 year per spec)
- Debt & cash: Latest quarterly balance sheet values
- Shares outstanding: Available in `ticker.info['sharesOutstanding']` or balance sheet

### Recommendation

**Decision**: Fetch quarterly cash flow and balance sheet; calculate historical metrics using 5-year rolling average where available.

**Rationale**: Quarterly data provides sufficient granularity for trend analysis; 5-year average smooths volatility and aligns with standard financial practice.

**Implementation Approach**:
```python
1. Fetch ticker object: yf.Ticker(symbol)
2. Extract quarterly cash flow: ticker.quarterly_cashflow
3. Extract quarterly balance sheet: ticker.quarterly_balance_sheet
4. Calculate FCF = Operating CF - Capital Expenditure for each period
5. Calculate CAGR for last 5 years (or available history)
6. Use most recent balance sheet for net debt calculation
7. Retrieve shares outstanding from ticker.info or balance sheet
```

---

## Research Task 2: WACC and Discount Rate Estimation

**Question**: How should discount rate (WACC) be estimated when only yfinance data is available?

### Findings

**WACC Formula**: WACC = (E/V × Cost of Equity) + (D/V × Cost of Debt × (1 - Tax Rate))

**Simplified Estimation Using yfinance**:
- **Cost of Equity**: CAPM = Risk-Free Rate + Beta × Market Risk Premium
  - Risk-free rate: Use US 10-year Treasury yield (~4-5% typical, default 4.5% if unavailable)
  - Beta: Available in `ticker.info['beta']`
  - Market risk premium: Use standard assumption (6% typical in US market)
- **Cost of Debt**: Can use weighted average of interest rates; alternatively, use default (5% if unavailable)
- **Capital Structure**: E/V and D/V derived from balance sheet (market cap + total debt)
- **Tax Rate**: Use corporate tax estimate (~21% in US) or extract from financials if available

**Constraints**:
- yfinance beta may be stale or unavailable for smaller caps
- International stocks may not have all data points
- Highly levered companies require careful debt cost estimation

### Recommendation

**Decision**: Use simplified CAPM-based approach with fallback to default discount rate.

**Rationale**: Balances accuracy with data availability; defaults ensure robustness for stocks missing beta or other data.

**Implementation Approach**:
```python
# Fallback defaults
DEFAULT_RISK_FREE_RATE = 0.045  # 4.5%
DEFAULT_MARKET_RISK_PREMIUM = 0.06  # 6%
DEFAULT_BETA = 1.0  # Market average
DEFAULT_COST_OF_DEBT = 0.05  # 5%
DEFAULT_TAX_RATE = 0.21  # 21% (US corporate tax)

# Fetch from yfinance
beta = ticker.info.get('beta', DEFAULT_BETA)
market_cap = ticker.info.get('marketCap', 0)
total_debt = balance_sheet.get('Total Debt', 0)  # Latest quarterly

# Calculate
cost_of_equity = risk_free_rate + beta * market_risk_premium
cost_of_debt = DEFAULT_COST_OF_DEBT  # Simplified; could parse from financials
capital_structure_ratio = market_cap / (market_cap + total_debt) if (market_cap + total_debt) > 0 else 0.5
wacc = (capital_structure_ratio * cost_of_equity) + ((1 - capital_structure_ratio) * cost_of_debt * (1 - DEFAULT_TAX_RATE))
```

---

## Research Task 3: Growth Rate Estimation from Historical Trends

**Question**: How should FCF and revenue growth rates be estimated?

### Findings

**CAGR Calculation**:
- Compound Annual Growth Rate (CAGR) = (Ending Value / Beginning Value)^(1/Years) - 1
- Use last 5 years of available data for robust trend
- Handle negative FCF: Use revenue growth as proxy or flag for user validation

**Data Availability**:
- yfinance provides quarterly cash flow going back multiple years
- Most stocks have 5+ years of quarterly data (20+ data points)
- Some IPO stocks may have <1 year (handled by FR-003 minimum requirement)

**Growth Assumptions**:
- Historical CAGR is backward-looking; assumes past growth continues
- More conservative: Use 50% of historical CAGR or GDP growth rate (~2-3%) for perpetuity
- Terminal growth rate should not exceed long-term GDP growth (~2-3%)

### Recommendation

**Decision**: Calculate 5-year FCF CAGR; cap forecast growth at 2x historical CAGR; set terminal growth to 2.5% (GDP proxy).

**Rationale**: Prevents overoptimistic projections while respecting historical evidence; 2.5% aligns with long-term economic growth expectations.

**Implementation Approach**:
```python
# Extract quarterly FCF history (e.g., last 20 quarters = 5 years)
fcf_history = [
    (cf['Operating Cash Flow'] - cf['Capital Expenditure'])
    for cf in quarterly_cash_flows
]

# Calculate CAGR (5-year)
if len(fcf_history) >= 5 and fcf_history[-1] > 0:
    cagr_fcf = (fcf_history[-1] / fcf_history[0]) ** (1 / 5) - 1
else:
    # Use revenue CAGR as fallback
    cagr_fcf = revenue_cagr

# Forecast growth: cap at 2x historical or 20%, whichever is lower
forecast_growth = min(cagr_fcf * 2, 0.20)

# Terminal growth: conservative, GDP-anchored
terminal_growth = 0.025  # 2.5%
```

---

## Research Task 4: Error Handling and Data Validation

**Question**: How should missing or invalid data be handled gracefully?

### Findings

**Common yfinance Issues**:
- Ticker not found: Returns None or empty data
- Delisted/recently IPO'd stocks: Limited historical data
- International stocks: Different accounting standards, missing USD data
- Data delays: yfinance updates on schedule; may lag market by 1-2 days
- Partial data: Some fields (beta, debt) may be missing

**Validation Strategy**:
1. Check ticker validity (non-empty, return non-null data)
2. Check minimum historical data: At least 1 year (4 quarters) per specification
3. Check data completeness: Required fields present (FCF, shares, debt)
4. Sanitize negative/extreme values: Flag for user review

### Recommendation

**Decision**: Implement three-tier validation with specific error codes for different failure modes.

**Rationale**: Clear feedback helps users understand why valuation failed; enables better error handling and logging.

**Implementation Approach**:
```python
class ValidationError(Exception):
    """Raised when data validation fails"""
    pass

def validate_yfinance_data(ticker_symbol, financials):
    """Validate extracted yfinance data for DCF input"""
    
    errors = []
    
    # 1. Ticker validity
    if not financials or financials.empty:
        raise ValidationError("TICKER_NOT_FOUND: No data available for ticker")
    
    # 2. Minimum historical data (1 year = 4 quarters)
    if len(quarterly_cf) < 4:
        raise ValidationError("INSUFFICIENT_HISTORY: Less than 1 year of data available")
    
    # 3. Required fields
    required_fields = ['operating_cash_flow', 'capital_expenditure', 'total_debt', 'cash', 'shares_outstanding']
    for field in required_fields:
        if field not in financials or financials[field] is None:
            errors.append(f"MISSING_FIELD: {field}")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    # 4. Sanity checks on extreme values
    if fcf < 0 and forecast_growth > 0.30:
        # Warn but don't fail; user may validate manually
        logger.warning(f"{ticker_symbol}: Negative FCF with high growth rate")
    
    return True  # Validation passed
```

---

## Research Task 5: Network and Timeout Handling

**Question**: How should network errors and timeouts from yfinance be handled?

### Findings

**Network Concerns**:
- yfinance relies on external data sources (Yahoo Finance, other APIs)
- Network timeouts: Can occur during peak usage or data provider outages
- Partial failures: May retrieve some data but fail on others (e.g., beta missing)
- Rate limiting: yfinance has soft rate limits; concurrent requests may fail

**Python Handling**:
- yfinance raises exceptions (RequestException, URLError) on network failures
- Timeout: Set explicitly on requests (e.g., 10-second timeout per call)
- Retry strategy: Exponential backoff for transient failures

### Recommendation

**Decision**: Implement timeout (10 seconds) with single retry for transient errors; fail fast on persistent errors.

**Rationale**: Balances robustness with API response time requirement (5 seconds target).

**Implementation Approach**:
```python
import yfinance as yf
from requests.exceptions import Timeout, ConnectionError
import time

def fetch_with_retry(ticker_symbol, max_retries=1, timeout=10):
    """Fetch yfinance data with timeout and retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            ticker = yf.Ticker(ticker_symbol, timeout=timeout)
            # Trigger data fetch to catch errors early
            _ = ticker.quarterly_financials
            return ticker
        except (Timeout, ConnectionError) as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                raise ValidationError(f"NETWORK_ERROR: Unable to fetch data (timeout after {timeout}s)")
        except Exception as e:
            raise ValidationError(f"YFINANCE_ERROR: {str(e)}")
```

---

## Research Task 6: Endpoint Design and API Naming

**Question**: What should the endpoint path and HTTP method be?

### Findings

**REST Convention**:
- POST for actions that cause side effects or return computed results
- Endpoint naming: `/dcf/calculate-auto`, `/dcf/auto`, or `/auto-calculate`
- Input: JSON body with `{"ticker": "AAPL"}`
- Output: Same `DCFResponse` structure as existing `/dcf/calculate`

**Consistency with Existing API**:
- Existing: `POST /dcf/calculate` accepts `DCFRequest` JSON
- New endpoint should follow same pattern (same response model)
- Consideration: Separate path to distinguish from manual input or same router prefix

### Recommendation

**Decision**: Endpoint path `/dcf/auto-calculate` with JSON body `{"ticker": "AAPL"}`.

**Rationale**: Clear naming convention (auto = automatic from yfinance); distinct from `/calculate` (manual); consistent with REST POST semantics.

**Specification**:
```
POST /dcf/auto-calculate

Request Body:
{
  "ticker": "AAPL"
}

Response:
{
  "enterprise_value": 2500.5,
  "equity_value": 2400.3,
  "value_per_share": 150.2,
  "discounted_fcfs": [100, 110, 121, ...],
  "discounted_terminal_value": 1200.5
}

Error Responses:
- 400: Bad Request (invalid ticker, insufficient data)
- 500: Internal Server Error (yfinance/calculation error)
```

---

## Summary of Key Decisions

| Decision | Implementation | Rationale |
|----------|---|---|
| **Data Source** | yfinance quarterly financials | Most accessible; covers major global stocks |
| **FCF Calculation** | Operating CF - CapEx | Standard financial practice |
| **Growth Rate** | 5-year FCF CAGR, capped at 2x or 20% | Balances historical evidence with realism |
| **Discount Rate (WACC)** | Simplified CAPM + fallback defaults | Accurate for stocks with beta; robust for others |
| **Terminal Growth** | 2.5% fixed (GDP anchor) | Conservative; standard practice |
| **Minimum Data** | 1 year (4 quarters) | Per specification |
| **Error Handling** | Validation tier with error codes | Clear feedback for debugging |
| **Timeouts** | 10 seconds with single retry | Balances reliability with response time |
| **Endpoint** | POST /dcf/auto-calculate | REST convention; clear naming |

---

## Assumptions for Implementation

1. yfinance data is sufficiently accurate for valuation estimates (not real-time trading)
2. Quarterly data is preferred; annual data acceptable as fallback
3. Default parameters (risk-free rate, market premium, tax rate) are reasonable for broad stock coverage
4. Users understand that automated valuations are estimates; manual validation recommended
5. Network timeout of 10 seconds is acceptable for the endpoint
