from __future__ import annotations

from fastapi.testclient import TestClient

from ccg_agent.main import app


def test_liveness_is_dependency_free() -> None:
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_openapi_declares_candidate_not_legal_advice() -> None:
    schema = TestClient(app).get("/openapi.json").json()
    assert "Not legal advice" in schema["info"]["description"]


def test_openapi_requires_idempotency_for_every_mutation_and_identity_for_reviews() -> None:
    schema = app.openapi()
    mutation_methods = {"post", "put", "patch", "delete"}
    mutations: list[tuple[str, str, dict]] = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method in mutation_methods:
                mutations.append((method, path, operation))

    assert mutations
    for method, path, operation in mutations:
        headers = {
            parameter["name"]
            for parameter in operation.get("parameters", [])
            if parameter.get("in") == "header"
        }
        assert "Idempotency-Key" in headers, f"{method.upper()} {path} lacks idempotency"
        if path.endswith("/review"):
            assert "X-Reviewer-Id" in headers, f"{method.upper()} {path} lacks reviewer identity"
            body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
            assert body_schema["$ref"].endswith("/HumanReviewRequest")

    review_schema = schema["components"]["schemas"]["HumanReviewRequest"]
    assert {"disposition", "rationale"}.issubset(review_schema["required"])
    assert review_schema["properties"]["rationale"]["minLength"] == 20
