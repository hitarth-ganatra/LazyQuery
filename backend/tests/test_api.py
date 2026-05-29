from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app, db_service, nl2sql_service
from app.services.db import TableColumn


@pytest.fixture(autouse=True)
def reset_dependency_state() -> None:
    db_service.pool = None


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_tables_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    schema = {
        "orders": [
            TableColumn(table_name="orders", column_name="id", data_type="integer"),
            TableColumn(table_name="orders", column_name="amount", data_type="numeric"),
        ]
    }
    monkeypatch.setattr(db_service, "fetch_schema", AsyncMock(return_value=schema))

    with TestClient(app) as client:
        response = client.get("/api/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": [{"name": "orders", "columns": ["id", "amount"]}]}


def test_table_rows_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        db_service,
        "fetch_table_rows",
        AsyncMock(return_value=(['id', 'name'], [{'id': 1, 'name': 'A'}], 1)),
    )

    with TestClient(app) as client:
        response = client.get('/api/tables/customers/rows?limit=10&offset=0')

    assert response.status_code == 200
    payload = response.json()
    assert payload['table'] == 'customers'
    assert payload['row_count'] == 1
    assert payload['total_rows'] == 1


def test_table_rows_endpoint_requires_both_filter_fields() -> None:
    with TestClient(app) as client:
        response = client.get('/api/tables/customers/rows?filter_column=name')

    assert response.status_code == 400
    assert 'required together' in response.json()['detail']


def test_query_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    schema = AsyncMock()
    monkeypatch.setattr(db_service, "fetch_schema", AsyncMock(return_value=schema))
    monkeypatch.setattr(
        nl2sql_service,
        "generate_sql",
        AsyncMock(return_value=("SELECT category, SUM(amount) AS total FROM orders GROUP BY category", "Show revenue", [])),
    )
    monkeypatch.setattr(
        db_service,
        "execute_readonly",
        AsyncMock(return_value=(["category", "total"], [{"category": "A", "total": 10}])),
    )

    with TestClient(app) as client:
        response = client.post("/api/query", json={"prompt": "Show revenue by category", "limit": 25, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["columns"] == ["category", "total"]
    assert payload["row_count"] == 1
    assert payload["chart"]["chart_type"] == "bar"


def test_query_endpoint_rejects_invalid_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    schema = AsyncMock()
    monkeypatch.setattr(db_service, "fetch_schema", AsyncMock(return_value=schema))
    monkeypatch.setattr(nl2sql_service, "generate_sql", AsyncMock(return_value=("DROP TABLE orders", "Delete data", [])))

    with TestClient(app) as client:
        response = client.post("/api/query", json={"prompt": "Delete data", "limit": 25, "offset": 0})

    assert response.status_code == 400
    assert "Only SELECT statements are permitted" in response.json()["detail"]
