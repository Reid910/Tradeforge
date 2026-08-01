from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.inventory import router as inventory_router
from app.api.map import router as map_router
from app.api.mines import router as mines_router
from app.api.system import router as system_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.resource_seed import seed_resources


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_resources(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(map_router, prefix="/api")
app.include_router(mines_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
