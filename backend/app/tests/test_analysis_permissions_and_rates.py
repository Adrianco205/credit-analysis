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


def test_projection_response_prefers_current_semantics_when_present():
    payload = {
        "id": uuid4(),
        "numero_opcion": 1,
        "nombre_opcion": "1a Eleccion",
        "abono_adicional_mensual": Decimal("149658"),
        "cuotas_nuevas": 173,
        "tiempo_restante_anios": 14,
        "tiempo_restante_meses": 5,
        "cuotas_reducidas": 132,
        "tiempo_ahorrado_anios": 11,
        "tiempo_ahorrado_meses": 0,
        "nuevo_valor_cuota": Decimal("673085"),
        "total_por_pagar_aprox": Decimal("116444705.00"),
        "total_por_pagar_simple": Decimal("116444705.00"),
        "costo_total_proyectado": Decimal("116128948.66"),
        "costo_total_proyectado_banco": Decimal("133031628.66"),
        "total_subsidio_frech_proyectado": Decimal("16902680.00"),
        "valor_ahorrado_intereses": Decimal("33903586.28"),
        "veces_pagado": Decimal("1.88"),
        "honorarios_calculados": Decimal("2034215.18"),
        "honorarios_con_iva": Decimal("2420716.06"),
        "ingreso_minimo_requerido": Decimal("2243616.67"),
        "origen": "USER",
        "es_opcion_seleccionada": False,
    }

    response = analyses_module.ProjectionResponse.model_validate(payload)

    assert response.total_por_pagar_aprox == Decimal("116444705.00")
    assert response.costo_total_proyectado == Decimal("116128948.66")
    assert response.costo_total_proyectado_banco == Decimal("133031628.66")


def test_projection_response_legacy_maps_total_por_pagar_aprox_to_projected_cost():
    payload = {
        "id": uuid4(),
        "numero_opcion": 1,
        "nombre_opcion": "Legacy",
        "abono_adicional_mensual": Decimal("200000"),
        "cuotas_nuevas": 120,
        "tiempo_restante_anios": 10,
        "tiempo_restante_meses": 0,
        "cuotas_reducidas": 24,
        "tiempo_ahorrado_anios": 2,
        "tiempo_ahorrado_meses": 0,
        "nuevo_valor_cuota": Decimal("1600000"),
        # Valor legacy: campo usado antiguamente para costo real.
        "total_por_pagar_aprox": Decimal("181234567.89"),
        "valor_ahorrado_intereses": Decimal("18000000"),
        "veces_pagado": Decimal("1.80"),
        "honorarios_calculados": Decimal("540000"),
        "honorarios_con_iva": Decimal("642600"),
        "ingreso_minimo_requerido": Decimal("5333333.33"),
        "origen": "USER",
        "es_opcion_seleccionada": False,
    }

    response = analyses_module.ProjectionResponse.model_validate(payload)

    # Se conserva compatibilidad: costo proyectado se infiere del campo legacy.
    assert response.costo_total_proyectado == Decimal("181234567.89")
    # Y el simple se deriva con nueva_cuota x cuotas para no contaminar UI.
    assert response.total_por_pagar_simple == Decimal("192000000.00")
    assert response.total_por_pagar_aprox == Decimal("192000000.00")


def test_projection_admin_response_legacy_mapping_matches_user_mapping():
    payload = {
        "id": uuid4(),
        "analisis_id": uuid4(),
        "numero_opcion": 2,
        "nombre_opcion": "Legacy Admin",
        "abono_adicional_mensual": Decimal("300000"),
        "cuotas_nuevas": 100,
        "tiempo_restante_anios": 8,
        "tiempo_restante_meses": 4,
        "cuotas_reducidas": 40,
        "tiempo_ahorrado_anios": 3,
        "tiempo_ahorrado_meses": 4,
        "nuevo_valor_cuota": Decimal("1900000"),
        "total_por_pagar_aprox": Decimal("175000000"),
        "valor_ahorrado_intereses": Decimal("22000000"),
        "veces_pagado": Decimal("1.72"),
        "honorarios_calculados": Decimal("1320000"),
        "honorarios_con_iva": Decimal("1570800"),
        "ingreso_minimo_requerido": Decimal("6333333.33"),
        "origen": "ADMIN",
        "es_opcion_seleccionada": False,
        "created_at": None,
    }

    response = admin_module.ProjectionAdminResponse.model_validate(payload)

    assert response.costo_total_proyectado == Decimal("175000000")
    assert response.total_por_pagar_simple == Decimal("190000000.00")
    assert response.total_por_pagar_aprox == Decimal("190000000.00")
