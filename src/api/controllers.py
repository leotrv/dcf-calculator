from __future__ import annotations
from fastapi import APIRouter, HTTPException
from src.models.request import DCFRequest, AutoDCFRequest
from src.models.response import DCFResponse
from src.services.dcf_calculation_service import DCFCalculationService
from src.services.yfinance_service import YFinanceService, ValidationError

router = APIRouter(prefix="/dcf")


@router.post('/calculate', response_model=DCFResponse)
async def calculate(payload: DCFRequest):
    """Calculate DCF and return values.

    Units and conventions:
    - All cash amounts (`starting_fcf`, `net_debt`, `terminal_value`) are expressed in billions.
    - Feel free to use other units, but be consistent. Mathematical model is unit-agnostic.
    - Growth rates and discount rates are expressed in decimal format (e.g., `0.08` means 8%).
    - `starting_fcf` is the last historical year's FCF; the first forecast FCF (FCF1) = starting_fcf * (1 + fcf_growth_rate).
    """

    service = DCFCalculationService()
    try:
        result = service.calculate_dcf(payload)
        response = DCFResponse(
            enterprise_value=result.enterprise_value,
            equity_value=result.equity_value,
            value_per_share=result.value_per_share,
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


@router.post('/auto-calculate', response_model=DCFResponse)
async def auto_calculate(payload: AutoDCFRequest):
    """Automatically calculate DCF from stock ticker.
    
    This endpoint:
    1. Fetches historical financial data from yfinance
    2. Extracts FCF, growth rates, and WACC
    3. Performs DCF calculation automatically
    
    Query parameters:
    - ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
    - DCFResponse with calculated enterprise value, equity value, and per-share value
    
    Error responses:
    - 400: INVALID_TICKER, TICKER_NOT_FOUND, INSUFFICIENT_HISTORY, MISSING_FIELD, YFINANCE_ERROR
    - 503: Network/service error from yfinance
    """
    
    yfinance_service = YFinanceService()
    dcf_service = DCFCalculationService()
    
    try:
        # Extract DCF inputs from yfinance
        dcf_request = yfinance_service.extract_dcf_inputs(payload.ticker)
        
        # Calculate DCF using extracted inputs
        result = dcf_service.calculate_dcf(dcf_request)
        response = DCFResponse(
            enterprise_value=result.enterprise_value,
            equity_value=result.equity_value,
            value_per_share=result.value_per_share,
            discounted_fcfs=result.discounted_fcfs,
            discounted_terminal_value=result.discounted_terminal_value,
        )
        return response
    except ValidationError as exc:
        # yfinance validation errors (ticker not found, insufficient history, etc.)
        raise HTTPException(status_code=400, detail={
            'error': exc.message,
            'error_code': exc.error_code,
        })
    except ValueError as exc:
        # DCF calculation errors
        msg = str(exc)
        error_code = msg.split(':')[0] if ':' in msg else 'BUSINESS_ERROR'
        raise HTTPException(status_code=400, detail={
            'error': msg,
            'error_code': error_code,
        })
    except Exception as exc:
        # Network/timeout errors from yfinance
        raise HTTPException(status_code=503, detail={
            'error': f'Service unavailable: {str(exc)}',
            'error_code': 'SERVICE_UNAVAILABLE',
        })
