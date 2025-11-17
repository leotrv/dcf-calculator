from __future__ import annotations
import json
import sys
from src.models.request import DCFRequest
from src.services.dcf_calculation_service import DCFCalculationService
from src.models.response import DCFResponse


def main():
    # Simple CLI: read JSON payload from stdin or first arg
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception as e:
        print('Invalid JSON input:', e)
        sys.exit(2)

    try:
        req = DCFRequest.model_validate(payload)
    except Exception as e:
        print('Validation error:', e)
        sys.exit(2)

    svc = DCFCalculationService()
    try:
        res = svc.calculate_dcf(req)
        resp = DCFResponse(
            enterprise_value=res.enterprise_value,
            equity_value=res.equity_value,
            discounted_fcfs=res.discounted_fcfs,
            discounted_terminal_value=res.discounted_terminal_value,
        )
        print(json.dumps(resp.model_dump(), indent=2))
    except ValueError as e:
        print('Calculation error:', str(e))
        sys.exit(3)


if __name__ == '__main__':
    main()
