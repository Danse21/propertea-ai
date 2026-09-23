from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import models  # noqa: F401
from app.db import Base, engine
from app.routers import auth, datasets
from app.routers import models as model_routes

MIGRATIONS = (
    "ALTER TABLE models ADD COLUMN IF NOT EXISTS importances JSON",
    "ALTER TABLE models ADD COLUMN IF NOT EXISTS best_params JSON",
    "UPDATE models SET importances = '{}'::json WHERE importances IS NULL",
    "ALTER TABLE datasets ALTER COLUMN target_column DROP NOT NULL",
)


def migrate() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        for statement in MIGRATIONS:
            conn.execute(text(statement))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    migrate()
    yield


app = FastAPI(title="propertea-ai", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(model_routes.router)


@app.get("/health")
def get_health():
    return {"status": "ok"}
