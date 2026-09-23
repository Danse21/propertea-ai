"""Model training endpoints — separate from routers/datasets.py's dataset CRUD."""

import io
from typing import Annotated

import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUserDep
from app.db import get_db
from app.models import Model, User
from app.routers.datasets import get_owned_dataset, rows_to_dataframe
from app.schemas import ModelOut, PredictRequest, PredictResponse, TrainRequest, TrainResponse
from app.services import modeling
from app.services.preprocessing import DataValidationError

router = APIRouter(tags=["models"])

DbDep = Annotated[Session, Depends(get_db)]


def _get_owned_model(db: Session, model_id: int, user: User) -> Model:
    model = db.get(Model, model_id)
    if model is None:
        raise HTTPException(404, "Model not found")
    get_owned_dataset(db, model.dataset_id, user)
    return model


@router.get("/algorithms", response_model=list[str])
def list_algorithms() -> list[str]:
    return list(modeling.MODELS.keys())


@router.post("/datasets/{dataset_id}/train", response_model=TrainResponse, status_code=201)
def train(
    db: DbDep,
    dataset_id: int,
    body: TrainRequest,
    user: CurrentUserDep,
) -> TrainResponse:
    get_owned_dataset(db, dataset_id, user)

    if body.algo not in modeling.MODELS:
        raise HTTPException(400, f"Unknown algorithm {body.algo!r}. Choose from {list(modeling.MODELS)}.")

    df = rows_to_dataframe(db, dataset_id)
    try:
        result = modeling.train_model(df, body.algo)
    except DataValidationError as exc:
        raise HTTPException(400, f"Can't train on this dataset: {exc}") from exc

    artifact_buf = io.BytesIO()
    joblib.dump({"pipeline": result["pipeline"], "defaults": result["defaults"]}, artifact_buf)

    model = Model(
        dataset_id=dataset_id,
        algo=body.algo,
        metrics=result["metrics"],
        importances=result["importances"].to_dict(),
        best_params=result["best_params"],
        artifact=artifact_buf.getvalue(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return TrainResponse(
        model_id=model.id,
        algo=model.algo,
        metrics=model.metrics,
        best_params=model.best_params,
        importances=model.importances,
    )


@router.get("/datasets/{dataset_id}/models", response_model=list[ModelOut])
def list_models(db: DbDep, dataset_id: int, user: CurrentUserDep) -> list[Model]:
    get_owned_dataset(db, dataset_id, user)
    stmt = select(Model).where(Model.dataset_id == dataset_id).order_by(Model.created_at.desc())
    return list(db.scalars(stmt))


@router.post("/models/{model_id}/predict", response_model=PredictResponse)
def predict(
    db: DbDep,
    model_id: int,
    body: PredictRequest,
    user: CurrentUserDep,
) -> PredictResponse:
    model = _get_owned_model(db, model_id, user)
    bundle = joblib.load(io.BytesIO(model.artifact))

    row = modeling.build_predict_row(bundle["defaults"], body.overrides)

    log_price = bundle["pipeline"].predict(row)[0]
    return PredictResponse(prediction=float(np.expm1(log_price)))
