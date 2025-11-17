from __future__ import annotations
from fastapi import APIRouter, HTTPException
from src.models.request import DCFRequest
from src.models.response import DCFResponse
from src.services.dcf_calculation_service import DCFCalculationService

router = APIRouter(prefix="/dcf")


@router.post('/calculate', response_model=DCFResponse)
async def calculate(payload: DCFRequest):
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
