import pytest
from datetime import datetime

from frontend_endpoints import app


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_diary_crud_flow(client):
    # create — minimal valid payload
    payload = {"timestamp": datetime.utcnow().isoformat(), "moodLevel": 3}
    r = client.post("/entries", json=payload)
    assert r.status_code == 201
    entry = r.get_json()
    entry_id = entry["id"]
    assert int(entry["moodLevel"]) == 3

    # read
    r2 = client.get(f"/entries/{entry_id}")
    assert r2.status_code == 200

    # update — change mood and add emotion
    r3 = client.put(f"/entries/{entry_id}", json={"moodLevel": 4, "emotions": ["happy"]})
    assert r3.status_code == 200
    assert int(r3.get_json()["moodLevel"]) == 4
    assert r3.get_json()["emotions"] == ["happy"]

    # delete
    r4 = client.delete(f"/entries/{entry_id}")
    assert r4.status_code == 204

    # ensure gone
    r5 = client.get(f"/entries/{entry_id}")
    assert r5.status_code == 404
