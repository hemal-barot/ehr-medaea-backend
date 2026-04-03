import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.fastapi_app.core.config import settings
from backend.fastapi_app.core.database import init_db

from backend.fastapi_app.domains.identity.router import router as auth_router, users_router
from backend.fastapi_app.domains.patient.router import router as patient_router
from backend.fastapi_app.domains.organization.router import router as org_router
from backend.fastapi_app.domains.scheduling.router import router as appt_router, calendar_router
from backend.fastapi_app.domains.encounter.router import router as encounter_router
from backend.fastapi_app.domains.charting.router import router as charting_router
from backend.fastapi_app.domains.audit.router import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Medaea EHR API",
    description="FastAPI backend for Medaea Electronic Health Records system.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

app.include_router(auth_router, prefix=PREFIX)
app.include_router(users_router, prefix=PREFIX)
app.include_router(patient_router, prefix=PREFIX)
app.include_router(org_router, prefix=PREFIX)
app.include_router(appt_router, prefix=PREFIX)
app.include_router(calendar_router, prefix=PREFIX)
app.include_router(encounter_router, prefix=PREFIX)
app.include_router(charting_router, prefix=PREFIX)
app.include_router(audit_router, prefix=PREFIX)


@app.get("/api/health", tags=["System"], summary="Health Check",
         description="Returns service health status. No authentication required.")
def health():
    return {"status": "ok", "service": "medaea-fastapi"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    uvicorn.run("backend.fastapi_app.main:app", host="0.0.0.0", port=port, reload=True)
