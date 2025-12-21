# Implementation Tasks: Auto-DCF Valuation Endpoint

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)  
**Branch**: `002-auto-dcf-valuation` | **Created**: December 21, 2025

---

## Overview

This tasks list provides a complete, executable breakdown for implementing the auto-DCF endpoint. Each task is specific enough for an LLM to complete independently. Tasks follow TDD (Red-Green-Refactor) discipline organized by user story.

**Task Count**: 28 total  
**Phases**: 5 (Setup + Foundational + 2 User Stories + Polish)  

---

## Dependency Graph

```
Phase 1: Setup (Infrastructure)
    │
    ▼
Phase 2: Foundational (Models & Service Base)
    │
    ├──────────────────────────┬──────────────────────────┐
    │                          │                          │
    ▼                          ▼                          ▼
US1: Auto Valuation    US2: Error Handling    (parallel implementation)
    │                          │
    └──────────────────────────┴──────────────────────────┘
                               │
                               ▼
Phase 5: Polish & Cross-Cutting Concerns
```

**Parallel Execution**: US1 and US2 can be implemented in parallel (different code paths, no shared state changes until final integration).

**MVP Scope**: Complete US1 (P1) for minimum viable product. US2 (P2) adds robustness.

---

## Phase 1: Setup & Project Initialization

### Create Test Structure and Base Configuration

- [ ] T001 Create integration test file `tests/integration/test_auto_dcf_endpoints.py` with test class `TestAutoDCFEndpoint`
- [ ] T002 Create unit test file `tests/unit/test_yfinance_service.py` with test class `TestYFinanceService`
- [ ] T003 Create fixture file `tests/conftest.py` with mock yfinance data fixtures (mock Ticker, quarterly financials, balance sheet)
- [ ] T004 Verify pytest is configured to discover tests in `tests/` directory; verify `pytest.ini` or `pyproject.toml` test config

### Create Model Scaffolding

- [ ] T005 Create Pydantic request model `src/models/request.py::AutoDCFRequest` with single `ticker` field (string, validation)

---

## Phase 2: Foundational Prerequisites (Blocking for All User Stories)

### Create YFinance Service Base

- [ ] T006 Create service file `src/services/yfinance_service.py` with class `YFinanceService` (empty methods)
- [ ] T007 [P] Create method stub `YFinanceService.extract_dcf_inputs(ticker: str) -> Dict` placeholder
- [ ] T008 [P] Create validation method `YFinanceService.validate_ticker(ticker: str) -> bool` (non-empty, alphanumeric)

### Endpoint Registration

- [ ] T009 Update `src/api/controllers.py` to add route `@router.post('/auto-calculate', response_model=DCFResponse)` with placeholder implementation

---

## Phase 3: User Story 1 - Automatic DCF Valuation via Stock Ticker (P1)

### 3.1 Unit Tests (TDD Red Phase)

- [ ] T010 [US1] Write failing unit test: `test_extract_dcf_inputs_valid_ticker_returns_dict` - expects valid yfinance data extraction for AAPL
- [ ] T011 [US1] Write failing unit test: `test_extract_dcf_inputs_calculates_fcf_correctly` - expects FCF = Operating CF - CapEx
- [ ] T012 [US1] Write failing unit test: `test_extract_dcf_inputs_calculates_fcf_5yr_cagr` - expects CAGR calculation from quarterly history
- [ ] T013 [US1] Write failing unit test: `test_extract_dcf_inputs_estimates_wacc_via_capm` - expects WACC = risk_free + (beta × market_premium)
- [ ] T014 [US1] Write failing unit test: `test_extract_dcf_inputs_applies_growth_rate_cap` - expects FCF growth capped at min(2x CAGR, 20%)
- [ ] T015 [US1] Write failing unit test: `test_convert_yfinance_to_dcf_request` - expects populated DCFRequest with correct field mapping
- [ ] T016 [US1] Write failing unit test: `test_auto_dcf_endpoint_returns_dcf_response` - expects endpoint returns DCFResponse with correct structure

### 3.2 Service Implementation (TDD Green & Refactor)

- [ ] T017 [US1] Implement `YFinanceService.fetch_yfinance_ticker(ticker: str)` - fetch Ticker object with 10s timeout, return or raise validation error
- [ ] T018 [US1] Implement `YFinanceService.extract_quarterly_cashflow(ticker)` - extract operating CF, CapEx; calculate FCF for each quarter
- [ ] T019 [US1] Implement `YFinanceService.extract_quarterly_balance_sheet(ticker)` - extract total debt, cash, shares outstanding (latest)
- [ ] T020 [US1] Implement `YFinanceService.calculate_fcf_growth_rate(fcf_history: List[float]) -> float` - calculate 5-year CAGR, cap at 2x or 20%
- [ ] T021 [US1] Implement `YFinanceService.estimate_discount_rate(ticker) -> float` - fetch beta, apply CAPM (risk_free=4.5%, market_premium=6%), return WACC
- [ ] T022 [US1] Implement `YFinanceService.extract_dcf_inputs(ticker: str) -> DCFRequest` - orchestrate all extraction methods, return populated DCFRequest
- [ ] T023 [US1] Implement endpoint logic: `POST /dcf/auto-calculate` calls `YFinanceService.extract_dcf_inputs()`, invokes `DCFCalculationService.calculate_dcf()`, returns `DCFResponse`
- [ ] T024 [US1] [P] Write integration test: `test_auto_dcf_endpoint_valid_ticker_aapl` - POST with valid ticker, assert 200 response with DCFResponse structure

### 3.3 Validation & Edge Cases (US1)

- [ ] T025 [US1] Handle missing beta: Use default 1.0 if unavailable; unit test `test_estimate_discount_rate_missing_beta_uses_default`
- [ ] T026 [US1] Handle negative FCF: Flag for user awareness (logging); unit test `test_extract_dcf_inputs_negative_fcf_logged`
- [ ] T027 [US1] Pass existing endpoint tests: Run `pytest tests/integration/test_dcf_api_endpoints.py::TestAutoDCFEndpoint::test_auto_dcf_endpoint_valid_ticker_aapl` - must pass

---

## Phase 4: User Story 2 - Handling Invalid or Unsupported Stock Tickers (P2)

### 4.1 Error Validation Tests (TDD Red Phase)

- [ ] T028 [P] [US2] Write failing unit test: `test_validate_ticker_empty_string_raises_error` - expect `ValidationError` with code `INVALID_TICKER`
- [ ] T029 [P] [US2] Write failing unit test: `test_validate_ticker_invalid_chars_raises_error` - expect error for non-alphabetic characters
- [ ] T030 [P] [US2] Write failing unit test: `test_extract_dcf_inputs_ticker_not_found_raises_error` - expect `ValidationError` with code `TICKER_NOT_FOUND`
- [ ] T031 [P] [US2] Write failing unit test: `test_extract_dcf_inputs_insufficient_history_raises_error` - expect error when < 1 year (4 quarters) of data
- [ ] T032 [P] [US2] Write failing integration test: `test_auto_dcf_endpoint_invalid_ticker_returns_400` - POST with invalid ticker, assert 400 response with error code
- [ ] T033 [P] [US2] Write failing integration test: `test_auto_dcf_endpoint_insufficient_history_returns_400` - POST with newly IPO'd stock, assert 400 with error message

### 4.2 Error Handling Implementation (TDD Green & Refactor)

- [ ] T034 [P] [US2] Implement validation layer in `YFinanceService._validate_yfinance_data(ticker, financials)` - check ticker validity, minimum history, required fields
- [ ] T035 [P] [US2] Add error codes to `YFinanceService`: `TICKER_NOT_FOUND`, `INSUFFICIENT_HISTORY`, `INVALID_TICKER`, `MISSING_FIELD`
- [ ] T036 [P] [US2] Update endpoint error handling: catch `ValidationError` exceptions, return 400 with `error_code` and `error` message (consistent with existing `/calculate` endpoint)
- [ ] T037 [P] [US2] Add network timeout handling: wrap yfinance calls in try-except for `Timeout` and `ConnectionError`; raise `ValidationError` with code `YFINANCE_ERROR`
- [ ] T038 [P] [US2] Write integration test: `test_auto_dcf_endpoint_network_error_returns_503` - mock yfinance timeout, assert 503 response

### 4.3 Acceptance Criteria Validation (US2)

- [ ] T039 [US2] Pass all US2 integration tests: Run `pytest tests/integration/test_auto_dcf_endpoints.py::TestAutoDCFEndpoint -k "error"` - all error scenarios pass
- [ ] T040 [US2] Verify error responses match spec: error message includes error code prefix (e.g., "TICKER_NOT_FOUND: ..."), `error_code` field present

---

## Phase 5: Polish & Cross-Cutting Concerns

### Integration & Consistency

- [ ] T041 Verify endpoint response matches `DCFResponse` model exactly (same field names, types, precision as manual endpoint)
- [ ] T042 Run full integration test suite: `pytest tests/integration/test_dcf_api_endpoints.py -v` - all tests pass (both manual and auto endpoints)
- [ ] T043 Run full unit test suite: `pytest tests/unit/ -v` - all tests pass, coverage > 90% for new code

### Documentation & Handoff

- [ ] T044 Update [quickstart.md](quickstart.md) with actual endpoint response examples (copy from test fixtures)
- [ ] T045 Add docstrings to `YFinanceService` and endpoint controller following project style
- [ ] T046 Document assumptions in code comments: default risk-free rate (4.5%), market premium (6%), terminal growth (2.5%), growth cap (20%)

### Performance & Monitoring

- [ ] T047 Verify endpoint performance: response time < 5 seconds for major-cap stocks; unit test with mock data proves calculation time negligible
- [ ] T048 Verify error responses are fast: invalid ticker validation should fail in < 500ms (no unnecessary yfinance calls)

---

## Implementation Strategy

### MVP Scope (Core Value)

**Minimum viable product = User Story 1 (P1) only**

To deliver a working feature quickly:
1. **Complete Phase 1**: Setup (4 tasks)
2. **Complete Phase 2**: Foundational (4 tasks)
3. **Complete Phase 3**: US1 implementation (18 tasks)
4. **Skip Phase 4**: US2 error handling (for later)
5. **Light Phase 5**: Basic integration tests only

**Time estimate**: 4-6 hours for experienced Python/FastAPI developer

### Full Feature (Recommended)

**Complete feature = User Story 1 (P1) + User Story 2 (P2)**

1. **Complete all phases** (48 tasks)
2. **Parallel execution**: Tasks T028-T040 (US2) can run in parallel with T024-T027 (US1 validation)
3. **Benefits**: Complete error handling, robust user experience, production-ready

**Time estimate**: 6-8 hours for experienced developer

### Incremental Rollout

1. **Sprint 1** (Day 1): Phases 1-2 + T010-T024 (US1 core)
2. **Sprint 2** (Day 2): T025-T027 (US1 edge cases) + T028-T040 (US2)
3. **Sprint 3** (Day 3): Phase 5 polish, documentation, testing

---

## Testing Checklist

### Unit Test Coverage

- [ ] `test_yfinance_service.py` - 12 tests covering all parameter extraction logic
- [ ] All error codes testable as unique exception raises
- [ ] Mock yfinance data provided in `conftest.py` (no external API calls in CI)

### Integration Test Coverage

- [ ] Valid ticker (AAPL): Returns 200 with DCFResponse
- [ ] Invalid ticker (INVALID123): Returns 400 with error code
- [ ] Insufficient history: Returns 400 with error code
- [ ] Network timeout: Returns 503 with error code

### Cross-Endpoint Consistency

- [ ] `/dcf/auto-calculate` response format = `/dcf/calculate` response format
- [ ] Both endpoints accept input that passes validation
- [ ] Both endpoints return same error response structure

### Performance Validation

- [ ] Endpoint latency < 5 seconds (major-cap stocks)
- [ ] Calculation time < 100ms (optimization focus in Phase 5)
- [ ] Memory usage stable (no leaks in repeated calls)

---

## Success Criteria Verification

| Success Criterion | Verified By | Status |
|------------------|------------|--------|
| Endpoint accepts ticker, returns DCF valuation | T024, T025 (integration tests) | 🟢 |
| Output matches manual endpoint format | T041, T042 | 🟢 |
| System derives all DCF parameters from yfinance | T017-T022 (unit tests) | 🟢 |
| Error handling for invalid/insufficient tickers | T028-T040 (error tests) | 🟢 |
| Response time < 5 seconds | T047 (performance test) | 🟢 |

---

## File Manifest

**Files to Create**:
- `src/services/yfinance_service.py` (350-400 LOC)
- `tests/unit/test_yfinance_service.py` (300-400 LOC)
- `tests/integration/test_auto_dcf_endpoints.py` (200-300 LOC)
- `tests/conftest.py` (100-150 LOC, shared fixtures)

**Files to Modify**:
- `src/models/request.py` - Add `AutoDCFRequest` class (15-20 LOC)
- `src/api/controllers.py` - Add `/auto-calculate` route (25-30 LOC)

**Files to Update**:
- [quickstart.md](quickstart.md) - Add actual examples
- [plan.md](plan.md) - Mark completion

---

## Quality Gates

✅ **Before merging to main**:
1. All 48 tasks completed (or MVP 26 tasks for P1 only)
2. All tests pass (`pytest` with 90%+ coverage for new code)
3. Code follows project style (PEP 8, consistent with existing code)
4. Documentation complete (docstrings, updated quickstart)
5. Constitution compliance verified (no violations)

---

## Notes

- **TDD Discipline**: Each task includes explicit test-first instruction. Write failing test, then implement.
- **Parallelization**: T007-T008, T028-T040, and other tasks marked `[P]` can run in parallel.
- **No External Dependencies**: All implementation uses Python stdlib + existing FastAPI/Pydantic/yfinance.
- **Backward Compatibility**: No changes to existing endpoints; only additions.
- **Error Codes**: Use consistent error code prefixes across all error paths (TICKER_NOT_FOUND, INSUFFICIENT_HISTORY, etc.).
