from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401 -- registers tables on Base.metadata before create_all
from app.db import Base, engine
from app.routers import datasets
from app.routers import models as model_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="propertea-ai", lifespan=lifespan)
app.include_router(datasets.router)
app.include_router(model_routes.router)


@app.get("/health")
def get_health():
    return {"status": "ok"}
