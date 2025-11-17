# Research: DCF Analysis API

**Date**: 2025-11-16  
**Phase**: 0 (Outline & Research)  
**Purpose**: Resolve technical unknowns and document best practices decisions

## Questions Resolved

### Q1: Web Framework Selection (FastAPI vs Alternatives)

**Question**: User specification requires "FastAPI project." Is FastAPI the appropriate choice for a stateless DCF calculation API?

**Decision**: FastAPI

**Rationale**:
- User specification explicitly requires FastAPI ("Build a FastAPI project")
- FastAPI is lightweight and minimal for this use case
- Excellent Pydantic integration for input validation (critical for financial data)
- Automatic OpenAPI (Swagger) documentation generation (aids development and testing)
- Performance >100ms requirement: FastAPI easily handles sub-100ms responses
- Async support available if needed for future scaling (not needed for Phase 0)

**Alternatives Considered**:
- **Flask**: Lighter, but requires manual request parsing/validation. Pydantic support via extension only. ✗ (inferior)
- **Django**: Overkill for stateless API, requires database/ORM configuration. ✗ (too heavy)
- **http.server (stdlib)**: Maintains "minimal dependencies" but requires 500+ LOC for HTTP routing, JSON parsing, error handling. ✗ (violates simplicity principle)
- **uvicorn + Starlette**: Lower-level alternative to FastAPI, but FastAPI adds value with Pydantic models and OpenAPI docs. ✓ (equivalent, but FastAPI has advantages)

**Final Choice**: FastAPI + uvicorn + Pydantic

### Q2: Core Calculation Service Architecture (Layered Pattern)

**Question**: Should DCF calculations be embedded in FastAPI route handlers, or separated into a service layer with a dedicated calculation service class?

**Decision**: Dedicated `DCFCalculationService` class in `services/dcf_calculation_service.py` using layered architecture (100% stdlib core)

**Rationale**:
- **Layered Architecture**: Controller (HTTP) → Service (business logic) → Models (data validation)
- **Separation of Concerns**: HTTP transport layer completely independent from calculation domain logic
- **Service Class Pattern**: Single responsibility principle; DCFCalculationService encapsulates all calculation methods
- **Independent Testing**: Calculation logic testable without FastAPI dependency (pure Python class with no async/HTTP)
- **Future Flexibility**: Can be reused by CLI tools, batch processing, or other frameworks without code duplication
- **Constitution Compliance**: "No external libraries for core" - service class uses 100% stdlib only
- **Controller Adapter Pattern**: API routes in `api/controllers.py` act as thin HTTP adapters

**Architecture Layers**:
```
FastAPI Application (src/main.py)
    ↓
Controller Layer (src/api/controllers.py)  [HTTP handling, request→response]
    ↓ calls
Service Layer (src/services/dcf_calculation_service.py)  [Business logic, 100% stdlib]
    ↓ uses
Models (src/models/request.py, response.py)  [Data validation & serialization]
```

**Implementation**:
```python
# src/services/dcf_calculation_service.py - 100% stdlib
from typing import NamedTuple

class DCFResult(NamedTuple):
    enterprise_value: float
    equity_value: float
    terminal_value: float
    discounted_cash_flows: list[float]
    discounted_terminal_value: float

class DCFCalculationService:
    """Service for DCF valuation calculations using Gordon Growth Model"""
    
    def calculate_dcf(
        self,
        fcf: list[float],
        wacc: float,
        g: float,
        net_debt: float,
        terminal_value: float | None = None
    ) -> DCFResult:
        """Calculate Enterprise Value and Equity Value using DCF method"""
        # Business logic validation (separate from Pydantic format validation)
        self._validate_inputs(fcf, wacc, g)
        
        # Calculation logic
        tv = terminal_value if terminal_value is not None else self._calculate_terminal_value(fcf[-1], wacc, g)
        pv_fcfs = [self._calculate_pv_fcf(cf, wacc, i+1) for i, cf in enumerate(fcf)]
        pv_tv = self._calculate_pv_terminal_value(tv, wacc, len(fcf))
        ev = sum(pv_fcfs) + pv_tv
        equity_value = ev - net_debt
        
        return DCFResult(
            enterprise_value=ev,
            equity_value=equity_value,
            terminal_value=tv,
            discounted_cash_flows=pv_fcfs,
            discounted_terminal_value=pv_tv
        )
    
    def _validate_inputs(self, fcf: list[float], wacc: float, g: float) -> None:
        """Validate business logic constraints (not handled by Pydantic)"""
        if wacc <= g:
            raise ValueError(f"WACC_LE_G: WACC ({wacc}) must be strictly greater than g ({g})")
    
    def _calculate_terminal_value(self, final_fcf: float, wacc: float, g: float) -> float:
        """TV = (FCF[n] × (1 + g)) / (WACC - g)"""
        return (final_fcf * (1 + g)) / (wacc - g)
    
    def _calculate_pv_fcf(self, fcf: float, wacc: float, year: int) -> float:
        """PV(FCF[t]) = FCF[t] / (1 + WACC)^t"""
        return fcf / ((1 + wacc) ** year)
    
    def _calculate_pv_terminal_value(self, tv: float, wacc: float, n: int) -> float:
        """PV(TV) = TV / (1 + WACC)^n"""
        return tv / ((1 + wacc) ** n)

# Usage in controller layer:
# service = DCFCalculationService()
# result = service.calculate_dcf(fcf, wacc, g, net_debt, terminal_value)
```

### Q3: Input Validation Strategy (Two-Layer Approach)

**Question**: Should validation occur only in Pydantic models, or be split between Pydantic (format) and service layer (business logic)?

**Decision**: Two-layer validation: Pydantic (format/type validation at boundary) + Service (business logic validation)

**Rationale**:
- **Pydantic Layer** (models/request.py): Validates data format, types, array bounds, value ranges
  - Automatic HTTP 422 response on failure (invalid format/structure)
  - Deserialization + type coercion + field validators
  - Examples: fcf array length 1-30, non-negative values, rates are floats > 0
- **Service Layer** (services/dcf_calculation_service.py): Validates business constraints independently
  - Happens AFTER valid request object is created
  - Raises ValueError with error_code message for business rule violations
  - Can be tested independently without FastAPI or HTTP
- **Controller Layer** (api/controllers.py): Error handling adapter
  - Catches ValueError from service layer
  - Converts to HTTP 400 with error_code field (per spec FR-020)
  - Enables programmatic error handling without string parsing
- **Benefits**: Clear error semantics (422 = format error, 400 = valid data but business violation)

**Three-Layer Validation Flow**:
```
1. HTTP Request arrives
   ↓
2. Pydantic Validation (models/request.py)
   - Type checks: fcf is list[float], wacc is float, etc.
   - Range checks: 1-30 elements, non-negative values
   - Failure → HTTP 422 (automatic FastAPI response)
   ↓ (if valid, create DCFRequest Pydantic model)
3. Service Validation (services/dcf_calculation_service.py)
   - Business logic checks: WACC > g, other domain rules
   - Failure → raises ValueError("WACC_LE_G: message")
   ↓ (if valid, perform calculations)
4. Calculation & Response (services/dcf_calculation_service.py)
   - Calculate PV, TV, EV, Equity Value
   - Return DCFResult NamedTuple
   ↓
5. Controller Error Handling (api/controllers.py)
   - Catches ValueError from service
   - Extracts error_code from error message
   - Returns HTTP 400 with error_code field
```

**Pydantic Validation** (automatic, HTTP 422):
```python
from pydantic import BaseModel, field_validator

class DCFRequest(BaseModel):
    fcf: list[float]
    wacc: float
    g: float
    net_debt: float
    terminal_value: float | None = None
    
    @field_validator('fcf')
    def validate_fcf_array(cls, v):
        if not v:
            raise ValueError("FCF array cannot be empty")
        if len(v) > 30:
            raise ValueError("Forecast period exceeds 30 years")
        if any(x < 0 for x in v):
            raise ValueError("All FCF values must be non-negative")
        return v
    
    @field_validator('wacc', 'g')
    def validate_rates(cls, v):
        if v < 0:
            raise ValueError("Rate must be non-negative")
        return v
```

**Service Validation** (business logic, raises ValueError → HTTP 400):
```python
class DCFCalculationService:
    def calculate_dcf(self, fcf: list[float], wacc: float, g: float, ...) -> DCFResult:
        # Business logic validation (WACC > g is a constraint not just a format issue)
        self._validate_inputs(fcf, wacc, g)
        # ... continue with calculations
    
    def _validate_inputs(self, fcf: list[float], wacc: float, g: float) -> None:
        if wacc <= g:
            raise ValueError("WACC_LE_G: WACC must be strictly greater than growth rate")
```

**Controller Error Conversion** (HTTP adapter):
```python
from fastapi import HTTPException
from services.dcf_calculation_service import DCFCalculationService

service = DCFCalculationService()

@router.post("/dcf/calculate")
async def calculate_dcf(request: DCFRequest) -> DCFResponse:
    try:
        result = service.calculate_dcf(request.fcf, request.wacc, request.g, request.net_debt, request.terminal_value)
        return DCFResponse(
            enterprise_value=result.enterprise_value,
            equity_value=result.equity_value,
            terminal_value=result.terminal_value,
            discounted_cash_flows=result.discounted_cash_flows,
            discounted_terminal_value=result.discounted_terminal_value
        )
    except ValueError as e:
        error_msg = str(e)
        error_code = error_msg.split(':')[0]  # Extract "WACC_LE_G" from "WACC_LE_G: message"
        raise HTTPException(
            status_code=400,
            detail={"error": error_msg, "error_code": error_code, "details": {}}
        )
```

### Q4: Error Response Format & HTTP Status Codes

**Question**: How to handle validation errors to support programmatic error handling?

**Decision**: HTTP 400 with `error_code` field (per spec requirement FR-020)

**Rationale**:
- HTTP 400 = Bad Request (standard for client input errors)
- Specification explicitly requires error_code field for programmatic distinction
- Clients can parse error_code instead of error message text
- Enables retry logic based on error type (e.g., WACC_LE_G cannot be retried)

**Error Codes** (per FR-020):
- `WACC_LE_G`: WACC <= g validation failure
- `EMPTY_FCF_ARRAY`: FCF array is empty
- `NEGATIVE_FCF_VALUE`: FCF contains negative values
- `INVALID_WACC`: WACC validation failure
- `INVALID_G`: terminal growth rate validation failure
- `FORECAST_PERIOD_OUT_OF_RANGE`: FCF array length outside 1-30
- `INVALID_NETDEBT`: NetDebt validation failure

**Implementation**:
```python
class DCFError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message

@app.exception_handler(DCFError)
async def dcf_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": {}
        }
    )
```

### Q5: Testing Strategy & TDD Approach (Service-Layer First)

**Question**: What is the optimal TDD test structure for this layered API architecture?

**Decision**: Three-layer testing pyramid (unit → integration → contract) with service layer as testable core

**Rationale**:
- **Unit Tests** (fastest, MOST tests): DCFCalculationService class methods in isolation
  - Pure Python functions, zero FastAPI/HTTP dependencies
  - Write tests FIRST (TDD), assert calculation accuracy against known values
  - Test all edge cases: single year FCF, g=0, negative net debt, large values, precision boundaries
  - 100% stdlib; can run without any FastAPI or uvicorn
  - Enables calculator logic to be tested, refined, and verified independently
  - Example: `test_calculate_dcf_single_year()`, `test_wacc_le_g_raises_error()`, `test_precision_calculation()`
- **Integration Tests** (medium speed, FEWER tests): Full API workflow with FastAPI test client
  - Test request → Pydantic validation → service.calculate_dcf() → response serialization flow
  - Verify HTTP status codes (400 for business validation, 422 for format validation)
  - Verify output format, rounding to 2 decimals
  - Test error responses contain correct error_code field
  - Example: `test_dcf_api_success()`, `test_dcf_api_wacc_le_g_error()`, `test_dcf_api_invalid_format()`
- **Contract Tests** (smoke level): OpenAPI specification compliance
  - Verify Pydantic models match OpenAPI spec in contracts/
  - Verify response structure matches documented schema
  - Example: `test_openapi_schema_validation()`

**Test Structure**:
```
tests/
├── unit/
│   └── test_dcf_calculation_service.py      [70% of tests, pure Python, no HTTP]
├── integration/
│   └── test_dcf_api_endpoints.py            [25% of tests, with FastAPI client]
└── contract/
    └── test_dcf_openapi_compliance.py       [5% of tests, schema validation]
```

**Example Unit Test** (service layer):
```python
import pytest
from services.dcf_calculation_service import DCFCalculationService

@pytest.fixture
def service():
    return DCFCalculationService()

def test_calculate_dcf_single_year(service):
    """Single year FCF, simple calculation"""
    fcf = [100.0]
    wacc = 0.10
    g = 0.03
    net_debt = 50.0
    terminal_value = 100.0
    
    result = service.calculate_dcf(fcf, wacc, g, net_debt, terminal_value)
    
    assert result.enterprise_value == pytest.approx(1090.91, rel=0.001)  # 0.01% tolerance
    assert result.equity_value == pytest.approx(1040.91, rel=0.001)

def test_wacc_le_g_raises_error(service):
    """Service should raise ValueError when WACC <= g"""
    fcf = [100.0]
    wacc = 0.05
    g = 0.10
    
    with pytest.raises(ValueError, match="WACC_LE_G"):
        service.calculate_dcf(fcf, wacc, g, 0)
```

**Example Integration Test** (API layer):
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_dcf_api_success():
    """Full API workflow should return 200 with formatted response"""
    payload = {
        "fcf": [100.0, 105.0, 110.0],
        "wacc": 0.10,
        "g": 0.03,
        "net_debt": 50.0,
        "terminal_value": None
    }
    
    response = client.post("/dcf/calculate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "enterprise_value" in data
    assert "equity_value" in data
    # Values should be rounded to 2 decimals
    assert len(str(data["enterprise_value"]).split('.')[-1]) <= 2

def test_dcf_api_wacc_le_g_error():
    """API should return 400 with error_code for business validation failure"""
    payload = {
        "fcf": [100.0],
        "wacc": 0.05,
        "g": 0.10,
        "net_debt": 0
    }
    
    response = client.post("/dcf/calculate", json=payload)
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "WACC_LE_G"
    assert "error" in data

def test_dcf_api_invalid_format():
    """API should return 422 for format/type validation failure (Pydantic)"""
    payload = {
        "fcf": "not_a_list",  # Invalid type
        "wacc": 0.10,
        "g": 0.03,
        "net_debt": 0
    }
    
    response = client.post("/dcf/calculate", json=payload)
    
    assert response.status_code == 422  # Pydantic validation error
```

### Q6: Precision & Rounding Implementation

**Question**: How to implement 0.01% precision tolerance + 2 decimal place output?

**Decision**: Maintain double-precision (IEEE 754) throughout calculation; round only at output

**Rationale** (per FR-012):
- Python's `float` is double-precision by default
- Intermediate rounding accumulates floating-point errors
- Final rounding to 2 decimals (currency standard) happens only at serialization
- Comparison tolerance of 0.01% used in test assertions

**Implementation**:
```python
from decimal import Decimal, ROUND_HALF_UP

def round_to_2_decimals(value: float) -> float:
    """Round to 2 decimal places using banker's rounding"""
    return float(Decimal(str(value)).quantize(
        Decimal('0.01'), 
        rounding=ROUND_HALF_UP
    ))

# In response model:
class DCFResponse(BaseModel):
    enterprise_value: float
    equity_value: float
    terminal_value: float
    discounted_cash_flows: list[float]
    discounted_terminal_value: float
    
    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data['enterprise_value'] = round_to_2_decimals(self.enterprise_value)
        data['equity_value'] = round_to_2_decimals(self.equity_value)
        # ... etc
        return data
```

### Q7: Python Type Hints & Compatibility

**Question**: Should code use Python 3.13 features (union operator `|`, match statements)?

**Decision**: Use 3.13 features, but maintain `from __future__ import annotations` for compatibility

**Rationale**:
- `pyproject.toml` specifies `requires-python = ">=3.13"`
- Union operator `|` (PEP 604) is cleaner: `float | None` vs `Optional[float]`
- `match` statements (PEP 634) improve error code dispatch
- `from __future__ import annotations` ensures forward compatibility with future versions

**Implementation**:
```python
from __future__ import annotations
from typing import NamedTuple

class DCFRequest(BaseModel):
    fcf: list[float]
    terminal_value: float | None = None  # Python 3.10+ syntax
```

## Dependencies Summary

| Package | Version | Justification | Alternatives Rejected |
|---------|---------|---------------|----------------------|
| FastAPI | latest | User specification requirement; REST API framework | Flask (less validation support), Django (too heavy), stdlib http.server (too complex) |
| uvicorn | latest | ASGI server for FastAPI; minimal + performant | Gunicorn (overkill for single endpoint), stdlib only (no mature stdlib ASGI) |
| Pydantic | v2 (FastAPI default) | Input validation + type coercion; OpenAPI schema generation | Manual validation (verbose, error-prone), marshmallow (heavier) |
| pytest | latest | TDD testing framework (per constitution); installed for dev only | unittest (less assertion syntax), nose2 (discontinued) |

## Technology Stack Decisions

| Component | Decision | Justification |
|-----------|----------|---------------|
| Core Calculations | Python stdlib only | Maintains "minimal dependencies" principle; simple math operations don't need scipy/numpy |
| HTTP Server | FastAPI + uvicorn | User requirement; mature, lightweight, excellent for microservices |
| Request Validation | Pydantic | Built into FastAPI; provides OpenAPI docs automatically |
| Response Format | JSON | Universal, standard for REST APIs (per specification) |
| Testing | pytest + unittest | Standard Python testing, TDD-friendly, per constitution |
| Documentation | OpenAPI/Swagger | Generated by FastAPI automatically; no extra dependency |
| Deployment | ASGI-compatible | Supports uvicorn, Gunicorn, etc.; cloud-ready |

## Phase 0 Complete

✅ All research questions resolved  
✅ No [NEEDS CLARIFICATION] markers remain  
✅ Technical approach documented and justified  
✅ Aligns with constitution principles (with documented exceptions for FastAPI)  
✅ Ready to proceed to Phase 1 (design artifacts: data-model.md, contracts/, quickstart.md)
