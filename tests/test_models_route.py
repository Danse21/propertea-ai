import numpy as np
import pandas as pd

from app.models import Model
from app.services.preprocessing import FEATURES_COLUMNS, TARGET_COLUMN


def _training_csv(n_rows: int = 40) -> bytes:
    """Enough rows, with real numeric variation, for GridSearchCV's cv folds to be non-degenerate."""
    rng = np.random.default_rng(0)
    rows = []
    for i in range(n_rows):
        row = {col: 0 for col in FEATURES_COLUMNS}
        overall_qual = int(rng.integers(1, 10))
        gr_liv_area = int(rng.integers(800, 3000))
        row.update(
            {
                "MSSubClass": 60,
                "Neighborhood": "CollgCr",
                "OverallQual": overall_qual,
                "TotalBsmtSF": int(rng.integers(0, 2000)),
                "1stFlrSF": int(rng.integers(500, 2000)),
                "2ndFlrSF": int(rng.integers(0, 1500)),
                "GrLivArea": gr_liv_area,
                "YearBuilt": int(rng.integers(1950, 2010)),
                "YearRemodAdd": 2000,
                "YrSold": 2008,
                "FullBath": int(rng.integers(1, 4)),
                "GarageCars": int(rng.integers(0, 4)),
                "KitchenQual": "TA",
            }
        )
        row["Id"] = i + 1
        row[TARGET_COLUMN] = 80_000 + overall_qual * 15_000 + gr_liv_area * 40 + rng.normal(scale=5000)
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False).encode()


def _upload_training_dataset(client, session="s1"):
    return client.post(
        "/datasets/upload",
        files={"file": ("train.csv", _training_csv(), "text/csv")},
        data={"name": "training-set", "target_column": TARGET_COLUMN},
        headers={"X-Session-Id": session},
    )


def test_train_happy_path(client, db_session):
    ds_id = _upload_training_dataset(client).json()["id"]

    r = client.post(
        f"/datasets/{ds_id}/train",
        json={"algo": "Linear Regression"},
        headers={"X-Session-Id": "s1"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # Same regression guard as test_modeling.py: catches an accidental extra
    # sqrt() inflating a small RMSE.
    assert 0 < body["metrics"]["rmse_log"] < 1.0
    assert body["best_params"] is None
    assert isinstance(body["importances"], dict) and len(body["importances"]) > 0

    model = db_session.get(Model, body["model_id"])
    assert model is not None
    assert model.artifact is not None and len(model.artifact) > 0


def test_train_unknown_dataset_is_404(client):
    r = client.post(
        "/datasets/999/train",
        json={"algo": "Linear Regression"},
        headers={"X-Session-Id": "s1"},
    )
    assert r.status_code == 404


def test_train_wrong_session_is_404(client):
    ds_id = _upload_training_dataset(client, session="s1").json()["id"]
    r = client.post(
        f"/datasets/{ds_id}/train",
        json={"algo": "Linear Regression"},
        headers={"X-Session-Id": "s2"},
    )
    assert r.status_code == 404


def test_train_unknown_algo_is_400(client):
    ds_id = _upload_training_dataset(client).json()["id"]
    r = client.post(
        f"/datasets/{ds_id}/train",
        json={"algo": "Nonexistent Model"},
        headers={"X-Session-Id": "s1"},
    )
    assert r.status_code == 400


def _train(client, ds_id, session="s1", algo="Linear Regression"):
    return client.post(
        f"/datasets/{ds_id}/train",
        json={"algo": algo},
        headers={"X-Session-Id": session},
    )


def test_list_models_for_dataset(client):
    ds_id = _upload_training_dataset(client).json()["id"]
    _train(client, ds_id, algo="Linear Regression")
    _train(client, ds_id, algo="Decision Tree")

    r = client.get(f"/datasets/{ds_id}/models", headers={"X-Session-Id": "s1"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert {m["algo"] for m in body} == {"Linear Regression", "Decision Tree"}
    assert "artifact" not in body[0]


def test_list_models_wrong_session_is_404(client):
    ds_id = _upload_training_dataset(client, session="s1").json()["id"]
    r = client.get(f"/datasets/{ds_id}/models", headers={"X-Session-Id": "s2"})
    assert r.status_code == 404


def test_predict_happy_path_and_shifts_with_overall_qual(client):
    ds_id = _upload_training_dataset(client).json()["id"]
    model_id = _train(client, ds_id).json()["model_id"]

    low = client.post(
        f"/models/{model_id}/predict",
        json={"overrides": {"OverallQual": 2}},
        headers={"X-Session-Id": "s1"},
    )
    high = client.post(
        f"/models/{model_id}/predict",
        json={"overrides": {"OverallQual": 9}},
        headers={"X-Session-Id": "s1"},
    )
    assert low.status_code == 200, low.text
    assert high.status_code == 200, high.text
    # Synthetic target is 80_000 + OverallQual * 15_000 + ... — a strong,
    # reliably-recoverable positive relationship, even through noise.
    assert high.json()["prediction"] > low.json()["prediction"]


def test_predict_unknown_model_is_404(client):
    r = client.post(
        "/models/999/predict",
        json={"overrides": {}},
        headers={"X-Session-Id": "s1"},
    )
    assert r.status_code == 404


def test_predict_wrong_session_is_404(client):
    ds_id = _upload_training_dataset(client, session="s1").json()["id"]
    model_id = _train(client, ds_id, session="s1").json()["model_id"]
    r = client.post(
        f"/models/{model_id}/predict",
        json={"overrides": {}},
        headers={"X-Session-Id": "s2"},
    )
    assert r.status_code == 404
