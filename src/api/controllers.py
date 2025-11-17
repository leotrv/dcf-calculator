from __future__ import annotations
from fastapi import APIRouter, HTTPException
from src.models.request import DCFRequest
from src.models.response import DCFResponse
from src.services.dcf_calculation_service import DCFCalculationService

router = APIRouter(prefix="/dcf")


@router.post('/calculate', response_model=DCFResponse)
async def calculate(payload: DCFRequest):
    """Calculate DCF and return values.

    Units and conventions:
    - All cash amounts (`starting_fcf`, `net_debt`, `terminal_value`) are expressed in billions.
    - Feel free to use other units, but be consistent. Mathematical model is unit-agnostic.
    - Growth rates and discount rates are expressed in percent (e.g., `8.0` means 8%).
    - `starting_fcf` is the last historical year's FCF; the first forecast FCF (FCF1) = starting_fcf * (1 + fcf_growth_rate).
    """

    service = DCFCalculationService()
    try:
        result = service.calculate_dcf(payload)
        response = DCFResponse(
            enterprise_value=result.enterprise_value,
            equity_value=result.equity_value,
            discounted_fcfs=result.discounted_fcfs,
            discounted_terminal_value=result.discounted_terminal_value,
        )
        return response
    except ValueError as exc:
        # Expect error messages prefixed with an error code like "WACC_LE_G: ..."
        msg = str(exc)
        error_code = msg.split(':')[0] if ':' in msg else 'BUSINESS_ERROR'
        raise HTTPException(status_code=400, detail={
            'error': msg,
            'error_code': error_code,
        })
