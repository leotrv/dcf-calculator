from __future__ import annotations
from typing import NamedTuple, List, Optional
from src.models.request import DCFRequest


class DCFResult(NamedTuple):
    enterprise_value: float
    equity_value: float
    value_per_share: Optional[float]
    discounted_fcfs: List[float]
    discounted_terminal_value: float


class DCFCalculationService:
    """Service implementing DCF calculation logic.

    Rules:
    - Uses python floats for internal computation for speed.
        - Business validation that depends on multiple fields (e.g., discount_rate > terminal_growth_rate)
            is enforced in the `DCFRequest` model validators and will raise `ValueError` with an
            error code prefix (e.g., "G_GTE_DISCOUNT_RATE: ...").
        - `starting_fcf` semantics: the model's `starting_fcf` represents the last historical year's
            FCF. The first forecasted FCF (FCF1) is `starting_fcf * (1 + fcf_growth_rate)` as used
            when building the FCF list.
        - Terminal value: computed by the `DCFRequest` model (Gordon Growth). The service treats
            an explicit `None` terminal value as "no terminal value"; a numeric `0.0` is considered
            a valid terminal value of zero.
        - Returns raw floats; rounding to 2 decimals is performed at serialization in `DCFResponse`.
    """

    def calculate_dcf(self, req: DCFRequest) -> DCFResult:
        # Cross-field business validation is performed in DCFRequest model validators
        wacc = req.discount_rate
        fcf_list = req.fcf
        if len(fcf_list) == 0:
            raise ValueError('FCF_LENGTH: fcf list must contain at least 1 item')

        discounted_fcfs: List[float] = []
        for i, fcf in enumerate(fcf_list, start=1):
            discounted = fcf / ((1.0 + wacc) ** i)
            discounted_fcfs.append(discounted)

        pv_fcfs = sum(discounted_fcfs)

        # Terminal value is computed by DCFRequest model
        tv = req.terminal_value

        discounted_tv = 0.0
        if tv is not None:
            discounted_tv = tv / ((1.0 + wacc) ** len(fcf_list))

        enterprise_value = pv_fcfs + discounted_tv
        equity_value = enterprise_value - (req.net_debt or 0.0)

        # Calculate value per share if number_of_shares is provided
        # equity_value is in billions, number_of_shares is in actual shares
        # value_per_share should be in dollars: (equity_value_billions * 1e9) / shares
        value_per_share = None
        if req.number_of_shares and req.number_of_shares > 0:
            value_per_share = (equity_value * 1e9) / req.number_of_shares

        return DCFResult(
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            value_per_share=value_per_share,
            discounted_fcfs=discounted_fcfs,
            discounted_terminal_value=discounted_tv,
        )
