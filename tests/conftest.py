import os
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from model_service.app import app, get_db, ml

# ------------------------------------------------------------------
# SQLite database used ONLY for tests
# ------------------------------------------------------------------

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ------------------------------------------------------------------
# Create tables once before all tests
# ------------------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ------------------------------------------------------------------
# Database fixture
# ------------------------------------------------------------------


@pytest.fixture()
def db():

    connection = engine.connect()

    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()

    transaction.rollback()

    connection.close()


# ------------------------------------------------------------------
# Mock ML model
# ------------------------------------------------------------------


@pytest.fixture()
def mock_model():

    fake_model = MagicMock()

    fake_model.predict.return_value = np.array([1])

    fake_model.predict_proba.return_value = np.array([[0.10, 0.90]])

    ml["model"] = fake_model

    yield fake_model

    ml.clear()


# ------------------------------------------------------------------
# Override FastAPI dependency
# ------------------------------------------------------------------


@pytest.fixture()
def client(db):

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    ml.clear()


# ------------------------------------------------------------------
# Remove SQLite database after tests
# ------------------------------------------------------------------


def pytest_sessionfinish(session, exitstatus):

    if os.path.exists("test.db"):
        os.remove("test.db")
