# Implementation Plan: Auto-DCF Valuation Endpoint

**Branch**: `002-auto-dcf-valuation` | **Date**: December 21, 2025 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-auto-dcf-valuation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The feature adds a new HTTP endpoint that accepts a stock ticker symbol, automatically fetches financial data from yfinance, derives all required DCF calculation parameters, and returns a valuation result in the same format as the existing manual `/calculate` endpoint. This streamlines the DCF analysis workflow by eliminating manual data gathering.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI, yfinance (already installed), Pydantic  
**Storage**: N/A (stateless endpoint)  
**Testing**: pytest (existing test structure in place)  
**Target Platform**: Linux server (existing FastAPI app)  
**Project Type**: Single Python project (existing structure: src/api, src/services, src/models)  
**Performance Goals**: Return valuation in under 5 seconds for major-cap stocks  
**Constraints**: Endpoint must handle network timeouts gracefully; requires minimum 1 year historical data  
**Scale/Scope**: Single endpoint addition; integrates with existing DCFCalculationService

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Evaluation** ✅ PASSED

✅ **Python Native First**: The feature uses Python standard library for core logic (parameter derivation, validation). yfinance is an existing approved dependency already in pyproject.toml.

✅ **Minimal Dependencies**: No new dependencies required; yfinance already approved and installed.

✅ **FastAPI Endpoint Focus**: Feature adds a new HTTP endpoint (`/dcf/auto-calculate`) to the existing FastAPI router—aligns with project architecture.

✅ **Test-Driven Development**: Implementation will follow TDD workflow with unit tests for parameter extraction logic and integration tests for the endpoint.

✅ **Simplicity and Readability**: New code will be straightforward service method + controller endpoint, following existing patterns in the codebase (models, services, controllers).

**Additional Constraints Compliance**:
- ✅ No external libraries required for core; yfinance is pre-approved for data fetching
- ✅ Code will be cross-platform compatible (no platform-specific logic)

**Post-Phase-1 Re-evaluation** ✅ PASSED

After design phase completion:
- ✅ Data model (ExtractedYFinanceData → DCFRequest) maintains simplicity and clarity
- ✅ All error codes and validation rules adhere to TDD principle (testable conditions)
- ✅ Endpoint design (POST /dcf/auto-calculate) consistent with existing `/dcf/calculate`
- ✅ No violations of principles discovered during design; all gates remain satisfied

## Project Structure

### Documentation (this feature)

```text
specs/002-auto-dcf-valuation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

**Selected Structure**: Single Python project (existing)

```text
src/
├── api/
│   ├── __init__.py
│   └── controllers.py          # Existing: POST /dcf/calculate
                                # New: POST /dcf/auto-dcf (or /calculate-auto)
├── models/
│   ├── request.py              # DCFRequest (existing, will be reused)
│   └── response.py             # DCFResponse (existing, will be reused)
└── services/
    ├── dcf_calculation_service.py    # Existing: DCF calculation logic
    └── yfinance_service.py           # NEW: Data extraction from yfinance

tests/
├── unit/
│   └── test_yfinance_service.py      # NEW: Parameter extraction tests
└── integration/
    └── test_dcf_api_endpoints.py     # Existing: will add auto-dcf endpoint tests
```

**Structure Decision**: The feature extends the existing single-project structure. A new `yfinance_service.py` will handle yfinance data fetching and parameter derivation (single responsibility). The existing `controllers.py` will add a new POST endpoint that calls this service. No changes to existing models or calculation logic.

## Complexity Tracking

**No Constitution violations** - all principles are satisfied without trade-offs or special justifications required.
