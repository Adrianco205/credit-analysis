"""
Motor UVR de simulacion mes a mes para ahorro real de intereses.

Este modulo implementa comparacion de escenarios:
- Escenario A: credito original sin abono adicional
- Escenario B: credito con abono adicional mensual

Principio clave:
    ahorro_intereses_real = sum(intereses_original) - sum(intereses_con_abono)

No usa como metrica principal la diferencia entre totales pagados,
porque en UVR el capital evoluciona con inflacion y el costo futuro no es fijo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List

PRECISION_MONEY = Decimal("0.01")
PRECISION_RATE = Decimal("0.00000001")
EPSILON_BALANCE = Decimal("0.01")
DEFAULT_MAX_MESES = 1200
DEFAULT_FRECH_MAX_MESES = 84


@dataclass(frozen=True)
class UvrProjectionInput:
    saldo_inicial: Decimal
    tasa_efectiva_anual: Decimal
    plazo_meses: int
    cuota_actual: Decimal
    abono_adicional: Decimal
    uvr_actual: Decimal
    inflacion_anual_estimada: Decimal
    tasa_efectiva_anual_subsidiada: Decimal | None = None
    subsidio_frech: Decimal = Decimal("0")
    seguro_mensual: Decimal = Decimal("0")
    cuota_uvr_actual: Decimal | None = None
    frech_meses_restantes: int | None = None
    max_meses_simulacion: int = DEFAULT_MAX_MESES


@dataclass(frozen=True)
class UvrMonthlyRow:
    mes: int
    uvr_mes: Decimal
    saldo_inicial_pesos: Decimal
    interes_mes: Decimal
    capital_mes: Decimal
    seguro_mes: Decimal
    subsidio_frech_mes: Decimal
    pago_cliente_mes: Decimal
    pago_banco_mes: Decimal
    saldo_final_pesos: Decimal


@dataclass(frozen=True)
class UvrScenarioResult:
    meses_totales: int
    total_pagado_cliente: Decimal
    total_pagado_banco: Decimal
    intereses_totales: Decimal
    capital_total_amortizado: Decimal
    saldo_final_pesos: Decimal
    mes_inicio_amortizacion_significativa: int | None
    terminado: bool
    tabla: List[UvrMonthlyRow]


@dataclass(frozen=True)
class UvrComparisonResult:
    ahorro_intereses_real: Decimal
    ahorro_intereses_real_ajustado_inflacion: Decimal
    meses_reducidos: int
    total_pagado_original: Decimal
    total_pagado_con_abono: Decimal
    intereses_original: Decimal
    intereses_con_abono: Decimal
    mes_inicio_amortizacion_significativa_original: int | None
    mes_inicio_amortizacion_significativa_con_abono: int | None
    escenario_original: UvrScenarioResult
    escenario_con_abono: UvrScenarioResult


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(PRECISION_MONEY, rounding=ROUND_HALF_UP)


def tasa_ea_a_mensual(tasa_efectiva_anual: Decimal) -> Decimal:
    """Convierte tasa efectiva anual a tasa mensual efectiva."""
    if tasa_efectiva_anual <= 0:
        return Decimal("0")

    tasa_normalizada = tasa_efectiva_anual / Decimal("100") if tasa_efectiva_anual > 1 else tasa_efectiva_anual
    mensual = Decimal(str((1 + float(tasa_normalizada)) ** (1 / 12))) - Decimal("1")
    return mensual.quantize(PRECISION_RATE)


def inflacion_anual_a_mensual_lineal(inflacion_anual: Decimal) -> Decimal:
    """Convierte inflacion anual a factor lineal mensual: inflacion/12."""
    if inflacion_anual <= 0:
        return Decimal("0")

    inflacion_normalizada = inflacion_anual / Decimal("100") if inflacion_anual > 1 else inflacion_anual
    return (inflacion_normalizada / Decimal("12")).quantize(PRECISION_RATE)


def simulate_uvr_scenario(
    data: UvrProjectionInput,
    abono_adicional_override: Decimal | None = None,
) -> UvrScenarioResult:
    """
    Simula mes a mes la evolucion del credito UVR.

    Reglas de simulacion:
    1. UVR crece cada mes con inflacion mensual estimada.
    2. Interes del mes se calcula sobre saldo indexado en pesos.
    3. La cuota base se indexa con UVR cuando se dispone de cuota en UVR.
    4. FRECH solo aplica durante su vigencia (meses restantes o tope default).
    5. Seguro mensual se suma al flujo del cliente, pero no amortiza capital.

    Nota de negocio:
    El subsidio FRECH se modela como flujo separado de costo banco (reporting),
    no como abono extra al capital; de lo contrario se sobre-amortiza el credito.
    """
    if data.saldo_inicial <= 0:
        raise ValueError("saldo_inicial debe ser mayor a cero")
    if data.uvr_actual <= 0:
        raise ValueError("uvr_actual debe ser mayor a cero")
    if data.cuota_actual <= 0:
        raise ValueError("cuota_actual debe ser mayor a cero")
    if data.plazo_meses <= 0:
        raise ValueError("plazo_meses debe ser mayor a cero")

    abono_adicional = data.abono_adicional if abono_adicional_override is None else abono_adicional_override
    if abono_adicional < 0:
        raise ValueError("abono_adicional no puede ser negativo")

    tasa_mensual = tasa_ea_a_mensual(data.tasa_efectiva_anual)
    tasa_mensual_subsidiada = (
        tasa_ea_a_mensual(data.tasa_efectiva_anual_subsidiada)
        if data.tasa_efectiva_anual_subsidiada is not None and data.tasa_efectiva_anual_subsidiada > 0
        else None
    )
    inflacion_mensual = inflacion_anual_a_mensual_lineal(data.inflacion_anual_estimada)

    cuota_uvr_actual = data.cuota_uvr_actual
    if cuota_uvr_actual is None and data.uvr_actual > 0:
        cuota_uvr_actual = data.cuota_actual / data.uvr_actual

    frech_meses_restantes = data.frech_meses_restantes
    if frech_meses_restantes is None:
        frech_meses_restantes = DEFAULT_FRECH_MAX_MESES
    try:
        frech_meses_restantes = max(0, int(frech_meses_restantes))
    except (TypeError, ValueError):
        frech_meses_restantes = DEFAULT_FRECH_MAX_MESES

    saldo_uvr = (data.saldo_inicial / data.uvr_actual)
    uvr_mes = data.uvr_actual

    tabla: List[UvrMonthlyRow] = []
    total_intereses = Decimal("0")
    total_pagado_cliente = Decimal("0")
    total_pagado_banco = Decimal("0")
    total_capital = Decimal("0")
    mes_inicio_amortizacion_significativa: int | None = None

    for mes in range(1, data.max_meses_simulacion + 1):
        if saldo_uvr * uvr_mes <= EPSILON_BALANCE:
            break

        # Evolucion UVR mensual.
        uvr_mes = (uvr_mes * (Decimal("1") + inflacion_mensual)).quantize(PRECISION_RATE)

        saldo_inicial_pesos = _quantize_money(saldo_uvr * uvr_mes)
        tasa_mes = tasa_mensual
        if tasa_mensual_subsidiada is not None and mes <= frech_meses_restantes:
            tasa_mes = tasa_mensual_subsidiada

        interes_mes = _quantize_money(saldo_inicial_pesos * tasa_mes)

        cuota_uvr_es_solo_deuda = cuota_uvr_actual is not None and cuota_uvr_actual > 0

        if cuota_uvr_es_solo_deuda:
            cuota_total_mes = _quantize_money(cuota_uvr_actual * uvr_mes)
        else:
            cuota_total_mes = _quantize_money(data.cuota_actual)

        # Si existe cuota UVR explicita, se asume cuota de deuda (sin seguros).
        # En caso contrario, cuota_actual suele venir con seguros y se separa
        # el componente amortizable para no inflar el pago a deuda.
        if cuota_uvr_es_solo_deuda:
            cuota_deuda_mes = cuota_total_mes
        else:
            cuota_deuda_mes = _quantize_money(max(cuota_total_mes - data.seguro_mensual, Decimal("0")))

        subsidio_frech_mes = data.subsidio_frech if mes <= frech_meses_restantes else Decimal("0")
        subsidio_frech_mes = _quantize_money(subsidio_frech_mes)

        seguro_cliente_mes = data.seguro_mensual if cuota_uvr_es_solo_deuda else Decimal("0")
        pago_cliente_mes = _quantize_money(cuota_total_mes + seguro_cliente_mes + abono_adicional)
        pago_para_deuda = _quantize_money(cuota_deuda_mes + abono_adicional)
        pago_banco_mes = _quantize_money(pago_para_deuda + data.seguro_mensual + subsidio_frech_mes)

        capital_mes = _quantize_money(pago_para_deuda - interes_mes)

        if capital_mes <= Decimal("0"):
            capital_mes = Decimal("0.00")

        # Ajuste de ultima cuota para no amortizar por encima del saldo.
        if capital_mes > saldo_inicial_pesos:
            capital_mes = saldo_inicial_pesos
            pago_para_deuda = _quantize_money(interes_mes + capital_mes)
            pago_banco_mes = _quantize_money(pago_para_deuda + data.seguro_mensual + subsidio_frech_mes)
            pago_cliente_mes = _quantize_money(pago_para_deuda + seguro_cliente_mes)

        saldo_final_pesos = _quantize_money(max(saldo_inicial_pesos - capital_mes, Decimal("0")))

        capital_uvr = (capital_mes / uvr_mes) if uvr_mes > 0 else Decimal("0")
        saldo_uvr = max(saldo_uvr - capital_uvr, Decimal("0"))

        total_intereses += interes_mes
        total_pagado_cliente += pago_cliente_mes
        total_pagado_banco += pago_banco_mes
        total_capital += capital_mes

        if mes_inicio_amortizacion_significativa is None and capital_mes >= interes_mes:
            mes_inicio_amortizacion_significativa = mes

        tabla.append(
            UvrMonthlyRow(
                mes=mes,
                uvr_mes=uvr_mes,
                saldo_inicial_pesos=saldo_inicial_pesos,
                interes_mes=interes_mes,
                capital_mes=capital_mes,
                seguro_mes=_quantize_money(data.seguro_mensual),
                subsidio_frech_mes=subsidio_frech_mes,
                pago_cliente_mes=pago_cliente_mes,
                pago_banco_mes=pago_banco_mes,
                saldo_final_pesos=saldo_final_pesos,
            )
        )

    saldo_final = _quantize_money(saldo_uvr * uvr_mes)
    terminado = saldo_final <= EPSILON_BALANCE

    return UvrScenarioResult(
        meses_totales=len(tabla),
        total_pagado_cliente=_quantize_money(total_pagado_cliente),
        total_pagado_banco=_quantize_money(total_pagado_banco),
        intereses_totales=_quantize_money(total_intereses),
        capital_total_amortizado=_quantize_money(total_capital),
        saldo_final_pesos=_quantize_money(max(saldo_final, Decimal("0"))),
        mes_inicio_amortizacion_significativa=mes_inicio_amortizacion_significativa,
        terminado=terminado,
        tabla=tabla,
    )


def _intereses_ajustados_inflacion(tabla: List[UvrMonthlyRow], inflacion_mensual: Decimal) -> Decimal:
    """Valor presente aproximado de intereses descontando inflacion mensual estimada."""
    if not tabla:
        return Decimal("0.00")

    total = Decimal("0")
    base = Decimal("1") + inflacion_mensual

    for row in tabla:
        factor = Decimal(str(float(base) ** row.mes)) if base > 0 else Decimal("1")
        if factor <= 0:
            factor = Decimal("1")
        total += (row.interes_mes / factor)

    return _quantize_money(total)


def compare_uvr_scenarios(data: UvrProjectionInput) -> UvrComparisonResult:
    """
    Ejecuta escenario original vs escenario con abono y compara intereses reales.
    """
    escenario_original = simulate_uvr_scenario(data, abono_adicional_override=Decimal("0"))
    escenario_con_abono = simulate_uvr_scenario(data, abono_adicional_override=data.abono_adicional)

    ahorro_intereses_real = _quantize_money(
        escenario_original.intereses_totales - escenario_con_abono.intereses_totales
    )

    meses_reducidos = max(0, escenario_original.meses_totales - escenario_con_abono.meses_totales)

    inflacion_mensual = inflacion_anual_a_mensual_lineal(data.inflacion_anual_estimada)
    intereses_original_ajustados = _intereses_ajustados_inflacion(escenario_original.tabla, inflacion_mensual)
    intereses_con_abono_ajustados = _intereses_ajustados_inflacion(escenario_con_abono.tabla, inflacion_mensual)

    ahorro_intereses_real_ajustado = _quantize_money(
        intereses_original_ajustados - intereses_con_abono_ajustados
    )

    return UvrComparisonResult(
        ahorro_intereses_real=ahorro_intereses_real,
        ahorro_intereses_real_ajustado_inflacion=ahorro_intereses_real_ajustado,
        meses_reducidos=meses_reducidos,
        total_pagado_original=escenario_original.total_pagado_cliente,
        total_pagado_con_abono=escenario_con_abono.total_pagado_cliente,
        intereses_original=escenario_original.intereses_totales,
        intereses_con_abono=escenario_con_abono.intereses_totales,
        mes_inicio_amortizacion_significativa_original=escenario_original.mes_inicio_amortizacion_significativa,
        mes_inicio_amortizacion_significativa_con_abono=escenario_con_abono.mes_inicio_amortizacion_significativa,
        escenario_original=escenario_original,
        escenario_con_abono=escenario_con_abono,
    )
