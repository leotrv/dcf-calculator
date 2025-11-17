from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from src.api.controllers import router as dcf_router

app = FastAPI(title='DCF Analysis Agent', version='0.0.1')
app.include_router(dcf_router)


@app.get('/', include_in_schema=False)
async def root():
    return RedirectResponse(url='/docs')
