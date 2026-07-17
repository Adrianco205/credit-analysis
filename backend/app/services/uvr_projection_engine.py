"""Motor UVR V3: simulación mes a mes unificada.

Cambios respecto a V2:
- Una sola función de simulación (baseline = abono_extra=0).
- IPC anual se convierte a mensual de forma efectiva, no lineal.
- Primer mes usa uvr_actual sin aplicar inflación adicional.
- FRECH solo afecta el flujo del cliente, nunca el cálculo de interés/capital.
- La simulación termina cuando el saldo llega a cero, incluso en baseline.
- Resultados desglosados: total_insurance, total_frech.

Principio clave:
    ahorro_intereses_real = sum(intereses_original) - sum(intereses_con_abono)

No usa como métrica principal la diferencia entre totales pagados,
porque en UVR el capital evoluciona con inflación y el costo futuro no es fijo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from app.services.financial_rates import annual_effective_to_monthly as _ea_to_monthly
from app.services.financial_rates import inflacion_anual_a_mensual_efectiva

PRECISION_MONEY = Decimal("0.01")
PRECISION_RATE = Decimal("0.00000001")
EPSILON_BALANCE = Decimal("0.01")
DEFAULT_MAX_MESES = 1200
DEFAULT_FRECH_MAX_MESES = 84


class UvrProjectionInfeasibleError(ValueError):
    """Raised before iteration when the debt installment cannot amortize."""


@dataclass(frozen=True)
class UvrProjectionInput:
    saldo_inicial: Decimal
    tasa_efectiva_anual: Decimal
    plazo_meses: int
    cuota_actual: Decimal
    abono_adicional: Decimal
    uvr_actual: Decimal
    inflacion_anual_estimada: Decimal
    # Legacy field — kept for backwards compatibility but ignored by the V3
    # engine.  FRECH is modelled exclusively as a cash-flow offset via
    # ``subsidio_frech``.
    tasa_efectiva_anual_subsidiada: Decimal | None = None
    subsidio_frech: Decimal = Decimal("0")
    seguro_mensual: Decimal = Decimal("0")
    cuota_deuda_pesos: Decimal | None = None
    cuota_deuda_uvr: Decimal | None = None
    cuota_uvr_actual: Decimal | None = None
    frech_meses_restantes: int | None = None
    tasa_seguro_vida: Decimal = Decimal("0")
    valor_seguro_incendio_fijo: Decimal = Decimal("0")
    cargos_no_amortizables_mensuales: Decimal = Decimal("0")
    pago_inicial_especial: Decimal = Decimal("0")
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
    total_insurance: Decimal
    total_frech: Decimal
    saldo_final_pesos: Decimal
    mes_inicio_amortizacion_significativa: int | None
    terminado: bool
    tabla: List[UvrMonthlyRow]
    es_impagable: bool = False


@dataclass(frozen=True)
class UvrComparisonResult:
    ahorro_intereses_real: Decimal
    ahorro_intereses_real_ajustado_inflacion: Decimal
    meses_reducidos: int
    total_pagado_original: Decimal
    total_pagado_con_abono: Decimal
    intereses_original: Decimal
    intereses_con_abono: Decimal
    ahorro_seguros: Decimal
    reduccion_frech: Decimal
    ahorro_total_cliente: Decimal
    mes_inicio_amortizacion_significativa_original: int | None
    mes_inicio_amortizacion_significativa_con_abono: int | None
    escenario_original: UvrScenarioResult
    escenario_con_abono: UvrScenarioResult


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(PRECISION_MONEY, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Public helpers (kept for external callers that imported them)
# ---------------------------------------------------------------------------

def tasa_ea_a_mensual(tasa_efectiva_anual: Decimal) -> Decimal:
    """Delegada a financial_rates — mantiene la firma original."""
    return _ea_to_monthly(tasa_efectiva_anual)


def inflacion_anual_a_mensual_lineal(inflacion_anual: Decimal) -> Decimal:
    """DEPRECATED — redirige a conversión efectiva.

    Callers that relied on the old linear ``ipc/12`` will now receive the
    correct effective monthly rate.  The function name is kept so that
    existing imports do not break.
    """
    return inflacion_anual_a_mensual_efectiva(inflacion_anual)


# ---------------------------------------------------------------------------
# Core simulation — single unified function
# ---------------------------------------------------------------------------

def simulate_uvr_scenario(
    data: UvrProjectionInput,
    abono_adicional_override: Decimal | None = None,
) -> UvrScenarioResult:
    """Simulate a UVR credit month-by-month.

    This is the **only** simulation function.  The baseline scenario is
    obtained by calling with ``abono_adicional_override=Decimal("0")``.

    Key rules:
    1. UVR grows each month with effective monthly inflation.
    2. Interest is calculated on the indexed balance **using the contractual
       rate** — never a subsidised rate.
    3. FRECH is a cash-flow offset that reduces the client payment; it does
       **not** change interest or capital.
    4. The loop terminates when the balance reaches EPSILON_BALANCE or the
       safety cap is hit.
    5. The first month uses ``uvr_actual`` without applying inflation (the
       value already corresponds to the statement date).
    """
    if data.saldo_inicial <= 0:
        raise ValueError("saldo_inicial debe ser mayor a cero")
    if data.uvr_actual <= 0:
        raise ValueError("uvr_actual debe ser mayor a cero")
    if data.plazo_meses <= 0:
        raise ValueError("plazo_meses debe ser mayor a cero")

    abono_adicional = (
        data.abono_adicional if abono_adicional_override is None
        else abono_adicional_override
    )
    if abono_adicional < 0:
        raise ValueError("abono_adicional no puede ser negativo")

    tasa_mensual = _ea_to_monthly(data.tasa_efectiva_anual)
    inflacion_mensual = inflacion_anual_a_mensual_efectiva(
        data.inflacion_anual_estimada,
    )

    # ----- Resolve debt installment in UVR ---------------------------------
    cuota_uvr = data.cuota_deuda_uvr or data.cuota_uvr_actual
    if cuota_uvr is None or cuota_uvr <= 0:
        if data.cuota_deuda_pesos is not None and data.cuota_deuda_pesos > 0:
            cuota_uvr = data.cuota_deuda_pesos / data.uvr_actual
        else:
            raise UvrProjectionInfeasibleError(
                "Se requiere una cuota de deuda UVR o en pesos explícita "
                "para proyectar el crédito.",
            )

    # Pre-flight: the debt installment must cover initial interest.
    cuota_deuda_inicial_pesos = cuota_uvr * data.uvr_actual
    interes_inicial = data.saldo_inicial * tasa_mensual
    es_impagable = False
    if cuota_deuda_inicial_pesos + abono_adicional <= interes_inicial:
        # Calcular cuota teórica en UVR
        saldo_uvr_inicial = data.saldo_inicial / data.uvr_actual
        if tasa_mensual > 0:
            factor = (Decimal("1") + tasa_mensual) ** data.plazo_meses
            cuota_uvr = saldo_uvr_inicial * (tasa_mensual * factor) / (factor - Decimal("1"))
        else:
            cuota_uvr = saldo_uvr_inicial / Decimal(str(data.plazo_meses))
        cuota_deuda_inicial_pesos = cuota_uvr * data.uvr_actual
        es_impagable = True

    # ----- Resolve FRECH term ----------------------------------------------
    frech_meses_restantes = data.frech_meses_restantes
    if frech_meses_restantes is None:
        frech_meses_restantes = DEFAULT_FRECH_MAX_MESES
    try:
        frech_meses_restantes = max(0, int(frech_meses_restantes))
    except (TypeError, ValueError):
        frech_meses_restantes = DEFAULT_FRECH_MAX_MESES

    # ----- Initial state ---------------------------------------------------
    saldo_uvr = data.saldo_inicial / data.uvr_actual
    uvr_mes = data.uvr_actual  # first month uses this value as-is



    tabla: List[UvrMonthlyRow] = []
    total_intereses = Decimal("0")
    total_pagado_cliente = Decimal("0")
    total_pagado_banco = Decimal("0")
    total_capital = Decimal("0")
    total_insurance = Decimal("0")
    total_frech = Decimal("0")
    mes_inicio_amortizacion_significativa: int | None = None

    max_iter = min(data.max_meses_simulacion, DEFAULT_MAX_MESES)

    for mes in range(1, max_iter + 1):
        # --- Early termination when balance is paid off --------------------
        if saldo_uvr * uvr_mes <= EPSILON_BALANCE:
            break

        # --- UVR growth (skip first month — uvr_actual already set) --------
        if mes > 1:
            uvr_mes = (
                uvr_mes * (Decimal("1") + inflacion_mensual)
            ).quantize(PRECISION_RATE)

        saldo_inicial_pesos = _quantize_money(saldo_uvr * uvr_mes)

        # --- Insurance (monthly) ------------------------------------------
        seguros_mes = _quantize_money(
            data.seguro_mensual
            + data.valor_seguro_incendio_fijo
            + data.cargos_no_amortizables_mensuales,
        )

        # --- Interest (always contractual rate) ----------------------------
        interes_mes = _quantize_money(saldo_inicial_pesos * tasa_mensual)

        # --- Debt installment in pesos ------------------------------------
        cuota_deuda_pesos = _quantize_money(cuota_uvr * uvr_mes)

        # --- Capital = debt installment + extra - interest -----------------
        capital_mes = _quantize_money(
            cuota_deuda_pesos + abono_adicional - interes_mes,
        )
        if mes == 1 and data.pago_inicial_especial > 0:
            capital_mes = _quantize_money(
                capital_mes + data.pago_inicial_especial,
            )

        if capital_mes <= Decimal("0"):
            # Permitir amortización negativa (incremento de saldo) si la cuota no alcanza
            es_impagable = True

        # --- Cap capital at remaining balance ------------------------------
        if capital_mes > saldo_inicial_pesos:
            capital_mes = saldo_inicial_pesos
            cuota_deuda_pesos = _quantize_money(interes_mes + capital_mes)

        # --- FRECH as cash-flow offset (does NOT change capital) -----------
        subsidio_frech_mes = (
            data.subsidio_frech if mes <= frech_meses_restantes
            else Decimal("0")
        )
        subsidio_frech_mes = _quantize_money(subsidio_frech_mes)

        # --- Client payment -----------------------------------------------
        pago_cliente_mes = _quantize_money(
            cuota_deuda_pesos
            + seguros_mes
            + abono_adicional
            - subsidio_frech_mes,
        )
        if mes == 1 and data.pago_inicial_especial > 0:
            pago_cliente_mes = _quantize_money(
                pago_cliente_mes + data.pago_inicial_especial,
            )

        # --- Bank flow (total credit flow = client + frech) ----------------
        pago_banco_mes = _quantize_money(pago_cliente_mes + subsidio_frech_mes)

        # --- Update UVR balance -------------------------------------------
        saldo_final_pesos = _quantize_money(
            max(saldo_inicial_pesos - capital_mes, Decimal("0")),
        )
        capital_uvr = capital_mes / uvr_mes if uvr_mes > 0 else Decimal("0")
        saldo_uvr = max(saldo_uvr - capital_uvr, Decimal("0"))

        # --- Accumulate totals --------------------------------------------
        total_intereses += interes_mes
        total_pagado_cliente += pago_cliente_mes
        total_pagado_banco += pago_banco_mes
        total_capital += capital_mes
        total_insurance += seguros_mes
        total_frech += subsidio_frech_mes

        if (
            mes_inicio_amortizacion_significativa is None
            and capital_mes >= interes_mes
        ):
            mes_inicio_amortizacion_significativa = mes

        tabla.append(
            UvrMonthlyRow(
                mes=mes,
                uvr_mes=uvr_mes,
                saldo_inicial_pesos=saldo_inicial_pesos,
                interes_mes=interes_mes,
                capital_mes=capital_mes,
                seguro_mes=seguros_mes,
                subsidio_frech_mes=subsidio_frech_mes,
                pago_cliente_mes=pago_cliente_mes,
                pago_banco_mes=pago_banco_mes,
                saldo_final_pesos=saldo_final_pesos,
            ),
        )

    saldo_final = _quantize_money(saldo_uvr * uvr_mes)
    terminado = saldo_final <= EPSILON_BALANCE

    return UvrScenarioResult(
        meses_totales=len(tabla),
        total_pagado_cliente=_quantize_money(total_pagado_cliente),
        total_pagado_banco=_quantize_money(total_pagado_banco),
        intereses_totales=_quantize_money(total_intereses),
        capital_total_amortizado=_quantize_money(total_capital),
        total_insurance=_quantize_money(total_insurance),
        total_frech=_quantize_money(total_frech),
        saldo_final_pesos=_quantize_money(max(saldo_final, Decimal("0"))),
        mes_inicio_amortizacion_significativa=mes_inicio_amortizacion_significativa,
        terminado=terminado,
        es_impagable=es_impagable,
        tabla=tabla,
    )


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------

def _intereses_ajustados_inflacion(
    tabla: List[UvrMonthlyRow],
    inflacion_mensual: Decimal,
) -> Decimal:
    """Present-value approximation of interest discounted by monthly inflation."""
    if not tabla:
        return Decimal("0.00")

    total = Decimal("0")
    base = Decimal("1") + inflacion_mensual

    for row in tabla:
        factor = (
            Decimal(str(float(base) ** row.mes))
            if base > 0
            else Decimal("1")
        )
        if factor <= 0:
            factor = Decimal("1")
        total += row.interes_mes / factor

    return _quantize_money(total)


def calcular_ahorro_intereses_inflado_v1(
    data: UvrProjectionInput, 
    abono_adicional: Decimal
) -> Decimal:
    """
    Simula el bug de la versión V1 para calcular un ahorro de intereses masivo.
    El bug de V1 consistía en:
    1. Si la cuota no cubría los intereses, el abono a capital base se truncaba a 0, 
       pero el interés no pagado se descartaba (no se capitalizaba).
    2. El abono adicional iba DIRECTAMENTE a reducir el saldo de capital, saltándose
       el interés no pagado.
    Esto hacía que el saldo en el escenario sin abono nunca bajara, generando intereses
    astronómicos, mientras que en el escenario con abono bajaba rápidamente.
    """
    def _simular_v1(abono_extra_pesos: Decimal) -> Decimal:
        saldo_uvr = data.saldo_inicial / data.uvr_actual
        uvr_mes = data.uvr_actual
        tasa_mensual = (Decimal("1") + data.tasa_efectiva_anual) ** (Decimal("1") / Decimal("12")) - Decimal("1")
        
        # En V1 la cuota fija base se determinaba por la cuota visible
        cuota_fija_pesos = data.cuota_actual
        cuota_fija_uvr_falsa = cuota_fija_pesos / data.uvr_actual
        
        inflacion_mensual = (Decimal("1") + data.inflacion_anual_estimada) ** (Decimal("1") / Decimal("12")) - Decimal("1")
        
        total_intereses_salida = Decimal("0")
        
        # En V1, max_cuotas estaba hardcodeado a 600 en generar_tabla_amortizacion
        max_cuotas = 600
        
        for mes in range(1, max_cuotas + 1):
            if saldo_uvr <= EPSILON_BALANCE:
                break
                
            if mes > 1:
                uvr_mes = (uvr_mes * (Decimal("1") + inflacion_mensual)).quantize(PRECISION_RATE)
                
            interes_mes_uvr = saldo_uvr * tasa_mensual
            interes_mes_pesos = _quantize_money(interes_mes_uvr * uvr_mes)
            total_intereses_salida += interes_mes_pesos
            
            seguros_pesos = data.seguro_mensual + data.valor_seguro_incendio_fijo + data.cargos_no_amortizables_mensuales
            seguros_uvr = seguros_pesos / uvr_mes if uvr_mes > 0 else Decimal("0")
            
            abono_capital_base_uvr = cuota_fija_uvr_falsa - seguros_uvr - interes_mes_uvr
            if abono_capital_base_uvr < 0:
                abono_capital_base_uvr = Decimal("0")
                
            abono_extra_uvr = abono_extra_pesos / uvr_mes if uvr_mes > 0 else Decimal("0")
            
            abono_capital_total = abono_capital_base_uvr + abono_extra_uvr
            
            if saldo_uvr <= abono_capital_total:
                saldo_uvr = Decimal("0")
            else:
                saldo_uvr -= abono_capital_total
                
        return total_intereses_salida

    intereses_baseline = _simular_v1(Decimal("0"))
    intereses_con_abono = _simular_v1(abono_adicional)
    
    ahorro = _quantize_money(intereses_baseline - intereses_con_abono)
    return max(ahorro, Decimal("0"))


def compare_uvr_scenarios(data: UvrProjectionInput) -> UvrComparisonResult:
    """Run baseline vs. extra-payment scenario and compare."""
    escenario_original = simulate_uvr_scenario(
        data, abono_adicional_override=Decimal("0"),
    )
    escenario_con_abono = simulate_uvr_scenario(
        data, abono_adicional_override=data.abono_adicional,
    )

    ahorro_intereses_real = _quantize_money(
        escenario_original.intereses_totales
        - escenario_con_abono.intereses_totales,
    )

    meses_reducidos = max(
        0,
        escenario_original.meses_totales - escenario_con_abono.meses_totales,
    )

    inflacion_mensual = inflacion_anual_a_mensual_efectiva(
        data.inflacion_anual_estimada,
    )
    intereses_original_ajustados = _intereses_ajustados_inflacion(
        escenario_original.tabla, inflacion_mensual,
    )
    intereses_con_abono_ajustados = _intereses_ajustados_inflacion(
        escenario_con_abono.tabla, inflacion_mensual,
    )

    ahorro_intereses_real_ajustado = _quantize_money(
        intereses_original_ajustados - intereses_con_abono_ajustados,
    )

    ahorro_seguros = _quantize_money(
        escenario_original.total_insurance
        - escenario_con_abono.total_insurance,
    )
    reduccion_frech = _quantize_money(
        escenario_original.total_frech
        - escenario_con_abono.total_frech,
    )
    ahorro_total_cliente = _quantize_money(
        escenario_original.total_pagado_cliente
        - escenario_con_abono.total_pagado_cliente,
    )

    return UvrComparisonResult(
        ahorro_intereses_real=ahorro_intereses_real,
        ahorro_intereses_real_ajustado_inflacion=ahorro_intereses_real_ajustado,
        meses_reducidos=meses_reducidos,
        total_pagado_original=escenario_original.total_pagado_cliente,
        total_pagado_con_abono=escenario_con_abono.total_pagado_cliente,
        intereses_original=escenario_original.intereses_totales,
        intereses_con_abono=escenario_con_abono.intereses_totales,
        ahorro_seguros=ahorro_seguros,
        reduccion_frech=reduccion_frech,
        ahorro_total_cliente=ahorro_total_cliente,
        mes_inicio_amortizacion_significativa_original=escenario_original.mes_inicio_amortizacion_significativa,
        mes_inicio_amortizacion_significativa_con_abono=escenario_con_abono.mes_inicio_amortizacion_significativa,
        escenario_original=escenario_original,
        escenario_con_abono=escenario_con_abono,
    )
