from decimal import Decimal

from app.services.uvr_projection_engine import (
    UvrProjectionInput,
    compare_uvr_scenarios,
    inflacion_anual_a_mensual_lineal,
    simulate_uvr_scenario,
    tasa_ea_a_mensual,
)


def _build_input(abono: Decimal) -> UvrProjectionInput:
    return UvrProjectionInput(
        saldo_inicial=Decimal("61765856"),
        tasa_efectiva_anual=Decimal("0.0747"),
        plazo_meses=305,
        cuota_actual=Decimal("523427"),
        abono_adicional=abono,
        uvr_actual=Decimal("376.1794"),
        inflacion_anual_estimada=Decimal("0.06"),
        subsidio_frech=Decimal("201270"),
        seguro_mensual=Decimal("46384.35"),
    )


def test_tasa_ea_a_mensual_uvr_engine():
    tasa = tasa_ea_a_mensual(Decimal("0.0747"))
    assert Decimal("0.005") < tasa < Decimal("0.007")


def test_inflacion_anual_a_mensual_lineal_uvr_engine():
    inflacion = inflacion_anual_a_mensual_lineal(Decimal("0.06"))
    assert inflacion == Decimal("0.00500000")


def test_simulation_uvr_grows_month_by_month():
    result = simulate_uvr_scenario(_build_input(abono=Decimal("0")))

    assert result.meses_totales > 1
    assert result.tabla[1].uvr_mes > result.tabla[0].uvr_mes
    assert result.intereses_totales > Decimal("0")


def test_abono_reduces_interest_and_months_real_savings_formula():
    comparison = compare_uvr_scenarios(_build_input(abono=Decimal("149658")))

    assert comparison.intereses_con_abono < comparison.intereses_original
    assert comparison.meses_reducidos > 0

    ahorro_esperado = (comparison.intereses_original - comparison.intereses_con_abono).quantize(Decimal("0.01"))
    assert comparison.ahorro_intereses_real == ahorro_esperado


def test_output_contract_required_fields():
    comparison = compare_uvr_scenarios(_build_input(abono=Decimal("202176")))

    assert comparison.total_pagado_original > Decimal("0")
    assert comparison.total_pagado_con_abono > Decimal("0")
    assert comparison.intereses_original > Decimal("0")
    assert comparison.intereses_con_abono > Decimal("0")
    assert comparison.ahorro_intereses_real_ajustado_inflacion != Decimal("0")


def test_significant_amortization_point_detected():
    comparison = compare_uvr_scenarios(_build_input(abono=Decimal("173789")))

    assert comparison.mes_inicio_amortizacion_significativa_original is not None
    assert comparison.mes_inicio_amortizacion_significativa_con_abono is not None
    assert comparison.mes_inicio_amortizacion_significativa_con_abono <= comparison.mes_inicio_amortizacion_significativa_original


def test_cuota_uvr_actual_treats_insurance_as_non_debt_component():
    base = UvrProjectionInput(
        saldo_inicial=Decimal("56069733.47"),
        tasa_efectiva_anual=Decimal("0.0471"),
        plazo_meses=325,
        cuota_actual=Decimal("523427"),
        abono_adicional=Decimal("149658"),
        uvr_actual=Decimal("376.1794"),
        inflacion_anual_estimada=Decimal("0.06"),
        subsidio_frech=Decimal("183855.65"),
        seguro_mensual=Decimal("21134"),
        cuota_uvr_actual=Decimal("1391.45"),
        frech_meses_restantes=36,
    )

    with_insurance = simulate_uvr_scenario(base)
    without_insurance = simulate_uvr_scenario(
        UvrProjectionInput(
            **{
                **base.__dict__,
                "seguro_mensual": Decimal("0"),
            }
        )
    )

    assert with_insurance.meses_totales == without_insurance.meses_totales
    assert with_insurance.intereses_totales == without_insurance.intereses_totales
    assert with_insurance.total_pagado_cliente > without_insurance.total_pagado_cliente


def test_without_cuota_uvr_insurance_reduces_debt_component():
    base = UvrProjectionInput(
        saldo_inicial=Decimal("56069733.47"),
        tasa_efectiva_anual=Decimal("0.0471"),
        plazo_meses=325,
        cuota_actual=Decimal("523427"),
        abono_adicional=Decimal("149658"),
        uvr_actual=Decimal("376.1794"),
        inflacion_anual_estimada=Decimal("0.06"),
        subsidio_frech=Decimal("183855.65"),
        seguro_mensual=Decimal("21134"),
        cuota_uvr_actual=None,
        frech_meses_restantes=36,
    )

    with_insurance = simulate_uvr_scenario(base)
    without_insurance = simulate_uvr_scenario(
        UvrProjectionInput(
            **{
                **base.__dict__,
                "seguro_mensual": Decimal("0"),
            }
        )
    )

    assert with_insurance.meses_totales >= without_insurance.meses_totales
