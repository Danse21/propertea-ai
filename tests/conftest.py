import os

# db.py reads os.environ["DATABASE_URL"] at import time, so this must run before
# anything from `app` is imported or collection dies with KeyError.
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # Without StaticPool every connection gets its own empty in-memory DB.
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def csv_bytes() -> bytes:
    return (
        "Id,LotArea,MasVnrType,SalePrice\n"
        "1,8450,BrkFace,208500\n"
        "2,9600,None,181500\n"  # literal category, must survive as the string "None"
        "3,11250,NA,223500\n"  # genuinely missing -> JSON null
        "4,9550,,140000\n"  # blank cell -> JSON null
    ).encode()
