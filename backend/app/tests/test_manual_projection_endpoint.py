"""Cobertura del módulo de proyección manual (admin)."""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parent)

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("SMTP_HOST", "smtp.test.local")
os.environ.setdefault("SMTP_USER", "user@test.local")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.local")

from app.main import app  # noqa: E402
from app.api import deps  # noqa: E402
from app.api.v1 import admin as admin_module  # noqa: E402
from app.schemas.manual_projection import ManualProjectionInput  # noqa: E402
from app.services import manual_projection_service as service_module  # noqa: E402


BASE_FORM = {
    "customer_full_name": "Ana Maria Perez Gomez",
    "customer_id_number": "1020304050",
    "customer_email": "Ana.Perez@Example.com",
    "customer_phone": "3001234567",
    "ingresos_mensuales": "4500000",
    "capacidad_pago_max": "1500000",
    "tipo_contrato_laboral": "Indefinido",
    "banco_id": "1",
    "numero_credito": "9876543210",
    "sistema_amortizacion": "pesos",
    "plan_credito": "Cuota constante en pesos",
    "fecha_extracto": "2026-06-30",
    "fecha_desembolso": "2019-06-30",
    "valor_prestado_inicial": "150000000",
    "saldo_capital_pesos": "120000000",
    "cuotas_pactadas": "240",
    "cuotas_pagadas": "84",
    "cuotas_pendientes": "156",
    # El cliente envía los números ya normalizados (punto decimal).
    "tasa_interes_cobrada_ea": "9.53",
    "valor_cuota_con_seguros": "1450000",
    "valor_cuota_sin_seguros": "1350000",
    "seguro_vida": "60000",
    "seguro_incendio": "40000",
}


class DummySession:
    """Sesión mínima: solo resuelve el banco y absorbe el ciclo de commit."""

    def get(self, model, _id):
        if model is service_module.Banco:
            return SimpleNamespace(id=_id, activo=True)
        return None

    def add(self, _obj):
        pass

    def flush(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def refresh(self, _obj):
        pass


def _build_input(**overrides) -> ManualProjectionInput:
    payload = {
        "customer_full_name": "Ana Perez",
        "customer_id_number": "1020304050",
        "customer_email": "ana@example.com",
        "customer_phone": "3001234567",
        "ingresos_mensuales": Decimal("4500000"),
        "banco_id": 1,
        "numero_credito": "987654",
        "sistema_amortizacion": "PESOS",
        "fecha_extracto": "2026-06-30",
        "valor_prestado_inicial": Decimal("150000000"),
        "saldo_capital_pesos": Decimal("120000000"),
        "cuotas_pactadas": 240,
        "cuotas_pagadas": 84,
        "cuotas_pendientes": 156,
        "tasa_interes_cobrada_ea": Decimal("9.53"),
        "valor_cuota_con_seguros": Decimal("1450000"),
    }
    payload.update(overrides)
    return ManualProjectionInput(**payload)


# ── Schema ────────────────────────────────────────────────────────────────────


def test_tasa_en_porcentaje_y_en_fraccion_producen_lo_mismo():
    assert _build_input(tasa_interes_cobrada_ea=Decimal("9.53")).tasa_interes_cobrada_ea == Decimal("0.0953")
    assert _build_input(tasa_interes_cobrada_ea=Decimal("0.0953")).tasa_interes_cobrada_ea == Decimal("0.0953")


def test_tasa_mayor_a_cien_es_rechazada():
    with pytest.raises(ValueError, match="no puede superar el 100"):
        _build_input(tasa_interes_cobrada_ea=Decimal("150"))


def test_cuotas_pagadas_mas_pendientes_no_superan_las_pactadas():
    with pytest.raises(ValueError, match="cuotas pactadas"):
        _build_input(cuotas_pagadas=200, cuotas_pendientes=100)


def test_uvr_exige_saldo_y_valor_de_la_uvr():
    with pytest.raises(ValueError, match="UVR"):
        _build_input(sistema_amortizacion="UVR")

    data = _build_input(
        sistema_amortizacion="UVR",
        saldo_capital_uvr=Decimal("149292.3850"),
        valor_uvr_fecha_extracto=Decimal("376.1794"),
    )
    assert data.is_uvr


def test_frech_marcado_exige_el_valor_mensual():
    with pytest.raises(ValueError, match="FRECH"):
        _build_input(tiene_beneficio_frech=True)


def test_sin_frech_se_limpian_los_campos_de_subsidio():
    data = _build_input(
        tiene_beneficio_frech=False,
        beneficio_frech_mensual=Decimal("200000"),
        total_frech_recibido=Decimal("16800000"),
    )
    assert data.beneficio_frech_mensual is None
    assert data.frech_acumulado == Decimal("0")


def test_plazo_por_defecto_es_el_numero_de_cuotas_pactadas():
    assert _build_input().plazo_total_meses == 240


def test_totales_derivados_cuando_no_se_declaran():
    data = _build_input(
        tiene_beneficio_frech=True,
        beneficio_frech_mensual=Decimal("200000"),
    )
    # cuota cliente = 1.450.000 - 200.000 = 1.250.000
    assert data.pagado_por_cliente == Decimal("1250000") * 84
    assert data.frech_acumulado == Decimal("200000") * 84
    assert data.total_abonado_credito == data.pagado_por_cliente + data.frech_acumulado
    assert data.declara_totales is False


def test_totales_declarados_mandan_sobre_la_estimacion():
    data = _build_input(
        tiene_beneficio_frech=True,
        beneficio_frech_mensual=Decimal("200000"),
        total_pagado_cliente=Decimal("99000000"),
        total_frech_recibido=Decimal("16800000"),
    )
    assert data.pagado_por_cliente == Decimal("99000000")
    assert data.frech_acumulado == Decimal("16800000")
    assert data.total_abonado_credito == Decimal("115800000")
    assert data.declara_totales is True


def test_seguros_total_mensual_suma_los_tres_componentes():
    data = _build_input(
        seguro_vida=Decimal("60000"),
        seguro_incendio=Decimal("40000"),
        seguro_terremoto=Decimal("10000"),
    )
    assert data.seguros_total_mensual == Decimal("110000")


# ── Endpoint ──────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(monkeypatch):
    """Cliente HTTP con admin autenticado y persistencia simulada."""
    created = {}

    class FakeUsersRepo:
        def __init__(self, db):
            self.db = db

        def get_by_identificacion(self, _identificacion):
            return None

        def get_by_email(self, _email):
            return None

        def ensure_role_assignment(self, user_id, role_code):
            created["role"] = (user_id, role_code)

    class FakeDocumentsRepo:
        def __init__(self, db):
            self.db = db

        def create(self, **kwargs):
            created["documento"] = kwargs
            return SimpleNamespace(id=uuid4(), **kwargs)

    class FakeAnalysesRepo:
        def __init__(self, db):
            self.db = db

        def create(self, **kwargs):
            created["analisis"] = kwargs
            return SimpleNamespace(id=uuid4(), **kwargs)

        def calculate_derived_fields(self, analisis):
            created["derived_called"] = True
            return analisis

    class FakePdfService:
        def validate_pdf(self, _stream, check_keywords=False):
            return SimpleNamespace(
                is_valid=True,
                status=service_module.PDFStatus.OK,
                message="ok",
            )

    class FakeStorage:
        def save_pdf(self, content, user_id, original_filename):
            return SimpleNamespace(
                success=True,
                file_size_bytes=len(content),
                file_path=f"{user_id}/{original_filename}",
                checksum="abc123",
                message="ok",
            )

    monkeypatch.setattr(service_module, "UsersRepo", FakeUsersRepo)
    monkeypatch.setattr(service_module, "DocumentsRepo", FakeDocumentsRepo)
    monkeypatch.setattr(service_module, "AnalysesRepo", FakeAnalysesRepo)
    monkeypatch.setattr(service_module, "PdfService", FakePdfService)
    monkeypatch.setattr(service_module, "get_storage_service", lambda: FakeStorage())
    def fake_usuario(**kwargs):
        return SimpleNamespace(id=uuid4(), **{"status": "INVITED", "email": None, **kwargs})

    monkeypatch.setattr(service_module, "Usuario", fake_usuario)

    app.dependency_overrides[deps.get_db] = lambda: DummySession()
    app.dependency_overrides[admin_module.verify_admin] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as client:
        yield client, created

    app.dependency_overrides.clear()


def _pdf_file():
    return {"file": ("extracto.pdf", b"%PDF-1.4 contenido", "application/pdf")}


def test_endpoint_crea_analisis_validado_manualmente(admin_client):
    client, created = admin_client

    response = client.post(
        "/api/v1/admin/analyses/manual-projection",
        data=BASE_FORM,
        files=_pdf_file(),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "VALIDATED_MANUAL"

    analisis = created["analisis"]
    assert analisis["status"] == "VALIDATED_MANUAL"
    assert analisis["sistema_amortizacion"] == "PESOS"  # normalizado desde "pesos"
    assert analisis["tasa_interes_cobrada_ea"] == Decimal("0.0953")
    assert analisis["seguros_total_mensual"] == Decimal("100000")
    assert analisis["cuotas_vencidas"] == 0
    assert analisis["monto_real_pagado_banco"] == (
        analisis["total_pagado_fecha"] + analisis["total_frech_recibido"]
    )
    assert analisis["is_total_paid_estimated"] is True
    assert created["derived_called"] is True


def test_endpoint_marca_totales_declarados_como_no_estimados(admin_client):
    client, created = admin_client

    payload = {
        **BASE_FORM,
        "tiene_beneficio_frech": "true",
        "beneficio_frech_mensual": "200000",
        "total_frech_recibido": "16800000",
        "total_pagado_cliente": "99000000",
        "nro_cuota_a_cancelar": "85",
    }

    response = client.post(
        "/api/v1/admin/analyses/manual-projection",
        data=payload,
        files=_pdf_file(),
    )

    assert response.status_code == 201, response.text
    analisis = created["analisis"]
    assert analisis["is_total_paid_estimated"] is False
    assert analisis["total_pagado_fecha"] == Decimal("99000000")
    assert analisis["total_frech_recibido"] == Decimal("16800000")
    assert analisis["monto_real_pagado_banco"] == Decimal("115800000")
    assert analisis["raw_data_json"]["nro_cuota_a_cancelar"] == 85


def test_endpoint_rechaza_cuotas_incoherentes(admin_client):
    client, _ = admin_client

    response = client.post(
        "/api/v1/admin/analyses/manual-projection",
        data={**BASE_FORM, "cuotas_pagadas": "200", "cuotas_pendientes": "100"},
        files=_pdf_file(),
    )

    assert response.status_code == 422
    assert "cuotas pactadas" in response.text


def test_endpoint_rechaza_uvr_sin_datos_uvr(admin_client):
    client, _ = admin_client

    response = client.post(
        "/api/v1/admin/analyses/manual-projection",
        data={**BASE_FORM, "sistema_amortizacion": "UVR"},
        files=_pdf_file(),
    )

    assert response.status_code == 422
    assert "UVR" in response.text
