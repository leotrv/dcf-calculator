from __future__ import annotations
from typing import NamedTuple, List
from src.models.request import DCFRequest


class DCFResult(NamedTuple):
    enterprise_value: float
    equity_value: float
    discounted_fcfs: List[float]
    discounted_terminal_value: float


class DCFCalculationService:
    """Service implementing DCF calculation logic.

    Rules:
    - Uses python floats for internal computation for speed.
    - Business validation that depends on multiple fields (e.g., discount_rate > terminal_growth_rate)
      is enforced here and raises ValueError with an error code prefix (e.g., "WACC_LE_G: ...").
    - Returns raw floats; rounding to 2 decimals is performed at serialization in `DCFResponse`.
    """

    def calculate_dcf(self, req: DCFRequest) -> DCFResult:
        # Cross-field business validation
        wacc = float(req.discount_rate)
        g = req.terminal_growth_rate
        if g is not None and wacc <= float(g):
            raise ValueError('WACC_LE_G: discount_rate must be strictly greater than terminal_growth_rate')

        fcf_list = [float(x) for x in req.fcf]
        if len(fcf_list) == 0:
            raise ValueError('FCF_LENGTH: fcf list must contain at least 1 item')

        discounted_fcfs: List[float] = []
        for i, fcf in enumerate(fcf_list, start=1):
            discounted = fcf / ((1.0 + wacc) ** i)
            discounted_fcfs.append(discounted)

        pv_fcfs = sum(discounted_fcfs)

        # Terminal value: provided explicit TV takes precedence
        if req.terminal_value is not None:
            tv = float(req.terminal_value)
        elif g is not None:
            last_fcf = fcf_list[-1]
            denom = (wacc - float(g))
            if denom == 0:
                raise ValueError('DIV_BY_ZERO: discount_rate equals terminal_growth_rate')
            tv = last_fcf * (1.0 + float(g)) / denom
        else:
            tv = 0.0

        discounted_tv = 0.0
        if tv:
            discounted_tv = tv / ((1.0 + wacc) ** len(fcf_list))

        enterprise_value = pv_fcfs + discounted_tv
        equity_value = enterprise_value - (float(req.net_debt) if req.net_debt is not None else 0.0)

        return DCFResult(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            discounted_fcfs=discounted_fcfs,
            discounted_terminal_value=discounted_tv,
        )
