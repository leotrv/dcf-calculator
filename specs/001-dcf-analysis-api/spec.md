# Feature Specification: DCF Analysis API

**Feature Branch**: `001-dcf-analysis-api`  
**Created**: 2025-11-16  
**Status**: Draft  
**Input**: FastAPI project providing DCF analysis based on five key financial variables (FCF, WACC, g, TV, NetDebt)

## Clarifications

### Session 2025-11-16

- Q: What is the API endpoint design? → A: Single `/dcf/calculate` endpoint accepting all inputs and returning both EV and Equity Value
- Q: When should rounding to 2 decimals occur? → A: Only on final output fields; maintain double-precision throughout intermediate calculations
- Q: How should system handle explicit terminal_value=0 input? → A: Accept as valid and use in calculation (honors user intent)
- Q: What is the enforcement for forecast period length constraint? → A: Hard limit of 30 years; reject with HTTP 400 if FCF array > 30 elements
- Q: Which HTTP status code for validation failures? → A: HTTP 400 for all validation errors with error_code field for programmatic distinction

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate DCF Enterprise Value (Priority: P1)

A financial analyst needs to calculate the Enterprise Value of a company using the Discounted Cash Flow method. The analyst provides a series of annual Free Cash Flow projections (e.g., 5 years), along with the Weighted Average Cost of Capital (WACC) and a terminal growth rate. The system computes the present value of each projected cash flow and the terminal value, then sums them to determine the Enterprise Value.

**Why this priority**: Enterprise Value is the fundamental output of DCF analysis. All other calculations depend on it. This is the core value proposition of the system.

**Independent Test**: Can be fully tested by providing FCF array, WACC, and g; the system returns a calculated EV without requiring any other features. This is a complete, testable analysis.

**Acceptance Scenarios**:

1. **Given** FCF array [1000, 1100, 1200, 1300, 1400], WACC=0.10, g=0.03, **When** user requests DCF analysis, **Then** system returns Enterprise Value calculated as the sum of discounted FCFs plus discounted terminal value
2. **Given** FCF array with single year [1000], WACC=0.08, g=0.02, **When** user requests DCF analysis, **Then** system returns Enterprise Value with single-year discount plus terminal value
3. **Given** multiple valid FCF projections with varying lengths, **When** user submits each, **Then** system correctly calculates EV for each scenario independently

---

### User Story 2 - Calculate Equity Value from Enterprise Value (Priority: P2)

A financial analyst has calculated the Enterprise Value but needs to convert it to Equity Value by accounting for the company's net debt position. The system accepts the calculated Enterprise Value and NetDebt as inputs, then applies the formula: Equity Value = EV - NetDebt. This gives the true value available to equity holders.

**Why this priority**: Equity Value is the immediate next step after EV calculation. Required for equity analysts and equity value assessments. Completes the DCF valuation chain.

**Independent Test**: Given an EV and NetDebt value, system returns Equity Value. Can be tested independently once EV is calculated. Directly observable output.

**Acceptance Scenarios**:

1. **Given** Enterprise Value = 10,000,000, NetDebt = 2,000,000, **When** user requests equity value calculation, **Then** system returns Equity Value = 8,000,000
2. **Given** Enterprise Value = 5,000,000, NetDebt = 0 (no debt), **When** user requests equity value, **Then** system returns Equity Value = 5,000,000 (identical to EV)
3. **Given** Enterprise Value = 3,000,000, NetDebt = 4,000,000 (negative equity situation), **When** user requests equity value, **Then** system returns Equity Value = -1,000,000

---

### User Story 3 - Accept Explicit Terminal Value Input (Priority: P3)

Some financial analysts may already have calculated the Terminal Value separately using their own methodology or tools, and want to provide it as a direct input rather than having the system calculate it from FCF, WACC, and g. The system accepts an optional Terminal Value parameter; if provided, it uses the provided value; if not provided, it calculates TV = (FCF[-1] × (1 + g)) / (WACC - g).

**Why this priority**: Provides flexibility for power users and integration scenarios. Extends the system to handle pre-calculated terminal values. Lower priority as the default calculation suffices for most users.

**Independent Test**: Given a Terminal Value input, system uses it in EV calculation without recalculating. Can be tested by comparing results when TV is provided vs. calculated.

**Acceptance Scenarios**:

1. **Given** FCF array, WACC, g, and explicit TV value, **When** user provides TV, **Then** system uses provided TV instead of calculating it
2. **Given** same inputs with and without explicit TV, **When** both requests are made, **Then** results match only when TV is correctly calculated from implicit values
3. **Given** FCF array, WACC, and g but TV explicitly set to 0, **When** user provides TV=0, **Then** system honors the zero value in calculation

---

### Edge Cases

- What happens when WACC is less than or equal to g? (Terminal growth rate must be strictly less than discount rate; system MUST reject with clear error)
- What happens when FCF array is empty? (System MUST reject; at least one FCF value required)
- What happens when FCF array contains negative values? (System MUST reject; all FCFs must be non-negative per assumption)
- What happens when WACC or g are provided as percentages (5) vs. decimals (0.05)? (Input format must specify one format; mixed formats are ambiguous)
- What happens when NetDebt is negative (company has net cash)? (Valid scenario; negative debt reduces equity value correctly)
- What happens when input precision exceeds system limits? (Specify rounding/precision handling in Success Criteria)

## Requirements *(mandatory)*

### Functional Requirements

#### API Endpoint

- **FR-001**: System MUST expose a single HTTP POST endpoint at `/dcf/calculate` that accepts DCF calculation requests and returns valuation results. The endpoint processes all inputs (FCF, WACC, g, NetDebt, optional terminal_value) in a single request and returns both Enterprise Value and Equity Value in a unified response.

#### Input Format & Variables

- **FR-002**: System MUST accept Free Cash Flows (FCF) as an array of numeric values representing projected annual cash flows for a multi-year forecast period. Input format: `fcf` (JSON array of numbers, e.g., `[1000, 1100, 1200, 1300, 1400]`)

- **FR-003**: System MUST accept Weighted Average Cost of Capital (WACC) as a decimal numeric value. Input format: `wacc` (single number as decimal, e.g., `0.10` for 10%, NOT `10`). WACC represents the discount rate applied to future cash flows.

- **FR-004**: System MUST accept terminal growth rate (g) as a decimal numeric value. Input format: `g` (single number as decimal, e.g., `0.03` for 3%, NOT `3`). Represents perpetual growth rate beyond the forecast period.

- **FR-005**: System MUST accept Net Debt as a numeric value (can be positive, zero, or negative). Input format: `net_debt` (single number, e.g., `2000000`). Net Debt = Total Debt - Cash & Equivalents. Positive values represent net debt; negative values represent net cash.

- **FR-006**: System MUST optionally accept pre-calculated Terminal Value as a numeric value. Input format: `terminal_value` (optional, single number). If provided, system uses this value; if omitted, system calculates it from FCF, WACC, and g. If explicitly set to 0, system honors the zero value in calculation.

#### Calculation Order & Formulas

- **FR-007**: System MUST calculate Terminal Value using Gordon Growth Model if not explicitly provided. Formula:
  ```
  TV = (FCF[n] × (1 + g)) / (WACC - g)
  ```
  Where:
  - FCF[n] = the final (last) Free Cash Flow in the forecast array
  - g = terminal growth rate (decimal)
  - WACC = Weighted Average Cost of Capital (decimal)

- **FR-008**: System MUST calculate the Present Value of each forecasted Free Cash Flow. Formula for each FCF:
  ```
  PV(FCF[t]) = FCF[t] / (1 + WACC)^t
  ```
  Where:
  - FCF[t] = Free Cash Flow in year t
  - t = year number (1-indexed: year 1, 2, 3, ..., n)
  - WACC = discount rate (decimal)

- **FR-009**: System MUST calculate the Present Value of Terminal Value. Formula:
  ```
  PV(TV) = TV / (1 + WACC)^n
  ```
  Where:
  - TV = Terminal Value (calculated per FR-007 or provided per FR-006)
  - n = number of years in the forecast period (length of FCF array)
  - WACC = discount rate (decimal)

- **FR-010**: System MUST calculate Enterprise Value as the sum of all discounted cash flows and discounted terminal value. Formula:
  ```
  EV = Σ(PV(FCF[t])) + PV(TV)
       = PV(FCF[1]) + PV(FCF[2]) + ... + PV(FCF[n]) + PV(TV)
  ```
  Where all terms are calculated per FR-008 and FR-009.

- **FR-011**: System MUST calculate Equity Value by subtracting Net Debt from Enterprise Value. Formula:
  ```
  Equity Value = EV - NetDebt
  ```
  Where:
  - EV = Enterprise Value (from FR-010)
  - NetDebt = Net Debt input (per FR-005)

- **FR-012**: System MUST maintain double-precision floating-point accuracy throughout all intermediate calculations (per IEEE 754). Rounding to 2 decimal places is applied ONLY to final output fields (enterprise_value, equity_value, discounted_terminal_value), not during intermediate calculation steps. This preserves precision and achieves the 0.01% tolerance target.

#### Validation & Constraints

- **FR-013**: System MUST validate that FCF array length is between 1 and 30 elements (inclusive). If array length < 1 or > 30, system MUST reject with HTTP 400 error: "Forecast period must be between 1 and 30 years. Provided: {n} years"

- **FR-014**: System MUST validate that WACC is strictly greater than terminal growth rate (g). If WACC ≤ g, system MUST reject the request with HTTP 400 error message: "WACC must be strictly greater than terminal growth rate g. Current: WACC={wacc}, g={g}"
- **FR-015**: (Consolidated with FR-013) System MUST validate that FCF array length is between 1 and 30 elements (inclusive). If array length < 1 or > 30, system MUST reject with HTTP 400 error: "Forecast period must be between 1 and 30 years. Provided: {n} years"

- **FR-016**: System MUST validate that all FCF values are non-negative (≥ 0). If any FCF < 0, system MUST reject with HTTP 400 error: "All Free Cash Flow values must be non-negative. Found negative value: FCF[{index}]={value}"

- **FR-017**: System MUST validate that WACC is a valid positive decimal (> 0). If invalid, system MUST reject with HTTP 400 error: "WACC must be a positive decimal value greater than 0. Provided: {wacc}"

- **FR-018**: System MUST validate that terminal growth rate (g) is a valid non-negative decimal (≥ 0). If invalid, system MUST reject with HTTP 400 error: "Terminal growth rate must be a non-negative decimal. Provided: {g}"

- **FR-019**: System MUST validate that NetDebt is a valid numeric value (positive, zero, or negative). Decimal precision: at least 2 decimal places for currency values.

#### HTTP Response Codes & Error Format

- **FR-020**: System MUST return HTTP 400 (Bad Request) for all input validation failures. Each error response MUST include an `error_code` field for programmatic error handling. Error codes: `WACC_LE_G`, `EMPTY_FCF_ARRAY`, `NEGATIVE_FCF_VALUE`, `INVALID_WACC`, `INVALID_G`, `FORECAST_PERIOD_OUT_OF_RANGE`, `INVALID_NETDEBT`

#### Output Format

- **FR-021**: System MUST return calculation results in JSON format with the following fields:
  ```json
  {
    "enterprise_value": <number>,
    "equity_value": <number>,
    "terminal_value": <number>,
    "discounted_cash_flows": [<number>, <number>, ...],
    "discounted_terminal_value": <number>
  }
  ```

- **FR-022**: System MUST round all monetary outputs (enterprise_value, equity_value, terminal_value, discounted_terminal_value, and each element in discounted_cash_flows array) to exactly 2 decimal places (standard currency precision).

- **FR-023**: System MUST include detailed error responses for validation failures in JSON format with HTTP 400 status:
  ```json
  {
    "error": <string>,
    "error_code": <string>,
    "details": <object (optional)>
  }
  ```

### Key Entities

- **DCF Request**: Input parameters (fcf array, wacc, g, net_debt, optional terminal_value) representing a single valuation scenario
- **DCF Response**: Output object containing calculated values (enterprise_value, equity_value, terminal_value, discounted_cash_flows, discounted_terminal_value)
- **Valuation Scenario**: A unique combination of financial inputs that produces a specific EV and Equity Value for analysis

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System correctly calculates Enterprise Value for a baseline 5-year DCF scenario within 0.01% precision compared to manual calculation using the published formulas (tolerance for floating-point arithmetic)

- **SC-002**: System correctly calculates Equity Value (EV - NetDebt) with same 0.01% precision, verified against manual calculation

- **SC-003**: System rejects invalid inputs (WACC ≤ g, empty FCF array, negative FCF values) with appropriate HTTP 400 error and descriptive error message within 100% of test cases

- **SC-004**: System validates WACC > g constraint and returns error message citing both values in every validation failure case
- **SC-005**: System processes DCF calculation request and returns complete JSON response (with all 5 required fields: enterprise_value, equity_value, terminal_value, discounted_cash_flows, discounted_terminal_value). Performance objectives are deferred to a dedicated benchmark plan and are not a blocking requirement for Phase 2.

- **SC-006**: System handles edge cases correctly:
  - Single-year forecast (1 FCF value): calculates EV and returns valid response
  - Zero terminal growth rate (g=0): calculates terminal value and EV correctly
  - Company with net cash position (negative NetDebt): calculates correct Equity Value
  - Large cash flow values (> $1 billion): maintains precision to 2 decimal places

- **SC-007**: System output JSON response is valid and parseable by standard JSON parsers in 100% of successful responses

- **SC-008**: System monetary values are rounded to exactly 2 decimal places in all outputs (no ambiguity in currency representation)

- **SC-009**: System correctly implements the order of operations: Calculate TV (if needed) → Calculate PV of FCFs → Calculate PV of TV → Sum for EV → Calculate Equity Value from EV and NetDebt

## Assumptions & Constraints

### Assumptions

1. **Positive Cash Flows**: All Free Cash Flow values are non-negative. Negative FCF values are invalid and indicate incorrect input data.

2. **Stable Terminal Growth**: The terminal growth rate (g) represents a sustainable, perpetual growth rate beyond the forecast period. Users are responsible for selecting realistic g values (typically 0-3% range for developed economies).

3. **WACC is Stable**: The Weighted Average Cost of Capital remains constant across the entire forecast period and terminal period. Year-to-year variation is not modeled.

4. **Standard Discounting Convention**: Discounting follows standard financial practice where year 1 FCF is discounted by (1+WACC)^1, year 2 by (1+WACC)^2, etc. Terminal Value is discounted by (1+WACC)^n where n is the forecast period length.

5. **Input Format Consistency**: WACC and g are always provided as decimals (0.10 for 10%), never as percentages (10). The system does not attempt to auto-detect or convert percentage inputs.

6. **No Tax Adjustments**: The FCF values provided are assumed to already incorporate any necessary tax adjustments. The system does not perform tax calculations.

7. **No Corporate Actions**: The system does not model stock splits, dividends, share buybacks, or other corporate actions that might affect valuation between calculation date and future periods.

### Constraints

1. **API Endpoint**: Single POST endpoint at `/dcf/calculate` processes all inputs and returns unified response with both EV and Equity Value.

2. **Forecast Period Length**: FCF array MUST contain 1 to 30 annual projections (inclusive). Requests with array length outside this range are rejected with HTTP 400 error. Longer forecast periods are rejected due to reduced reliability of distant projections.

3. **Numeric Precision**: All calculations maintain double-precision floating-point accuracy (IEEE 754) throughout intermediate steps. Final output values rounded to exactly 2 decimal places for currency representation.

4. **Rounding Strategy**: Rounding is applied ONLY to final output fields (enterprise_value, equity_value, discounted_terminal_value, and discounted_cash_flows array elements). All intermediate calculations preserve full double-precision to maintain the 0.01% tolerance target.

5. **WACC > g Requirement**: Mathematically enforced. Terminal Value formula becomes undefined or negative if WACC ≤ g. This is a hard validation gate; no workarounds or exceptions. Rejection returns HTTP 400 with error_code WACC_LE_G.

6. **Terminal Value Override**: If terminal_value is explicitly provided (including 0), system uses that value in calculation without modification. Zero is a valid input value and is honored in the EV calculation.

7. **HTTP Error Handling**: All validation failures return HTTP 400 (Bad Request) with error_code field for programmatic distinction. Error codes enable client logic to handle specific failure scenarios without string parsing.

8. **No Interim Cash Distributions**: System assumes all calculated cash flows are available for reinvestment or return to equity holders. Interim distributions, management fees, or other cash outflows between forecast periods are not modeled.

9. **API Response Format**: All responses (success or error) are JSON format. No XML, CSV, or other formats are supported.

10. **No Historical Data**: System is designed for forward-looking DCF analysis. Historical financial data, guidance revisions, or scenario comparison features are out of scope.
