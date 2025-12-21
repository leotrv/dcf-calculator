# Data Model: Auto-DCF Valuation

**Phase**: 1 - Design & Contracts  
**Feature**: [spec.md](spec.md)  
**Research**: [research.md](research.md)

## Overview

This document defines the data model for the auto-DCF endpoint. It specifies the input and output models, internal data structures, and transformation pipeline.

---

## Input Model

### AutoDCFRequest

**Purpose**: Accept a stock ticker for automatic DCF valuation.

**Fields**:

| Field | Type | Validation | Description |
|-------|------|-----------|-------------|
| `ticker` | string | non-empty, max 5 chars | Stock ticker symbol (e.g., "AAPL", "MSFT") |

**Example**:
```json
{
  "ticker": "AAPL"
}
```

**Error Conditions**:
- Empty string: Raise ValueError with code `INVALID_TICKER`
- Missing field: Raise validation error
- Unsupported format: Reject non-alphabetic characters (allow only A-Z)

---

## Output Model

### DCFResponse (Reused from existing endpoint)

**Purpose**: Return the same valuation results as the manual `/dcf/calculate` endpoint.

**Fields**:

| Field | Type | Description | Precision |
|-------|------|-------------|-----------|
| `enterprise_value` | float | Sum of discounted cash flows and terminal value (in billions) | 2 decimal places |
| `equity_value` | float | Enterprise value minus net debt (in billions) | 2 decimal places |
| `value_per_share` | float or null | Equity value / shares outstanding (per share) | 2 decimal places |
| `discounted_fcfs` | list[float] | Discounted FCF for each forecast year (in billions) | 2 decimal places |
| `discounted_terminal_value` | float | Present value of terminal (perpetuity) value (in billions) | 2 decimal places |

**Example**:
```json
{
  "enterprise_value": 2500.50,
  "equity_value": 2400.30,
  "value_per_share": 150.20,
  "discounted_fcfs": [100.00, 110.00, 121.00, 133.10, 146.41],
  "discounted_terminal_value": 1200.50
}
```

---

## Internal Data Structures

### ExtractedYFinanceData

**Purpose**: Intermediate structure holding extracted data from yfinance before transformation to DCFRequest.

**Fields**:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `ticker` | string | Input | Original ticker symbol |
| `company_name` | string | ticker.info | Company name (informational) |
| `quarterly_fcf` | list[float] | quarterly_cashflow | Free cash flow = Operating CF - CapEx for each quarter (billions) |
| `fcf_dates` | list[date] | quarterly_cashflow | Dates corresponding to FCF periods |
| `operating_cash_flow` | list[float] | quarterly_cashflow | Operating cash flow (latest period, billions) |
| `capital_expenditure` | list[float] | quarterly_cashflow | Capital expenditure (latest period, billions) |
| `revenue` | list[float] | quarterly_financials | Revenue history (billions) |
| `total_debt` | float | quarterly_balance_sheet | Total debt (latest, billions) |
| `cash_and_equivalents` | float | quarterly_balance_sheet | Cash and short-term investments (latest, billions) |
| `net_debt` | float | Calculated | Total debt - cash (billions) |
| `shares_outstanding` | float | ticker.info or balance sheet | Number of shares (millions) |
| `beta` | float | ticker.info | Beta coefficient (1.0 = market average) |
| `market_cap` | float | ticker.info | Market capitalization (billions) |
| `data_quality` | dict | Validation | Flags for data completeness (see Validation section) |

**Calculation Examples**:
```python
net_debt = total_debt - cash_and_equivalents
fcf_5yr_cagr = (fcf_history[-1] / fcf_history[0]) ** (1/5) - 1
revenue_5yr_cagr = (revenue[-1] / revenue[0]) ** (1/5) - 1
```

---

## Transformation Pipeline: yfinance → DCFRequest

### Step 1: Fetch yfinance Data

**Input**: Stock ticker  
**Output**: ExtractedYFinanceData object  
**Validation**: Ticker validity, minimum 1 year of history  

**Process**:
1. Create Ticker object: `yf.Ticker(ticker_symbol)`
2. Fetch quarterly cash flow statements (20+ quarters)
3. Fetch quarterly balance sheets (latest)
4. Fetch company info (beta, market cap, shares outstanding)
5. Validate data completeness (see Validation section)

### Step 2: Derive DCF Parameters

**Input**: ExtractedYFinanceData  
**Output**: DCFRequest object  

**Parameter Mapping**:

| DCFRequest Field | Derived From | Formula/Source |
|------------------|--------------|-----------------|
| `starting_fcf` | Quarterly FCF | Latest quarter FCF (billions) |
| `fcf_growth_rate` | 5-year history | CAGR of historical FCF; cap at 2x or 20% |
| `years` | Constant | 10 (standard forecast period) |
| `discount_rate` | CAPM formula | Risk-free (4.5%) + Beta × Market Premium (6%) |
| `terminal_growth_rate` | Constant | 2.5% (GDP growth anchor) |
| `net_debt` | Balance sheet | Total Debt - Cash (billions) |
| `number_of_shares` | Balance sheet / info | Shares outstanding (millions) |

**Calculations**:

```python
# FCF Growth Rate
fcf_history = [calc_fcf(cf) for cf in quarterly_cashflows[-20:]]  # 5 years
if len(fcf_history) >= 2 and fcf_history[0] > 0:
    fcf_growth_rate = (fcf_history[-1] / fcf_history[0]) ** (1/5) - 1
    fcf_growth_rate = min(fcf_growth_rate * 2, 0.20)  # Cap growth
else:
    # Use revenue CAGR or default
    fcf_growth_rate = 0.10  # Default 10%

# Discount Rate (WACC via CAPM)
risk_free_rate = 0.045  # 4.5%
market_risk_premium = 0.06  # 6%
beta = extracted_data.beta or 1.0
cost_of_equity = risk_free_rate + (beta * market_risk_premium)

# Simplified WACC (assuming all equity for simplicity; can be enhanced)
discount_rate = cost_of_equity  # For now; full WACC formula in future

# Terminal Growth (conservative anchor)
terminal_growth_rate = 0.025  # 2.5%
```

### Step 3: Populate DCFRequest

**Input**: Derived parameters  
**Output**: DCFRequest object ready for calculation  

**Validation**: Ensure all required fields present and within valid ranges (handled by DCFRequest pydantic validators)

### Step 4: Invoke DCF Calculation

**Input**: DCFRequest  
**Output**: DCFResponse (via existing DCFCalculationService)  

**Process**: Call `DCFCalculationService.calculate_dcf(request)` (existing logic unchanged)

---

## Validation Rules

### Input Validation (AutoDCFRequest)

1. **Ticker Field**:
   - Must be non-empty string
   - Must contain only alphabetic characters (A-Z, case-insensitive)
   - Maximum 5 characters
   - Error code: `INVALID_TICKER`

### Data Quality Validation (ExtractedYFinanceData)

2. **Ticker Existence**:
   - yfinance must return non-empty data for ticker
   - Error code: `TICKER_NOT_FOUND`

3. **Minimum Historical Data**:
   - At least 1 year (4 quarters) of quarterly cash flow
   - Error code: `INSUFFICIENT_HISTORY`

4. **Required Fields**:
   - Operating cash flow, capital expenditure present
   - Total debt, cash values present
   - Shares outstanding available
   - Error code: `MISSING_FIELD_<fieldname>`

5. **Data Quality Flags** (warning, not fatal):
   - Missing beta: Use default (1.0)
   - Negative FCF in latest period: Flag for user awareness
   - Extreme growth rates (>50% or <-50%): Flag for review
   - Sparse data (< 5 years): Note in output metadata

### Output Validation (DCFRequest)

6. **Derived Parameter Ranges**:
   - All validators from existing `DCFRequest` model apply
   - Growth rates must be positive decimals (0.00 to 0.50)
   - Discount rate must be > 0
   - Number of shares > 0

---

## State Diagram

```
┌─────────────────┐
│  AutoDCFRequest │
│ {ticker: "AAPL"}│
└────────┬────────┘
         │
         ▼
┌──────────────────────┐
│ Fetch yfinance Data  │
│ (timeout: 10s)       │
└────────┬─────────────┘
         │ ✓ Success
         ├─ Validation: Ticker found, ≥1yr data
         │
         ▼
┌──────────────────────┐
│ExtractedYFinanceData │
│ (quarterly financials,│
│  balance sheet)      │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  Derive Parameters   │
│  (FCF growth, WACC,  │
│   terminal growth)   │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  DCFRequest          │
│ (auto-populated)     │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ DCFCalculationService│
│ .calculate_dcf()     │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  DCFResponse         │
│ (valuation results)  │
└──────────────────────┘
```

---

## Units and Conventions

All monetary amounts in this feature follow the same convention as the existing DCF system:

- **Cash Amounts**: Billions (e.g., $50 billion = 50.0)
- **Rates**: Decimal format (e.g., 5% = 0.05)
- **Shares**: Millions (e.g., 2,500 million shares = 2500.0)
- **Precision**: All monetary output rounded to 2 decimal places

---

## Error Responses

### Validation Errors (400 Bad Request)

```json
{
  "detail": {
    "error": "TICKER_NOT_FOUND: No data available for ticker 'INVALID123'",
    "error_code": "TICKER_NOT_FOUND"
  }
}
```

```json
{
  "detail": {
    "error": "INSUFFICIENT_HISTORY: Less than 1 year of historical data for 'NEWCO'",
    "error_code": "INSUFFICIENT_HISTORY"
  }
}
```

### Network/Timeout Errors (503 Service Unavailable or 400 Bad Request)

```json
{
  "detail": {
    "error": "YFINANCE_ERROR: Unable to fetch data (timeout after 10s)",
    "error_code": "YFINANCE_ERROR"
  }
}
```

---

## Future Enhancements

1. **Full WACC Calculation**: Include cost of debt from interest expense in financials
2. **Analyst Estimates**: Incorporate EPS growth consensus when available
3. **Industry Benchmarking**: Compare derived parameters to peer multiples
4. **Tax Rate Calculation**: Extract effective tax rate from historical financials
5. **Sensitivity Analysis**: Return high/low valuations based on parameter ranges
