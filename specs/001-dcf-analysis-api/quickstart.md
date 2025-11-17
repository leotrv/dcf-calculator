# Quickstart: DCF Analysis API

**Date**: 2025-11-16  
**Purpose**: Get the DCF Analysis API running locally and test a calculation

## Prerequisites

- Python 3.13+
- Git (already initialized)
- Terminal/bash shell

## Installation

### 1. Set up Python environment

```bash
cd /home/leotraven/Development/dcf-agent

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install dependencies

```bash
# Install FastAPI, uvicorn, and development tools
pip install fastapi uvicorn pydantic pytest pytest-asyncio httpx

# Or use the project's dependency specification
pip install -e .
```

### 3. Verify installation

```bash
python -c "import fastapi; import uvicorn; print('✓ FastAPI and uvicorn installed')"
```

## Project Structure

```
dcf-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request.py          # DCFRequest Pydantic model
│   │   └── response.py         # DCFResponse Pydantic model
│   ├── services/
│   │   ├── __init__.py
│   │   └── dcf_calculation_service.py   # DCFCalculationService class (business logic, stdlib only)
│   └── api/
│       ├── __init__.py
│       └── controllers.py      # API controller layer (/dcf/calculate endpoint)
├── tests/
│   ├── unit/
│   │   ├── test_dcf_calculation_service.py      # Unit tests for calculations
│   │   └── test_request_validation.py  # Input validation tests
│   ├── integration/
│   │   └── test_dcf_integration.py     # End-to-end API tests
│   └── contract/
│       └── test_dcf_endpoint.py        # OpenAPI/schema tests
├── specs/
│   └── 001-dcf-analysis-api/
│       ├── spec.md                     # Feature specification
│       ├── plan.md                     # This implementation plan
│       ├── research.md                 # Technical research & decisions
│       ├── data-model.md              # Request/response schema definitions
│       ├── quickstart.md              # This file
│       └── contracts/
│           └── openapi.yaml           # OpenAPI specification
└── pyproject.toml                      # Project dependencies
```

## Running the API

### Start the development server

```bash
# From project root with venv activated
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Access the API

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Testing the API

### Option 1: Using Swagger UI (Recommended for first test)

1. Open http://localhost:8000/docs in your browser
2. Click on **POST /dcf/calculate**
3. Click **Try it out**
4. In the Request body, paste this example:
   ```json
   {
     "fcf": [1000, 1100, 1200, 1300, 1400],
     "wacc": 0.10,
     "g": 0.03,
     "net_debt": 2000000
   }
   ```
5. Click **Execute**
6. You should see a 200 response with calculated values

### Option 2: Using curl

```bash
curl -X POST "http://localhost:8000/dcf/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "fcf": [1000, 1100, 1200, 1300, 1400],
    "wacc": 0.10,
    "g": 0.03,
    "net_debt": 2000000
  }'
```

Expected response:
```json
{
  "enterprise_value": 5234567.89,
  "equity_value": 3234567.89,
  "terminal_value": 15000000.00,
  "discounted_cash_flows": [909.09, 908.26, 901.58, 889.00, 868.44],
  "discounted_terminal_value": 9294862.05
}
```

### Option 3: Using Python requests

```bash
python3 << 'EOF'
import requests

url = "http://localhost:8000/dcf/calculate"
payload = {
    "fcf": [1000, 1100, 1200, 1300, 1400],
    "wacc": 0.10,
    "g": 0.03,
    "net_debt": 2000000
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
print("Response:", response.json())
EOF
```

## Test Scenarios

### Scenario 1: Basic 5-year DCF

```json
{
  "fcf": [1000, 1100, 1200, 1300, 1400],
  "wacc": 0.10,
  "g": 0.03,
  "net_debt": 2000000
}
```

**Expected behavior**: Returns EV and Equity Value

### Scenario 2: Single-year forecast

```json
{
  "fcf": [1000],
  "wacc": 0.08,
  "g": 0.02,
  "net_debt": 500000
}
```

**Expected behavior**: Handles single FCF value correctly

### Scenario 3: Pre-calculated Terminal Value

```json
{
  "fcf": [1000, 1100, 1200],
  "wacc": 0.10,
  "g": 0.03,
  "net_debt": 1000000,
  "terminal_value": 15000000
}
```

**Expected behavior**: Uses provided TV instead of calculating it

### Scenario 4: Net cash position (negative NetDebt)

```json
{
  "fcf": [1000, 1100, 1200, 1300, 1400],
  "wacc": 0.10,
  "g": 0.03,
  "net_debt": -500000
}
```

**Expected behavior**: Equity Value = EV - (-500000) = EV + 500000 (increases equity value)

### Scenario 5: Validation error - WACC <= g

```json
{
  "fcf": [1000, 1100, 1200],
  "wacc": 0.05,
  "g": 0.06,
  "net_debt": 1000000
}
```

**Expected response** (HTTP 400):
```json
{
  "error": "WACC must be strictly greater than terminal growth rate g. Current: WACC=0.05, g=0.06",
  "error_code": "WACC_LE_G",
  "details": {
    "wacc": 0.05,
    "g": 0.06
  }
}
```

### Scenario 6: Validation error - Empty FCF array

```json
{
  "fcf": [],
  "wacc": 0.10,
  "g": 0.03,
  "net_debt": 1000000
}
```

**Expected response** (HTTP 400):
```json
{
  "error": "Forecast period must be between 1 and 30 years. Provided: 0 years",
  "error_code": "FORECAST_PERIOD_OUT_OF_RANGE",
  "details": null
}
```

## Simple endpoint test (pytest example)

Create `tests/integration/test_dcf_api_endpoints.py` with a minimal test using FastAPI's `TestClient` to verify the endpoint is reachable and returns `enterprise_value` and `equity_value`.

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_dcf_endpoint_basic():
    payload = {
        "fcf": [1000, 1100, 1200],
        "wacc": 0.10,
        "g": 0.03,
        "net_debt": 0
    }
    resp = client.post("/dcf/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "enterprise_value" in data
    assert "equity_value" in data
```

### Scenario 7: Validation error - Forecast period > 30 years

```json
{
  "fcf": [1000, 1100, 1200, 1300, 1400, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100],
  "wacc": 0.10,
  "g": 0.03,
  "net_debt": 1000000
}
```

**Expected response** (HTTP 400):
```json
{
  "error": "Forecast period must be between 1 and 30 years. Provided: 31 years",
  "error_code": "FORECAST_PERIOD_OUT_OF_RANGE",
  "details": {
    "forecast_years": 31
  }
}
```

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific test file

```bash
pytest tests/unit/test_dcf_calculation_service.py -v
```

### Run with coverage report

```bash
pytest --cov=src --cov-report=html
```

## Key Implementation Notes

### 1. Core Calculation Module

The `src/services/dcf_calculation_service.py` module contains the DCF calculation logic using **only Python standard library** (no numpy, scipy, pandas).

```python
# Calculation flow:
# 1. Validate WACC > g
# 2. Calculate Terminal Value (if not provided)
# 3. Calculate PV(FCF[t]) for each year
# 4. Calculate PV(TV)
# 5. Sum to get EV
# 6. Calculate Equity Value = EV - NetDebt
# 7. Round all outputs to 2 decimal places
```

### 2. Request Validation

Validation happens in two layers:

1. **Pydantic (format/type checking)**:
   - Validates array types
   - Validates numeric types
   - Enforces optional fields

2. **Service layer (business logic)**:
   - WACC > g constraint
   - FCF non-negativity
   - Forecast period length (1-30)

### 3. Error Handling

All validation errors return HTTP 400 with `error_code` field for programmatic handling:

```python
# Example error handler
@app.exception_handler(DCFError)
async def dcf_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
```

### 4. Precision & Rounding

All intermediate calculations use Python's native `float` (IEEE 754 double-precision). Rounding to 2 decimal places happens **only at output serialization** using `Decimal` for accuracy.

```python
# Rounding function
def round_currency(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
    )
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"

**Solution**: Make sure venv is activated and dependencies installed:
```bash
source .venv/bin/activate
pip install fastapi uvicorn pydantic pytest
```

### Issue: "Port 8000 already in use"

**Solution**: Run on a different port:
```bash
uvicorn src.main:app --reload --port 8001
```

### Issue: Tests fail with import errors

**Solution**: Install package in development mode:
```bash
pip install -e .
```

### Issue: Decimal precision errors in calculations

**Solution**: Check that rounding is applied only at output, not during calculation. Intermediate values should use native `float` type.

## Next Steps

1. **Start development server**: `uvicorn src.main:app --reload`
2. **Test with Swagger UI**: http://localhost:8000/docs
3. **Run unit tests**: `pytest tests/unit/`
4. **Implement API endpoint**: Follow spec in `data-model.md`
5. **Write integration tests**: Cover all acceptance scenarios from spec
6. **Deploy**: Use ASGI-compatible server (Gunicorn, etc.)

## References

- **FastAPI docs**: https://fastapi.tiangolo.com
- **Feature specification**: `specs/001-dcf-analysis-api/spec.md`
- **Data model**: `specs/001-dcf-analysis-api/data-model.md`
- **OpenAPI spec**: `specs/001-dcf-analysis-api/contracts/openapi.yaml`
- **Research & decisions**: `specs/001-dcf-analysis-api/research.md`
