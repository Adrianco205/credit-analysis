from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.credit_snapshot_service import (
    ProjectionStatus,
    ProjectionValidationError,
    SnapshotType,
    normalize_credit_snapshot,
    validate_projection_snapshot,
)
from app.services.uvr_projection_engine import (
    UvrProjectionInfeasibleError,
    UvrProjectionInput,
    simulate_uvr_scenario,
)


def analysis(**overrides):
    values = dict(
        sistema_amortizacion="UVR", plan_credito="CUOTA CONSTANTE UVR",
        saldo_capital_pesos=Decimal("177833619"), saldo_capital_uvr=None,
        valor_cuota_sin_seguros=None, valor_cuota_con_seguros=None,
        valor_cuota_con_subsidio=None, valor_cuota_uvr=None,
        valor_uvr_fecha_extracto=Decimal("381.00"), seguros_total_mensual=Decimal("50734"),
        otros_cargos=Decimal("0"), beneficio_frech_mensual=Decimal("0"),
        frech_meses_restantes=None, cuotas_pendientes=356, cuotas_vencidas=0,
        capital_pagado_periodo=None, intereses_corrientes_periodo=None,
        raw_data_json={}, datos_raw_gemini={}, tasa_interes_cobrada_ea=Decimal("0.064"),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_hosman_partial_payment_does_not_return_1200_months():
    hosman = analysis(
        capital_pagado_periodo=Decimal("0"), intereses_corrientes_periodo=Decimal("549266"),
        raw_data_json={"pago_aplicado_periodo": "600000", "valor_pendiente_cuota": "543918.08"},
    )
    snapshot = normalize_credit_snapshot(hosman)
    assert snapshot.validation_status == ProjectionStatus.PARTIAL_PAYMENT_DETECTED
    with pytest.raises(ProjectionValidationError):
        validate_projection_snapshot(snapshot, hosman.tasa_interes_cobrada_ea)


def test_lianis_full_uvr_installment_is_valid():
    lianis = analysis(
        saldo_capital_pesos=Decimal("120000000"), valor_uvr_fecha_extracto=Decimal("407.525"),
        valor_cuota_uvr=Decimal("1121.0961"), valor_cuota_sin_seguros=Decimal("456873.57"),
        valor_cuota_con_seguros=Decimal("485537.57"), seguros_total_mensual=Decimal("28664"),
        capital_pagado_periodo=Decimal("100000"), intereses_corrientes_periodo=Decimal("356873.57"),
    )
    snapshot = normalize_credit_snapshot(lianis)
    assert snapshot.validation_status == ProjectionStatus.VALID
    assert abs(snapshot.contractual_debt_installment - Decimal("456873.57")) < Decimal("15")
    assert snapshot.insurance_total == Decimal("28664")


def test_explicit_uvr_installment_has_priority_and_insurance_does_not_amortize():
    luis = analysis(
        saldo_capital_pesos=Decimal("60000000"), valor_uvr_fecha_extracto=Decimal("403.38"),
        valor_cuota_uvr=Decimal("912.3494"), valor_cuota_con_seguros=Decimal("400881.46"),
        seguros_total_mensual=Decimal("32869"), capital_pagado_periodo=Decimal("100000"),
        intereses_corrientes_periodo=Decimal("268012.46"),
    )
    snapshot = normalize_credit_snapshot(luis)
    assert abs(snapshot.contractual_debt_installment - Decimal("368012.46")) < Decimal("15")
    assert snapshot.contractual_debt_installment + snapshot.insurance_total < Decimal("401000")


def test_negative_amortization_stops_before_iteration_limit():
    data = UvrProjectionInput(
        saldo_inicial=Decimal("177833619"), tasa_efectiva_anual=Decimal("0.064"), plazo_meses=356,
        cuota_actual=Decimal("600000"), abono_adicional=Decimal("100000"), uvr_actual=Decimal("381"),
        inflacion_anual_estimada=Decimal("0.022"), seguro_mensual=Decimal("50734"),
    )
    with pytest.raises(UvrProjectionInfeasibleError):
        simulate_uvr_scenario(data)


def test_pesos_frech_flows_are_separated():
    eloy = analysis(
        sistema_amortizacion="PESOS", saldo_capital_pesos=Decimal("50000000"),
        valor_cuota_con_subsidio=Decimal("321905.13"), valor_cuota_con_seguros=Decimal("446941.75"),
        valor_cuota_sin_seguros=Decimal("388796.75"), seguros_total_mensual=Decimal("58145"),
        beneficio_frech_mensual=Decimal("125036.62"), capital_pagado_periodo=Decimal("100000"),
        intereses_corrientes_periodo=Decimal("288796.75"), frech_meses_restantes=24,
    )
    snapshot = normalize_credit_snapshot(eloy)
    assert snapshot.contractual_debt_installment == Decimal("388796.75")
    assert snapshot.insurance_total == Decimal("58145")
    assert snapshot.frech_monthly == Decimal("125036.62")


def test_osnaider_uvr_with_frech_is_valid():
    osnaider = analysis(
        sistema_amortizacion="UVR", plan_credito="CUOTA CONSTANTE EN UVR-VIVDA VIS",
        saldo_capital_pesos=Decimal("56069733.47"), valor_uvr_fecha_extracto=Decimal("376.1794"),
        valor_cuota_uvr=Decimal("810.8742"), valor_cuota_sin_seguros=Decimal("305034.17"),
        valor_cuota_con_seguros=Decimal("326168.17"), seguros_total_mensual=Decimal("21134"),
        beneficio_frech_mensual=Decimal("183855.65"), cuotas_pendientes=325,
    )
    snapshot = normalize_credit_snapshot(osnaider)
    assert snapshot.validation_status == ProjectionStatus.VALID
    assert snapshot.snapshot_type == SnapshotType.FULL_INSTALLMENT_WITH_FRECH
    assert abs(snapshot.contractual_debt_installment - Decimal("305034.17")) < Decimal("15")
    assert snapshot.insurance_total == Decimal("21134")
    assert snapshot.frech_monthly == Decimal("183855.65")


def test_lizleidis_cutoff_on_payment_day_is_valid():
    lizleidis = analysis(
        sistema_amortizacion="UVR", plan_credito="CUOTA CONSTANTE EN UVR-VIVDA VIP",
        saldo_capital_pesos=Decimal("76182587.09"), valor_uvr_fecha_extracto=Decimal("408.9685"),
        valor_cuota_uvr=Decimal("1019.3295"), valor_cuota_sin_seguros=Decimal("416873.66"),
        valor_cuota_con_seguros=Decimal("442281.66"), seguros_total_mensual=Decimal("25408"),
        cuotas_pendientes=340,
        raw_data_json={
            "pago_aplicado_periodo": "438655.70",
            "valor_pendiente_cuota": "442281.66"
        }
    )
    snapshot = normalize_credit_snapshot(lizleidis)
    assert snapshot.validation_status == ProjectionStatus.VALID
    assert snapshot.snapshot_type == SnapshotType.UVR_CONSTANT_INSTALLMENT
    assert abs(snapshot.contractual_debt_installment - Decimal("416873.66")) < Decimal("15")
    assert snapshot.insurance_total == Decimal("25408")


def test_jose_daniel_overdue_installment_is_blocked():
    jose_daniel = analysis(
        sistema_amortizacion="UVR", plan_credito="CUOTA CONSTANTE EN UVR-VIVDA VIS",
        saldo_capital_pesos=Decimal("121325607.23"), valor_uvr_fecha_extracto=Decimal("407.6653"),
        valor_cuota_uvr=Decimal("1702.7794"), valor_cuota_sin_seguros=Decimal("694164.07"),
        valor_cuota_con_seguros=Decimal("720286.18"), seguros_total_mensual=Decimal("29731"),
        cuotas_pendientes=348, cuotas_vencidas=1,
    )
    snapshot = normalize_credit_snapshot(jose_daniel)
    assert snapshot.validation_status == ProjectionStatus.OVERDUE_SNAPSHOT
    assert snapshot.snapshot_type == SnapshotType.OVERDUE_INSTALLMENT
    with pytest.raises(ProjectionValidationError):
        validate_projection_snapshot(snapshot, Decimal("0.0560"))


def test_andres_uvr_baja_is_unsupported():
    andres = analysis(
        sistema_amortizacion="UVR", plan_credito="BAJA UVR",
        saldo_capital_pesos=Decimal("85628753.63"), valor_uvr_fecha_extracto=Decimal("404.4291"),
        cuotas_pendientes=358,
    )
    snapshot = normalize_credit_snapshot(andres)
    assert snapshot.validation_status == ProjectionStatus.UNSUPPORTED_UVR_PRODUCT
    assert snapshot.snapshot_type == SnapshotType.UVR_BAJA
    with pytest.raises(ProjectionValidationError):
        validate_projection_snapshot(snapshot, Decimal("0.0695"))

