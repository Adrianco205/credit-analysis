from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.repositories.propuestas_repo import PropuestasRepo


class TestPropuestasRepoProjectionFields:
    """Validaciones de persistencia para campos financieros de proyeccion."""

    def test_filter_model_fields_keeps_projection_columns(self):
        payload = {
            "analisis_id": "test-id",
            "numero_opcion": 1,
            "nombre_opcion": "1a Eleccion",
            "abono_adicional_mensual": Decimal("149658"),
            "nuevo_valor_cuota": Decimal("673085"),
            "total_por_pagar_aprox": Decimal("116444705.00"),
            "costo_total_proyectado": Decimal("116128948.66"),
            "costo_total_proyectado_banco": Decimal("133031628.66"),
            "total_subsidio_frech_proyectado": Decimal("16902680.00"),
            "valor_ahorrado_intereses": Decimal("33903586.28"),
            "veces_pagado": Decimal("1.88"),
            "honorarios_calculados": Decimal("2034215.18"),
            "honorarios_con_iva": Decimal("2420716.06"),
            "ingreso_minimo_requerido": Decimal("2243616.67"),
            "campo_no_existente": "debe-filtrarse",
        }

        filtered = PropuestasRepo._filter_model_fields(payload)

        assert "campo_no_existente" not in filtered
        assert filtered["total_por_pagar_aprox"] == Decimal("116444705.00")
        assert filtered["costo_total_proyectado"] == Decimal("116128948.66")
        assert filtered["costo_total_proyectado_banco"] == Decimal("133031628.66")
        assert filtered["total_subsidio_frech_proyectado"] == Decimal("16902680.00")

    def test_update_calculo_updates_all_projection_cost_fields(self):
        db = MagicMock()
        repo = PropuestasRepo(db)

        propuesta = SimpleNamespace(
            cuotas_nuevas=None,
            tiempo_restante_anios=None,
            tiempo_restante_meses=None,
            cuotas_reducidas=None,
            tiempo_ahorrado_anios=None,
            tiempo_ahorrado_meses=None,
            nuevo_valor_cuota=None,
            total_por_pagar_aprox=None,
            costo_total_proyectado=None,
            costo_total_proyectado_banco=None,
            total_subsidio_frech_proyectado=None,
            valor_ahorrado_intereses=None,
            veces_pagado=None,
            honorarios_calculados=None,
            honorarios_con_iva=None,
            ingreso_minimo_requerido=None,
        )

        resultado = {
            "cuotas_nuevas": 173,
            "tiempo_restante_anios": 14,
            "tiempo_restante_meses": 5,
            "cuotas_reducidas": 132,
            "tiempo_ahorrado_anios": 11,
            "tiempo_ahorrado_meses": 0,
            "nuevo_valor_cuota": Decimal("673085"),
            "total_por_pagar_aprox": Decimal("116444705.00"),
            "costo_total_proyectado": Decimal("116128948.66"),
            "costo_total_proyectado_banco": Decimal("133031628.66"),
            "total_subsidio_frech_proyectado": Decimal("16902680.00"),
            "valor_ahorrado_intereses": Decimal("33903586.28"),
            "veces_pagado": Decimal("1.88"),
            "honorarios_calculados": Decimal("2034215.18"),
            "honorarios_con_iva": Decimal("2420716.06"),
            "ingreso_minimo_requerido": Decimal("2243616.67"),
        }

        updated = repo.update_calculo(propuesta, resultado)

        assert updated.total_por_pagar_aprox == Decimal("116444705.00")
        assert updated.costo_total_proyectado == Decimal("116128948.66")
        assert updated.costo_total_proyectado_banco == Decimal("133031628.66")
        assert updated.total_subsidio_frech_proyectado == Decimal("16902680.00")
        db.flush.assert_called_once()
