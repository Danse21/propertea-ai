import io
from typing import Annotated

import httpx
import numpy as np
import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.auth import CurrentUserDep
from app.db import get_db
from app.models import Dataset, DatasetRow, User
from app.schemas import DatasetCreateFromUrl, DatasetDetail, DatasetOut

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000

DbDep = Annotated[Session, Depends(get_db)]


def get_owned_dataset(db: Session, dataset_id: int, user: User) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if ds is None or ds.owner_id != str(user.id):
        raise HTTPException(404, "Dataset not found")
    return ds


def parse_csv(raw: bytes, target_column: str | None) -> pd.DataFrame:
    if not raw:
        raise HTTPException(400, "File is empty")
    try:
        df = pd.read_csv(io.BytesIO(raw), na_values=[
                         "NA", ""], keep_default_na=False)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}") from exc
    if df.empty:
        raise HTTPException(400, "CSV has a header but no rows")
    if target_column is not None and target_column not in df.columns:
        raise HTTPException(
            400,
            f"target_column {target_column!r} not found. Columns: {list(df.columns)[:20]}",
        )
    if len(df) > MAX_ROWS:
        raise HTTPException(413, f"Too many rows: {len(df)} > {MAX_ROWS}")
    return df


def to_records(df: pd.DataFrame) -> list[dict]:
    clean = df.replace([np.inf, -np.inf], np.nan)
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict("records")


def persist(
    db: Session,
    *,
    name: str,
    target_column: str | None,
    source_url: str | None,
    owner_id: str | None,
    df: pd.DataFrame,
) -> Dataset:
    records = to_records(df)
    ds = Dataset(
        name=name,
        target_column=target_column,
        source_url=source_url,
        owner_id=owner_id,
        n_rows=len(records),
    )
    db.add(ds)
    db.flush()

    db.execute(
        insert(DatasetRow),
        [{"dataset_id": ds.id, "idx": i, "data": rec}
            for i, rec in enumerate(records)],
    )
    db.commit()
    return ds


def rows_to_dataframe(db: Session, dataset_id: int) -> pd.DataFrame:
    rows = list(
        db.scalars(
            select(DatasetRow.data)
            .where(DatasetRow.dataset_id == dataset_id)
            .order_by(DatasetRow.idx)
        )
    )
    columns = list(rows[0]) if rows else []
    return pd.DataFrame(rows, columns=columns)


async def fetch(url: str) -> bytes:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                declared = resp.headers.get("content-length")
                if declared and int(declared) > MAX_BYTES:
                    raise HTTPException(413, "Remote file too large")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise HTTPException(413, "Remote file too large")
                    chunks.append(chunk)
                return b"".join(chunks)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            502, f"Source returned {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Could not fetch URL: {exc}") from exc


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    db: DbDep,
    file: Annotated[UploadFile, File()],
    name: Annotated[str, Form(min_length=1, max_length=255)],
    user: CurrentUserDep,
    target_column: Annotated[str | None, Form(max_length=255)] = None,
) -> Dataset:
    if file.size is not None and file.size > MAX_BYTES:
        raise HTTPException(
            413, f"File too large: {file.size} > {MAX_BYTES} bytes")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            413, f"File too large: {len(raw)} > {MAX_BYTES} bytes")
    df = parse_csv(raw, target_column)
    return persist(
        db,
        name=name,
        target_column=target_column,
        source_url=None,
        owner_id=str(user.id),
        df=df,
    )


@router.post("/from-url", response_model=DatasetOut, status_code=201)
async def dataset_from_url(
    db: DbDep,
    body: DatasetCreateFromUrl,
    user: CurrentUserDep,
) -> Dataset:
    raw = await fetch(str(body.url))
    df = parse_csv(raw, body.target_column)
    return persist(
        db,
        name=body.name,
        target_column=body.target_column,
        source_url=str(body.url),
        owner_id=str(user.id),
        df=df,
    )


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: DbDep, user: CurrentUserDep) -> list[Dataset]:
    stmt = (
        select(Dataset)
        .where(Dataset.owner_id == str(user.id))
        .order_by(Dataset.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(
    db: DbDep,
    dataset_id: int,
    user: CurrentUserDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> DatasetDetail:
    ds = get_owned_dataset(db, dataset_id, user)

    base = (
        select(DatasetRow.data)
        .where(DatasetRow.dataset_id == ds.id)
        .order_by(DatasetRow.idx)
    )
    first = db.scalars(base.limit(1)).first()
    rows = list(db.scalars(base.offset(offset).limit(limit)))

    return DatasetDetail(
        **DatasetOut.model_validate(ds).model_dump(),
        columns=list(first) if first else [],
        rows=rows,
    )
