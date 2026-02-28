"""Tests para el servicio de indicadores financieros (providers oficiales)."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.services.indicadores_service import (
    BanRepFilesProvider,
    CacheIndicadores,
    FuenteDatos,
    IndicadorNoDisponibleError,
    IndicadoresFinancierosService,
)


@pytest.fixture
def servicio():
    return IndicadoresFinancierosService()


@pytest.fixture
def cache():
    return CacheIndicadores()


class TestCacheIndicadores:
    def test_cache_set_get(self, cache):
        cache.set("key", {"valor": Decimal("1")}, ttl_horas=1)
        assert cache.get("key") == {"valor": Decimal("1")}

    def test_cache_stale(self, cache):
        cache.set("key", {"valor": Decimal("1")}, ttl_horas=0)
        assert cache.get("key") is None
        assert cache.get_stale("key") == {"valor": Decimal("1")}


class TestNormalizacion:
    def test_parse_date(self, servicio):
        assert servicio.parse_date("2026-02-15") == date(2026, 2, 15)
        assert servicio.parse_date("15/02/2026") == date(2026, 2, 15)

    def test_parse_decimal(self, servicio):
        assert servicio.parse_decimal("1.234,56") == Decimal("1234.56")
        assert servicio.parse_decimal("9.80%") == Decimal("9.80")

    def test_extract_records_from_payload(self, servicio):
        payload = {
            "data": [
                {"fecha": "2025-10-31", "valor": "5.41"},
                {"fecha": "2025-11-30", "valor": "5.30"},
            ]
        }
        records = servicio.extract_records(payload)
        assert len(records) == 2
        assert records[0]["fecha"] == "2025-10-31"

    def test_normalize_records(self, servicio):
        records = [
            {"fecha": "31/10/2025", "valor": "5,41"},
            {"fecha": "30/11/2025", "valor": "5,30"},
        ]
        normalized = servicio.normalize_records(records)
        assert len(normalized) == 2
        assert normalized[1]["fecha"] == date(2025, 11, 30)
        assert normalized[1]["valor"] == Decimal("5.30")


class TestBanRepFilesParser:
    def test_extract_uvr_from_dataframe(self, servicio):
        provider = BanRepFilesProvider(servicio)
        df = pd.DataFrame(
            {
                "Fecha": ["2026-02-14", "2026-02-15"],
                "UVR": ["400,1234", "400,5678"],
            }
        )
        rows = provider.extract_records_from_dataframe("uvr", df)
        assert len(rows) == 2
        assert rows[-1]["valor"] == Decimal("400.5678")

    def test_extract_dtf_from_dataframe(self, servicio):
        provider = BanRepFilesProvider(servicio)
        df = pd.DataFrame(
            {
                "fecha": ["14/02/2026", "15/02/2026"],
                "DTF E.A.": ["9,75", "9,80"],
            }
        )
        rows = provider.extract_records_from_dataframe("dtf", df)
        assert len(rows) == 2
        assert rows[-1]["valor"] == Decimal("9.80")

    def test_extract_ibr_from_dataframe(self, servicio):
        provider = BanRepFilesProvider(servicio)
        df = pd.DataFrame(
            {
                "Fecha": ["2026-02-14", "2026-02-15"],
                "IBR Overnight": ["9.70", "9.71"],
            }
        )
        rows = provider.extract_records_from_dataframe("ibr", df)
        assert len(rows) == 2
        assert rows[-1]["valor"] == Decimal("9.71")

    def test_extract_uvr_from_matrix_layout(self, servicio):
        provider = BanRepFilesProvider(servicio)
        df = pd.DataFrame(
            {
                "Indicador": ["TRM", "UVR (Unidad de Valor Real)"],
                pd.Timestamp("2026-02-14"): ["4200", "400.1234"],
                pd.Timestamp("2026-02-15"): ["4210", "400.5678"],
                pd.Timestamp("2026-02-16"): ["4220", "400.9876"],
                pd.Timestamp("2026-02-17"): ["4230", "401.1111"],
                pd.Timestamp("2026-02-18"): ["4240", "401.2222"],
            }
        )
        rows = provider.extract_records_from_matrix("uvr", df)
        assert len(rows) == 5
        assert rows[-1]["valor"] == Decimal("401.2222")

    @pytest.mark.asyncio
    async def test_fetch_records_uvr_prefers_fresher_workbook_over_stale_pdf(self, servicio):
        provider = BanRepFilesProvider(servicio)
        fecha_inicio = date(2026, 2, 1)
        fecha_fin = date(2026, 2, 28)

        with patch.object(
            provider,
            "_extract_uvr_from_pdf",
            AsyncMock(return_value=[{"fecha": date(2026, 2, 15), "valor": Decimal("398.3298")}]),
        ), patch.object(
            provider,
            "_load_workbook",
            AsyncMock(return_value={"hoja": pd.DataFrame()}),
        ), patch.object(
            provider,
            "extract_records_from_workbook",
            return_value=[
                {"fecha": date(2026, 2, 27), "valor": Decimal("399.1111")},
                {"fecha": date(2026, 2, 28), "valor": Decimal("399.2222")},
            ],
        ):
            rows = await provider.fetch_records("uvr", fecha_inicio, fecha_fin)

        assert rows[-1]["fecha"] == date(2026, 2, 28)
        assert rows[-1]["valor"] == Decimal("399.2222")

    @pytest.mark.asyncio
    async def test_fetch_records_uvr_keeps_pdf_when_workbook_fails(self, servicio):
        provider = BanRepFilesProvider(servicio)
        fecha_inicio = date(2026, 2, 1)
        fecha_fin = date(2026, 2, 28)

        with patch.object(
            provider,
            "_extract_uvr_from_pdf",
            AsyncMock(return_value=[{"fecha": date(2026, 2, 15), "valor": Decimal("398.3298")}]),
        ), patch.object(
            provider,
            "_load_workbook",
            AsyncMock(side_effect=RuntimeError("workbook unavailable")),
        ):
            rows = await provider.fetch_records("uvr", fecha_inicio, fecha_fin)

        assert len(rows) == 1
        assert rows[0]["fecha"] == date(2026, 2, 15)
        assert rows[0]["valor"] == Decimal("398.3298")


class TestConversiones:
    def test_uvr_a_pesos(self, servicio):
        assert servicio.convertir_uvr_a_pesos(Decimal("1000"), Decimal("400")) == Decimal("400000.00")

    def test_pesos_a_uvr(self, servicio):
        assert servicio.convertir_pesos_a_uvr(Decimal("400000"), Decimal("400")) == Decimal("1000.0000")


class TestIpcBuilder:
    def test_ipc_builder_with_annual_variation_series(self, servicio):
        records = [
            {"fecha": date(2024, 11, 29), "valor": Decimal("5.20")},
            {"fecha": date(2025, 10, 31), "valor": Decimal("5.41")},
            {"fecha": date(2025, 11, 28), "valor": Decimal("5.30")},
        ]

        ipc = servicio._build_ipc(records, 2025, 11, FuenteDatos.BANREP_FILES)
        assert ipc.tipo_serie == "VARIACION_ANUAL_PORCENTUAL"
        assert ipc.variacion_anual == Decimal("5.30")
        assert ipc.variacion_mensual is None
        assert Decimal("4.5") <= ipc.variacion_anual <= Decimal("6.5")

    def test_ipc_builder_with_index_series(self, servicio):
        records = [
            {"fecha": date(2024, 11, 30), "valor": Decimal("145.00")},
            {"fecha": date(2025, 10, 31), "valor": Decimal("152.00")},
            {"fecha": date(2025, 11, 30), "valor": Decimal("152.30")},
        ]

        ipc = servicio._build_ipc(records, 2025, 11, FuenteDatos.BANREP_API)
        assert ipc.tipo_serie == "INDICE_IPC"
        assert ipc.variacion_mensual is not None
        assert ipc.variacion_mensual > Decimal("0")
        assert ipc.variacion_anual > Decimal("0")


@pytest.mark.asyncio
class TestServicio:
    async def test_obtener_uvr_files_provider(self, servicio):
        records = [{"fecha": date(2026, 2, 15), "valor": Decimal("400.5678")}]
        with patch.object(servicio, "_fetch_records_with_providers", AsyncMock(return_value=(records, FuenteDatos.BANREP_FILES))):
            result = await servicio.obtener_uvr(date(2026, 2, 15))
            assert result.valor == Decimal("400.5678")
            assert result.fuente == FuenteDatos.BANREP_FILES

    async def test_fallback_stale_when_provider_fails(self, servicio):
        key = "uvr:2026-02-15"
        from app.services.indicadores_service import _cache

        _cache.set(
            key,
            {
                "fecha": date(2026, 2, 15),
                "valor": Decimal("400.1111"),
                "fecha_actualizacion": datetime.now(),
            },
            ttl_horas=0,
        )

        with patch.object(servicio, "_fetch_records_with_providers", AsyncMock(side_effect=IndicadorNoDisponibleError("down"))):
            result = await servicio.obtener_uvr(date(2026, 2, 15))
            assert result.fuente == FuenteDatos.CACHE_STALE
            assert result.valor == Decimal("400.1111")
            assert result.warning is not None

    async def test_historico_uvr_single_fetch(self, servicio):
        records = [
            {"fecha": date(2026, 2, 10), "valor": Decimal("399.10")},
            {"fecha": date(2026, 2, 11), "valor": Decimal("399.20")},
        ]
        with patch.object(servicio, "_fetch_records_with_providers", AsyncMock(return_value=(records, FuenteDatos.BANREP_FILES))) as mocked:
            result = await servicio.obtener_historico_uvr(date(2026, 2, 10), date(2026, 2, 11))
            assert len(result) == 2
            mocked.assert_awaited_once()

    async def test_fetch_uvr_combines_providers_and_keeps_latest_date(self, servicio):
        files_provider = AsyncMock()
        files_provider.name = "BANREP_FILES"
        files_provider.fetch_records = AsyncMock(return_value=[
            {"fecha": date(2026, 2, 15), "valor": Decimal("398.3298")},
        ])

        api_provider = AsyncMock()
        api_provider.name = "BANREP_API"
        api_provider.fetch_records = AsyncMock(return_value=[
            {"fecha": date(2026, 2, 28), "valor": Decimal("400.5052")},
        ])

        servicio._providers = [files_provider, api_provider]

        records, fuente = await servicio._fetch_records_with_providers(
            "uvr",
            date(2026, 2, 1),
            date(2026, 2, 28),
        )

        assert records[-1]["fecha"] == date(2026, 2, 28)
        assert records[-1]["valor"] == Decimal("400.5052")
        assert fuente == FuenteDatos.BANREP_API
