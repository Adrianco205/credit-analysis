from decimal import Decimal
import pytest
from app.services.pesos_projection_engine import PesosProjectionInfeasibleError, PesosProjectionInput, simulate_pesos


def test_pesos_frech_flows_and_expiry_are_separated():
    result = simulate_pesos(PesosProjectionInput(
        principal_balance=Decimal("30586456.09"), annual_rate=Decimal("0.0621"),
        contractual_debt_installment=Decimal("388796.75"), insurance_monthly=Decimal("58145"),
        non_amortizable_charges=Decimal("0"), frech_monthly=Decimal("125036.62"),
        frech_remaining_months=12, remaining_term=175, extra_payment=Decimal("200000"),
    ))
    assert result.terminated
    assert result.total_bank_flow == result.total_client_payment + result.total_frech
    assert result.total_insurance > 0 and result.total_interest > 0


def test_pesos_frech_without_term_is_blocked():
    with pytest.raises(PesosProjectionInfeasibleError):
        simulate_pesos(PesosProjectionInput(Decimal("10000000"), Decimal("0.1"), Decimal("200000"), Decimal("0"), Decimal("0"), Decimal("10000"), None, 100))


# ═══════════════════════════════════════════════════════════════════════════════
# VENCIMIENTO DEL FRECH — el subsidio es de TASA, no de cuota
# ═══════════════════════════════════════════════════════════════════════════════
# Caso Addeson (Banco de Bogotá 00558564407): 7,47% subsidiada, 11,75% pactada,
# 29 cuotas de FRECH restantes sobre un plazo de 305.

def _addeson(post_rate=Decimal("0.1175"), extra=Decimal("0")):
    return PesosProjectionInput(
        principal_balance=Decimal("61409771.65"),
        annual_rate=Decimal("0.0747"),
        contractual_debt_installment=Decimal("440826.00"),
        insurance_monthly=Decimal("47172.35"),
        non_amortizable_charges=Decimal("35428.73"),
        frech_monthly=Decimal("201269.70"),
        frech_remaining_months=29,
        remaining_term=305,
        extra_payment=extra,
        post_subsidy_annual_rate=post_rate,
    )


def test_vencimiento_frech_no_alarga_el_plazo():
    """Alargar el plazo sería una reestructuración y causal de pérdida del FRECH."""
    resultado = simulate_pesos(_addeson())
    assert resultado.months == 305
    assert resultado.terminated


def test_vencimiento_frech_encarece_el_credito_frente_a_ignorarlo():
    con_vencimiento = simulate_pesos(_addeson())
    sin_vencimiento = simulate_pesos(_addeson(post_rate=None))

    assert con_vencimiento.total_interest > sin_vencimiento.total_interest
    assert con_vencimiento.total_client_payment > sin_vencimiento.total_client_payment


def test_durante_el_subsidio_el_cliente_paga_la_cuota_completa():
    """Con subsidio de tasa el alivio ya está en la cuota: no se resta del bolsillo."""
    resultado = simulate_pesos(_addeson())
    # 440.826,00 + 47.172,35 + 35.428,73 = 523.427,08 (total a pagar del extracto)
    assert resultado.total_client_payment > Decimal("0")
    primeros_29 = Decimal("523427.08") * 29
    assert resultado.total_client_payment > primeros_29


def test_el_frech_reportado_es_el_interes_que_cubre_el_gobierno():
    resultado = simulate_pesos(_addeson())
    # 29 meses de alivio sobre ~61,4M a 4,28 puntos de diferencia.
    assert Decimal("5000000") < resultado.total_frech < Decimal("6500000")
    assert resultado.total_bank_flow == (
        resultado.total_client_payment + resultado.total_frech
    ).quantize(Decimal("0.01"))


def test_sin_tasa_post_subsidio_se_conserva_el_modelo_de_descuento_de_caja():
    """Compatibilidad: sin la tasa nueva, el FRECH sigue restándose del flujo."""
    resultado = simulate_pesos(_addeson(post_rate=None))
    assert resultado.total_frech == Decimal("201269.70") * 29
