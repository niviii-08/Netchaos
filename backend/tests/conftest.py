"""Tests run against in-memory SQLite by default (fast, no server needed).

Set TEST_DATABASE_URL (e.g. mysql+pymysql://user:pass@host/netchaos_test) to run the
same tests against a real MySQL server. That database is wiped by every test.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db, make_engine
from app.graph import graph_manager
from app.main import app
from app import models  # noqa: F401


@pytest.fixture()
def session_factory():
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        engine = make_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = make_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    graph_manager.clear()
    yield TestClient(app)  # no `with`: skips the lifespan, which would connect to MySQL
    app.dependency_overrides.clear()
    graph_manager.clear()


@pytest.fixture()
def network_id(client) -> str:
    return client.post("/api/networks", json={"name": "Campus Network"}).json()["network_id"]


def make_node(client, network_id: str, name: str, node_type: str = "router") -> str:
    response = client.post(f"/api/networks/{network_id}/nodes", json={"name": name, "type": node_type})
    assert response.status_code == 201, response.text
    return response.json()["node_id"]


def link_payload(source: str, destination: str, **overrides) -> dict:
    return {"source": source, "destination": destination, "bandwidth": 100, "latency": 10, **overrides}
