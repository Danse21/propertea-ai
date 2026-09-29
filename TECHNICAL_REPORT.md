# propertea-ai - Technical Report

Coursework project, MAI25HA / AI1 / KK1, September 2026.
Team: Ivan Kolokoltsev, Damasus Okeke, AzarDani.

## 1. Summary

propertea-ai is a web app that predicts house prices. A signed-in user uploads a
CSV of house sales (or gives the backend a URL to fetch it from), explores it,
trains one or more scikit-learn regression models on it and asks a trained model
for a price. Every dataset and every trained model is stored in Postgres, so
work survives restarts and is private to each account.

The best model, Lasso regression on the Kaggle Ames data, reaches
**RMSE 0.116 on log price and R² 0.920** on a 20 % hold-out set. The code is
covered by 137 automated tests that run in GitHub Actions against a real
Postgres 17 on every pull request.

## 2. Where the project started

The course brief asked for a deployed full-stack application that downloads a
dataset through a web API, persists it, trains a regression model with
scikit-learn and serves predictions, with tests and a public URL.

We picked the **Kaggle "House Prices - Advanced Regression Techniques"** dataset
from Ames, Iowa (1 460 sales, 79 features, target `SalePrice`) because:

- it is a clean supervised regression problem with a numeric target, which
  matched the brief directly;
- it ships a detailed data dictionary
  ([data_description.txt](exploratory-data-analysis/data/data_description.txt)),
  so EDA decisions could be checked against the source instead of guessed;
- it is small enough to train on free-tier hosting (Render's 512 MB RAM was
  the constraint we planned around in [PLAN.md](PLAN.md)).

The plan set a hard **freeze point on 17 September**: a working deployed MVP
first, then optional features in order of cost, with the deadline on
25 September.

Later in the project we looked at two more real-estate datasets to see whether
our process carried over to data we had not tuned it for:

- **King County, WA** (21.6k sales) - same validate → clean → engineer → train
  steps in [notebook_king_county.ipynb](exploratory-data-analysis/notebook_king_county.ipynb).
  Linear Regression reached RMSE 0.183 (log price), Random Forest 0.185 and a
  single Decision Tree 0.227.
- **Realtor.com listings** (2.2 million rows) - an unsupervised side track in
  [realtor_eda_updated.ipynb](exploratory-data-analysis/realtor_eda_updated.ipynb):
  K-Means on price, beds, baths, lot and house size. k = 3 was chosen from the
  elbow curve and the best silhouette score (0.354).

Neither of these was wired into the app's training endpoint. What they did
change in the app is that `target_column` became optional and the **Prepare**
page was added, so any CSV can at least be uploaded, inspected and cleaned.

## 3. What the application does

```
 Sign in ─► Datasets ─► Upload / fetch CSV
               │
               ├─► Prepare  (any CSV: trim, rename, reorder, cast, impute,
               │             filter rows, drop duplicates, plot; save as new dataset)
               │
               └─► Explore ─► Train ─► Predict      (Ames-shaped data only)
```

| Page     | What the user gets |
| -------- | ------------------ |
| Sign in  | Register or log in with username and password. |
| Datasets | Every dataset the user owns, with row count, target, source and the models trained on it. |
| Upload   | Drag-and-drop a CSV (max 10 MB, 100k rows) or paste a URL for the backend to fetch. |
| Prepare  | Column and row cleaning with live preview and seaborn plots; the result is saved as a new dataset. |
| Explore  | Target distribution before and after `log1p`, missingness split into "genuinely missing" and "NA means none", correlation heatmap of the top price drivers. |
| Train    | Choose one of five algorithms, train it, compare RMSE and R² across all trained models. |
| Predict  | Describe a house through 11 inputs (neighbourhood, quality, areas, baths, garage, year built/renovated), get a price, see it plotted against historical sales and see the model's top-10 features. |

## 4. Architecture

```
┌──────────────┐   HTTP + X-Session-Id   ┌──────────────┐   SQLAlchemy   ┌──────────────┐
│  Streamlit   │ ──────────────────────► │   FastAPI    │ ─────────────► │ Postgres 17  │
│  frontend/   │ ◄────────────────────── │ backend/app/ │ ◄───────────── │ (Docker/Neon)│
└──────────────┘          JSON           └──────────────┘                └──────────────┘
```

The frontend never touches the database. It only calls the backend through
[frontend/api_client.py](frontend/api_client.py), so the database credentials
live in one place.

### Data model

```
users         id, username, password_hash, token, created_at
datasets      id, name, source_url, target_column, n_rows, owner_id, created_at, updated_at
dataset_rows  id, dataset_id → datasets (cascade), idx, data JSON
models        id, dataset_id → datasets (cascade), algo, metrics JSON,
              importances JSON, best_params JSON, artifact BLOB, created_at
```

### Design decisions worth explaining

**Raw rows stored as JSON, one row per CSV line.** A single `dataset_rows` table
holds any CSV, not just Ames, and `pd.DataFrame([r.data for r in rows])`
rebuilds the frame. Nothing is transformed on the way in, so the original data
can always be re-used with a different preprocessing.

**All preprocessing lives inside the scikit-learn `Pipeline`.** Imputation,
scaling and one-hot encoding are fitted together with the model and serialised
with it. The predict endpoint therefore runs exactly the transformations the
model was trained with - there is no second copy of the preprocessing code that
could drift.

**Trained models are joblib blobs in Postgres.** Free hosting has an ephemeral
disk, so a model saved to a file would disappear on the next restart. The blob
also carries the median / most-common value of every feature, computed at
training time. When the user fills in 11 fields on the Predict page, the other
~70 columns are taken from those defaults.

**Portable column types.** Using SQLAlchemy's generic `JSON` instead of the
Postgres-only `JSONB` lets the test suite run on in-memory SQLite with the same
models file.

**Schema changes without a migration tool.** Tables are created with
`create_all` at startup, followed by a short list of idempotent
`ALTER TABLE ... IF NOT EXISTS` statements
([backend/app/main.py](backend/app/main.py)). For a three-week project with one
schema owner this was enough; Alembic is the upgrade path if the schema keeps
changing.

**Accounts.** The plan started with an anonymous per-browser session id in the
`owner_id` column. It was replaced by real accounts: passwords hashed with
bcrypt, a random 32-byte token issued on login and sent as the `X-Session-Id`
header. Because `owner_id` existed from day one, no query had to be rewritten.

## 5. Data and model

### What the EDA changed

The Ames EDA ([notebook.ipynb](exploratory-data-analysis/notebook.ipynb)) led
directly to these choices in
[preprocessing.py](backend/app/services/preprocessing.py) and
[modeling.py](backend/app/services/modeling.py):

| Finding | Decision |
| ------- | -------- |
| `SalePrice` is right-skewed (skew 1.88); `log1p(SalePrice)` is almost symmetric (0.12). | Train on `log1p(SalePrice)`, report RMSE on the log scale, convert back with `expm1` for display. |
| pandas treats the string `"None"` as missing by default, but `MasVnrType = "None"` is a real category. 864 valid rows were silently turned into NaN. | Read CSVs with `na_values=["NA", ""]` and `keep_default_na=False`. |
| In 14 columns (`PoolQC`, `Alley`, `GarageType`, …) `NA` means "no pool / no alley / no garage", not unknown. | Fill those with an explicit `"None"` category instead of imputing. |
| `MSSubClass` is stored as a number but is a dwelling-type label. | Cast it to string so it is one-hot encoded. |
| Two sales (`Id` 524, 1299) are huge houses sold far below market. | Drop them before training (the raw rows stay in the database). |
| `test.csv` contains an `MSSubClass` code never seen in training. | `OneHotEncoder(handle_unknown="ignore")`. |
| Price depends on total area and age more than on the separate columns. | Engineer `TotalSF` (basement + 1st + 2nd floor) and `HouseAge` (year sold − year built). |

### Training pipeline

```
numeric columns     → SimpleImputer(median)        → StandardScaler
categorical columns → SimpleImputer(most_frequent) → OneHotEncoder(ignore unknown)
                          ↓
                      estimator (one of five)
```

1. Split 80 / 20 into train and test (`random_state=42`).
2. If the algorithm has hyperparameters, run `GridSearchCV` with 3-fold CV on
   the training part.
3. Score RMSE and R² on the held-out 20 %.
4. Compute permutation importance on the test set (top 10 features are kept for
   the Predict page).
5. Refit the best pipeline on all rows and store it.

### Results on Ames

Hold-out 20 %, RMSE on `log1p(SalePrice)` (lower is better). Training times are
from a laptop run of the same code the backend uses.

| Model | RMSE (log) | R² | Best parameters | Top features by permutation importance | Time |
| ----- | ---------: | ---: | --------------- | -------------------------------------- | ---: |
| **Lasso** | **0.116** | **0.920** | α = 0.0005 | GrLivArea, TotalSF, OverallQual | 5.6 s |
| Elastic Net | 0.117 | 0.919 | α = 0.001, l1_ratio = 0.5 | GrLivArea, TotalSF, OverallQual | 9.2 s |
| Ridge | 0.123 | 0.911 | α = 10 | OverallQual, GrLivArea, OverallCond | 3.5 s |
| Linear Regression | 0.141 | 0.883 | - | PoolArea, SaleType, PoolQC | 3.3 s |
| Random Forest | 0.146 | 0.874 | max_depth = 10 | TotalSF, OverallQual, CentralAir | 9.4 s |

An RMSE of 0.116 on the log scale means a typical error of roughly 12 % of the
price.

What the table tells us:

- **Regularisation matters more than model complexity here.** After one-hot
  encoding there are about 300 columns for about 1 170 training rows. Plain
  Linear Regression fits noise in rare categories: its "most important"
  features are pool area and pool quality, which almost no house has. Lasso and
  Elastic Net shrink those coefficients and land on living area, total area and
  overall quality - the same features the EDA found most correlated with price.
- **Random Forest came last.** With only 50 trees and a two-value depth grid
  (kept small for the free-tier memory and time limit) it does not beat a
  well-regularised linear model on a target that is already near-linear after
  the log transform. The King County notebook showed the same pattern.
- **The engineered `TotalSF` feature is used by every regularised model and by
  the forest**, so it earned its place.

## 6. Technical specification

### Stack

| Layer | Technology | Version |
| ----- | ---------- | ------- |
| Language | Python | 3.13 |
| Package manager | uv | lockfile in [uv.lock](uv.lock) |
| Database | PostgreSQL (Docker locally, Neon in production); SQLite in-memory for tests | 17 |
| Backend | FastAPI, served by uvicorn | 0.141.1 / 0.52.4 |
| ORM / driver | SQLAlchemy, psycopg | 2.0.52 / 3.3.5 |
| Frontend | Streamlit | 1.63.0 |
| Machine learning | scikit-learn, pandas, numpy, joblib | 1.9.0 / 3.0.5 / 2.5.3 / 1.6.0 |
| Tests | pytest, pytest-cov | 9.1.1 / 7.1.0 |
| CI | GitHub Actions with a Postgres 17 service container | - |

### Standard library

| Module | What we use it for |
| ------ | ------------------ |
| `io` | `BytesIO` to parse uploaded CSV bytes with pandas and to (de)serialise model artifacts with joblib ([routers/models.py](backend/app/routers/models.py)). |
| `os` | Reading `DATABASE_URL` and `BACKEND_URL` from the environment. |
| `secrets` | `token_urlsafe(32)` for session tokens ([auth.py](backend/app/auth.py)). |
| `contextlib` | `asynccontextmanager` for the FastAPI lifespan that creates tables on startup. |
| `datetime` | UTC timestamps on every table; date formatting in the UI. |
| `typing` | `Annotated` for FastAPI dependencies (database session, current user). |
| `copy` | Deep-copying Streamlit session defaults so users never share a mutable object ([state.py](frontend/state.py)). |
| `sys`, `pathlib` | Let the frontend import the backend's Ames validation instead of duplicating it ([eda_service.py](frontend/eda_service.py)). |
| `json` | Checking in tests that stored rows are valid JSON (no `NaN` or `inf`). |
| `unittest.mock` | Replacing HTTP calls in frontend client tests ([test_api_client.py](tests/test_api_client.py)). |

### Third-party packages

| Package | Role |
| ------- | ---- |
| `fastapi` | REST API, request validation, dependency injection for the DB session and the current user. `TestClient` drives the API in tests. |
| `pydantic` | Request and response schemas ([schemas.py](backend/app/schemas.py)), e.g. the 72-byte bcrypt password limit. |
| `sqlalchemy` | ORM models, sessions and bulk inserts of dataset rows. |
| `psycopg` | Postgres driver. |
| `httpx` | Streaming download of CSVs by URL, with a 10 MB cap enforced while reading ([routers/datasets.py](backend/app/routers/datasets.py)). |
| `bcrypt` | Password hashing. |
| `python-dotenv` | Loads `.env` for local runs. |
| `pandas` | CSV parsing, all data cleaning and every Prepare operation ([prep_ops.py](frontend/prep_ops.py)). |
| `numpy` | `log1p` / `expm1` on the target, cleaning infinities before JSON storage. |
| `scikit-learn` | The whole modelling pipeline, see below. |
| `joblib` | Serialising the fitted pipeline plus prediction defaults into one blob. |
| `streamlit` | The entire UI. |
| `streamlit-sortables` | Drag-and-drop column reordering on the Prepare page. |
| `requests` | Every call from the frontend to the backend ([api_client.py](frontend/api_client.py)). |
| `matplotlib`, `seaborn` | Charts on Explore, Prepare and Predict, and in the notebooks. |
| `pytest`, `pytest-cov` | Test runner and coverage. |

### scikit-learn modules

| Module | Used for |
| ------ | -------- |
| `sklearn.compose` | `ColumnTransformer` - different preprocessing for numeric and categorical columns. |
| `sklearn.impute` | `SimpleImputer` (median / most frequent). |
| `sklearn.preprocessing` | `StandardScaler`, `OneHotEncoder`. |
| `sklearn.pipeline` | `Pipeline` - preprocessing and estimator as one object. |
| `sklearn.linear_model` | `LinearRegression`, `Ridge`, `Lasso`, `ElasticNet`. |
| `sklearn.ensemble` | `RandomForestRegressor`. |
| `sklearn.model_selection` | `train_test_split`, `GridSearchCV`. |
| `sklearn.metrics` | `root_mean_squared_error`, `r2_score`; `silhouette_score` in the Realtor notebook. |
| `sklearn.inspection` | `permutation_importance` for the feature chart on Predict. |
| `sklearn.tree`, `sklearn.cluster` | `DecisionTreeRegressor` (King County notebook), `KMeans` (Realtor notebook). |

## 7. Testing and quality

- **137 tests** in [tests/](tests/), about 40 s locally. They cover:
  - auth: register, login, logout, duplicate usernames, wrong passwords,
    passwords never stored in plain text, missing or fake tokens;
  - datasets: upload and fetch-by-URL, bad uploads (empty, garbage bytes,
    header only, missing target) answered with 400 instead of 500, `"None"`
    kept as a real value, pagination, and that one user cannot see another
    user's data;
  - modelling: every algorithm trains with a plausible RMSE and R², tuned
    models report parameters from their grid, feature importances are ranked
    correctly, the prediction row matches the training feature engineering,
    and a higher `OverallQual` raises the predicted price;
  - the frontend's pure logic: API client error handling, Prepare operations,
    EDA helpers.
- **Database isolation.** Each test gets a fresh schema. Locally that is
  in-memory SQLite. In CI it is a real Postgres 17 container, because SQLite
  does not enforce foreign keys and a cascade-delete test would pass there for
  the wrong reason ([KNOWN_ISSUES.md](KNOWN_ISSUES.md), KI-1).
- **CI** runs on every push and pull request to `main`.

## 8. Limitations and next steps

- **Train, Explore and Predict only work on Ames-shaped data.** The pipeline
  itself is generic, but the cleaning rules and the Predict form are
  Ames-specific. A per-dataset "schema" (which columns the Predict form shows,
  which NA columns mean "none") would open the app to King County or Realtor
  data. `realtor_preprocessing.py` is a first step that is not wired in yet.
- **No dataset delete or row edit.** Both were on the nice-to-have list and were
  not reached.
- **Tokens never expire.** Fine for coursework; a real deployment needs expiry
  and rate limiting on login.
- **Training runs inside the request.** A slow model blocks that request for its
  whole duration (the client waits up to 240 s). A background job queue is the
  fix if datasets grow.
- **Permutation importance is the slowest step** of training for the fast
  models (it re-runs the whole preprocessing for every shuffled column). Running
  it in parallel or with fewer repeats would cut training time noticeably.

## 9. How the team worked

**Roles, as they turned out.** Damasus built the first EDA notebook, the
preprocessing module and its tests, the first Streamlit UI and the CI pipeline.
Ivan set up the project, database and dataset API, then added accounts, the
Datasets and Prepare pages and the final UI rework. AzarDani did the King County
and Realtor analyses and the Realtor preprocessing module.

**What worked.**

- Every change went through a pull request into `main` (21 merged PRs), so each
  feature was reviewed and merged as one piece.
- Writing the plan with estimates, a freeze date and a ranked nice-to-have list
  up front meant we always knew what to cut. The core flow (upload → train →
  predict) was in place around the planned freeze date.
- EDA findings were written down as decisions in the notebook, and those
  decisions map one-to-one to code in the preprocessing module. That made the
  modelling choices easy to explain and to test.

**What we would do differently.**

- **Tests and CI earlier.** CI was added on 22 September, after most backend
  features, so many tests were written after the code instead of alongside it.
- **One list of dependencies.** The frontend has its own
  `frontend/requirements.txt` for Streamlit Cloud next to `pyproject.toml`.
  The two drifted apart more than once: the deployed build broke on a missing
  package, and `streamlit-sortables` was never added to `pyproject.toml`, so a
  fresh local install could not start the app. A CI step that installs the
  frontend from its own file would catch both.
- **Less work in the final 48 hours.** Accounts, the Datasets page, the Prepare
  page and a full UI rework all landed on 23-24 September. Spreading these out
  would have left time to test the deployed app end to end.
- **Integrate side work, or decide early not to.** The King County and Realtor
  analyses are solid on their own but stayed in notebooks and side branches.
  Deciding at the start whether they should reach the app would have saved
  effort or produced a multi-dataset app.
- **Agree on conventions on day one.** The plan described a `dev` branch that
  was never used, and commit message styles differed between members until
  late in the project.
