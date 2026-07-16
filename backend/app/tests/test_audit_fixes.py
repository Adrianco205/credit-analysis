import pytest
from decimal import Decimal
from app.services.financial_rates import annual_effective_to_monthly
from app.services.uvr_projection_engine import (
    simulate_uvr_scenario,
    UvrProjectionInput,
    compare_uvr_scenarios,
)
from app.services.pesos_projection_engine import (
    simulate_pesos,
    PesosProjectionInput,
    PesosProjectionInfeasibleError,
)

def test_annual_ipc_compounds_to_exact_annual_rate():
    # 5% annual inflation
    annual_rate = Decimal("0.05")
    monthly = annual_effective_to_monthly(annual_rate)
    
    # Compound 12 times
    compounded = ((Decimal("1") + monthly) ** 12) - Decimal("1")
    assert compounded.quantize(Decimal("0.0001")) == Decimal("0.0500")

def test_uvr_first_month_does_not_apply_inflation_twice():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
    )
    result = simulate_uvr_scenario(data)
    # The UVR of the first month should be exactly the input UVR
    assert result.tabla[0].uvr_mes == Decimal("300.00")
    # The UVR of the second month should have inflation applied
    assert result.tabla[1].uvr_mes > Decimal("300.00")

def test_baseline_equals_zero_extra_scenario():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
    )
    baseline = simulate_uvr_scenario(data, abono_adicional_override=Decimal("0"))
    scenario = simulate_uvr_scenario(data)
    
    assert baseline.meses_totales == scenario.meses_totales
    assert baseline.intereses_totales == scenario.intereses_totales
    assert baseline.total_pagado_cliente == scenario.total_pagado_cliente

def test_frech_does_not_change_principal_schedule():
    # Scenario without FRECH
    data_no_frech = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        subsidio_frech=Decimal("0"),
        frech_meses_restantes=0,
    )
    
    # Scenario with FRECH
    data_with_frech = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        subsidio_frech=Decimal("100000"),
        frech_meses_restantes=84,
    )
    
    res_no = simulate_uvr_scenario(data_no_frech)
    res_yes = simulate_uvr_scenario(data_with_frech)
    
    # Principal schedule and term should be identical
    assert res_no.meses_totales == res_yes.meses_totales
    assert res_no.intereses_totales == res_yes.intereses_totales
    assert res_no.capital_total_amortizado == res_yes.capital_total_amortizado

def test_frech_only_changes_client_cashflow():
    # Using the same setup as above
    data_no_frech = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        subsidio_frech=Decimal("0"),
        frech_meses_restantes=0,
    )
    data_with_frech = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=120,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        subsidio_frech=Decimal("100000"),
        frech_meses_restantes=84,
    )
    
    res_no = simulate_uvr_scenario(data_no_frech)
    res_yes = simulate_uvr_scenario(data_with_frech)
    
    # The client should pay less in total, exactly by the FRECH amount applied
    assert res_yes.total_pagado_cliente < res_no.total_pagado_cliente
    assert res_yes.total_frech > Decimal("0")
    
    expected_frech_total = min(res_yes.meses_totales, 84) * Decimal("100000")
    assert res_yes.total_frech == expected_frech_total

def test_baseline_stops_when_balance_reaches_zero():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("1000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=360, # very long term
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("0"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"), # massive payment
    )
    # The baseline should stop in about 2 months, way before 360
    baseline = simulate_uvr_scenario(data, abono_adicional_override=Decimal("0"))
    assert baseline.meses_totales < 5
    assert baseline.terminado is True

def test_months_reduced_uses_baseline_months():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=360,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("500000"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
    )
    comparison = compare_uvr_scenarios(data)
    
    expected_reduced = comparison.escenario_original.meses_totales - comparison.escenario_con_abono.meses_totales
    assert comparison.meses_reducidos == expected_reduced
    # Not 360 - meses_con_abono!
    assert comparison.meses_reducidos != (360 - comparison.escenario_con_abono.meses_totales)

def test_interest_savings_excludes_insurance():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=360,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("500000"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        seguro_mensual=Decimal("50000"),
    )
    comparison = compare_uvr_scenarios(data)
    
    # Interest savings should strictly be the difference in interests
    expected_interest_savings = comparison.escenario_original.intereses_totales - comparison.escenario_con_abono.intereses_totales
    assert comparison.ahorro_intereses_real == expected_interest_savings

def test_client_savings_includes_insurance_reduction():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("50000000"),
        tasa_efectiva_anual=Decimal("0.10"),
        plazo_meses=360,
        cuota_actual=Decimal("500000"),
        abono_adicional=Decimal("500000"),
        uvr_actual=Decimal("300.00"),
        inflacion_anual_estimada=Decimal("0.05"),
        cuota_deuda_pesos=Decimal("800000"),
        seguro_mensual=Decimal("50000"),
    )
    comparison = compare_uvr_scenarios(data)
    
    expected_client_savings = comparison.escenario_original.total_pagado_cliente - comparison.escenario_con_abono.total_pagado_cliente
    assert comparison.ahorro_total_cliente == expected_client_savings
    assert comparison.ahorro_total_cliente > comparison.ahorro_intereses_real # Since it includes saved insurance

def test_unknown_frech_term_blocks_commercial_projection():
    data = PesosProjectionInput(
        principal_balance=Decimal("50000000"),
        annual_rate=Decimal("0.10"),
        contractual_debt_installment=Decimal("800000"),
        insurance_monthly=Decimal("0"),
        non_amortizable_charges=Decimal("0"),
        frech_monthly=Decimal("100000"),
        frech_remaining_months=None, # Missing!
        remaining_term=120,
    )
    with pytest.raises(PesosProjectionInfeasibleError, match="La vigencia del FRECH no está confirmada"):
        simulate_pesos(data)
