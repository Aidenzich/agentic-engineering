from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import AppException, app_exception_handler
from app.realtime.socket import socket_app
from app.routers.auth import router as auth_router
from app.routers.orgs.orgs import router as orgs_router
from app.routers.orgs.members import router as members_router
from app.routers.orgs.teams import router as teams_router
from app.services.audit_service import register_audit_handlers, router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    register_audit_handlers()
    yield
    # Shutdown


app = FastAPI(
    title="AI-Native Internal Developer Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Routers
app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(members_router)
app.include_router(teams_router)
app.include_router(audit_router)

# Mount Socket.IO
app.mount("/ws", socket_app)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
