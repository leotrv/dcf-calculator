# Quickstart: Auto-DCF Valuation Endpoint

**Feature**: [spec.md](spec.md) | **Design**: [data-model.md](data-model.md) | **API**: [contracts/openapi.yaml](contracts/openapi.yaml)

## Overview

This quickstart shows how to use the new `/dcf/auto-calculate` endpoint to value a stock automatically using yfinance data.

---

## Installation

The endpoint requires no additional dependencies beyond the existing project stack:

```bash
# yfinance is already in pyproject.toml
pip install -e .
```

Verify yfinance is installed:
```bash
python -c "import yfinance; print(yfinance.__version__)"
```

---

## Basic Usage

### 1. Start the API Server

```bash
uvicorn src.main:app --reload
```

Server runs at `http://localhost:8000`

### 2. Make a Request

**Using cURL**:
```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

**Using Python requests**:
```python
import requests

response = requests.post(
    "http://localhost:8000/dcf/auto-calculate",
    json={"ticker": "AAPL"}
)
print(response.json())
```

**Using httpx (async)**:
```python
import httpx
import asyncio

async def value_stock(ticker):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/dcf/auto-calculate",
            json={"ticker": ticker}
        )
        return response.json()

# Run it
result = asyncio.run(value_stock("MSFT"))
print(result)
```

### 3. Interpret the Response

**Success Response**:
```json
{
  "enterprise_value": 2500.50,
  "equity_value": 2400.30,
  "value_per_share": 150.20,
  "discounted_fcfs": [100.00, 110.00, 121.00, 133.10, 146.41],
  "discounted_terminal_value": 1200.50
}
```

**What It Means**:
- **enterprise_value**: Total company value to all investors (debt holders + equity holders), in billions
- **equity_value**: Value to shareholders only (enterprise value - net debt), in billions  
- **value_per_share**: Implied stock price per share (if shares outstanding available)
- **discounted_fcfs**: Year-by-year projected free cash flows discounted to present value
- **discounted_terminal_value**: Value of all cash flows beyond the forecast period (in perpetuity)

**Example Interpretation**:
- If current stock price is $100/share and valuation shows $150/share, the stock is undervalued
- If current price is $200/share, the stock is overvalued relative to fundamentals

---

## Error Handling

### Ticker Not Found

**Request**:
```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "INVALID123"}'
```

**Response** (400 Bad Request):
```json
{
  "detail": {
    "error": "TICKER_NOT_FOUND: No data available for ticker 'INVALID123'",
    "error_code": "TICKER_NOT_FOUND"
  }
}
```

**What To Do**:
- Verify ticker symbol is correct (e.g., "AAPL" not "Apple")
- Check stock is actively traded (delisted stocks not supported)
- Try a different ticker from a major index

### Insufficient Historical Data

**Request**:
```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NEWCO"}'
```

**Response** (400 Bad Request):
```json
{
  "detail": {
    "error": "INSUFFICIENT_HISTORY: Less than 1 year of historical data for 'NEWCO'",
    "error_code": "INSUFFICIENT_HISTORY"
  }
}
```

**What To Do**:
- Stock must be traded for at least 1 year
- IPO'd companies may not have enough data
- Use manual `/dcf/calculate` endpoint with custom assumptions instead

### Invalid Ticker Format

**Request**:
```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": ""}'
```

**Response** (400 Bad Request):
```json
{
  "detail": {
    "error": "INVALID_TICKER: Ticker must be non-empty alphanumeric string",
    "error_code": "INVALID_TICKER"
  }
}
```

**What To Do**:
- Provide a non-empty ticker (1-5 characters, letters only)
- Example: `{"ticker": "AAPL"}`

### Network Timeout

**Response** (503 Service Unavailable):
```json
{
  "detail": {
    "error": "YFINANCE_ERROR: Unable to fetch data (timeout after 10s)",
    "error_code": "YFINANCE_ERROR"
  }
}
```

**What To Do**:
- yfinance data source may be temporarily unavailable
- Retry after 1-2 minutes
- Check internet connection
- If persistent, contact system administrator

---

## Examples: Valuing Different Stocks

### Example 1: Tech Stock with Strong Growth (Microsoft)

```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "MSFT"}'
```

**Expected**:
- High FCF growth rate (~15-20% historically)
- Higher discount rate due to larger beta
- Result: Higher valuation per share

### Example 2: Mature Consumer Stock (Coca-Cola)

```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "KO"}'
```

**Expected**:
- Lower FCF growth rate (~3-5% historically)
- Lower discount rate (defensive stock, lower beta)
- Result: Lower valuation per share (but more stable)

### Example 3: Financial Services (JPMorgan)

```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "JPM"}'
```

**Expected**:
- FCF from financial institutions can be volatile
- High leverage affects net debt and WACC
- Result: Lower valuation if highly leveraged

---

## How It Works Under the Hood

```
1. User Request: {"ticker": "AAPL"}
   │
   ├─→ YFinanceService.extract_dcf_inputs("AAPL")
   │   ├─ Fetch quarterly cash flows (5 years of history)
   │   ├─ Fetch quarterly balance sheet (latest)
   │   ├─ Calculate FCF = Operating CF - CapEx
   │   ├─ Calculate FCF growth rate (5-year CAGR)
   │   ├─ Estimate WACC (CAPM-based)
   │   ├─ Calculate net debt (Total Debt - Cash)
   │   └─ Return ExtractedYFinanceData
   │
   ├─→ DCFRequest.from_yfinance_data()
   │   ├─ starting_fcf = Latest quarter FCF
   │   ├─ fcf_growth_rate = Capped 5-year CAGR
   │   ├─ discount_rate = WACC (risk-free + beta × market premium)
   │   ├─ terminal_growth_rate = 2.5% (GDP anchor)
   │   ├─ net_debt = From balance sheet
   │   ├─ number_of_shares = From share info
   │   └─ Return populated DCFRequest
   │
   ├─→ DCFCalculationService.calculate_dcf(request)
   │   ├─ Project 10-year FCF with growth rate
   │   ├─ Discount each year's FCF to present value
   │   ├─ Calculate terminal value
   │   ├─ Sum discounted cash flows
   │   └─ Return DCFResponse
   │
   └─→ User Response: DCFResponse (enterprise value, equity value, etc.)
```

---

## Advanced: Comparing Manual vs. Auto Endpoints

### Manual Endpoint (`/dcf/calculate`)

**Use When**:
- You have custom assumptions (e.g., management guidance on growth)
- Stock is newly IPO'd or missing data
- You want to model specific scenarios

**Example**:
```bash
curl -X POST http://localhost:8000/dcf/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "starting_fcf": 50.0,
    "fcf_growth_rate": 0.12,
    "years": 10,
    "discount_rate": 0.08,
    "terminal_growth_rate": 0.03,
    "net_debt": -30.0,
    "number_of_shares": 2500.0
  }'
```

### Auto Endpoint (`/dcf/auto-calculate`)

**Use When**:
- You want quick estimates without data gathering
- Stock has 1+ year of trading history
- You trust yfinance data quality
- You want consistent methodology across many stocks

**Example**:
```bash
curl -X POST http://localhost:8000/dcf/auto-calculate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
```

---

## Troubleshooting

### "TICKER_NOT_FOUND" for a Valid Stock

**Possible Causes**:
- Ticker symbol spelling (case-sensitive lookup in yfinance)
- Stock uses different symbol in yfinance (e.g., Chinese stocks)
- Stock recently delisted or name changed

**Solution**: Verify ticker on Yahoo Finance or yfinance directly:
```python
import yfinance as yf
ticker = yf.Ticker("AAPL")
print(ticker.info.get('longName'))  # Should print "Apple Inc."
```

### "INSUFFICIENT_HISTORY" for Recently IPO'd Stock

**Possible Causes**:
- Stock IPO'd less than 1 year ago
- yfinance data not yet fully historical

**Solution**: Use manual `/dcf/calculate` endpoint with management guidance:
```bash
# Use current quarter FCF and management guidance for growth
curl -X POST http://localhost:8000/dcf/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "starting_fcf": 1.0,
    "fcf_growth_rate": 0.25,
    "years": 10,
    "discount_rate": 0.15,
    "terminal_growth_rate": 0.03,
    "net_debt": 0.5,
    "number_of_shares": 100.0
  }'
```

### Very High or Very Low Valuation

**Possible Causes**:
- Stock in distress (negative FCF or high debt)
- Stock in high-growth phase (inflated multiples)
- Outlier historical data affecting CAGR calculation

**Solution**: Review the fundamentals:
```python
# Fetch raw yfinance data to inspect
import yfinance as yf
ticker = yf.Ticker("SYMBOL")
print(ticker.quarterly_cashflow)
print(ticker.quarterly_balance_sheet)
```

---

## Next Steps

1. **Integrate with Your App**: Use the API response to display valuations, create watchlists, or build alerts
2. **Customize**: Modify [src/services/yfinance_service.py](../../src/services/yfinance_service.py) to add industry-specific adjustments
3. **Monitor**: Track API response times and error rates to ensure reliability
4. **Iterate**: Gather user feedback and improve parameter derivation logic
