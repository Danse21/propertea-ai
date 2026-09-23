from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


BCRYPT_MAX_PASSWORD_BYTES = 72


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(
                f"password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes"
            )
        return value


class AuthResponse(BaseModel):
    token: str
    username: str


class DatasetCreateFromUrl(BaseModel):
    url: HttpUrl
    name: str = Field(min_length=1, max_length=255)
    target_column: str = Field(min_length=1, max_length=255)


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_url: str | None
    target_column: str
    n_rows: int
    created_at: datetime
    updated_at: datetime


class DatasetDetail(DatasetOut):
    columns: list[str]
    rows: list[dict]


class TrainRequest(BaseModel):
    algo: str


class TrainResponse(BaseModel):
    model_id: int
    algo: str
    metrics: dict
    best_params: dict | None
    importances: dict[str, float]


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    algo: str
    metrics: dict
    created_at: datetime


class PredictRequest(BaseModel):
    overrides: dict[str, str | int | float]


class PredictResponse(BaseModel):
    prediction: float
