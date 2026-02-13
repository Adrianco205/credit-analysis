from datetime import datetime
import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("SMTP_HOST", "smtp.test.local")
os.environ.setdefault("SMTP_USER", "user@test.local")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.local")

from app.main import app
from app.api import deps
from app.api.v1 import admin as admin_module
from app.schemas.admin_analysis import (
    AdminAnalysesListResponse,
    AdminAnalysisActions,
    AdminAnalysisBank,
    AdminAnalysisCustomer,
    AdminAnalysisFilters,
    AdminAnalysisItem,
    AdminAnalysisPagination,
    AdminBankOption,
)


class DummySession:
    pass


def _build_mock_response() -> AdminAnalysesListResponse:
    return AdminAnalysesListResponse(
        data=[
            AdminAnalysisItem(
                analysis_id=uuid4(),
                uploaded_at=datetime(2026, 2, 13, 10, 0, 0),
                document_id=uuid4(),
                credit_number="CR-001",
                status="COMPLETED",
                customer=AdminAnalysisCustomer(
                    user_id=uuid4(),
                    full_name="Admin Test Cliente",
                    id_number="1234567890",
                ),
                bank=AdminAnalysisBank(id=1, name="Bancolombia"),
                actions=AdminAnalysisActions(
                    can_view_summary=True,
                    can_view_detail=True,
                    can_view_pdf=True,
                ),
            )
        ],
        pagination=AdminAnalysisPagination(page=1, page_size=25, total=1, total_pages=1),
        filters=AdminAnalysisFilters(bank_options=[AdminBankOption(id=1, name="Bancolombia")]),
    )


def test_admin_analyses_requires_auth_header():
    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.get_db] = lambda: DummySession()

    client = TestClient(app)
    response = client.get("/api/v1/admin/analyses")

    assert response.status_code in (401, 403)

    app.dependency_overrides = {}


def test_admin_analyses_returns_403_for_non_admin():
    def non_admin_override():
        raise HTTPException(status_code=403, detail="No admin")

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.verify_admin] = non_admin_override

    client = TestClient(app)
    response = client.get("/api/v1/admin/analyses")

    assert response.status_code == 403

    app.dependency_overrides = {}


def test_admin_analyses_query_params_and_pagination(monkeypatch):
    captured = {}

    def fake_list(self, params):
        captured["page"] = params.page
        captured["page_size"] = params.page_size
        captured["customer_id_number"] = params.customer_id_number
        captured["customer_name"] = params.customer_name
        captured["credit_number"] = params.credit_number
        captured["bank_id"] = params.bank_id
        captured["uploaded_from"] = params.uploaded_from
        captured["uploaded_to"] = params.uploaded_to
        captured["sort_by"] = params.sort_by
        captured["sort_dir"] = params.sort_dir
        return _build_mock_response()

    monkeypatch.setattr(admin_module.AdminAnalysisService, "list_analyses", fake_list)

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.verify_admin] = lambda: object()

    client = TestClient(app)
    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "page": 2,
            "page_size": 50,
            "customer_id_number": "987",
            "customer_name": "juan",
            "credit_number": "CR",
            "bank_id": 3,
            "uploaded_from": "2026-01-01T00:00:00",
            "uploaded_to": "2026-01-31T23:59:59",
            "sort_by": "uploaded_at",
            "sort_dir": "asc",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 25
    assert body["pagination"]["total"] == 1
    assert len(body["data"]) == 1

    assert captured["page"] == 2
    assert captured["page_size"] == 50
    assert captured["customer_id_number"] == "987"
    assert captured["customer_name"] == "juan"
    assert captured["credit_number"] == "CR"
    assert captured["bank_id"] == 3
    assert captured["sort_by"] == "uploaded_at"
    assert captured["sort_dir"] == "asc"

    app.dependency_overrides = {}


def test_admin_analyses_invalid_sort_dir_falls_back_to_desc(monkeypatch):
    captured = {}

    def fake_list(self, params):
        captured["normalized_sort_dir"] = params.normalized_sort_dir
        return _build_mock_response()

    monkeypatch.setattr(admin_module.AdminAnalysisService, "list_analyses", fake_list)

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.verify_admin] = lambda: object()

    client = TestClient(app)
    response = client.get("/api/v1/admin/analyses", params={"sort_dir": "invalid"})

    assert response.status_code == 200
    assert captured["normalized_sort_dir"] == "desc"

    app.dependency_overrides = {}
