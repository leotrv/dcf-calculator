from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, field_validator


class DCFRequest(BaseModel):
    fcf: List[float]
    discount_rate: float
    terminal_value: Optional[float] = None
    terminal_growth_rate: Optional[float] = None
    net_debt: float = 0.0

    @field_validator('fcf')
    def validate_fcf(cls, v: List[float]):
        if not isinstance(v, list):
            raise ValueError('FCF_INVALID: fcf must be a list of numbers')
        if not (1 <= len(v) <= 30):
            raise ValueError('FCF_LENGTH: fcf must contain between 1 and 30 items')
        if any((x is None) or (not isinstance(x, (int, float))) for x in v):
            raise ValueError('FCF_INVALID: fcf items must be numbers')
        if any(x < 0 for x in v):
            raise ValueError('FCF_NEGATIVE: fcf values must be non-negative')
        return v

    @field_validator('discount_rate')
    def validate_discount_rate(cls, v: float):
        if v is None:
            raise ValueError('DISCOUNT_RATE_REQUIRED: discount_rate is required')
        if not isinstance(v, (int, float)):
            raise ValueError('DISCOUNT_RATE_INVALID: discount_rate must be a number')
        if v <= 0:
            raise ValueError('DISCOUNT_RATE_NONPOSITIVE: discount_rate must be > 0')
        return float(v)

    @field_validator('terminal_growth_rate')
    def validate_terminal_growth_rate(cls, v: Optional[float]):
        if v is None:
            return v
        if not isinstance(v, (int, float)):
            raise ValueError('G_INVALID: terminal_growth_rate must be a number')
        if v < 0:
            raise ValueError('G_NEGATIVE: terminal_growth_rate must be >= 0')
        return float(v)

    @field_validator('net_debt')
    def validate_net_debt(cls, v: float):
        if v is None:
            return 0.0
        if not isinstance(v, (int, float)):
            raise ValueError('NET_DEBT_INVALID: net_debt must be a number')
        return float(v)
