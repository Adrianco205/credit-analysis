"""Tests de compatibilidad legacy para normalizacion de respuestas de proyecciones."""

import os
import uuid
from decimal import Decimal

# Variables minimas para inicializar settings en imports de API
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "testsecretkey12345678901234567890")
os.environ.setdefault("SMTP_HOST", "smtp.test.com")
os.environ.setdefault("SMTP_USER", "test@test.com")
os.environ.setdefault("SMTP_PASSWORD", "testpassword")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.com")

from app.api.v1.admin import ProjectionAdminResponse
from app.api.v1.analyses import ProjectionResponse


def _base_payload() -> dict:
    return {
        "id": uuid.uuid4(),
        "analisis_id": uuid.uuid4(),
        "numero_opcion": 1,
        "nombre_opcion": "1a Eleccion",
        "abono_adicional_mensual": Decimal("100000"),
        "cuotas_nuevas": 100,
        "tiempo_restante_anios": 8,
        "tiempo_restante_meses": 4,
        "cuotas_reducidas": 20,
        "tiempo_ahorrado_anios": 1,
        "tiempo_ahorrado_meses": 8,
        "nuevo_valor_cuota": Decimal("700000"),
        "total_por_pagar_aprox": Decimal("70000000"),
        "total_por_pagar_simple": None,
        "costo_total_proyectado": None,
        "costo_total_proyectado_banco": None,
        "total_subsidio_frech_proyectado": Decimal("0"),
        "valor_ahorrado_intereses": Decimal("1000000"),
        "veces_pagado": Decimal("1.13"),
        "honorarios_calculados": Decimal("60000"),
        "honorarios_con_iva": Decimal("71400"),
        "ingreso_minimo_requerido": Decimal("2333333.33"),
        "origen": "USER",
        "es_opcion_seleccionada": False,
        "created_at": None,
    }


def test_projection_admin_response_maintains_legacy_fallbacks():
    payload = _base_payload()
    model = ProjectionAdminResponse(**payload)

    # Deriva total simple si no viene
    assert model.total_por_pagar_simple == Decimal("70000000.00")
    # Como costo_total_proyectado venia null y aprox != simple antes de normalizar,
    # conserva compatibilidad legacy asignando costo desde aprox original.
    assert model.costo_total_proyectado == Decimal("70000000")
    # Si no viene costo banco, cae a costo cliente.
    assert model.costo_total_proyectado_banco == model.costo_total_proyectado


def test_projection_response_maintains_legacy_fallbacks():
    payload = _base_payload()
    payload.pop("analisis_id")
    payload.pop("created_at")

    model = ProjectionResponse(**payload)

    assert model.total_por_pagar_simple == Decimal("70000000.00")
    assert model.costo_total_proyectado == Decimal("70000000")
    assert model.costo_total_proyectado_banco == model.costo_total_proyectado
