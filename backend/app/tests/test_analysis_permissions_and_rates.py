import os
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("SMTP_HOST", "smtp.test.local")
os.environ.setdefault("SMTP_USER", "user@test.local")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.local")

from app.main import app
from app.api import deps
from app.api.v1 import analyses as analyses_module
from app.api.v1 import admin as admin_module


class DummySession:
    pass


def test_generate_projections_allows_authenticated_non_admin(monkeypatch):
    class FakeService:
        def generate_projections(self, analisis_id, opciones, usuario_id):
            _ = (analisis_id, opciones, usuario_id)
            propuesta = SimpleNamespace(
                id=uuid4(),
                numero_opcion=1,
                nombre_opcion="Opción 1",
                abono_adicional_mensual=Decimal("300000"),
                cuotas_nuevas=120,
                tiempo_restante_anios=10,
                tiempo_restante_meses=0,
                cuotas_reducidas=24,
                tiempo_ahorrado_anios=2,
                tiempo_ahorrado_meses=0,
                nuevo_valor_cuota=Decimal("1600000"),
                total_por_pagar_aprox=Decimal("120000000"),
                valor_ahorrado_intereses=Decimal("18000000"),
                veces_pagado=Decimal("1.80"),
                honorarios_calculados=Decimal("540000"),
                honorarios_con_iva=Decimal("642600"),
                ingreso_minimo_requerido=Decimal("5333333.33"),
                origen="USER",
                es_opcion_seleccionada=False,
            )
            return SimpleNamespace(success=True, propuestas=[propuesta])

    fake_user = SimpleNamespace(id=uuid4())

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[analyses_module.get_db] = lambda: DummySession()
    app.dependency_overrides[deps.get_current_user] = lambda: fake_user
    app.dependency_overrides[analyses_module.get_current_user] = lambda: fake_user
    monkeypatch.setattr(analyses_module, "get_analysis_service", lambda db: FakeService())

    client = TestClient(app)
    response = client.post(
        f"/api/v1/analyses/{uuid4()}/projections",
        json={
            "opciones": [
                {
                    "numero_opcion": 1,
                    "abono_adicional_mensual": "300000"
                }
            ]
        },
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["numero_opcion"] == 1
    assert body[0]["origen"] == "USER"

    app.dependency_overrides = {}


def test_manual_request_normalizes_percentage_rates():
    request = analyses_module.UpdateManualFieldsRequest(
        tasa_interes_pactada_ea=Decimal("9.53"),
        tasa_interes_cobrada_ea=Decimal("4.71"),
    )

    assert request.tasa_interes_pactada_ea == Decimal("0.0953")
    assert request.tasa_interes_cobrada_ea == Decimal("0.0471")


def test_admin_update_request_normalizes_percentage_rates():
    request = admin_module.AdminUpdateAnalysisRequest(
        tasa_interes_cobrada_ea=Decimal("12.5")
    )

    assert request.tasa_interes_cobrada_ea == Decimal("0.125")
