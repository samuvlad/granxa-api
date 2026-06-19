from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.lotes import router as lotes_router
from app.routers.plots import router as plots_router
from app.routers.rotation import router as rotations_router
from app.routers.sheep import router as sheep_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # As táboas xestiónanse con Alembic (ver alembic/versions/).
    # En desenvolvemento pódese activar INIT_DB=1 no .env para usar
    # SQLModel.metadata.create_all como atallo.
    import os

    if os.getenv("INIT_DB") == "1":
        from app.database import init_db

        init_db()
    yield


app = FastAPI(
    title="Granxa Maps API",
    description="API para xestión de parcelas e gando",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plots_router)
app.include_router(sheep_router)
app.include_router(rotations_router)
app.include_router(lotes_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
