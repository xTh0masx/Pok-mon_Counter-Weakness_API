import asyncio

from fastapi import APIRouter, HTTPException, Request

from App.models.schemas import AnalysisRequest, AnalysisResponse
from App.services.analysis_service import AnalysisService
from App.services.pokeapi_client import NotFound, UpstreamUnavailable

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
    try:
        async with asyncio.timeout(20):
            return await AnalysisService(request.app.state.pokeapi).analyze(payload)
    except NotFound:
        raise HTTPException(status_code=404, detail="Pokemon or type not found") from None
    except (UpstreamUnavailable, TimeoutError):
        raise HTTPException(status_code=503, detail="Pokemon data temporarily unavailable", headers={"Retry-After": "15"}) from None
