import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, _normalize, get_db 
from app.main import app


TEST_DATABASE_URL = _normalize(os.environ["DATABASE_URL"])


def _make_engine():
    if TEST_DATABASE_URL.startswith("sqlite"):
        return create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture
def db_session():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
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
        "2,9600,None,181500\n"
        "3,11250,NA,223500\n"
        "4,9550,,140000\n"
    ).encode()
