from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field, PrivateAttr, ConfigDict


class AutoDCFRequest(BaseModel):
    """Request model for automatic DCF calculation from stock ticker.
    
    The /dcf/auto-calculate endpoint uses this to fetch historical financial
    data via yfinance and automatically populate DCFRequest fields.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL"
            }
        }
    )
    
    ticker: str = Field(..., description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')")
    
    @field_validator('ticker')
    def validate_ticker(cls, v: str):
        """Validate ticker is non-empty and alphanumeric."""
        if not v:
            raise ValueError('TICKER_EMPTY: ticker cannot be empty')
        if not v.isalpha():
            raise ValueError('TICKER_INVALID: ticker must contain only alphabetic characters')
        return v.upper()


class DCFRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "starting_fcf": 72.764,
                "fcf_growth_rate": 0.12,
                "years": 10,
                "discount_rate": 0.08,
                "terminal_growth_rate": 0.03,
                "net_debt": -54.3,
                "number_of_shares": 15500000000,  # Actual count (e.g., 15.5 billion shares)
            }
        }
    )
    
    starting_fcf: float = Field(..., description="Starting free cash flow (last historical year). Units: billions")
    fcf_growth_rate: float = Field(..., description="Forecast FCF growth rate (decimal). Example: 0.05 = 5%")
    years: int = Field(..., description="Number of forecast years (integer)")
    discount_rate: float = Field(..., description="Discount rate / WACC (decimal). Example: 0.08 = 8%")
    terminal_growth_rate: Optional[float] = Field(None, description="Terminal (perpetuity) growth rate (decimal). Example: 0.03 = 3%")
    net_debt: Optional[float] = Field(None, description="Net debt in billions. Positive = net debt; negative = net cash")
    number_of_shares: Optional[float] = Field(None, description="Number of shares outstanding (actual count, not millions)")
    
    _fcf_list: List[float] = PrivateAttr()

    @field_validator('starting_fcf')
    def validate_starting_fcf(cls, v: float):
        if v < 0:
            raise ValueError('STARTING_FCF_NEGATIVE: starting_fcf must be non-negative')
        return v

    @field_validator('fcf_growth_rate')
    def validate_fcf_growth_rate(cls, v: float):
        return v

    @field_validator('years')
    def validate_years(cls, v: int):
        if not (1 <= v <= 30):
            raise ValueError('YEARS_LENGTH: years must be between 1 and 30')
        return v

    @field_validator('discount_rate')
    def validate_discount_rate(cls, v: float):
        if v <= 0:
            raise ValueError('DISCOUNT_RATE_NONPOSITIVE: discount_rate must be > 0')
        return v

    @field_validator('terminal_growth_rate')
    def validate_terminal_growth_rate(cls, v: Optional[float]):
        if v is None:
            return v
        if v < 0:
            raise ValueError('G_NEGATIVE: terminal_growth_rate must be >= 0')
        return v

    @field_validator('net_debt')
    def validate_net_debt(cls, v: Optional[float]):
        # Net debt may be negative to represent net cash (e.g., large cash balances).
        # Allow negative values; no cross-field validation required here.
        return v

    @model_validator(mode='after')
    def validate_terminal_growth_rate_vs_discount_rate(self):
        """Ensure terminal_growth_rate < discount_rate for meaningful TV calculation."""
        if self.terminal_growth_rate is not None and self.terminal_growth_rate >= self.discount_rate:
            raise ValueError('G_GTE_DISCOUNT_RATE: terminal_growth_rate must be strictly less than discount_rate')
        return self

    @model_validator(mode='after')
    def compute_fcf_list(self):
        """Generate FCF list based on starting_fcf, fcf_growth_rate, and years."""
        fcf_list = []
        growth_factor = 1.0 + self.fcf_growth_rate
        for year in range(1, self.years + 1):
            fcf = self.starting_fcf * (growth_factor ** year)
            fcf_list.append(fcf)
        self._fcf_list = fcf_list
        return self

    @computed_field
    def fcf(self) -> List[float]:
        """Computed FCF list derived from starting_fcf, fcf_growth_rate, and years."""
        return self._fcf_list

    @computed_field
    def terminal_value(self) -> float:
        """Computed terminal value using Gordon Growth Model.
        
        Formula: TV = (Last Year FCF * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)
        
        If terminal_growth_rate is None, returns 0.
        """
        if self.terminal_growth_rate is None:
            return 0.0
        
        last_fcf = self.fcf[-1]
        wacc = self.discount_rate
        g = self.terminal_growth_rate
        
        tv = last_fcf * (1.0 + g) / (wacc - g)
        return tv

