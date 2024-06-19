import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.core.config import settings
# from app.core.db import initiate_database
from app.api.main import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


# @app.on_event("startup")
# async def start_database():
#     await initiate_database()


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def index():
    return "/docs"


app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
