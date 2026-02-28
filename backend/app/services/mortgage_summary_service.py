from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.analisis import (
    AjusteInflacionResumen,
    CostosExtraResumen,
    DatosBasicosResumen,
    LimitesBancoResumen,
    MortgageSummary,
    SummaryRow,
    SummarySection,
)


@dataclass
class ResolvedValue:
    value: Decimal | int | None
    source: str
    confidence: float | None
    refs: list[str]


class DocumentTypeClassifier:
    STRATEGIES = {
        "layout_bancolombia_uvr": [
            "estado de credito hipotecario",
            "valor a pagar",
            "saldo a la fecha",
            "uvr",
            "subsidio gobierno",
        ],
        "layout_tabular_hipotecario": [
            "datos generales del credito",
            "total a pagar",
            "valor beneficio",
            "valor total",
            "sistema de amortizacion",
        ],
        "fallback_regex": [
            "credito hipotecario",
            "saldo",
            "cuota",
            "desembolso",
        ],
    }

    @classmethod
    def classify(cls, text: str) -> dict[str, Any]:
        normalized_text = _normalize_key(text)
        scores: dict[str, int] = {}
        matches: dict[str, list[str]] = {}

        for strategy, keywords in cls.STRATEGIES.items():
            hits = [kw for kw in keywords if _normalize_key(kw) in normalized_text]
            matches[strategy] = hits
            scores[strategy] = len(hits)

        best_strategy = max(scores, key=scores.get) if scores else "fallback_regex"
        max_score = scores.get(best_strategy, 0)
        confidence = min(1.0, 0.35 + (max_score * 0.15))

        return {
            "strategy": best_strategy if max_score > 0 else "fallback_regex",
            "confidence": round(confidence, 3),
            "keyword_matches": matches,
        }


class MortgageSummaryBuilder:
    FIELD_SYNONYMS: dict[str, list[str]] = {
        "valor_prestado": ["valor prestado", "valor desembolso", "monto desembolsado", "desembolso"],
        "saldo_actual": [
            "saldo total a la fecha de corte",
            "saldo total a la fecha",
            "saldo a la fecha",
            "saldo actual",
            "saldo actual del credito",
            "saldo del credito",
            "saldo capital",
            "saldo capital en pesos",
        ],
        "total_a_pagar": [
            "total a pagar",
            "valor a pagar",
            "cuota a pagar",
            "cuota neta",
            "cuota con subsidio",
            "valor cuota con subsidio",
            "pago minimo",
        ],
        "beneficio_frech": ["subsidio gobierno", "beneficio frech", "valor beneficio", "valor subsidio"],
        "valor_total": ["valor total", "cuota sin subsidio", "valor cuota sin subsidio", "cuota plena"],
        "cuotas_pactadas": ["cuotas pactadas", "plazo total en meses", "plazo total"],
        "cuotas_pagadas": ["cuotas pagadas", "cuotas canceladas"],
        "nro_cuota_cancelar": ["nro cuota a cancelar", "nro cuota", "numero cuota a cancelar", "número cuota a cancelar"],
        "cuotas_pendientes": ["cuotas pendientes", "cuotas por pagar", "nro cuotas pendientes"],
        "intereses_seguros_acumulado": ["intereses y seguros", "total intereses y seguros", "intereses corrientes", "seguros del periodo"],
        "fecha_pago": ["fecha de pago", "proxima fecha de pago", "fecha proximo pago"],
    }

    ANALYSIS_PRIORITY_FIELDS: dict[str, list[str]] = {
        "valor_prestado": ["valor_prestado_inicial"],
        "saldo_actual": ["saldo_capital_pesos"],
        "total_a_pagar": ["total_por_pagar", "valor_cuota_con_subsidio"],
        "beneficio_frech": ["beneficio_frech_mensual"],
        "valor_total": ["valor_cuota_con_seguros", "valor_cuota_sin_seguros"],
        "cuotas_pactadas": ["cuotas_pactadas", "plazo_total_meses"],
        "cuotas_pagadas": ["cuotas_pagadas"],
        "nro_cuota_cancelar": [],
        "cuotas_pendientes": ["cuotas_pendientes"],
        "intereses_seguros_acumulado": ["total_intereses_seguros"],
        "fecha_pago": [],
    }

    def build(self, analisis: Any) -> dict[str, Any]:
        warnings: list[str] = []
        raw_data = self._collect_raw_data(analisis)
        classifier = DocumentTypeClassifier.classify(raw_data["search_text"])

        resolved: dict[str, ResolvedValue] = {}
        for field_key in self.FIELD_SYNONYMS:
            resolved[field_key] = self._resolve_field(field_key, analisis, raw_data)

        valor_prestado = _to_decimal_or_none(resolved["valor_prestado"].value)
        saldo_actual = _to_decimal_or_none(resolved["saldo_actual"].value)
        valor_total = _to_decimal_or_none(resolved["valor_total"].value)
        total_a_pagar = _to_decimal_or_none(resolved["total_a_pagar"].value)
        beneficio_frech = _to_decimal_or_none(resolved["beneficio_frech"].value) or Decimal("0")

        if (total_a_pagar is None) or (saldo_actual is not None and total_a_pagar == saldo_actual):
            raw_total_a_pagar = self._resolve_raw_field("total_a_pagar", raw_data)
            raw_total_value = _to_decimal_or_none(raw_total_a_pagar.value)
            if raw_total_value is not None and (saldo_actual is None or raw_total_value != saldo_actual):
                resolved["total_a_pagar"] = raw_total_a_pagar
                total_a_pagar = raw_total_value
                if saldo_actual is not None and _to_decimal_or_none(resolved["total_a_pagar"].value) == saldo_actual:
                    warnings.append("wrong_mapping_saldo_as_cuota")

        cuotas_pactadas = _to_int_or_none(resolved["cuotas_pactadas"].value)
        cuotas_pagadas_expl = _to_int_or_none(resolved["cuotas_pagadas"].value)
        nro_cuota_cancelar = _to_int_or_none(resolved["nro_cuota_cancelar"].value)
        cuotas_pendientes_expl = _to_int_or_none(resolved["cuotas_pendientes"].value)

        cuotas_pagadas = cuotas_pagadas_expl
        cuotas_pagadas_resolved = resolved["cuotas_pagadas"]

        if cuotas_pactadas is not None and cuotas_pendientes_expl is not None:
            cuotas_pagadas_calc = max(cuotas_pactadas - cuotas_pendientes_expl, 0)
            if cuotas_pagadas_expl is not None and cuotas_pagadas_expl != cuotas_pagadas_calc:
                warnings.append("cuotas_pagadas_source_discrepancy")
            cuotas_pagadas = cuotas_pagadas_calc
            cuotas_pagadas_resolved = ResolvedValue(
                value=cuotas_pagadas_calc,
                source="calculated",
                confidence=0.95,
                refs=["rule:cuotas_pactadas-cuotas_pendientes"],
            )
        elif cuotas_pagadas is None and nro_cuota_cancelar is not None:
            cuotas_pagadas = nro_cuota_cancelar
            cuotas_pagadas_resolved = ResolvedValue(
                value=nro_cuota_cancelar,
                source=resolved["nro_cuota_cancelar"].source,
                confidence=resolved["nro_cuota_cancelar"].confidence,
                refs=resolved["nro_cuota_cancelar"].refs,
            )

        if cuotas_pactadas is not None and cuotas_pagadas is not None:
            cuotas_por_pagar_calc = max(cuotas_pactadas - cuotas_pagadas, 0)
        else:
            cuotas_por_pagar_calc = None

        if cuotas_pendientes_expl is not None and cuotas_por_pagar_calc is not None and cuotas_pendientes_expl != cuotas_por_pagar_calc:
            warnings.append("cuotas_por_pagar_mismatch")

        cuotas_por_pagar = cuotas_pendientes_expl if cuotas_pendientes_expl is not None else cuotas_por_pagar_calc

        cuota_actual_source = "missing"
        cuota_actual_conf: float | None = None
        cuota_actual_refs: list[str] = []
        no_subsidy_detected = False

        cuota_fallback_value = None
        cuota_fallback_kind = None
        for key, raw_value in [
            ("valor_cuota_con_subsidio", getattr(analisis, "valor_cuota_con_subsidio", None)),
            ("valor_cuota_con_seguros", getattr(analisis, "valor_cuota_con_seguros", None)),
            ("valor_cuota_sin_seguros", getattr(analisis, "valor_cuota_sin_seguros", None)),
        ]:
            parsed_value = _to_decimal_or_none(raw_value)
            if parsed_value is not None and parsed_value > 0:
                cuota_fallback_value = parsed_value
                cuota_fallback_kind = key
                break

        if total_a_pagar is not None and total_a_pagar > 0:
            cuota_actual = total_a_pagar
            cuota_actual_source = resolved["total_a_pagar"].source
            cuota_actual_conf = resolved["total_a_pagar"].confidence
            cuota_actual_refs = resolved["total_a_pagar"].refs
        elif total_a_pagar is not None and total_a_pagar <= 0:
            warnings.append("non_positive_total_a_pagar")
            if cuota_fallback_value is not None:
                cuota_actual = cuota_fallback_value
                cuota_actual_source = f"analysis_fallback:{cuota_fallback_kind}"
                cuota_actual_conf = 0.86
                cuota_actual_refs = [f"fallback:{cuota_fallback_kind}"]
            elif valor_total is not None and beneficio_frech > 0:
                cuota_actual = max(valor_total - beneficio_frech, Decimal("0"))
                cuota_actual_source = "calculated"
                cuota_actual_conf = 0.82
                cuota_actual_refs = resolved["valor_total"].refs + resolved["beneficio_frech"].refs
            elif valor_total is not None:
                cuota_actual = valor_total
                cuota_actual_source = resolved["valor_total"].source
                cuota_actual_conf = resolved["valor_total"].confidence
                cuota_actual_refs = resolved["valor_total"].refs
                no_subsidy_detected = True
            else:
                cuota_actual = None
        elif valor_total is not None and beneficio_frech > 0:
            cuota_actual = max(valor_total - beneficio_frech, Decimal("0"))
            cuota_actual_source = "calculated"
            cuota_actual_conf = 0.82
            cuota_actual_refs = resolved["valor_total"].refs + resolved["beneficio_frech"].refs
        elif valor_total is not None:
            cuota_actual = valor_total
            cuota_actual_source = resolved["valor_total"].source
            cuota_actual_conf = resolved["valor_total"].confidence
            cuota_actual_refs = resolved["valor_total"].refs
            no_subsidy_detected = True
        else:
            cuota_actual = None

        quota_mapping_blocked = False
        if cuota_actual is not None and saldo_actual is not None and cuota_actual == saldo_actual:
            warnings.append("wrong_mapping_saldo_as_cuota")
            warnings.append("blocked_quota_equals_saldo")
            if cuota_fallback_value is not None and cuota_fallback_value != saldo_actual:
                cuota_actual = cuota_fallback_value
                cuota_actual_source = f"analysis_fallback:{cuota_fallback_kind}"
                cuota_actual_conf = 0.86
                cuota_actual_refs = [f"fallback:{cuota_fallback_kind}", "rule:blocked_quota_equals_saldo"]
            else:
                cuota_actual = None
                cuota_actual_source = "missing"
                cuota_actual_conf = None
                cuota_actual_refs = ["rule:blocked_quota_equals_saldo"]
            quota_mapping_blocked = True

        if cuota_actual is not None and valor_prestado is not None and valor_prestado > 0:
            cuota_ratio = cuota_actual / valor_prestado
            if cuota_ratio > Decimal("0.20"):
                warnings.append("possible_wrong_quota_mapping")

        if cuota_actual is not None and valor_total is not None and beneficio_frech > 0 and cuota_actual == valor_total:
            warnings.append("possible_wrong_quota_mapping")

        if valor_total is not None and beneficio_frech is not None and total_a_pagar is not None:
            delta = abs(valor_total - (beneficio_frech + total_a_pagar))
            if delta > Decimal("3"):
                warnings.append("value_total_inconsistency")

        cuota_completa = None
        if cuota_actual is not None:
            if cuota_actual_source.endswith("valor_cuota_con_seguros") or cuota_actual_source.endswith("valor_cuota_sin_seguros"):
                cuota_completa = cuota_actual
            else:
                cuota_completa = cuota_actual + beneficio_frech

        total_pagado_dia = None
        total_pagado_source = "missing"
        total_pagado_refs: list[str] = []
        total_beneficio_frech = None
        monto_real_pagado = None

        pagos_reales_acumulados = self._resolve_real_paid_from_movements(raw_data)
        if cuota_actual is not None and cuotas_pagadas is not None:
            if pagos_reales_acumulados is not None:
                total_pagado_dia = pagos_reales_acumulados
                total_pagado_source = "extracted"
                total_pagado_refs = ["raw:movimientos.total_pagado"]
            else:
                total_pagado_dia = cuota_actual * Decimal(cuotas_pagadas)
                total_pagado_source = "calculated"
                total_pagado_refs = ["rule:cuota_actual*cuotas_pagadas"]
                warnings.append("estimated_total_paid")

            total_beneficio_frech = beneficio_frech * Decimal(cuotas_pagadas)
            monto_real_pagado = total_pagado_dia + total_beneficio_frech

        variacion_saldo_pesos = None
        porcentaje_variacion_saldo = None
        if valor_prestado is not None and saldo_actual is not None and valor_prestado != 0:
            variacion_saldo_pesos = saldo_actual - valor_prestado
            porcentaje_variacion_saldo = (variacion_saldo_pesos / valor_prestado) * Decimal("100")
            if variacion_saldo_pesos > 0:
                warnings.append("saldo_mayor_que_desembolso")

        intereses_explicitos = _to_decimal_or_none(resolved["intereses_seguros_acumulado"].value)
        if intereses_explicitos is not None and intereses_explicitos > 0:
            total_intereses_seguros = intereses_explicitos
            intereses_source = resolved["intereses_seguros_acumulado"].source
            intereses_refs = resolved["intereses_seguros_acumulado"].refs
            intereses_conf = resolved["intereses_seguros_acumulado"].confidence
        elif monto_real_pagado is not None and variacion_saldo_pesos is not None:
            total_intereses_seguros = monto_real_pagado + variacion_saldo_pesos
            intereses_source = "calculated"
            intereses_refs = ["rule:total_abonado+variacion_saldo"]
            intereses_conf = 0.9
        else:
            total_intereses_seguros = None
            intereses_source = "missing"
            intereses_refs = []
            intereses_conf = None

        if intereses_source == "extracted":
            warnings.append("intereses_seguros_period_value")

        if no_subsidy_detected:
            warnings.append("no_subsidy_detected")

        if cuotas_pactadas is not None and cuotas_pagadas is not None and cuotas_por_pagar is not None:
            if abs(cuotas_pactadas - (cuotas_pagadas + cuotas_por_pagar)) > 1:
                warnings.append("cuotas_consistency_mismatch")

        for key, value in {
            "valor_prestado": valor_prestado,
            "saldo_actual": saldo_actual,
            "cuota_actual": cuota_actual,
        }.items():
            if value is not None and value < 0:
                warnings.append(f"negative_value:{key}")

        low_confidence_fields = [
            field_key
            for field_key, value in resolved.items()
            if value.confidence is not None and value.confidence < 0.5
        ]
        if low_confidence_fields:
            warnings.append("low_confidence_extraction")

        fecha_corte = self._resolve_date(getattr(analisis, "fecha_extracto", None))
        fecha_pago = self._resolve_date_field("fecha_pago", raw_data)
        limites_title = self._build_extract_section_title(fecha_corte, fecha_pago)

        sections = [
            SummarySection(
                key="datos_basicos",
                title="DATOS BÁSICOS",
                rows=[
                    self._row("valor_prestado", "Valor prestado", valor_prestado, True, resolved["valor_prestado"]),
                    self._row("cuotas_pactadas", "Cuotas pactadas", cuotas_pactadas, False, resolved["cuotas_pactadas"]),
                    self._row("cuotas_pagadas", "Cuotas pagadas", cuotas_pagadas, False, cuotas_pagadas_resolved),
                    self._row(
                        "cuotas_por_pagar",
                        "Cuotas por pagar",
                        cuotas_por_pagar,
                        False,
                        ResolvedValue(
                            value=cuotas_por_pagar,
                            source=resolved["cuotas_pendientes"].source if cuotas_pendientes_expl is not None else ("calculated" if cuotas_por_pagar is not None else "missing"),
                            confidence=resolved["cuotas_pendientes"].confidence if cuotas_pendientes_expl is not None else (0.9 if cuotas_por_pagar is not None else None),
                            refs=resolved["cuotas_pendientes"].refs if cuotas_pendientes_expl is not None else ["rule:cuotas_pactadas-cuentas_pagadas"],
                        ),
                    ),
                    self._row(
                        "cuota_actual_aprox",
                        "Cuota actual a cancelar aprox.",
                        cuota_actual,
                        True,
                        ResolvedValue(cuota_actual, cuota_actual_source, cuota_actual_conf, cuota_actual_refs),
                    ),
                    self._row("beneficio_frech", "Beneficio FRECH", beneficio_frech, True, resolved["beneficio_frech"]),
                    self._row(
                        "cuota_completa_aprox",
                        "Cuota completa aprox.",
                        cuota_completa,
                        True,
                        ResolvedValue(cuota_completa, "calculated" if cuota_completa is not None else "missing", 0.92 if cuota_completa is not None else None, ["rule:cuota_actual+beneficio"]),
                    ),
                    self._row(
                        "total_pagado_fecha",
                        "Pagado por el cliente (estimado)",
                        total_pagado_dia,
                        True,
                        ResolvedValue(total_pagado_dia, total_pagado_source if total_pagado_dia is not None else "missing", 0.9 if total_pagado_dia is not None else None, total_pagado_refs),
                    ),
                    self._row(
                        "total_frech_recibido",
                        "Aporte FRECH acumulado (estimado)",
                        total_beneficio_frech,
                        True,
                        ResolvedValue(total_beneficio_frech, "calculated" if total_beneficio_frech is not None else "missing", 0.92 if total_beneficio_frech is not None else None, ["rule:beneficio*cuotas_pagadas"]),
                    ),
                    self._row(
                        "monto_real_pagado_banco",
                        "Total abonado al crédito (cliente + FRECH)",
                        monto_real_pagado,
                        True,
                        ResolvedValue(monto_real_pagado, "calculated" if monto_real_pagado is not None else "missing", 0.9 if monto_real_pagado is not None else None, ["rule:total_pagado+total_frech"]),
                    ),
                ],
            ),
            SummarySection(
                key="limites_banco",
                title=limites_title,
                rows=[
                    self._row("valor_prestado_limites", "Valor prestado", valor_prestado, True, resolved["valor_prestado"]),
                    self._row("saldo_actual_credito", "Saldo actual del crédito", saldo_actual, True, resolved["saldo_actual"]),
                ],
            ),
            SummarySection(
                key="ajuste_inflacion",
                title="VARIACIÓN DEL SALDO VS DESEMBOLSO",
                rows=[
                    self._row(
                        "ajuste_pesos",
                        "Variación en pesos (saldo - desembolso)",
                        variacion_saldo_pesos,
                        True,
                        ResolvedValue(variacion_saldo_pesos, "calculated" if variacion_saldo_pesos is not None else "missing", 0.9 if variacion_saldo_pesos is not None else None, ["rule:saldo_actual-valor_prestado"]),
                    ),
                    self._row(
                        "porcentaje_ajuste",
                        "% Variación sobre desembolso",
                        porcentaje_variacion_saldo,
                        False,
                        ResolvedValue(porcentaje_variacion_saldo, "calculated" if porcentaje_variacion_saldo is not None else "missing", 0.9 if porcentaje_variacion_saldo is not None else None, ["rule:variacion/valor_prestado*100"]),
                    ),
                ],
            ),
            SummarySection(
                key="intereses_seguros",
                title="INTERESES Y SEGUROS",
                rows=[
                    self._row(
                        "total_intereses_seguros",
                        "Intereses y seguros",
                        total_intereses_seguros,
                        True,
                        ResolvedValue(total_intereses_seguros, intereses_source, intereses_conf, intereses_refs),
                    ),
                ],
            ),
        ]

        mortgage_summary = MortgageSummary(
            sections=sections,
            warnings=list(dict.fromkeys(warnings)),
            debug={
                "classifier": classifier,
                "applied_rules": {
                    "cuota_actual": cuota_actual_source,
                    "intereses_y_seguros": intereses_source,
                    "cuotas_por_pagar": "extracted" if cuotas_pendientes_expl is not None else "calculated",
                    "total_pagado": total_pagado_source,
                    "quota_mapping_blocked": quota_mapping_blocked,
                },
                "raw_matches": raw_data["matches"],
                "low_confidence_fields": low_confidence_fields,
            },
        )

        legacy = self._build_legacy_blocks(mortgage_summary)
        return {
            "mortgage_summary": mortgage_summary,
            "warnings": mortgage_summary.warnings,
            "debug": mortgage_summary.debug,
            **legacy,
        }

    def _row(self, key: str, label: str, value: Decimal | int | None, currency: bool, resolved: ResolvedValue) -> SummaryRow:
        return SummaryRow(
            key=key,
            label=label,
            value=value,
            currency=currency,
            source=resolved.source if resolved.source in {"extracted", "calculated", "missing"} else "missing",
            confidence=resolved.confidence,
            raw_text_refs=resolved.refs,
        )

    def _collect_raw_data(self, analisis: Any) -> dict[str, Any]:
        bundles: list[dict[str, Any]] = []
        if isinstance(getattr(analisis, "datos_raw_gemini", None), dict):
            bundles.append(analisis.datos_raw_gemini)
        if isinstance(getattr(analisis, "raw_data_json", None), dict):
            bundles.append(analisis.raw_data_json)
        if isinstance(getattr(analisis, "computed_summary_json", None), dict):
            bundles.append(analisis.computed_summary_json)

        flat_items: list[tuple[str, Any]] = []
        for bundle in bundles:
            flat_items.extend(_flatten_dict(bundle))

        search_text = " ".join([f"{k} {v}" for k, v in flat_items if v is not None])
        matches = {k: str(v) for k, v in flat_items[:120]}

        return {
            "flat_items": flat_items,
            "search_text": search_text,
            "matches": matches,
            "confidence_map": getattr(analisis, "confidence_map_json", {}) if isinstance(getattr(analisis, "confidence_map_json", None), dict) else {},
        }

    def _resolve_field(self, field_key: str, analisis: Any, raw_data: dict[str, Any]) -> ResolvedValue:
        confidence_map: dict[str, Any] = raw_data.get("confidence_map", {})

        for attr in self.ANALYSIS_PRIORITY_FIELDS.get(field_key, []):
            if hasattr(analisis, attr):
                raw_value = getattr(analisis, attr)
                parsed = _parse_mixed_number(raw_value)
                if parsed is not None:
                    conf = _to_float(confidence_map.get(attr)) or 0.88
                    return ResolvedValue(parsed, "extracted", conf, [f"model:{attr}"])

        synonyms = [_normalize_key(s) for s in self.FIELD_SYNONYMS.get(field_key, [])]
        best_match: ResolvedValue | None = None

        for key_path, raw_value in raw_data["flat_items"]:
            normalized_key = _normalize_key(key_path)
            if any(s in normalized_key for s in synonyms):
                parsed = _parse_mixed_number(raw_value)
                if parsed is None:
                    continue
                conf = _to_float(confidence_map.get(key_path)) or 0.7
                candidate = ResolvedValue(parsed, "extracted", conf, [f"raw:{key_path}"])
                if not best_match or (candidate.confidence or 0) > (best_match.confidence or 0):
                    best_match = candidate

        if best_match:
            return best_match

        return ResolvedValue(None, "missing", None, [])

    def _resolve_raw_field(self, field_key: str, raw_data: dict[str, Any]) -> ResolvedValue:
        confidence_map: dict[str, Any] = raw_data.get("confidence_map", {})
        synonyms = [_normalize_key(s) for s in self.FIELD_SYNONYMS.get(field_key, [])]

        preferred = [
            "valor a pagar",
            "total a pagar",
            "cuota a pagar",
            "cuota con subsidio",
            "pago minimo",
        ] if field_key == "total_a_pagar" else []

        best_match: ResolvedValue | None = None
        for key_path, raw_value in raw_data["flat_items"]:
            normalized_key = _normalize_key(key_path)
            if any(p in normalized_key for p in preferred):
                parsed = _parse_mixed_number(raw_value)
                if parsed is None:
                    continue
                conf = _to_float(confidence_map.get(key_path)) or 0.82
                return ResolvedValue(parsed, "extracted", conf, [f"raw:{key_path}"])

            if any(s in normalized_key for s in synonyms):
                parsed = _parse_mixed_number(raw_value)
                if parsed is None:
                    continue
                conf = _to_float(confidence_map.get(key_path)) or 0.75
                candidate = ResolvedValue(parsed, "extracted", conf, [f"raw:{key_path}"])
                if not best_match or (candidate.confidence or 0) > (best_match.confidence or 0):
                    best_match = candidate

        if best_match:
            return best_match
        return ResolvedValue(None, "missing", None, [])

    def _resolve_real_paid_from_movements(self, raw_data: dict[str, Any]) -> Decimal | None:
        target_tokens = [
            "total pagado",
            "pagado acumulado",
            "pagos acumulados",
            "abonos acumulados",
        ]
        for key_path, raw_value in raw_data["flat_items"]:
            normalized_key = _normalize_key(key_path)
            if any(token in normalized_key for token in target_tokens):
                parsed = _parse_mixed_number(raw_value)
                return _to_decimal_or_none(parsed)
        return None

    def _resolve_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if not text:
            return None
        for pattern in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(text, pattern).date()
            except ValueError:
                continue
        return None

    def _build_extract_section_title(self, fecha_corte: date | None, fecha_pago: date | None) -> str:
        if not fecha_corte and not fecha_pago:
            return "CORTE DEL EXTRACTO"

        parts: list[str] = []
        if fecha_corte:
            parts.append(f"corte: {fecha_corte.isoformat()}")
        if fecha_pago:
            parts.append(f"pago: {fecha_pago.isoformat()}")
        return f"CORTE DEL EXTRACTO ({', '.join(parts)})"

    def _resolve_date_field(self, field_key: str, raw_data: dict[str, Any]) -> date | None:
        synonyms = [_normalize_key(s) for s in self.FIELD_SYNONYMS.get(field_key, [])]
        for key_path, raw_value in raw_data["flat_items"]:
            normalized_key = _normalize_key(key_path)
            if any(s in normalized_key for s in synonyms):
                parsed = self._resolve_date(raw_value)
                if parsed:
                    return parsed
        return None

    def _build_legacy_blocks(self, summary: MortgageSummary) -> dict[str, Any]:
        row_map: dict[str, SummaryRow] = {}
        for section in summary.sections:
            for row in section.rows:
                row_map[row.key] = row

        datos_basicos = DatosBasicosResumen(
            valor_prestado=_to_decimal_or_zero(row_map.get("valor_prestado")),
            cuotas_pactadas=_to_int_or_zero(row_map.get("cuotas_pactadas")),
            cuotas_pagadas=_to_int_or_zero(row_map.get("cuotas_pagadas")),
            cuotas_por_pagar=_to_int_or_zero(row_map.get("cuotas_por_pagar")),
            cuota_actual_aprox=_to_decimal_or_zero(row_map.get("cuota_actual_aprox")),
            beneficio_frech=_to_decimal_or_zero(row_map.get("beneficio_frech")),
            cuota_completa_aprox=_to_decimal_or_zero(row_map.get("cuota_completa_aprox")),
            total_pagado_fecha=_to_decimal_or_zero(row_map.get("total_pagado_fecha")),
            total_frech_recibido=_to_decimal_or_zero(row_map.get("total_frech_recibido")),
            monto_real_pagado_banco=_to_decimal_or_zero(row_map.get("monto_real_pagado_banco")),
        )

        limites_banco = LimitesBancoResumen(
            valor_prestado=_to_decimal_or_zero(row_map.get("valor_prestado_limites")),
            saldo_actual_credito=_to_decimal_or_zero(row_map.get("saldo_actual_credito")),
            abono_adicional_cuota=None,
        )

        ajuste_value = row_map.get("ajuste_pesos")
        porcentaje_value = row_map.get("porcentaje_ajuste")
        ajuste_inflacion = None
        if ajuste_value and ajuste_value.value is not None:
            ajuste_inflacion = AjusteInflacionResumen(
                ajuste_pesos=_to_decimal_or_zero(ajuste_value),
                porcentaje_ajuste=_to_decimal_or_zero(porcentaje_value),
                metodo="plantilla_canonica",
            )

        costos_extra = CostosExtraResumen(
            total_intereses_seguros=_to_decimal_or_zero(row_map.get("total_intereses_seguros")),
            formula="total_abonado_al_credito + variacion_saldo_vs_desembolso",
        )

        return {
            "datos_basicos": datos_basicos,
            "limites_banco": limites_banco,
            "ajuste_inflacion": ajuste_inflacion,
            "costos_extra": costos_extra,
        }


def build_mortgage_summary_payload(analisis: Any) -> dict[str, Any]:
    builder = MortgageSummaryBuilder()
    return builder.build(analisis)


def _flatten_dict(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_flatten_dict(value, next_prefix))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            next_prefix = f"{prefix}[{index}]"
            items.extend(_flatten_dict(value, next_prefix))
    else:
        items.append((prefix, data))
    return items


def _normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _parse_mixed_number(value: Any) -> Decimal | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return None

    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except Exception:
            return None

    return _parse_decimal_string(text)


def _parse_decimal_string(text: str) -> Decimal | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    cleaned = re.sub(r"[^\d,.-]", "", cleaned)
    if cleaned in {"", "-", ".", ","}:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) in {1, 2}:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _to_decimal_or_none(value: Decimal | int | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return None


def _to_int_or_none(value: Decimal | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    return None


def _to_decimal_or_zero(row: SummaryRow | None) -> Decimal:
    if not row or row.value is None:
        return Decimal("0")
    if isinstance(row.value, Decimal):
        return row.value
    if isinstance(row.value, int):
        return Decimal(row.value)
    return Decimal("0")


def _to_int_or_zero(row: SummaryRow | None) -> int:
    if not row or row.value is None:
        return 0
    if isinstance(row.value, int):
        return row.value
    if isinstance(row.value, Decimal):
        return int(row.value)
    return 0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
