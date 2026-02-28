from types import SimpleNamespace
from uuid import uuid4
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parent)

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("SMTP_HOST", "smtp.test.local")
os.environ.setdefault("SMTP_USER", "user@test.local")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.local")

from app.main import app
from app.api import deps
from app.api.v1 import admin as admin_module


class DummySession:
    def get(self, model, _id):
        if model is admin_module.Banco:
            return SimpleNamespace(id=_id, activo=True)
        return None


def test_admin_upload_client_analysis_success(monkeypatch):
    captured = {}

    class FakeUsersRepo:
        def __init__(self, db):
            self.db = db

        def get_by_identificacion(self, identificacion: str):
            return None

        def get_by_email(self, email: str):
            return None

        def create_user(self, user):
            if not getattr(user, "id", None):
                user.id = uuid4()
            captured["created_user"] = user
            return user

        def ensure_role_assignment(self, user_id, role_code: str):
            captured["role_assignment"] = (str(user_id), role_code)

    class FakeDocumentsRepo:
        def __init__(self, db):
            self.db = db

        def create(self, **kwargs):
            captured["document_create"] = kwargs
            return SimpleNamespace(id=uuid4())

    class FakePdfService:
        def validate_pdf(self, file_stream, check_keywords=True):
            captured["check_keywords"] = check_keywords
            return SimpleNamespace(
                is_valid=True,
                status=admin_module.PDFStatus.OK,
                message="PDF válido",
                page_count=1,
                file_size_bytes=128,
                has_credit_keywords=False,
                keyword_confidence=0.0,
            )

        def decrypt_pdf(self, file_stream, password):
            return SimpleNamespace(success=False, status=admin_module.PDFStatus.INVALID_PASSWORD, message="Invalid")

    class FakeStorage:
        def save_pdf(self, content, user_id: str, original_filename: str):
            captured["save_pdf"] = {
                "user_id": user_id,
                "original_filename": original_filename,
                "bytes": len(content),
            }
            return SimpleNamespace(
                success=True,
                file_size_bytes=len(content),
                file_path=f"pdfs/{user_id}/archivo.pdf",
                checksum="checksum-test",
                message="ok",
            )

    class FakeAnalysisService:
        async def create_analysis_from_document(self, **kwargs):
            captured["analysis_kwargs"] = kwargs
            return SimpleNamespace(
                success=True,
                analisis=SimpleNamespace(id=uuid4(), status="EXTRACTED"),
                requires_manual_input=False,
                campos_faltantes=None,
                campos_extraidos=["saldo_capital_pesos"],
                name_mismatch=False,
                id_mismatch=False,
                invalid_document_type=False,
                tipo_documento_detectado=None,
            )

    monkeypatch.setattr(admin_module, "UsersRepo", FakeUsersRepo)
    monkeypatch.setattr(admin_module, "DocumentsRepo", FakeDocumentsRepo)
    monkeypatch.setattr(admin_module, "PdfService", FakePdfService)
    monkeypatch.setattr(admin_module, "get_storage_service", lambda: FakeStorage())
    monkeypatch.setattr(admin_module, "get_analysis_service", lambda db: FakeAnalysisService())

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.verify_admin] = lambda: SimpleNamespace(id=uuid4())

    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/clients/upload-analysis",
        data={
            "customer_full_name": "Cliente Prueba QA",
            "customer_id_number": "1234567890",
            "customer_email": "cliente.qa@example.com",
            "customer_phone": "3001234567",
            "ingresos_mensuales": "5000000",
            "capacidad_pago_max": "1500000",
            "tipo_contrato_laboral": "Indefinido",
            "banco_id": "1",
            "opcion_abono_1": "200000",
            "opcion_abono_2": "300000",
            "opcion_abono_3": "400000",
        },
        files={"file": ("extracto.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["analisis_id"] is not None

    assert captured["check_keywords"] is False
    assert captured["role_assignment"][1] == "CLIENT"
    assert captured["document_create"]["banco_id"] == 1
    assert captured["created_user"].status == "INVITED"
    assert captured["created_user"].email_verificado is False
    assert captured["created_user"].password_hash is None
    assert captured["analysis_kwargs"]["banco_id"] == 1
    assert captured["analysis_kwargs"]["skip_name_validation"] is True
    assert captured["analysis_kwargs"]["skip_id_validation"] is True
    assert captured["analysis_kwargs"]["allow_non_credit_document"] is True

    app.dependency_overrides = {}
