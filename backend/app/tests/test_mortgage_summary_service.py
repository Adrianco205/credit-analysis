from types import SimpleNamespace
from decimal import Decimal

from app.services.mortgage_summary_service import build_mortgage_summary_payload


def _analysis_stub(**overrides):
    base = {
        "valor_prestado_inicial": None,
        "saldo_capital_pesos": None,
        "total_por_pagar": None,
        "valor_cuota_con_subsidio": None,
        "valor_cuota_con_seguros": None,
        "valor_cuota_sin_seguros": None,
        "beneficio_frech_mensual": None,
        "cuotas_pactadas": None,
        "plazo_total_meses": None,
        "cuotas_pagadas": None,
        "cuotas_pendientes": None,
        "total_intereses_seguros": None,
        "datos_raw_gemini": {},
        "raw_data_json": {},
        "computed_summary_json": {},
        "confidence_map_json": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_summary_with_subsidy_uses_total_a_pagar_as_cuota_actual():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("64733094"),
        saldo_capital_pesos=Decimal("61765855.64"),
        total_por_pagar=Decimal("523427.08"),
        valor_cuota_con_seguros=Decimal("724696.78"),
        beneficio_frech_mensual=Decimal("201269.70"),
        cuotas_pactadas=360,
        cuotas_pagadas=55,
        cuotas_pendientes=305,
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]

    datos_basicos = {row.key: row for row in summary.sections[0].rows}
    ajuste_rows = {row.key: row for row in summary.sections[2].rows}
    intereses_rows = {row.key: row for row in summary.sections[3].rows}

    assert datos_basicos["cuota_actual_aprox"].value == Decimal("523427.08")
    assert datos_basicos["beneficio_frech"].value == Decimal("201269.70")
    assert datos_basicos["cuota_completa_aprox"].value == Decimal("724696.78")

    assert datos_basicos["total_pagado_fecha"].value == Decimal("28788489.40")
    assert datos_basicos["total_frech_recibido"].value == Decimal("11069833.50")
    assert datos_basicos["monto_real_pagado_banco"].value == Decimal("39858322.90")

    assert ajuste_rows["ajuste_pesos"].value == Decimal("-2967238.36")
    assert intereses_rows["total_intereses_seguros"].value == Decimal("36891084.54")
    assert "possible_wrong_quota_mapping" not in summary.warnings


def test_summary_extracts_valor_a_pagar_and_derives_cuotas_pagadas_from_pending():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("45200180"),
        saldo_capital_pesos=Decimal("56069733.47"),
        valor_cuota_con_subsidio=Decimal("56069733.47"),
        beneficio_frech_mensual=Decimal("183855.65"),
        plazo_total_meses=360,
        cuotas_pendientes=325,
        cuotas_pagadas=36,
        datos_raw_gemini={
            "Valor a Pagar": "$ 326,168.17",
            "Valor subsidio Gobierno": "$ 183,855.65",
        },
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]
    rows = {row.key: row for row in summary.sections[0].rows}

    assert rows["cuota_actual_aprox"].value == Decimal("326168.17")
    assert rows["cuota_completa_aprox"].value == Decimal("510023.82")
    assert rows["cuotas_pagadas"].value == 35
    assert rows["total_pagado_fecha"].value == Decimal("11415885.95")
    assert rows["total_frech_recibido"].value == Decimal("6434947.75")
    assert rows["monto_real_pagado_banco"].value == Decimal("17850833.70")
    assert "wrong_mapping_saldo_as_cuota" not in summary.warnings
    assert "cuotas_pagadas_source_discrepancy" in summary.warnings


def test_summary_with_total_a_pagar_and_beneficio_from_raw():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("64733094"),
        saldo_capital_pesos=Decimal("61765855.64"),
        cuotas_pactadas=360,
        cuotas_pagadas=55,
        datos_raw_gemini={
            "TOTAL A PAGAR": "$ 523.427,08",
            "VALOR BENEFICIO": "$ 201.269,70",
            "VALOR TOTAL": "$ 724.696,78",
        },
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]
    rows = {row.key: row for row in summary.sections[0].rows}

    assert rows["cuota_actual_aprox"].value == Decimal("523427.08")
    assert rows["beneficio_frech"].value == Decimal("201269.70")
    assert rows["cuota_completa_aprox"].value == Decimal("724696.78")
    assert rows["total_pagado_fecha"].value == Decimal("28788489.40")
    assert "value_total_inconsistency" not in summary.warnings


def test_summary_without_subsidy_falls_back_to_valor_total():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("45200180"),
        saldo_capital_pesos=Decimal("42000000"),
        valor_cuota_con_seguros=Decimal("400000"),
        beneficio_frech_mensual=Decimal("0"),
        cuotas_pactadas=360,
        cuotas_pagadas=10,
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]
    rows = {row.key: row for row in summary.sections[0].rows}

    assert rows["cuota_actual_aprox"].value == Decimal("400000")
    assert rows["cuota_completa_aprox"].value == Decimal("400000")
    assert "no_subsidy_detected" in summary.warnings


def test_summary_uses_analysis_quota_when_total_a_pagar_is_zero():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("9000158974"),
        saldo_capital_pesos=Decimal("56069733.47"),
        total_por_pagar=Decimal("0"),
        valor_cuota_con_seguros=Decimal("739086"),
        beneficio_frech_mensual=Decimal("0"),
        cuotas_pactadas=360,
        cuotas_pendientes=237,
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]
    rows = {row.key: row for row in summary.sections[0].rows}

    assert rows["cuota_actual_aprox"].value == Decimal("739086")
    assert rows["cuota_completa_aprox"].value == Decimal("739086")
    assert "non_positive_total_a_pagar" in summary.warnings


def test_summary_keeps_structure_when_values_missing_or_raw_formatted():
    analisis = _analysis_stub(
        datos_raw_gemini={
            "Estado de Crédito Hipotecario": "UVR",
            "Valor desembolso": "$ 1.234.567,89",
            "Saldo a la fecha": "$ 1,100,000.25",
            "Total a pagar": "$ 9.876,54",
            "Subsidio Gobierno": "$ 1.000,00",
        }
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]

    assert [section.title for section in summary.sections] == [
        "DATOS BÁSICOS",
        "CORTE DEL EXTRACTO",
        "VARIACIÓN DEL SALDO VS DESEMBOLSO",
        "INTERESES Y SEGUROS",
    ]

    datos_basicos_rows = summary.sections[0].rows
    assert len(datos_basicos_rows) == 10
    assert datos_basicos_rows[0].label == "Valor prestado"
    assert datos_basicos_rows[4].label == "Cuota actual a cancelar aprox."
    assert datos_basicos_rows[6].label == "Cuota completa aprox."

    value_map = {row.key: row.value for row in datos_basicos_rows}
    assert value_map["valor_prestado"] == Decimal("1234567.89")
    assert value_map["cuota_actual_aprox"] == Decimal("9876.54")
    assert value_map["beneficio_frech"] == Decimal("1000.00")


def test_summary_blocks_when_cuota_matches_saldo_value():
    analisis = _analysis_stub(
        valor_prestado_inicial=Decimal("64733094"),
        saldo_capital_pesos=Decimal("61765855.64"),
        total_por_pagar=Decimal("61765855.64"),
        valor_cuota_con_seguros=Decimal("724696.78"),
        beneficio_frech_mensual=Decimal("201269.70"),
        cuotas_pactadas=360,
        cuotas_pagadas=55,
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]
    rows = {row.key: row for row in summary.sections[0].rows}

    assert "blocked_quota_equals_saldo" in summary.warnings
    assert rows["cuota_actual_aprox"].value == Decimal("724696.78")
    assert rows["cuota_completa_aprox"].value == Decimal("724696.78")
    assert rows["total_pagado_fecha"].value == Decimal("39858322.90")
    assert rows["monto_real_pagado_banco"].value == Decimal("50928156.40")
    assert summary.debug["applied_rules"]["quota_mapping_blocked"] is True


def test_summary_sets_extract_section_title_with_corte_and_pago_dates():
    analisis = _analysis_stub(
        fecha_extracto="2024-08-31",
        datos_raw_gemini={
            "Fecha de pago": "2024/09/29",
        },
    )

    payload = build_mortgage_summary_payload(analisis)
    summary = payload["mortgage_summary"]

    assert summary.sections[1].title == "CORTE DEL EXTRACTO (corte: 2024-08-31, pago: 2024-09-29)"
