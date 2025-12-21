# Feature Specification: Auto-DCF Valuation Endpoint

**Feature Branch**: `002-auto-dcf-valuation`  
**Created**: December 21, 2025  
**Status**: Draft  
**Input**: User description: "Add yfinance-based stock data endpoint for automatic DCF calculation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic DCF Valuation via Stock Ticker (Priority: P1)

An analyst wants to quickly value a company by providing only its stock ticker symbol. The system automatically fetches financial data from yfinance and calculates the DCF valuation without requiring manual data entry.

**Why this priority**: This is the core value proposition of the feature. It eliminates the need for manual data gathering and allows users to value companies with a single endpoint call.

**Independent Test**: Can be fully tested by calling the endpoint with a valid stock ticker and verifying that it returns a DCF valuation response in the same format as the manual `/calculate` endpoint.

**Acceptance Scenarios**:

1. **Given** a user wants to value a company, **When** they call the endpoint with a valid stock ticker (e.g., "AAPL"), **Then** the system returns an enterprise value, equity value, and value per share in the same format as the manual endpoint.

2. **Given** a valid stock ticker is provided, **When** the endpoint fetches data, **Then** all required DCF input parameters (FCF, growth rate, discount rate, etc.) are populated from yfinance data.

3. **Given** valid financial data is available from yfinance, **When** calculations are performed, **Then** the DCF calculation uses the standard formula consistent with the existing `/calculate` endpoint.

---

### User Story 2 - Handling Invalid or Unsupported Stock Tickers (Priority: P2)

Users may provide invalid or delisted stock tickers that yfinance cannot find. The system should respond with a clear error indicating why the valuation could not be calculated.

**Why this priority**: Error handling is critical for user experience, but secondary to the happy path functionality.

**Independent Test**: Can be fully tested by providing invalid tickers and verifying appropriate error responses.

**Acceptance Scenarios**:

1. **Given** an invalid stock ticker (e.g., "INVALID123"), **When** the endpoint attempts to fetch data, **Then** a clear error is returned explaining the ticker is not found.

2. **Given** a stock with less than 1 year of historical data, **When** yfinance cannot provide adequate data, **Then** the user receives an error indicating insufficient data for valuation.

---



### Edge Cases

- What happens when yfinance data is temporarily unavailable (network error)?
- How does the system handle newly IPO'd companies with limited historical data?
- What should occur when a stock has extreme values (very high growth rates, negative FCF)?
- How should the system behave if yfinance returns incomplete financial statements?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept only a stock ticker symbol as the input parameter (no optional overrides).
- **FR-002**: System MUST validate that ticker input is a non-empty string.
- **FR-003**: System MUST require at least 1 year of historical financial data from yfinance to proceed with valuation.
- **FR-004**: System MUST fetch historical financial data from yfinance including cash flow, revenue, and balance sheet information.
- **FR-005**: System MUST automatically calculate or estimate the following DCF input parameters from yfinance data:
  - Free Cash Flow (FCF) from historical periods
  - FCF growth rate (derived from historical trend or analyst estimates if available)
  - Discount rate / WACC (derived from company risk profile and market data)
  - Terminal growth rate (derived from long-term market expectations)
  - Net debt (calculated from balance sheet assets and liabilities)
  - Number of shares outstanding (from yfinance share data)
- **FR-006**: System MUST populate a DCFRequest model with the derived parameters (same structure as manual endpoint).
- **FR-007**: System MUST invoke the existing DCF calculation logic using the populated DCFRequest.
- **FR-008**: System MUST return the same DCFResponse structure (enterprise value, equity value, value per share, discounted FCFs, discounted terminal value) as the existing `/calculate` endpoint.
- **FR-009**: System MUST return a 400 error with a descriptive message when the ticker symbol cannot be found or has insufficient historical data (less than 1 year).

### Key Entities

- **Stock Data**: yfinance provides historical prices, volumes, and fundamentals; mapped to DCF inputs.
- **DCFRequest**: Automatically populated model containing all parameters needed for DCF calculation.
- **DCFResponse**: Standard valuation output reused from existing endpoint.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New endpoint accepts a stock ticker and returns a DCF valuation in under 5 seconds for a major-cap stock with readily available data.
- **SC-002**: Valuation output structure is identical to the existing `/calculate` endpoint, allowing existing consumers to process results uniformly.
- **SC-003**: System correctly derives all required DCF parameters from yfinance for at least 90% of actively traded stocks in major indices.
- **SC-004**: Error messages clearly distinguish between ticker-not-found errors and insufficient-data errors, helping users understand what went wrong.
- **SC-005**: The endpoint can be fully tested independently without requiring manual data entry, improving developer productivity by eliminating setup time for test scenarios.

## Assumptions

- yfinance will be used as the data source for all financial information; no other data sources are being integrated in this feature.
- The FCF estimate will be derived from operating cash flow and capital expenditure data available in yfinance historical financials.
- Growth rates can be reasonably estimated from historical trends (e.g., 5-year revenue CAGR) or will use reasonable defaults if historical trends are unavailable.
- The discount rate / WACC can be estimated using a simplified model (e.g., risk-free rate + company beta × market risk premium) or reasonable defaults.
- Terminal growth rate will default to a reasonable long-term expectation (e.g., GDP growth rate proxy) unless historical data suggests otherwise.
- Number of shares will be fetched from yfinance's share count data.
- Net debt will be calculated from yfinance balance sheet data: Net Debt = Total Debt − Cash & Equivalents.
