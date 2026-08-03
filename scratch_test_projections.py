from decimal import Decimal
from backend.app.services.uvr_projection_engine import UvrProjectionInput, compare_uvr_scenarios
from backend.app.services.pesos_projection_engine import PesosProjectionInput, simulate_pesos

# Luis Eduardo Berrocal Monte (UVR)
# Option 1: 107032.05 abono, 230 cuotas
data_luis_1 = UvrProjectionInput(
    saldo_inicial=Decimal("66348797.99"),
    tasa_efectiva_anual=Decimal("0.0525"),
    plazo_meses=350,
    cuota_actual=Decimal("400881.00"),
    cuota_deuda_pesos=Decimal("400881.00") - Decimal("32869.00"),
    abono_adicional=Decimal("107032.05"),
    uvr_actual=Decimal("403.3679"),
    inflacion_anual_estimada=Decimal("0.05"), # guess inflation to see results
    seguro_mensual=Decimal("32869.00")
)
result_luis_1 = compare_uvr_scenarios(data_luis_1)

print(f"--- LUIS EDUARDO BERROCAL MONTE (UVR) ---")
print(f"Original: Meses={result_luis_1.escenario_original.meses_totales}, Total Pagado={result_luis_1.total_pagado_original}")
print(f"Opción 1 (Abono {data_luis_1.abono_adicional}): Meses={result_luis_1.escenario_con_abono.meses_totales}, Total Pagado={result_luis_1.total_pagado_con_abono}")
print(f"Ahorro Intereses (Real): {result_luis_1.ahorro_intereses_real}")
print(f"Ahorro Intereses (Inflado V1): {result_luis_1.ahorro_intereses_inflado}")


# Addeson Albert Zuiga Vega (PESOS)
# Option 1: 149658 abono
data_addeson_1 = PesosProjectionInput(
    principal_balance=Decimal("61409771.65"),
    annual_rate=Decimal("0.1175"),
    contractual_debt_installment=Decimal("724696.78") - Decimal("82601.08"), # cuota sin seguros = 642095.7
    insurance_monthly=Decimal("82601.08"),
    non_amortizable_charges=Decimal("0"),
    frech_monthly=Decimal("201269.70"),
    frech_remaining_months=84, # usually 7 years
    remaining_term=305,
    extra_payment=Decimal("149658.00"),
    post_subsidy_annual_rate=Decimal("0.1175")
)

# Baseline
data_addeson_base = PesosProjectionInput(
    principal_balance=Decimal("61409771.65"),
    annual_rate=Decimal("0.1175"),
    contractual_debt_installment=Decimal("724696.78") - Decimal("82601.08"),
    insurance_monthly=Decimal("82601.08"),
    non_amortizable_charges=Decimal("0"),
    frech_monthly=Decimal("201269.70"),
    frech_remaining_months=84,
    remaining_term=305,
    extra_payment=Decimal("0"),
    post_subsidy_annual_rate=Decimal("0.1175")
)

res_base = simulate_pesos(data_addeson_base)
res_op1 = simulate_pesos(data_addeson_1)

print(f"\n--- ADDESON ALBERT ZUIGA VEGA (PESOS) ---")
print(f"Original: Meses={res_base.months}, Total Pagado={res_base.total_client_payment}, Intereses={res_base.total_interest}")
print(f"Opción 1 (Abono {data_addeson_1.extra_payment}): Meses={res_op1.months}, Total Pagado={res_op1.total_client_payment}, Intereses={res_op1.total_interest}")
print(f"Ahorro Intereses: {res_base.total_interest - res_op1.total_interest}")
