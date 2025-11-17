from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal, ROUND_HALF_UP


def _round_currency(value: float) -> float:
    # round to 2 decimals using Decimal with HALF_UP behavior
    d = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return float(d)


class DCFResponse(BaseModel):
    enterprise_value: float
    equity_value: float
    discounted_fcfs: List[float]
    discounted_terminal_value: float

    def model_dump(self, *args, **kwargs):
        raw = super().model_dump(*args, **kwargs)
        # Round monetary outputs to 2 decimals only at serialization
        raw['enterprise_value'] = _round_currency(raw['enterprise_value'])
        raw['equity_value'] = _round_currency(raw['equity_value'])
        raw['discounted_fcfs'] = [ _round_currency(x) for x in raw.get('discounted_fcfs', []) ]
        raw['discounted_terminal_value'] = _round_currency(raw.get('discounted_terminal_value', 0.0))
        return raw
