import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture()
def client():
    yield TestClient(app)

@pytest.fixture()
def network_id(client) -> str:
    return client.post("/api/networks", json={"name": "Campus Network"}).json()["network_id"]

def make_node(client, network_id: str, name: str, node_type: str = "router") -> str:
    response = client.post(f"/api/networks/{network_id}/nodes", json={"name": name, "type": node_type})
    return response.json()["node_id"]

def link_payload(source: str, destination: str, **overrides) -> dict:
    return {"source": source, "destination": destination, "bandwidth": 100, "latency": 10, **overrides}
