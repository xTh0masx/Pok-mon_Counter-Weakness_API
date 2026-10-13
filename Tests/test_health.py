def test_health(client, upstream):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert not upstream["calls"]


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_degraded(client, upstream):
    upstream["fail"] = True
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["fallback_available"] is True


def test_docs_and_openapi(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/analyze" in schema["paths"]
    assert "AnalysisRequest" in schema["components"]["schemas"]


def test_interface_and_assets_are_served_without_upstream(client, upstream):
    response = client.get("/")
    assert response.status_code == 200
    assert "Pokémon Counter Lab" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/static/styles.css").status_code == 200
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "/api/v1/analyze" in script.text
    assert not upstream["calls"]
