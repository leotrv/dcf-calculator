# Implementation Plan: DCF Analysis API

**Branch**: `001-dcf-analysis-api` | **Date**: 2025-11-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-dcf-analysis-api/spec.md`

## Summary

Build a FastAPI-based REST API that calculates Discounted Cash Flow (DCF) valuation metrics. The system accepts five financial inputs (FCF array, WACC, terminal growth rate g, Net Debt, and optional Terminal Value) and returns Enterprise Value and Equity Value. All calculations follow explicit financial formulas with precision requirements (0.01% tolerance, 2 decimal place output). The system enforces strict validation (WACC > g, non-negative FCF, 1-30 year forecasts) and returns programmatically-distinct HTTP 400 errors for failures.

## Technical Context

**Language/Version**: Python 3.13 (per pyproject.toml requires-python)  
**Primary Dependencies**: FastAPI, uvicorn, Pydantic (minimal, justified by REST API need and type validation)  
**Storage**: None (stateless API; no persistence required)  
**Testing**: pytest (TDD required per constitution)  
**Target Platform**: Linux/macOS/Windows (cross-platform per constitution)  
**Project Type**: Single web service (REST API only)  
**Performance Goals**: Response time targets will be defined separately by benchmarks if required; not mandated in Phase 2.  
**Constraints**: 0.01% calculation precision, 2 decimal place output, 1-30 year forecast limit, WACC > g enforced  
**Scale/Scope**: Single `/dcf/calculate` endpoint, stateless, 5 primary inputs, 5 primary outputs

## Constitution Check

**Gate: MUST pass before Phase 0 research. Re-check after Phase 1 design.**

### Core Principles Alignment

| Principle | Status | Justification |
|-----------|--------|---------------|
| I. Python Native First | ✅ PASS | Core math uses stdlib (no numpy). FastAPI justified: REST API framework needed, no pure-stdlib alternative for HTTP/JSON. Pydantic: type validation critical for financial data. |
| II. Minimal Dependencies | ✅ PASS | 3 dependencies (FastAPI, uvicorn, Pydantic) - minimal and justified. Alternative: write HTTP server from scratch (unreasonable). Alternative: use Flask (no advantage, similar complexity). |
| III. CLI Focus | ✅ PASS | Primary interface for this feature is the HTTP API (FastAPI) per the feature specification; CLI wrappers may be added later for parity. |
| IV. Test-Driven Development (TDD) | ✅ PASS | All implementation tasks are TDD: write test first, then implementation. pytest for testing (per specification). |
| V. Simplicity and Readability | ✅ PASS | Pydantic models provide clear request/response contracts. Calculations are straightforward math formulas, no complex algorithms. Code will follow PEP 8. |

### Additional Constraints Alignment

| Constraint | Status | Justification |
|------------|--------|---------------|
| No external libs for core | ⚠️ REVIEW | Core DCF math uses stdlib only. FastAPI/uvicorn are for API transport, not core logic. Pydantic for validation (justified). Core calculation module is 100% stdlib. |
| Cross-platform compatibility | ✅ PASS | Python 3.13 + FastAPI/Pydantic/pytest are all cross-platform. No platform-specific code required. |

### Gate Decision: CONDITIONAL PASS

**Status**: Proceed to Phase 0 with documented exceptions:

**Exception 1: FastAPI + uvicorn + Pydantic**
- **Why Needed**: User specification explicitly requires "FastAPI project." REST API framework is necessary; no pure-stdlib HTTP server alternative exists that is maintainable.
- **Simpler Alternative Rejected**: Building HTTP server from stdlib alone (http.server, json) would exceed "simplicity" principle - ~500+ LOC vs ~50 LOC with FastAPI.
- **Justification**: Specification takes precedence over constitution for project-specific technology choice.

**Re-evaluation Point**: After Phase 1 design completion, confirm that core DCF calculation module is 100% stdlib and can be independently tested without FastAPI.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-dcf-analysis-api/
├── plan.md                # This file (Phase 0-1 output)
├── research.md            # Phase 0 output (research findings)
├── data-model.md          # Phase 1 output (request/response schema)
├── quickstart.md          # Phase 1 output (developer guide)
├── contracts/             # Phase 1 output (OpenAPI schema)
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── spec.md                # Original specification
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── __init__.py
│   ├── request.py         # DCFRequest Pydantic model (input validation)
│   └── response.py        # DCFResponse Pydantic model (output serialization with rounding)
├── services/
│   ├── __init__.py
│   └── dcf_calculation_service.py  # DCFCalculationService class (100% stdlib)
├── api/
│   ├── __init__.py
│   └── controllers.py      # FastAPI endpoint handlers (@router.post /dcf/calculate)
└── main.py                 # FastAPI application entry point (uvicorn server)

tests/
├── __init__.py
├── contract/
│   ├── __init__.py
│   └── test_dcf_openapi_compliance.py       # OpenAPI spec/request validation tests
├── integration/
│   ├── __init__.py
│   └── test_dcf_api_endpoints.py            # End-to-end API workflow tests
└── unit/
    ├── __init__.py
    ├── test_dcf_calculation_service.py      # Core calculation tests (TDD first)
    └── test_dcf_request_validation.py       # Pydantic model validation tests
```

**Layered Architecture**:
```
HTTP Request
    ↓
FastAPI (src/main.py)
    ↓
Controller Layer (src/api/controllers.py)  [HTTP adapter, request→response]
    ↓ calls
Service Layer (src/services/dcf_calculation_service.py)  [Business logic, 100% stdlib]
    ↓ uses
Model Layer (src/models/)  [Data validation & serialization]
    ↓
HTTP Response (JSON)
```

**Architecture Design**:
1. **Models** (`src/models/`): Pydantic request/response contracts
   - `DCFRequest`: Input validation (format, types, ranges, array bounds)
   - `DCFResponse`: Output serialization with 2-decimal rounding
   - `ErrorResponse`: Error payload structure
   
2. **Service Layer** (`src/services/dcf_calculation_service.py`): Business logic core
   - `DCFCalculationService` class with methods:
     - `calculate_dcf()`: Main orchestrator
     - `_validate_inputs()`: Business rule validation (WACC > g)
     - `_calculate_terminal_value()`: TV formula
     - `_calculate_pv_fcf()`: PV(FCF[t]) formula
     - `_calculate_pv_terminal_value()`: PV(TV) formula
   - Returns: `DCFResult` NamedTuple with calculation outputs
   - Zero external dependencies (100% stdlib: builtins, typing, collections.namedtuple)
   
3. **Controller Layer** (`src/api/controllers.py`): HTTP adapter
   - FastAPI route handler: `@router.post("/dcf/calculate")`
   - Exception handling: Catches service `ValueError` → HTTP 400 + error_code
   - Pydantic validation: Request deserialization (automatic HTTP 422 on failure)
   - Response marshalling: `DCFResult` → `DCFResponse` (with rounding applied)
   - Dependencies: FastAPI, Pydantic, DCFCalculationService
   
4. **Main** (`src/main.py`): FastAPI application setup
   - Create FastAPI app instance
   - Register routes/controllers
   - ASGI entry point for uvicorn

**Separation of Concerns**:
- **HTTP concerns** (routing, status codes, headers) → controller layer
- **Business logic** (calculations, validation) → service layer (100% stdlib, independently testable)
- **Data validation** (format, types) → Pydantic models (automatic, HTTP 422)
- **Business validation** (WACC > g) → service layer (raises ValueError → HTTP 400)

---

## Phase 0 Complete: Research ✅

**Deliverables**:
- ✅ `research.md`: 7 research questions resolved, technology stack documented
- ✅ No [NEEDS CLARIFICATION] markers remain
- ✅ Constitutional exceptions documented and justified
- ✅ Technology choices explained and alternatives considered
- ✅ Precision strategy documented (double-precision intermediate, 2-decimal output)

**Gate Status**: PASS (with documented exceptions for FastAPI/Pydantic per user specification)

---

## Phase 1 Complete: Design & Contracts ✅

**Deliverables**:
- ✅ `data-model.md`: Request/response schemas with all validation rules
- ✅ `contracts/openapi.yaml`: OpenAPI 3.0 specification with examples
- ✅ `quickstart.md`: Local setup guide with test scenarios
- ✅ Agent context updated: `.github/agents/copilot-instructions.md` generated with technology decisions

**Key Designs**:
1. **Single `/dcf/calculate` POST endpoint** accepting all inputs, returning unified response
2. **Two-layer validation**: Pydantic models (format) + service layer (business logic)
3. **HTTP 400 errors with error_code field** for programmatic error handling
4. **Core calculation module (100% stdlib)** separated from FastAPI for independent testing
5. **Double-precision intermediate calculations, 2-decimal output** rounding strategy

**Re-evaluation of Constitution Check**: PASS ✅
- FastAPI exception justified by user specification (explicit requirement)
- Core DCF math is 100% stdlib (maintains "no external libs for core" principle)
- Pydantic justified for request validation (critical for financial data integrity)
- All code will be tested via TDD (pytest), follow PEP 8, prioritize simplicity

---

## Ready for Phase 2: Task Generation

**Current Status**: ✅ READY FOR `/speckit.tasks` COMMAND

**Inputs to Tasks Phase**:
- Feature specification: `spec.md` (258 lines, complete and clarified)
- Implementation plan: `plan.md` (this file)
- Research findings: `research.md` (7 questions resolved)
- Data model: `data-model.md` (request/response schemas defined)
- API contract: `contracts/openapi.yaml` (OpenAPI 3.0 specification)
- Developer guide: `quickstart.md` (setup and testing instructions)

**Next Step**: Run `/speckit.tasks` to generate:
- Phase 2 task breakdown (by user story: P1, P2, P3)
- TDD-ordered tasks (tests first, then implementation)
- Dependencies between tasks
- Parallel execution opportunities

**Branch**: `001-dcf-analysis-api`  
**Spec Directory**: `specs/001-dcf-analysis-api/`
