"""HTTP client for the FastAPI backend."""

import io
import os

import pandas as pd
import requests

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
TIMEOUT_SECONDS = 180

TRAIN_TIMEOUT_SECONDS = 240
PAGE_SIZE = 500


class ApiError(Exception):
    """The backend responded, but with an error status."""


class BackendUnreachableError(ApiError):
    """The backend could not be reached at all (connection refused, timeout, DNS)."""


def _headers(session_id: str) -> dict:
    return {"X-Session-Id": session_id}


def _request(method: str, path: str, *, timeout: float = TIMEOUT_SECONDS, **kwargs) -> dict | list:
    try:
        response = requests.request(method, f"{BASE_URL}{path}", timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise BackendUnreachableError(f"Could not reach the backend at {BASE_URL}: {e}") from e

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(f"{response.status_code}: {detail}")

    return response.json()


def upload_dataset(session_id: str, file, name: str, target_column: str) -> dict:
    """`file` may be raw bytes or a file-like object (e.g. Streamlit's UploadedFile)."""
    if isinstance(file, (bytes, bytearray)):
        file = io.BytesIO(file)
    filename = getattr(file, "name", "dataset.csv")

    return _request(
        "POST",
        "/datasets/upload",
        files={"file": (filename, file, "text/csv")},
        data={"name": name, "target_column": target_column},
        headers=_headers(session_id),
    )


def fetch_dataset_from_url(session_id: str, url: str, name: str, target_column: str) -> dict:
    return _request(
        "POST",
        "/datasets/from-url",
        json={"url": url, "name": name, "target_column": target_column},
        headers=_headers(session_id),
    )


def list_datasets(session_id: str) -> list[dict]:
    return _request("GET", "/datasets", headers=_headers(session_id))


def get_dataset(session_id: str, dataset_id: int, offset: int = 0, limit: int = PAGE_SIZE) -> dict:
    return _request(
        "GET",
        f"/datasets/{dataset_id}",
        params={"offset": offset, "limit": limit},
        headers=_headers(session_id),
    )


def get_full_dataset(session_id: str, dataset_id: int) -> pd.DataFrame:
    """Page through GET /datasets/{id} until every row is fetched, and reassemble a DataFrame."""
    first = get_dataset(session_id, dataset_id, offset=0, limit=PAGE_SIZE)
    columns = first["columns"]
    rows = list(first["rows"])
    n_rows = first["n_rows"]

    offset = len(rows)
    while offset < n_rows:
        page = get_dataset(session_id, dataset_id, offset=offset, limit=PAGE_SIZE)
        if not page["rows"]:
            break
        rows.extend(page["rows"])
        offset += len(page["rows"])

    return pd.DataFrame(rows, columns=columns)


def list_algorithms() -> list[str]:
    return _request("GET", "/algorithms")


def train(session_id: str, dataset_id: int, algo: str) -> dict:
    return _request(
        "POST",
        f"/datasets/{dataset_id}/train",
        json={"algo": algo},
        headers=_headers(session_id),
        timeout=TRAIN_TIMEOUT_SECONDS,
    )


def list_models(session_id: str, dataset_id: int) -> list[dict]:
    return _request("GET", f"/datasets/{dataset_id}/models", headers=_headers(session_id))


def predict(session_id: str, model_id: int, overrides: dict) -> dict:
    return _request(
        "POST",
        f"/models/{model_id}/predict",
        json={"overrides": overrides},
        headers=_headers(session_id),
    )
