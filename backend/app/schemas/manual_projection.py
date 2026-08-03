"""Entrada canónica del módulo de proyección manual.

El admin transcribe aquí, campo por campo, la misma información que Gemini
extrae del extracto en el flujo automático.  Las validaciones son las mismas
que aplican las proyecciones normales, para que un análisis manual y uno
automático sean intercambiables aguas abajo.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Una tasa efectiva anual por encima de este umbral se asume digitada en
# porcentaje (7,47) en vez de en fracción (0,0747).
RATE_PERCENT_THRESHOLD = Decimal("1")
MAX_RATE_PERCENT = Decimal("100")

SISTEMAS_AMORTIZACION = {"PESOS", "UVR"}


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ManualProjectionInput(BaseModel):
    """Payload completo de una proyección cargada manualmente."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # ── Cliente ────────────────────────────────────────────────────────────
    customer_full_name: str = Field(..., min_length=3, max_length=200)
    customer_id_number: str = Field(..., min_length=5, max_length=30)
    customer_email: str = Field(..., min_length=5, max_length=255)
    customer_phone: str = Field(..., min_length=7, max_length=30)
    ingresos_mensuales: Decimal = Field(..., gt=0)
    capacidad_pago_max: Decimal | None = Field(None, ge=0)
    tipo_contrato_laboral: str | None = Field(None, max_length=80)

    # ── Identificación del crédito ─────────────────────────────────────────
    banco_id: int = Field(..., gt=0)
    numero_credito: str = Field(..., min_length=3, max_length=50)
    sistema_amortizacion: str = Field(..., min_length=3, max_length=20)
    plan_credito: str | None = Field(None, max_length=100)
    fecha_extracto: date
    fecha_desembolso: date | None = None
    plazo_total_meses: int | None = Field(None, gt=0)

    # ── Saldos ─────────────────────────────────────────────────────────────
    valor_prestado_inicial: Decimal = Field(..., gt=0)
    saldo_capital_pesos: Decimal = Field(..., gt=0)
    total_por_pagar: Decimal | None = Field(None, ge=0)

    # ── Cuotas ─────────────────────────────────────────────────────────────
    cuotas_pactadas: int = Field(..., gt=0)
    cuotas_pagadas: int = Field(..., ge=0)
    cuotas_pendientes: int = Field(..., gt=0)
    cuotas_vencidas: int = Field(0, ge=0)
    nro_cuota_a_cancelar: int | None = Field(None, ge=0)

    # ── Tasas (EA) ─────────────────────────────────────────────────────────
    tasa_interes_cobrada_ea: Decimal = Field(..., gt=0)
    tasa_interes_pactada_ea: Decimal | None = Field(None, ge=0)
    tasa_interes_subsidiada_ea: Decimal | None = Field(None, ge=0)
    tasa_mora_pactada_ea: Decimal | None = Field(None, ge=0)

    # ── Cuota mensual ──────────────────────────────────────────────────────
    valor_cuota_con_seguros: Decimal = Field(..., gt=0)
    valor_cuota_sin_seguros: Decimal | None = Field(None, ge=0)
    valor_cuota_con_subsidio: Decimal | None = Field(None, ge=0)

    # ── Beneficio FRECH ────────────────────────────────────────────────────
    tiene_beneficio_frech: bool = False
    beneficio_frech_mensual: Decimal | None = Field(None, ge=0)
    total_frech_recibido: Decimal | None = Field(None, ge=0)
    frech_fecha_inicio: date | None = None
    frech_fecha_fin: date | None = None

    # ── Pagos acumulados declarados ────────────────────────────────────────
    total_pagado_cliente: Decimal | None = Field(None, ge=0)

    # ── Datos UVR ──────────────────────────────────────────────────────────
    saldo_capital_uvr: Decimal | None = Field(None, ge=0)
    valor_uvr_fecha_extracto: Decimal | None = Field(None, ge=0)
    valor_cuota_uvr: Decimal | None = Field(None, ge=0)

    # ── Seguros mensuales ──────────────────────────────────────────────────
    seguro_vida: Decimal | None = Field(None, ge=0)
    seguro_incendio: Decimal | None = Field(None, ge=0)
    seguro_terremoto: Decimal | None = Field(None, ge=0)

    # ── Componentes del período ────────────────────────────────────────────
    capital_pagado_periodo: Decimal | None = Field(None, ge=0)
    intereses_corrientes_periodo: Decimal | None = Field(None, ge=0)
    intereses_mora: Decimal | None = Field(None, ge=0)
    otros_cargos: Decimal | None = Field(None, ge=0)

    # ── Preferencias de abono ──────────────────────────────────────────────
    opcion_abono_1: Decimal | None = Field(None, gt=0)
    opcion_abono_2: Decimal | None = Field(None, gt=0)
    opcion_abono_3: Decimal | None = Field(None, gt=0)

    @field_validator("*", mode="before")
    @classmethod
    def _empty_string_is_null(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @field_validator("cuotas_vencidas", mode="before")
    @classmethod
    def _default_cuotas_vencidas(cls, value: Any) -> Any:
        return 0 if value is None else value

    @field_validator("tiene_beneficio_frech", mode="before")
    @classmethod
    def _default_tiene_frech(cls, value: Any) -> Any:
        return False if value is None else value

    @field_validator("customer_email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("El correo del cliente no es válido")
        return normalized

    @field_validator("sistema_amortizacion")
    @classmethod
    def _normalize_sistema(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SISTEMAS_AMORTIZACION:
            raise ValueError("El sistema de amortización debe ser PESOS o UVR")
        return normalized

    @field_validator(
        "tasa_interes_cobrada_ea",
        "tasa_interes_pactada_ea",
        "tasa_interes_subsidiada_ea",
        "tasa_mora_pactada_ea",
    )
    @classmethod
    def _normalize_rate(cls, value: Decimal | None) -> Decimal | None:
        """Acepta 7,47 y 0,0747; siempre persiste la fracción."""
        if value is None:
            return None
        if value > MAX_RATE_PERCENT:
            raise ValueError("Una tasa efectiva anual no puede superar el 100%")
        return value / MAX_RATE_PERCENT if value > RATE_PERCENT_THRESHOLD else value

    @property
    def is_uvr(self) -> bool:
        return self.sistema_amortizacion == "UVR"

    @model_validator(mode="after")
    def _validate_business_rules(self) -> "ManualProjectionInput":
        if self.cuotas_pagadas + self.cuotas_pendientes > self.cuotas_pactadas:
            raise ValueError(
                "La suma de cuotas pagadas y cuotas por pagar no puede superar las cuotas pactadas"
            )

        if self.cuotas_vencidas > self.cuotas_pendientes:
            raise ValueError("Las cuotas vencidas no pueden superar las cuotas por pagar")

        if self.plazo_total_meses is None:
            self.plazo_total_meses = self.cuotas_pactadas

        if self.fecha_desembolso and self.fecha_desembolso > self.fecha_extracto:
            raise ValueError("La fecha del extracto no puede ser anterior al desembolso")

        if self.frech_fecha_inicio and self.frech_fecha_fin and self.frech_fecha_fin < self.frech_fecha_inicio:
            raise ValueError("La vigencia FRECH termina antes de iniciar")

        if self.is_uvr and (self.saldo_capital_uvr is None or self.valor_uvr_fecha_extracto is None):
            raise ValueError(
                "Un crédito UVR requiere el saldo de capital en UVR y el valor de la UVR a la fecha del extracto"
            )

        if self.tiene_beneficio_frech:
            if not self.beneficio_frech_mensual or self.beneficio_frech_mensual <= 0:
                raise ValueError(
                    "Indicaste que el crédito tiene FRECH: registra el valor mensual del beneficio"
                )
        else:
            # Un crédito sin FRECH no arrastra residuos de subsidio.
            self.beneficio_frech_mensual = None
            self.total_frech_recibido = None
            self.frech_fecha_inicio = None
            self.frech_fecha_fin = None

        if (
            self.beneficio_frech_mensual
            and self.beneficio_frech_mensual >= self.valor_cuota_con_seguros
        ):
            raise ValueError("El beneficio FRECH no puede ser mayor o igual a la cuota completa")

        if self.valor_cuota_sin_seguros and self.valor_cuota_sin_seguros > self.valor_cuota_con_seguros:
            raise ValueError("La cuota sin seguros no puede superar la cuota con seguros")

        return self

    @property
    def seguros_total_mensual(self) -> Decimal:
        return (
            (self.seguro_vida or Decimal("0"))
            + (self.seguro_incendio or Decimal("0"))
            + (self.seguro_terremoto or Decimal("0"))
        )

    @property
    def opciones_abono_preferidas(self) -> list[Decimal] | None:
        opciones = [
            opcion
            for opcion in (self.opcion_abono_1, self.opcion_abono_2, self.opcion_abono_3)
            if opcion is not None
        ]
        return opciones or None

    @property
    def frech_acumulado(self) -> Decimal:
        """Lo que el gobierno ha aportado al crédito hasta el extracto."""
        if self.total_frech_recibido is not None:
            return self.total_frech_recibido
        if self.beneficio_frech_mensual:
            return self.beneficio_frech_mensual * Decimal(self.cuotas_pagadas)
        return Decimal("0")

    @property
    def pagado_por_cliente(self) -> Decimal:
        """Lo que el cliente ha desembolsado de su bolsillo hasta el extracto."""
        if self.total_pagado_cliente is not None:
            return self.total_pagado_cliente
        cuota_cliente = self.valor_cuota_con_subsidio
        if cuota_cliente is None:
            cuota_cliente = max(
                self.valor_cuota_con_seguros - (self.beneficio_frech_mensual or Decimal("0")),
                Decimal("0"),
            )
        return cuota_cliente * Decimal(self.cuotas_pagadas)

    @property
    def total_abonado_credito(self) -> Decimal:
        """Total recibido por el banco: aporte del cliente + subsidio FRECH."""
        return self.pagado_por_cliente + self.frech_acumulado

    @property
    def declara_totales(self) -> bool:
        return self.total_pagado_cliente is not None or self.total_frech_recibido is not None
