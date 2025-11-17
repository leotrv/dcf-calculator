# Tasks: DCF Analysis API

Feature: DCF Analysis API

## Phase 1: Setup (project initialization)
- [ ] T001 Create repo directories and root package (`src/__init__.py`)
- [ ] T002 Create models package (`src/models/__init__.py`)
- [ ] T003 Create services package (`src/services/__init__.py`)
- [ ] T004 Create api package (`src/api/__init__.py`)
- [ ] T005 Create tests root and subdirectories (`tests/__init__.py`)
- [ ] T006 Create unit test package (`tests/unit/__init__.py`)
- [ ] T007 Create integration test package (`tests/integration/__init__.py`)
- [ ] T008 Create contract test package (`tests/contract/__init__.py`)

## Phase 2: Foundational (blocking prerequisites)
- [ ] T009 [P] Create `src/models/request.py` with `DCFRequest` Pydantic model and validators
- [ ] T010 [P] Create `src/models/response.py` with `DCFResponse` Pydantic model and output rounding helper
- [ ] T011 [P] Create `src/services/dcf_calculation_service.py` with `DCFCalculationService` class skeleton and `DCFResult` NamedTuple
- [ ] T012 Create `src/api/controllers.py` with FastAPI router and placeholder `/dcf/calculate` POST handler
- [ ] T013 Create `src/main.py` to instantiate FastAPI app and include the router from `src/api/controllers.py`
- [ ] T014 Create `pyproject.toml` or verify existing `pyproject.toml` contains FastAPI, uvicorn, pydantic, pytest entries (file: `pyproject.toml`)

## Phase 3: User Story Phases (priority order)

### Phase 3.1 - [US1] Calculate DCF Enterprise Value (P1)
- [ ] T015 [US1] Create unit tests for `DCfCalculationService.calculate_dcf` in `tests/unit/test_dcf_calculation_service.py` (tests: single-year, multi-year, g=0, precision checks)
- [ ] T016 [US1] Implement `calculate_dcf` orchestration in `src/services/dcf_calculation_service.py` (compute PV(FCF), TV if needed, PV(TV), EV)
- [ ] T017 [US1] Implement `_calculate_terminal_value`, `_calculate_pv_fcf`, `_calculate_pv_terminal_value` helpers in `src/services/dcf_calculation_service.py`
- [ ] T018 [US1] Run unit tests for `tests/unit/test_dcf_calculation_service.py` and fix failures
- [ ] T019 [US1] Create integration test for EV calculation in `tests/integration/test_dcf_api_endpoints.py` calling `/dcf/calculate` and asserting `enterprise_value` exists and is rounded to 2 decimals
- [ ] T020 [US1] Wire service into API controller: call `service.calculate_dcf` from `src/api/controllers.py` and map `DCFResult` → `DCFResponse`

### Phase 3.2 - [US2] Calculate Equity Value from Enterprise Value (P2)
- [ ] T021 [US2] Create unit tests for equity calculation in `tests/unit/test_dcf_calculation_service.py` (equity value = EV - net_debt)
- [ ] T022 [US2] Implement equity calculation in `src/services/dcf_calculation_service.py` (subtract net_debt, return in `DCFResult`)
- [ ] T023 [US2] Create integration test to assert `equity_value` in API response (`tests/integration/test_dcf_api_endpoints.py`)
- [ ] T024 [US2] Update `src/models/response.py` to ensure `equity_value` is rounded to 2 decimals in serialized output

### Phase 3.3 - [US3] Accept Explicit Terminal Value Input (P3)
- [ ] T025 [US3] Create unit tests for provided `terminal_value` behavior in `tests/unit/test_dcf_calculation_service.py` (verify provided TV is used as-is, including TV=0)
- [ ] T026 [US3] Implement `terminal_value` override behavior in `src/services/dcf_calculation_service.py`
- [ ] T027 [US3] Add integration test that posts a payload with explicit `terminal_value` and asserts correct EV/discounted_terminal_value handling in `tests/integration/test_dcf_api_endpoints.py`

## Final Phase: Polish & Cross-Cutting Concerns
- [ ] T028 Create `tests/contract/test_dcf_openapi_compliance.py` that validates `contracts/openapi.yaml` against implemented Pydantic models and endpoints
- [ ] T029 Add exception handler in `src/api/controllers.py` or `src/api/errors.py` to convert service `ValueError` into HTTP 400 responses with `error_code` and `details` (file: `src/api/controllers.py`)
- [ ] T030 Add CI job config for running `pytest` on push (file: `.github/workflows/ci.yml`)
- [ ] T031 Update `README.md` or `specs/001-dcf-analysis-api/quickstart.md` with commands to run tests and start the app (file: `README.md`)
- [ ] T032 Run all tests and fix any integration/contract failures (project root)

## Additional Tasks: CI & Simple Endpoint Tests
- [ ] T033 Create a minimal integration test `tests/integration/test_dcf_api_endpoints.py` that uses `TestClient` to POST to `/dcf/calculate` and assert presence of `enterprise_value` and `equity_value`
- [ ] T034 Ensure CI (`.github/workflows/ci.yml`) runs unit and integration tests (update job to run `pytest tests/unit tests/integration`)

## Dependencies
- User story completion order (blocking): [US1] → [US2] → [US3]
- Foundational tasks (`T009`-`T013`) MUST complete before story tasks that depend on them (e.g., controllers require service + models)

## Parallel Execution Examples
- [P] Tasks marked with `[P]` can be executed in parallel because they create independent files with no tight dependencies. For example: `T009`, `T010`, `T011` (models and service skeletons) are parallelizable initial work.
- [P] Unit test file creation and service skeletons can be created in parallel (e.g., `T015` authoring tests while `T011` implements skeletons), but TDD flow requires tests run before final implementation verification.

## Implementation Strategy (MVP first)
- MVP scope: deliver `US1` (Enterprise Value calculation) only. That includes `T015`-`T020` plus foundational setup tasks `T001`-`T013` and CI/test harness tasks `T028`-`T032` as needed.
- Incremental delivery: implement and pass unit tests for service layer first (pure Python), then add API wiring and integration tests.
- Testing approach: TDD — write unit tests in `tests/unit/` first, implement service methods, run tests, then write integration tests and fix controller wiring.

## Implementation Notes
- All task descriptions include explicit file paths; implementers should create or edit those files accordingly.
- Every story-phase is independently testable: service layer unit tests do not require FastAPI.

---

Generated file: `specs/001-dcf-analysis-api/tasks.md`
