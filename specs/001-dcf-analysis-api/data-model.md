# Data Model: DCF Analysis API

**Date**: 2025-11-16  
**Phase**: 1 (Design & Contracts)  
**Purpose**: Define request/response schemas and data model entities

## Request Model: DCFRequest

**Purpose**: Represents a single DCF calculation request (using `starting_fcf` + growth to derive forecasts)

**Fields**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `starting_fcf` | `float` | Yes | ≥ 0 | Starting free cash flow (last historical year). Units: billions. |
| `fcf_growth_rate` | `float` | Yes | any real number (percent) | Forecast growth rate in percent (e.g., `8.0` = 8%). Used to grow `starting_fcf` into multi-year forecasts. |
| `years` | `int` | Yes | 1-30 inclusive | Number of forecast years to compute. |
| `discount_rate` | `float` | Yes | > 0 (percent) and > `terminal_growth_rate` if provided | Discount rate / WACC expressed in percent (e.g., `8.0` = 8%). |
| `terminal_growth_rate` | `float` | No | ≥ 0 (percent) | Terminal growth rate in percent (e.g., `3.0` = 3%). If omitted, no terminal value will be used unless `terminal_value` is provided. |
| `net_debt` | `float` | No | any numeric value (can be negative) | Net debt in billions. Positive = net debt; negative = net cash. |
| `terminal_value` | `float` | No | any numeric value (can be zero) | Optional pre-calculated terminal value in billions. If provided, the service will use it as-is. |

**Validation Rules**:

1. **Years Validation**:
   - `years` must be between 1 and 30 inclusive. If outside this range, reject with HTTP 400: `FORECAST_PERIOD_OUT_OF_RANGE`.

2. **Starting FCF / Computed FCFs Validation**:
   - `starting_fcf` must be ≥ 0. Computed forecast values (starting_fcf grown by `fcf_growth_rate`) must be non-negative; if any computed FCF < 0, reject with HTTP 400: `NEGATIVE_FCF_VALUE`.

3. **Discount Rate Validation**:
   - `discount_rate` must be > 0. If invalid, reject with HTTP 400: `INVALID_DISCOUNT_RATE`.

4. **Terminal Growth Rate Validation**:
   - If provided, `terminal_growth_rate` must be ≥ 0 and strictly less than `discount_rate`. Otherwise, reject with HTTP 400: `WACC_LE_G` or `INVALID_G` as appropriate.

5. **Net Debt Validation**:
   - `net_debt` may be negative to represent net cash; no non-negativity requirement.

**Pydantic Model Definition (conceptual)**:

```python
from pydantic import BaseModel, field_validator

class DCFRequest(BaseModel):
    starting_fcf: float
    fcf_growth_rate: float  # percent, e.g. 8.0
    years: int
    discount_rate: float    # percent, e.g. 8.0
    terminal_growth_rate: float | None = None  # percent
    net_debt: float | None = None
    terminal_value: float | None = None

    @field_validator('starting_fcf')
    def validate_starting_fcf(cls, v):
        if v < 0:
            raise ValueError('STARTING_FCF_NEGATIVE')
        return v

    @field_validator('years')
    def validate_years(cls, v):
        if not (1 <= v <= 30):
            raise ValueError('YEARS_LENGTH')
        return v

    @field_validator('discount_rate')
    def validate_discount_rate(cls, v):
        if v <= 0:
            raise ValueError('INVALID_DISCOUNT_RATE')
        return v

    @field_validator('terminal_growth_rate')
    def validate_g(cls, v):
        if v is not None and v < 0:
            raise ValueError('INVALID_G')
        return v
```

---

## Response Model: DCFResponse

**Purpose**: Represents the complete result of a DCF calculation

**Fields**:

| Field | Type | Format | Description |
|-------|------|--------|-------------|
| `enterprise_value` | `float` | 2 decimal places | Sum of all discounted cash flows and discounted terminal value. Units: billions. |
| `equity_value` | `float` | 2 decimal places | EV - net_debt. Units: billions. |
| `discounted_fcfs` | `list[float]` | 2 decimal places each | Array of present values for each forecasted FCF. Length equals `years`.
| `discounted_terminal_value` | `float` | 2 decimal places | PV(TV) = TV / (1 + discount_rate/100)^n. Units: billions.

**Constraints**:
- All monetary values rounded to exactly 2 decimal places on serialization
- Array elements in `discounted_fcfs` also rounded to 2 decimals
- Values can be negative (edge cases allowed per spec)

**Pydantic Model Definition**:

```python
from decimal import Decimal, ROUND_HALF_UP

def round_currency(value: float) -> float:
    """Round to 2 decimal places using HALF_UP rounding"""
    return float(
        Decimal(str(value)).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
    )

class DCFResponse(BaseModel):
    enterprise_value: float
    equity_value: float
    discounted_fcfs: list[float]
    discounted_terminal_value: float
    
    def model_dump(self, **kwargs):
        """Override to apply rounding to all monetary fields"""
        data = super().model_dump(**kwargs)
        data['enterprise_value'] = round_currency(data['enterprise_value'])
        data['equity_value'] = round_currency(data['equity_value'])
        data['discounted_terminal_value'] = round_currency(data['discounted_terminal_value'])
        data['discounted_fcfs'] = [
            round_currency(x) for x in data.get('discounted_fcfs', [])
        ]
        return data
```

---

## Error Response Model: ErrorResponse

**Purpose**: Represents a validation or business logic error

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `error` | `string` | Human-readable error message (e.g., "WACC must be strictly greater than g. Current: WACC=0.05, g=0.06") |
| `error_code` | `string` | Machine-readable code for programmatic handling (e.g., "WACC_LE_G") |
| `details` | `object` (optional) | Additional context (e.g., `{"wacc": 0.05, "g": 0.06}`) |

**Error Codes** (per specification FR-020):

| Error Code | HTTP Status | Trigger | Example Message |
|------------|------------|---------|-----------------|
| `EMPTY_FCF_ARRAY` | 400 | FCF array is empty | "Free Cash Flow array cannot be empty. At least one FCF value required." |
| `NEGATIVE_FCF_VALUE` | 400 | Any FCF < 0 | "All FCF values must be non-negative. Found negative value: FCF[2]=−500" |
| `FORECAST_PERIOD_OUT_OF_RANGE` | 400 | len(fcf) < 1 or > 30 | "Forecast period must be between 1 and 30 years. Provided: 35 years" |
| `INVALID_WACC` | 400 | WACC ≤ 0 | "WACC must be a positive decimal value greater than 0. Provided: −0.05" |
| `INVALID_G` | 400 | g < 0 | "Terminal growth rate must be a non-negative decimal. Provided: −0.02" |
| `WACC_LE_G` | 400 | WACC ≤ g | "WACC must be strictly greater than terminal growth rate g. Current: WACC=0.05, g=0.06" |
| `INVALID_NETDEBT` | 400 | NetDebt not numeric | "Net Debt must be a valid numeric value. Provided: {invalid}" |

**Pydantic Model Definition**:

```python
class ErrorResponse(BaseModel):
    error: str
    error_code: str
    details: dict | None = None

class DCFError(Exception):
    """Custom exception for DCF calculation errors"""
    def __init__(self, error_code: str, message: str, details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)
```

---

## Calculation Intermediate Values

**Purpose**: Internal data structures used during calculation (not returned to client, but important for understanding flow)

**TerminalValue**:
- Type: `float`
- Calculated as: `TV = (FCF[n] × (1 + g)) / (WACC - g)` if not provided
- Or: provided value if `terminal_value` parameter is given
- Used in: Present Value of Terminal Value calculation

**PresentValueFCF** (array):
- Type: `list[float]`
- Each element: `PV(FCF[t]) = FCF[t] / (1 + WACC)^t` for t = 1 to n
- Returned to client as `discounted_cash_flows`
- Precision: Full double-precision throughout calculation; rounded to 2 decimals in response

**PresentValueTerminalValue**:
- Type: `float`
- Calculated as: `PV(TV) = TV / (1 + WACC)^n`
- Returned to client as `discounted_terminal_value`
- Precision: Full double-precision throughout calculation; rounded to 2 decimals in response

**EnterpriseValue**:
- Type: `float`
- Calculated as: `EV = Σ(PV(FCF[t])) + PV(TV)`
- Returned to client as `enterprise_value`
- Precision: Full double-precision throughout calculation; rounded to 2 decimals in response

**EquityValue**:
- Type: `float`
- Calculated as: `Equity Value = EV - NetDebt`
- Returned to client as `equity_value`
- Precision: Full double-precision throughout calculation; rounded to 2 decimals in response

---

## Data Type Considerations

**Numeric Precision**:
- Python `float`: IEEE 754 double-precision (64-bit)
- Sufficient for financial calculations up to $1 trillion with <0.01% error
- No need for Decimal type in intermediate calculations (per constitution "no external libs")
- Output formatted to 2 decimal places for currency representation

**Array Handling**:
- FCF array: 1-30 elements (validated)
- Discounted cash flows output: Same length as input FCF array
- Immutable during calculation (functional style)

**Null/None Handling**:
- `terminal_value`: Optional field; `None` means "calculate it"
- All other fields: Required (no None values accepted)
- Error messages never contain None values (validation prevents this)

---

## Data Model Summary

| Entity | Fields | Validation | Output Format |
|--------|--------|-----------|---------------|
| **DCFRequest** | fcf, wacc, g, net_debt, terminal_value | Pydantic + service layer | N/A (input only) |
| **DCFResponse** | enterprise_value, equity_value, terminal_value, discounted_cash_flows, discounted_terminal_value | N/A (output only) | JSON, 2 decimals |
| **ErrorResponse** | error, error_code, details | N/A (error only) | JSON with error_code |

## Phase 1 Complete

✅ Request schema defined with all validation rules  
✅ Response schema defined with rounding rules  
✅ Error response schema with all error codes  
✅ Pydantic models ready for implementation  
✅ Ready for API contract design (contracts/)
