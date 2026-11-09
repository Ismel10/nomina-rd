from fastapi.testclient import TestClient

from nomina.api.main import create_app


def test_health_responde_ok_con_configuracion_regional() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["country"] == "DO"
    assert body["currency"] == "DOP"
