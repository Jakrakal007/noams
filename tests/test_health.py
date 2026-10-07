def test_health_endpoint(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "operational"
    assert payload["application"] == "NOAMS"
    assert payload["database"] == "connected"
