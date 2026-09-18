"""Model training endpoints — separate from routers/datasets.py's dataset CRUD."""

import io
from typing import Annotated

import joblib
import numpy as np
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset, Model
from app.routers.datasets import rows_to_dataframe
from app.schemas import ModelOut, PredictRequest, PredictResponse, TrainRequest, TrainResponse
from app.services import modeling
from app.services.preprocessing import DataValidationError

router = APIRouter(tags=["models"])

DbDep = Annotated[Session, Depends(get_db)]
SessionIdDep = Annotated[str | None, Header(alias="X-Session-Id")]


def _get_owned_dataset(db: Session, dataset_id: int, owner_id: str | None) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None or ds.owner_id != owner_id:
        raise HTTPException(404, "Dataset not found")
    return ds


def _get_owned_model(db: Session, model_id: int, owner_id: str | None) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    _get_owned_dataset(db, model.dataset_id, owner_id)
    return model


@router.get("/algorithms", response_model=list[str])
def list_algorithms() -> list[str]:
    return list(modeling.MODELS.keys())


@router.post("/datasets/{dataset_id}/train", response_model=TrainResponse, status_code=201)
def train(
    db: DbDep,
    dataset_id: int,
    body: TrainRequest,
    x_session_id: SessionIdDep = None,
) -> TrainResponse:
    _get_owned_dataset(db, dataset_id, x_session_id)

    if body.algo not in modeling.MODELS:
        raise HTTPException(400, f"Unknown algorithm {body.algo!r}. Choose from {list(modeling.MODELS)}.")

    df = rows_to_dataframe(db, dataset_id)
    try:
        result = modeling.train_model(df, body.algo)
    except DataValidationError as exc:
        raise HTTPException(400, f"Can't train on this dataset: {exc}") from exc

    artifact_buf = io.BytesIO()
    joblib.dump(result["pipeline"], artifact_buf)

    model = Model(
        dataset_id=dataset_id,
        algo=body.algo,
        metrics=result["metrics"],
        artifact=artifact_buf.getvalue(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return TrainResponse(
        model_id=model.id,
        algo=model.algo,
        metrics=result["metrics"],
        best_params=result["best_params"],
        importances=result["importances"].to_dict(),
    )


@router.get("/datasets/{dataset_id}/models", response_model=list[ModelOut])
def list_models(db: DbDep, dataset_id: int, x_session_id: SessionIdDep = None) -> list[Model]:
    _get_owned_dataset(db, dataset_id, x_session_id)
    stmt = select(Model).where(Model.dataset_id == dataset_id).order_by(Model.created_at.desc())
    return list(db.scalars(stmt))


@router.post("/models/{model_id}/predict", response_model=PredictResponse)
def predict(
    db: DbDep,
    model_id: int,
    body: PredictRequest,
    x_session_id: SessionIdDep = None,
) -> PredictResponse:
    model = _get_owned_model(db, model_id, x_session_id)
    pipeline = joblib.load(io.BytesIO(model.artifact))

    df = rows_to_dataframe(db, model.dataset_id)
    try:
        row = modeling.build_predict_row(df, body.overrides)
    except DataValidationError as exc:
        raise HTTPException(400, f"Can't predict from this dataset: {exc}") from exc

    log_price = pipeline.predict(row)[0]
    return PredictResponse(prediction=float(np.expm1(log_price)))
