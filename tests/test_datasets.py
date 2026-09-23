import json

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from app.models import DatasetRow
from app.routers.datasets import persist, rows_to_dataframe, to_records


def _upload(client, auth, payload, *, target="SalePrice", name="ames"):
    return client.post(
        "/datasets/upload",
        files={"file": ("train.csv", payload, "text/csv")},
        data={"name": name, "target_column": target},
        headers=auth,
    )


def _rows(db_session):
    return list(db_session.scalars(select(DatasetRow.data).order_by(DatasetRow.idx)))


def test_upload_happy_path(client, auth, db_session, csv_bytes):
    r = _upload(client, auth, csv_bytes)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["n_rows"] == 4
    assert body["source_url"] is None
    assert "owner_id" not in body

    rows = _rows(db_session)
    assert len(rows) == 4
    assert [row["Id"] for row in rows] == [1, 2, 3, 4]


def test_missing_values_become_null_and_literal_none_survives(
    client, auth, db_session, csv_bytes
):
    assert _upload(client, auth, csv_bytes).status_code == 201
    rows = _rows(db_session)
    assert rows[1]["MasVnrType"] == "None"
    assert rows[2]["MasVnrType"] is None
    assert rows[3]["MasVnrType"] is None


def test_to_records_is_json_safe():
    df = pd.DataFrame(
        {
            "i": [1, 2, 3],
            "f": [1.5, np.nan, np.inf],
            "s": ["None", "x", "y"],
        }
    )
    recs = to_records(df)
    json.dumps(recs, allow_nan=False)
    assert type(recs[0]["i"]) is int
    assert recs[1]["f"] is None and recs[2]["f"] is None


def test_rows_to_dataframe_round_trips_persist(db_session):
    """to_records() -> persist() -> rows_to_dataframe() reproduces the original frame."""
    original = pd.DataFrame(
        {
            "Id": [1, 2, 3],
            "LotArea": [8450, 9600, 11250],
            "MasVnrType": ["BrkFace", "None", None],
        }
    )
    ds = persist(
        db_session,
        name="roundtrip",
        target_column="SalePrice",
        source_url=None,
        owner_id="s1",
        df=original,
    )

    df = rows_to_dataframe(db_session, ds.id)

    assert list(df.columns) == list(original.columns)
    assert df["Id"].tolist() == original["Id"].tolist()
    assert df["LotArea"].tolist() == original["LotArea"].tolist()
    assert df["MasVnrType"].tolist() == original["MasVnrType"].tolist()


def test_rows_to_dataframe_unknown_dataset_returns_empty_frame(db_session):
    df = rows_to_dataframe(db_session, dataset_id=999)
    assert df.empty
    assert list(df.columns) == []


@pytest.mark.parametrize(
    "payload, target, expected",
    [
        (b"Id,LotArea\n1,8450\n", "SalePrice", 400),
        (b"\xff\xfe\x00garbage", "SalePrice", 400),
        (b"", "SalePrice", 400),
        (b"Id,SalePrice\n", "SalePrice", 400),
    ],
)
def test_bad_uploads_are_4xx_not_500(client, auth, payload, target, expected):
    assert _upload(client, auth, payload, target=target).status_code == expected


def test_user_scoping(client, auth, other_auth, csv_bytes):
    _upload(client, auth, csv_bytes)
    assert len(client.get("/datasets", headers=auth).json()) == 1
    assert client.get("/datasets", headers=other_auth).json() == []


def test_get_detail(client, auth, other_auth, csv_bytes):
    ds_id = _upload(client, auth, csv_bytes).json()["id"]
    r = client.get(f"/datasets/{ds_id}?limit=2", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["columns"] == ["Id", "LotArea", "MasVnrType", "SalePrice"]
    assert len(body["rows"]) == 2

    other = client.get(f"/datasets/{ds_id}", headers=other_auth)
    assert other.status_code == 404


def test_from_url(client, auth, monkeypatch, csv_bytes):
    from app.routers import datasets as datasets_mod

    async def fake_fetch(url: str) -> bytes:
        return csv_bytes

    monkeypatch.setattr(datasets_mod, "fetch", fake_fetch)
    r = client.post(
        "/datasets/from-url",
        json={
            "url": "https://example.com/train.csv",
            "name": "ames",
            "target_column": "SalePrice",
        },
        headers=auth,
    )
    assert r.status_code == 201, r.text
    assert r.json()["source_url"] == "https://example.com/train.csv"
