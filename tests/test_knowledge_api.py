from fastapi.testclient import TestClient

from app.main import app


def test_api_empty_query_error():
    client = TestClient(app)
    response = client.post("/api/search", json={"query": "", "top_k": 5})
    assert response.status_code in {400, 422}
