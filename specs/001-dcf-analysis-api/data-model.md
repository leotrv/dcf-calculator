# Data Model: DCF Analysis API

**Date**: 2025-11-16  
**Phase**: 1 (Design & Contracts)  
**Purpose**: Define request/response schemas and data model entities

## Request Model: DCFRequest

**Purpose**: Represents a single DCF calculation request

**Fields**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `fcf` | `list[float]` | Yes | Non-empty, 1-30 elements, all ≥ 0 | Array of projected annual free cash flows. Values must be non-negative. Length determines forecast period. |
| `wacc` | `float` | Yes | > 0 (positive), < g constraint checked in service | Weighted Average Cost of Capital as decimal (e.g., 0.10 for 10%). Used as discount rate. |
| `g` | `float` | Yes | ≥ 0 (non-negative), WACC > g constraint checked in service | Terminal growth rate as decimal (e.g., 0.03 for 3%). Represents perpetual growth beyond forecast. |
| `net_debt` | `float` | Yes | Any numeric value (positive, zero, or negative) | Net Debt = Total Debt - Cash. Used to convert EV to Equity Value. Can be negative (net cash position). |
| `terminal_value` | `float` | No | Optional; if provided, any numeric value | Pre-calculated Terminal Value. If omitted, system calculates TV = (FCF[-1] × (1 + g)) / (WACC - g). If provided (including 0), system uses this value as-is. |

**Validation Rules**:

1. **FCF Array Validation** (Pydantic + service layer):
    - Length must be between 1 and 30 elements (inclusive). If outside this range, reject with HTTP 400: `FORECAST_PERIOD_OUT_OF_RANGE`.
    - All elements must be ≥ 0 (HTTP 400: `NEGATIVE_FCF_VALUE`)
    - Type: list of numbers (Pydantic enforces)

2. **WACC Validation** (Pydantic + service layer):
   - Must be numeric (Pydantic enforces)
   - Must be > 0 (HTTP 400: INVALID_WACC)
   - Must be > g (service layer, HTTP 400: WACC_LE_G)

3. **Growth Rate (g) Validation** (Pydantic + service layer):
   - Must be numeric (Pydantic enforces)
   - Must be ≥ 0 (HTTP 400: INVALID_G)
   - Must be < WACC (service layer, HTTP 400: WACC_LE_G)

4. **NetDebt Validation** (Pydantic):
   - Must be numeric (HTTP 400: INVALID_NETDEBT if type error)
   - Can be positive, zero, or negative (all valid)

5. **Terminal Value Validation** (Pydantic):
   - If provided, must be numeric
   - If 0, valid and honored (per clarification)
   - If negative, valid (represents declining terminal value scenario)

**Pydantic Model Definition**:

```python
from pydantic import BaseModel, field_validator

class DCFRequest(BaseModel):
    fcf: list[float]
    wacc: float
    g: float
    net_debt: float
    terminal_value: float | None = None
    
    @field_validator('fcf')
    @classmethod
    def validate_fcf(cls, v):
        if not v:
            raise ValueError("Free Cash Flow array cannot be empty")
        if len(v) > 30:
            raise ValueError(f"Forecast period exceeds 30 years. Provided: {len(v)} years")
        if any(x < 0 for x in v):
            idx = next(i for i, x in enumerate(v) if x < 0)
            raise ValueError(f"All FCF values must be non-negative. Found: FCF[{idx}]={v[idx]}")
        return v
    
    @field_validator('wacc')
    @classmethod
    def validate_wacc(cls, v):
        if v <= 0:
            raise ValueError(f"WACC must be positive. Provided: {v}")
        return v
    
    @field_validator('g')
    @classmethod
    def validate_g(cls, v):
        if v < 0:
            raise ValueError(f"Terminal growth rate must be non-negative. Provided: {v}")
        return v
    
    @field_validator('net_debt')
    @classmethod
    def validate_net_debt(cls, v):
        # Any numeric value is valid (positive, zero, negative)
        return v
```

---

## Response Model: DCFResponse

**Purpose**: Represents the complete result of a DCF calculation

**Fields**:

| Field | Type | Format | Description |
|-------|------|--------|-------------|
| `enterprise_value` | `float` | 2 decimal places | Sum of all discounted cash flows and discounted terminal value. Main valuation metric. |
| `equity_value` | `float` | 2 decimal places | EV - NetDebt. Value available to equity holders. |
| `terminal_value` | `float` | 2 decimal places | Terminal Value used in calculation (either provided or calculated). |
| `discounted_cash_flows` | `list[float]` | 2 decimal places each | Array of present values for each year's FCF. Length matches input FCF array. |
| `discounted_terminal_value` | `float` | 2 decimal places | PV(TV) = TV / (1 + WACC)^n. Present value of terminal value component. |

**Constraints**:
- All monetary values rounded to exactly 2 decimal places
- Array elements in discounted_cash_flows also rounded to 2 decimals
- Values can be negative (edge cases allowed per spec)

**Pydantic Model Definition**:

```python
from decimal import Decimal, ROUND_HALF_UP

def round_currency(value: float) -> float:
    """Round to 2 decimal places using banker's rounding"""
    return float(
        Decimal(str(value)).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
    )

class DCFResponse(BaseModel):
    enterprise_value: float
    equity_value: float
    terminal_value: float
    discounted_cash_flows: list[float]
    discounted_terminal_value: float
    
    def model_dump(self, **kwargs):
        """Override to apply rounding to all monetary fields"""
        data = super().model_dump(**kwargs)
        data['enterprise_value'] = round_currency(data['enterprise_value'])
        data['equity_value'] = round_currency(data['equity_value'])
        data['terminal_value'] = round_currency(data['terminal_value'])
        data['discounted_terminal_value'] = round_currency(data['discounted_terminal_value'])
        data['discounted_cash_flows'] = [
            round_currency(x) for x in data['discounted_cash_flows']
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
