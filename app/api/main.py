from fastapi import APIRouter

from app.api.routes import asr

api_router = APIRouter()
api_router.include_router(asr.router, prefix="/asr", tags=["asr"])
