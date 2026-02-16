"""
Servicio de Indicadores Financieros de Colombia (production-ready).

Estrategia de fuentes oficiales:
1) BanRepFilesProvider (XLS/XLSX oficiales) - PRIMARIO
2) BanRepSeriesProvider (API suameca) - SECUNDARIO
3) CacheProvider (fresh / stale)

No se usan estimaciones manuales.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional

import httpx
import pandas as pd
from pypdf import PdfReader

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30.0
RETRY_DELAYS_SECONDS = [0.5, 1.0, 2.0]

SERIES_BANREP = {
    "UVR": "32274",
    "DTF": "32249",
    "IBR": "32299",
    "IPC": "32278",
}

BANREP_STATS_URL = "https://suameca.banrep.gov.co/estadisticas-economicas/api/series"
BANREP_REFERER = "https://suameca.banrep.gov.co/estadisticas-economicas/"
BANREP_ORIGIN = "https://suameca.banrep.gov.co"

BANREP_FILES = {
    "INDICADORES_DIARIOS": "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls",
    "INDICADORES_3S": "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_3s_new.xls",
    "IBR": "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/IBR.xlsx",
    "UVR_PDF": "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/datos_estadisticos_uvr.pdf",
}

TTL_HORAS = {
    "uvr": 12,
    "dtf": 12,
    "ibr": 12,
    "ipc": 24,
    "historico_uvr": 12,
    "consolidados": 12,
    "banrep_file": 12,
}


class FuenteDatos(str, Enum):
    BANREP_FILES = "BANREP_FILES"
    BANREP_API = "BANREP_API"
    CACHE = "CACHE"
    CACHE_STALE = "CACHE_STALE"


class IndicadorNoDisponibleError(RuntimeError):
    """Proveedor oficial temporalmente no disponible."""


@dataclass
class ValorUVR:
    fecha: date
    valor: Decimal
    fuente: FuenteDatos
    fecha_actualizacion: datetime
    definicion: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class ValorIPC:
    fecha: date
    valor: Decimal
    variacion_mensual: Optional[Decimal]
    variacion_anual: Decimal
    fuente: FuenteDatos
    fecha_actualizacion: datetime
    tipo_serie: Optional[str] = None
    definicion: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class ValorDTF:
    fecha: date
    valor: Decimal
    fuente: FuenteDatos
    fecha_actualizacion: datetime
    definicion: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class ValorIBR:
    fecha: date
    overnight: Decimal
    un_mes: Optional[Decimal]
    tres_meses: Optional[Decimal]
    fuente: FuenteDatos
    fecha_actualizacion: datetime
    definicion: Optional[str] = None
    warning: Optional[str] = None


@dataclass
class IndicadoresFinancieros:
    fecha: date
    uvr: Optional[Decimal] = None
    dtf: Optional[Decimal] = None
    ibr_overnight: Optional[Decimal] = None
    ipc_anual: Optional[Decimal] = None
    fuente: FuenteDatos = FuenteDatos.BANREP_FILES
    fecha_actualizacion: datetime = field(default_factory=datetime.now)
    warning: Optional[str] = None


@dataclass
class CacheEntry:
    valor: Any
    creado_en: datetime
    ttl: timedelta


class CacheIndicadores:
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if datetime.now() - entry.creado_en <= entry.ttl:
            return entry.valor
        return None

    def get_stale(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        return entry.valor if entry else None

    def set(self, key: str, valor: Any, ttl_horas: int) -> None:
        self._cache[key] = CacheEntry(
            valor=valor,
            creado_en=datetime.now(),
            ttl=timedelta(hours=ttl_horas),
        )

    def clear(self) -> None:
        self._cache.clear()


@dataclass
class CircuitBreakerState:
    consecutivos_fallidos: int = 0
    abierto_hasta: Optional[datetime] = None


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_minutes: int = 10):
        self.threshold = threshold
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self._states: Dict[str, CircuitBreakerState] = {}

    def is_open(self, key: str) -> bool:
        state = self._states.get(key)
        if not state or not state.abierto_hasta:
            return False
        if datetime.now() >= state.abierto_hasta:
            state.abierto_hasta = None
            state.consecutivos_fallidos = 0
            return False
        return True

    def record_success(self, key: str) -> None:
        state = self._states.setdefault(key, CircuitBreakerState())
        state.consecutivos_fallidos = 0
        state.abierto_hasta = None

    def record_failure(self, key: str) -> None:
        state = self._states.setdefault(key, CircuitBreakerState())
        state.consecutivos_fallidos += 1
        if state.consecutivos_fallidos >= self.threshold:
            state.abierto_hasta = datetime.now() + self.cooldown


_cache = CacheIndicadores()
_breaker = CircuitBreaker()
_singleflight_locks: Dict[str, asyncio.Lock] = {}


def _get_singleflight_lock(key: str) -> asyncio.Lock:
    lock = _singleflight_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _singleflight_locks[key] = lock
    return lock


class BaseProvider:
    name = "BASE"

    async def fetch_records(
        self,
        indicator_key: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class BanRepSeriesProvider(BaseProvider):
    name = "BANREP_API"

    def __init__(self, service: "IndicadoresFinancierosService"):
        self.service = service

    async def fetch_records(
        self,
        indicator_key: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Dict[str, Any]]:
        serie = SERIES_BANREP[indicator_key.upper()]
        url = f"{BANREP_STATS_URL}/{serie}"
        params = {
            "fechaInicio": fecha_inicio.strftime("%d/%m/%Y"),
            "fechaFin": fecha_fin.strftime("%d/%m/%Y"),
            "formato": "json",
        }

        payload = await self._get_json_with_retry(url, params)
        records = self.service.extract_records(payload)
        normalized = self.service.normalize_records(records)
        self.service.log_provider_debug(
            provider=self.name,
            indicator_key=indicator_key,
            status=200,
            content_type="application/json",
            payload=payload,
            normalized=normalized,
        )
        return normalized

    async def _get_json_with_retry(self, url: str, params: Dict[str, Any]) -> Any:
        client = await self.service._get_client()
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "Referer": BANREP_REFERER,
            "Origin": BANREP_ORIGIN,
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        }

        last_error: Optional[Exception] = None

        for attempt, delay in enumerate(RETRY_DELAYS_SECONDS, start=1):
            try:
                response = await client.get(url, params=params, headers=headers)
                logger.debug(
                    "banrep_series_http provider=%s url=%s status=%s content_type=%s",
                    self.name,
                    str(response.url),
                    response.status_code,
                    response.headers.get("content-type"),
                )
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code}")

                content_type = (response.headers.get("content-type") or "").lower()
                body = response.text.strip()

                if not body:
                    raise RuntimeError("Respuesta vacía")

                if body.startswith("<") or "text/html" in content_type:
                    snippet = body[:200].replace("\n", " ")
                    logger.debug(
                        "banrep_series_invalid_html provider=%s url=%s snippet=%s",
                        self.name,
                        str(response.url),
                        snippet,
                    )
                    raise RuntimeError(f"Respuesta HTML no válida ({content_type}): {snippet}")

                try:
                    return json.loads(body)
                except json.JSONDecodeError as exc:
                    snippet = body[:200].replace("\n", " ")
                    raise RuntimeError(f"JSON inválido: {snippet}") from exc
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "banrep_series_attempt_failed provider=%s url=%s attempt=%s/%s error=%s",
                    self.name,
                    response.url if "response" in locals() else url,
                    attempt,
                    len(RETRY_DELAYS_SECONDS),
                    str(exc),
                )
                if attempt < len(RETRY_DELAYS_SECONDS):
                    await asyncio.sleep(delay)

        raise RuntimeError(f"Proveedor BanRep series no disponible: {last_error}")


class BanRepFilesProvider(BaseProvider):
    name = "BANREP_FILES"

    def __init__(self, service: "IndicadoresFinancierosService"):
        self.service = service

    async def fetch_records(
        self,
        indicator_key: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Dict[str, Any]]:
        indicator_key = indicator_key.lower()

        if indicator_key == "uvr":
            pdf_rows = await self._extract_uvr_from_pdf(fecha_inicio, fecha_fin)
            if pdf_rows:
                return pdf_rows

        if indicator_key == "ibr":
            ibr_rows = await self._extract_ibr_from_xlsx(fecha_inicio, fecha_fin)
            if ibr_rows:
                return ibr_rows

        urls = self._urls_for_indicator(indicator_key)
        for url in urls:
            workbook = await self._load_workbook(url)
            rows = self.extract_records_from_workbook(indicator_key, workbook)
            filtered = [r for r in rows if fecha_inicio <= r["fecha"] <= fecha_fin]
            if filtered:
                return filtered
        return []

    async def _extract_uvr_from_pdf(self, fecha_inicio: date, fecha_fin: date) -> List[Dict[str, Any]]:
        cache_key = "uvr_pdf_rows"
        cached = _cache.get(cache_key)
        if cached:
            return [r for r in cached if fecha_inicio <= r["fecha"] <= fecha_fin]

        lock = _get_singleflight_lock(cache_key)
        async with lock:
            cached = _cache.get(cache_key)
            if cached:
                return [r for r in cached if fecha_inicio <= r["fecha"] <= fecha_fin]

            content = await self._download_file(BANREP_FILES["UVR_PDF"])
            rows = await asyncio.to_thread(self._parse_uvr_pdf_rows_sync, content)

            if rows:
                rows.sort(key=lambda x: x["fecha"])
                dedup = {r["fecha"]: r for r in rows}
                normalized = sorted(dedup.values(), key=lambda x: x["fecha"])
                _cache.set(cache_key, normalized, TTL_HORAS["uvr"])
                return [r for r in normalized if fecha_inicio <= r["fecha"] <= fecha_fin]

        return []

    async def _extract_ibr_from_xlsx(self, fecha_inicio: date, fecha_fin: date) -> List[Dict[str, Any]]:
        cache_key = "ibr_xlsx_rows"
        cached = _cache.get(cache_key)
        if cached:
            return [r for r in cached if fecha_inicio <= r["fecha"] <= fecha_fin]

        lock = _get_singleflight_lock(cache_key)
        async with lock:
            cached = _cache.get(cache_key)
            if cached:
                return [r for r in cached if fecha_inicio <= r["fecha"] <= fecha_fin]

            content = await self._download_file(BANREP_FILES["IBR"])
            rows = await asyncio.to_thread(self._parse_ibr_xlsx_rows_sync, content)

            if rows:
                rows.sort(key=lambda x: x["fecha"])
                dedup = {r["fecha"]: r for r in rows}
                normalized = sorted(dedup.values(), key=lambda x: x["fecha"])
                _cache.set(cache_key, normalized, TTL_HORAS["ibr"])
                return [r for r in normalized if fecha_inicio <= r["fecha"] <= fecha_fin]

        return []

    def _urls_for_indicator(self, indicator_key: str) -> List[str]:
        indicator_key = indicator_key.lower()
        if indicator_key in {"uvr", "dtf", "ipc"}:
            return [BANREP_FILES["INDICADORES_DIARIOS"], BANREP_FILES["INDICADORES_3S"]]
        if indicator_key == "ibr":
            return [BANREP_FILES["IBR"], BANREP_FILES["INDICADORES_DIARIOS"]]
        return [BANREP_FILES["INDICADORES_DIARIOS"]]

    async def _load_workbook(self, url: str) -> Dict[str, pd.DataFrame]:
        cache_key = f"file_workbook:{url}"
        cached = _cache.get(cache_key)
        if cached:
            return cached

        lock = _get_singleflight_lock(cache_key)
        async with lock:
            cached = _cache.get(cache_key)
            if cached:
                return cached

            content = await self._download_file(url)
            engine = "openpyxl" if url.lower().endswith(".xlsx") else "xlrd"
            dataframes = await asyncio.to_thread(self._read_workbook_sync, content, engine)

            if not isinstance(dataframes, dict) or not dataframes:
                raise RuntimeError(f"No se pudo leer workbook oficial: {url}")

            _cache.set(cache_key, dataframes, TTL_HORAS["banrep_file"])
            return dataframes

    def _parse_uvr_pdf_rows_sync(self, content: bytes) -> List[Dict[str, Any]]:
        reader = PdfReader(BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)

        pattern = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})\s+([0-9]{2,4}\.[0-9]{4})")
        rows: List[Dict[str, Any]] = []
        for match in pattern.finditer(text):
            fecha_txt, valor_txt = match.groups()
            fecha = self.service.parse_date(fecha_txt)
            valor = self.service.parse_decimal(valor_txt)
            if fecha and valor is not None:
                rows.append({"fecha": fecha, "valor": valor})
        return rows

    def _parse_ibr_xlsx_rows_sync(self, content: bytes) -> List[Dict[str, Any]]:
        dataframe = pd.read_excel(BytesIO(content), engine="openpyxl", header=None)

        rows: List[Dict[str, Any]] = []
        current_date: Optional[date] = None
        for _, row in dataframe.iterrows():
            candidate_date = self.service.parse_date(row.iloc[0])
            if candidate_date:
                current_date = candidate_date

            if current_date is None:
                continue

            dias = self.service.parse_decimal(row.iloc[1])
            tasa_efectiva = self.service.parse_decimal(row.iloc[2])
            if dias is None or tasa_efectiva is None:
                continue

            if int(dias) in (1, 2, 3):
                rows.append({"fecha": current_date, "valor": tasa_efectiva})
        return rows

    def _read_workbook_sync(self, content: bytes, engine: str) -> Dict[str, pd.DataFrame]:
        return pd.read_excel(BytesIO(content), sheet_name=None, engine=engine)

    async def _download_file(self, url: str) -> bytes:
        client = await self.service._get_client()
        headers = {
            "Accept": "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
            "Referer": "https://www.banrep.gov.co/",
            "Origin": "https://www.banrep.gov.co",
        }

        last_error: Optional[Exception] = None
        for attempt, delay in enumerate(RETRY_DELAYS_SECONDS, start=1):
            try:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code} descargando archivo BanRep")

                content_type = (response.headers.get("content-type") or "").lower()
                body = response.content
                if not body:
                    raise RuntimeError("Archivo BanRep vacío")

                if "text/html" in content_type or body[:1] == b"<":
                    snippet = response.text[:200].replace("\n", " ")
                    raise RuntimeError(f"Archivo oficial inválido (HTML): {snippet}")

                return body
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "banrep_files_download_failed url=%s attempt=%s/%s error=%s",
                    url,
                    attempt,
                    len(RETRY_DELAYS_SECONDS),
                    str(exc),
                )
                if attempt < len(RETRY_DELAYS_SECONDS):
                    await asyncio.sleep(delay)

        raise RuntimeError(f"No se pudo descargar archivo oficial BanRep: {last_error}")

    def extract_records_from_workbook(self, indicator_key: str, workbook: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        for _, dataframe in workbook.items():
            if dataframe is None or dataframe.empty:
                continue
            extracted = self.extract_records_from_dataframe(indicator_key, dataframe)
            if not extracted:
                extracted = self.extract_records_from_matrix(indicator_key, dataframe)
            output.extend(extracted)

        output.sort(key=lambda x: x["fecha"])
        unique: Dict[date, Dict[str, Any]] = {item["fecha"]: item for item in output}
        return sorted(unique.values(), key=lambda x: x["fecha"])

    def extract_records_from_dataframe(self, indicator_key: str, dataframe: pd.DataFrame) -> List[Dict[str, Any]]:
        frame = dataframe.copy()
        frame.columns = [self.normalize_column_name(col) for col in frame.columns]

        date_col = self._detect_date_column(frame)
        value_cols = self._detect_value_columns(indicator_key, frame)
        if not date_col or not value_cols:
            return []

        records: List[Dict[str, Any]] = []
        for _, row in frame.iterrows():
            fecha = self.service.parse_date(row.get(date_col))
            if not fecha:
                continue

            valor = self.service.parse_decimal(row.get(value_cols[0]))
            if valor is None:
                continue

            records.append({"fecha": fecha, "valor": valor})

        return records

    def extract_records_from_matrix(self, indicator_key: str, dataframe: pd.DataFrame) -> List[Dict[str, Any]]:
        if indicator_key.lower() == "ipc":
            return self.extract_ipc_annual_records_from_matrix(dataframe)

        frame = dataframe.copy()
        keywords = {
            "uvr": ["uvr", "unidad de valor real"],
            "dtf": ["dtf"],
            "ibr": ["ibr", "overnight"],
            "ipc": ["ipc", "indice de precios", "inflacion"],
        }.get(indicator_key.lower(), [indicator_key.lower()])

        date_columns: List[Any] = []
        for col in frame.columns:
            if self.service.parse_date(col):
                date_columns.append(col)

        if len(date_columns) < 5:
            return []

        target_row_index: Optional[int] = None
        for idx, row in frame.iterrows():
            probe = " ".join(str(v).lower() for v in row.values[:6] if v is not None)
            if any(keyword in probe for keyword in keywords):
                target_row_index = idx
                break

        if target_row_index is None:
            return []

        target_row = frame.loc[target_row_index]
        records: List[Dict[str, Any]] = []
        for col in date_columns:
            fecha = self.service.parse_date(col)
            valor = self.service.parse_decimal(target_row.get(col))
            if fecha is None or valor is None:
                continue
            records.append({"fecha": fecha, "valor": valor})

        records.sort(key=lambda x: x["fecha"])
        return records

    def extract_ipc_annual_records_from_matrix(self, dataframe: pd.DataFrame) -> List[Dict[str, Any]]:
        frame = dataframe.copy()

        date_columns: List[Any] = []
        for col in frame.columns:
            if self.service.parse_date(col):
                date_columns.append(col)

        if len(date_columns) < 5:
            return []

        annual_row_index: Optional[int] = None
        for idx, row in frame.iterrows():
            row_text = " ".join(str(v).lower() for v in row.values[:10] if v is not None)
            if "inflacion total" in row_text and "variacion porcentual anual" in row_text:
                annual_row_index = idx
                break
            if "inflación total" in row_text and "variación porcentual anual" in row_text:
                annual_row_index = idx
                break

        if annual_row_index is None:
            return []

        annual_row = frame.loc[annual_row_index]
        records: List[Dict[str, Any]] = []
        for col in date_columns:
            fecha = self.service.parse_date(col)
            valor = self.service.parse_decimal(annual_row.get(col))
            if fecha is None or valor is None:
                continue
            records.append({"fecha": fecha, "valor": valor})

        records.sort(key=lambda x: x["fecha"])
        return records

    def normalize_column_name(self, name: Any) -> str:
        text = str(name).strip().lower()
        text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        text = text.replace("%", "pct").replace("_", " ")
        return " ".join(text.split())

    def _detect_date_column(self, frame: pd.DataFrame) -> Optional[str]:
        preferred = ["fecha", "date", "dia"]
        for col in frame.columns:
            if any(p in col for p in preferred):
                return col

        for col in frame.columns:
            series = frame[col].dropna().head(20)
            if series.empty:
                continue
            ok = 0
            for value in series:
                if self.service.parse_date(value):
                    ok += 1
            if ok >= max(3, int(len(series) * 0.5)):
                return col
        return None

    def _detect_value_columns(self, indicator_key: str, frame: pd.DataFrame) -> List[str]:
        mapping = {
            "uvr": ["uvr", "unidad de valor real"],
            "dtf": ["dtf", "dtf ea", "dtf e a", "deposito a termino fijo"],
            "ibr": ["ibr overnight", "overnight", "ibr"],
            "ipc": ["ipc", "indice de precios al consumidor", "inflacion", "variacion anual"],
        }
        patterns = mapping.get(indicator_key.lower(), [indicator_key.lower()])

        matches: List[str] = []
        for col in frame.columns:
            if any(pattern in col for pattern in patterns):
                matches.append(col)

        if matches:
            return matches

        for col in frame.columns:
            if "fecha" in col or "date" in col:
                continue
            series = frame[col].dropna().head(20)
            if series.empty:
                continue
            parsed = sum(1 for value in series if self.service.parse_decimal(value) is not None)
            if parsed >= max(3, int(len(series) * 0.6)):
                return [col]

        return []


class IndicadoresFinancierosService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._providers: List[BaseProvider] = [
            BanRepFilesProvider(self),
            BanRepSeriesProvider(self),
        ]

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": "EcoFinanzas/3.0 (Indicadores Oficiales)",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def parse_date(self, value: Any) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text:
            return None

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        if "T" in text:
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            except ValueError:
                return None

        return None

    def parse_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value

        text = str(value).strip()
        if not text:
            return None

        text = text.replace("$", "").replace("%", "").replace(" ", "")
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            parsed = Decimal(text)
            if not parsed.is_finite():
                return None
            return parsed
        except (InvalidOperation, ValueError):
            return None

    def extract_records(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            keys = ["data", "datos", "resultados", "results", "items", "value"]
            for key in keys:
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    return [item for item in candidate if isinstance(item, dict)]

            for candidate in payload.values():
                if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                    return candidate

        return []

    def normalize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        for item in records:
            fecha_raw = (
                item.get("fecha")
                or item.get("Fecha")
                or item.get("date")
                or item.get("Date")
                or item.get("fechaDato")
            )
            valor_raw = (
                item.get("valor")
                or item.get("Valor")
                or item.get("dato")
                or item.get("Dato")
                or item.get("value")
                or item.get("Value")
            )
            fecha = self.parse_date(fecha_raw)
            valor = self.parse_decimal(valor_raw)
            if fecha is None or valor is None:
                continue
            output.append({"fecha": fecha, "valor": valor})

        output.sort(key=lambda x: x["fecha"])
        unique = {row["fecha"]: row for row in output}
        return sorted(unique.values(), key=lambda x: x["fecha"])

    def log_provider_debug(
        self,
        provider: str,
        indicator_key: str,
        status: int,
        content_type: str,
        payload: Any,
        normalized: List[Dict[str, Any]],
    ) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return

        root_keys: List[str] = []
        if isinstance(payload, dict):
            root_keys = list(payload.keys())

        sample = normalized[0] if normalized else None
        logger.debug(
            "banrep_payload_audit provider=%s indicator=%s status=%s content_type=%s root_keys=%s records=%s normalized_sample=%s",
            provider,
            indicator_key,
            status,
            content_type,
            root_keys,
            len(normalized),
            sample,
        )

    async def _fetch_records_with_providers(
        self,
        indicator_key: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> tuple[List[Dict[str, Any]], FuenteDatos]:
        errors: List[str] = []

        for provider in self._providers:
            breaker_key = f"{provider.name}:{indicator_key}"
            if _breaker.is_open(breaker_key):
                errors.append(f"{provider.name}=circuit_open")
                continue

            try:
                records = await provider.fetch_records(indicator_key, fecha_inicio, fecha_fin)
                if records:
                    _breaker.record_success(breaker_key)
                    source = FuenteDatos.BANREP_FILES if provider.name == "BANREP_FILES" else FuenteDatos.BANREP_API
                    return records, source
                errors.append(f"{provider.name}=sin_datos")
                _breaker.record_failure(breaker_key)
            except Exception as exc:
                _breaker.record_failure(breaker_key)
                errors.append(f"{provider.name}={exc}")
                logger.warning(
                    "indicadores_provider_failed indicator=%s provider=%s error=%s",
                    indicator_key,
                    provider.name,
                    str(exc),
                )

        raise IndicadorNoDisponibleError(
            f"Proveedor oficial temporalmente no disponible ({indicator_key}). Detalles: {' | '.join(errors)}"
        )

    def _pick_on_or_before(self, records: List[Dict[str, Any]], target: date) -> Optional[Dict[str, Any]]:
        candidates = [r for r in records if r["fecha"] <= target]
        if not candidates:
            return None
        return candidates[-1]

    def _month_bounds(self, anio: int, mes: int) -> tuple[date, date]:
        start = date(anio, mes, 1)
        if mes == 12:
            end = date(anio + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(anio, mes + 1, 1) - timedelta(days=1)
        return start, end

    async def obtener_uvr_actual(self) -> ValorUVR:
        return await self.obtener_uvr(date.today())

    async def obtener_uvr(self, fecha: date) -> ValorUVR:
        cache_key = f"uvr:{fecha.isoformat()}"
        cached = _cache.get(cache_key)
        if cached:
            return ValorUVR(
                cached["fecha"],
                cached["valor"],
                FuenteDatos.CACHE,
                cached["fecha_actualizacion"],
                definicion="Unidad de Valor Real (UVR) en COP.",
            )

        try:
            records, fuente = await self._fetch_records_with_providers("uvr", fecha - timedelta(days=31), fecha)
            selected = self._pick_on_or_before(records, fecha)
            if not selected:
                raise IndicadorNoDisponibleError("No se encontró UVR oficial para la fecha solicitada")

            payload = {
                "fecha": selected["fecha"],
                "valor": selected["valor"].quantize(Decimal("0.0001")),
                "fecha_actualizacion": datetime.now(),
            }
            _cache.set(cache_key, payload, TTL_HORAS["uvr"])
            return ValorUVR(
                payload["fecha"],
                payload["valor"],
                fuente,
                payload["fecha_actualizacion"],
                definicion="Unidad de Valor Real (UVR) en COP.",
            )
        except IndicadorNoDisponibleError:
            stale = _cache.get_stale(cache_key)
            if stale:
                return ValorUVR(
                    stale["fecha"],
                    stale["valor"],
                    FuenteDatos.CACHE_STALE,
                    stale["fecha_actualizacion"],
                    definicion="Unidad de Valor Real (UVR) en COP.",
                    warning="Se devolvió valor UVR desde caché vencida por indisponibilidad temporal del proveedor oficial.",
                )
            raise

    async def obtener_historico_uvr(self, fecha_inicio: date, fecha_fin: date) -> List[ValorUVR]:
        cache_key = f"historico_uvr:{fecha_inicio.isoformat()}:{fecha_fin.isoformat()}"
        cached = _cache.get(cache_key)
        if cached:
            return [
                ValorUVR(item["fecha"], item["valor"], FuenteDatos.CACHE, item["fecha_actualizacion"])
                for item in cached
            ]

        try:
            records, fuente = await self._fetch_records_with_providers("uvr", fecha_inicio, fecha_fin)
            if not records:
                raise IndicadorNoDisponibleError("No se encontró histórico UVR oficial")

            payload = [
                {
                    "fecha": row["fecha"],
                    "valor": row["valor"].quantize(Decimal("0.0001")),
                    "fecha_actualizacion": datetime.now(),
                }
                for row in records
                if fecha_inicio <= row["fecha"] <= fecha_fin
            ]
            if not payload:
                raise IndicadorNoDisponibleError("No se encontró histórico UVR oficial en el rango solicitado")

            _cache.set(cache_key, payload, TTL_HORAS["historico_uvr"])
            return [
                ValorUVR(item["fecha"], item["valor"], fuente, item["fecha_actualizacion"])
                for item in payload
            ]
        except IndicadorNoDisponibleError:
            stale = _cache.get_stale(cache_key)
            if stale:
                return [
                    ValorUVR(item["fecha"], item["valor"], FuenteDatos.CACHE_STALE, item["fecha_actualizacion"])
                    for item in stale
                ]
            raise

    async def obtener_ipc_actual(self) -> ValorIPC:
        hoy = date.today()
        return await self.obtener_ipc(hoy.year, hoy.month)

    async def obtener_ipc(self, anio: int, mes: int) -> ValorIPC:
        cache_key = f"ipc:{anio}:{mes}"
        cached = _cache.get(cache_key)
        if cached:
            return ValorIPC(
                fecha=cached["fecha"],
                valor=cached["valor"],
                variacion_mensual=cached["variacion_mensual"],
                variacion_anual=cached["variacion_anual"],
                fuente=FuenteDatos.CACHE,
                fecha_actualizacion=cached["fecha_actualizacion"],
                tipo_serie=cached.get("tipo_serie"),
                definicion=cached.get("definicion"),
            )

        inicio_mes, fin_mes = self._month_bounds(anio, mes)
        try:
            records, fuente = await self._fetch_records_with_providers("ipc", inicio_mes - timedelta(days=400), fin_mes)
            ipc = self._build_ipc(records, anio, mes, fuente)
            payload = {
                "fecha": ipc.fecha,
                "valor": ipc.valor,
                "variacion_mensual": ipc.variacion_mensual,
                "variacion_anual": ipc.variacion_anual,
                "fecha_actualizacion": ipc.fecha_actualizacion,
                "tipo_serie": ipc.tipo_serie,
                "definicion": ipc.definicion,
            }
            _cache.set(cache_key, payload, TTL_HORAS["ipc"])
            return ipc
        except IndicadorNoDisponibleError:
            stale = _cache.get_stale(cache_key)
            if stale:
                return ValorIPC(
                    fecha=stale["fecha"],
                    valor=stale["valor"],
                    variacion_mensual=stale["variacion_mensual"],
                    variacion_anual=stale["variacion_anual"],
                    fuente=FuenteDatos.CACHE_STALE,
                    fecha_actualizacion=stale["fecha_actualizacion"],
                    tipo_serie=stale.get("tipo_serie"),
                    definicion=stale.get("definicion"),
                    warning="Se devolvió IPC desde caché vencida por indisponibilidad temporal del proveedor oficial.",
                )
            raise
        except Exception as exc:
            stale = _cache.get_stale(cache_key)
            if stale:
                return ValorIPC(
                    fecha=stale["fecha"],
                    valor=stale["valor"],
                    variacion_mensual=stale["variacion_mensual"],
                    variacion_anual=stale["variacion_anual"],
                    fuente=FuenteDatos.CACHE_STALE,
                    fecha_actualizacion=stale["fecha_actualizacion"],
                    tipo_serie=stale.get("tipo_serie"),
                    definicion=stale.get("definicion"),
                    warning="Se devolvió IPC desde caché vencida por indisponibilidad temporal del proveedor oficial.",
                )
            raise IndicadorNoDisponibleError(f"Proveedor oficial temporalmente no disponible (ipc): {exc}") from exc

    def _build_ipc(self, records: List[Dict[str, Any]], anio: int, mes: int, fuente: FuenteDatos) -> ValorIPC:
        _inicio, fin = self._month_bounds(anio, mes)
        records = [r for r in records if r["fecha"] <= fin]
        if not records:
            raise IndicadorNoDisponibleError("No hay datos oficiales de IPC para el periodo solicitado")

        actual = self._pick_on_or_before(records, fin)
        if not actual:
            raise IndicadorNoDisponibleError("No hay dato oficial IPC para el periodo solicitado")

        values = [r["valor"] for r in records]
        max_abs = max((abs(v) for v in values), default=Decimal("0"))
        is_variacion = max_abs <= Decimal("30")

        var_mensual: Optional[Decimal] = None
        if is_variacion:
            var_anual = actual["valor"]
            tipo_serie = "VARIACION_ANUAL_PORCENTUAL"
            definicion = "Inflación total, variación porcentual anual (Dic.2018=100)."
        else:
            anteriores = [r for r in records if r["fecha"] < actual["fecha"]]
            previo = anteriores[-1] if anteriores else None

            prev_year = [
                r
                for r in records
                if r["fecha"].year == actual["fecha"].year - 1 and r["fecha"].month == actual["fecha"].month
            ]
            previo_anual = prev_year[-1] if prev_year else None

            if previo and previo["valor"] != 0:
                var_mensual = ((actual["valor"] / previo["valor"]) - Decimal("1")) * Decimal("100")

            var_anual = Decimal("0")
            if previo_anual and previo_anual["valor"] != 0:
                var_anual = ((actual["valor"] / previo_anual["valor"]) - Decimal("1")) * Decimal("100")
            tipo_serie = "INDICE_IPC"
            definicion = "Índice de Precios al Consumidor (IPC)."

        return ValorIPC(
            fecha=actual["fecha"],
            valor=actual["valor"].quantize(Decimal("0.01")),
            variacion_mensual=var_mensual.quantize(Decimal("0.01")) if var_mensual is not None else None,
            variacion_anual=var_anual.quantize(Decimal("0.01")),
            fuente=fuente,
            fecha_actualizacion=datetime.now(),
            tipo_serie=tipo_serie,
            definicion=definicion,
        )

    async def obtener_dtf_actual(self) -> ValorDTF:
        return await self.obtener_dtf(date.today())

    async def obtener_dtf(self, fecha: date) -> ValorDTF:
        cache_key = f"dtf:{fecha.isoformat()}"
        cached = _cache.get(cache_key)
        if cached:
            return ValorDTF(
                cached["fecha"],
                cached["valor"],
                FuenteDatos.CACHE,
                cached["fecha_actualizacion"],
                definicion="DTF efectiva anual (% E.A.).",
            )

        try:
            records, fuente = await self._fetch_records_with_providers("dtf", fecha - timedelta(days=45), fecha)
            selected = self._pick_on_or_before(records, fecha)
            if not selected:
                raise IndicadorNoDisponibleError("No se encontró DTF oficial para la fecha solicitada")

            payload = {
                "fecha": selected["fecha"],
                "valor": selected["valor"].quantize(Decimal("0.01")),
                "fecha_actualizacion": datetime.now(),
            }
            _cache.set(cache_key, payload, TTL_HORAS["dtf"])
            return ValorDTF(
                payload["fecha"],
                payload["valor"],
                fuente,
                payload["fecha_actualizacion"],
                definicion="DTF efectiva anual (% E.A.).",
            )
        except IndicadorNoDisponibleError:
            stale = _cache.get_stale(cache_key)
            if stale:
                return ValorDTF(
                    stale["fecha"],
                    stale["valor"],
                    FuenteDatos.CACHE_STALE,
                    stale["fecha_actualizacion"],
                    definicion="DTF efectiva anual (% E.A.).",
                    warning="Se devolvió DTF desde caché vencida por indisponibilidad temporal del proveedor oficial.",
                )
            raise

    async def obtener_ibr_actual(self) -> ValorIBR:
        return await self.obtener_ibr(date.today())

    async def obtener_ibr(self, fecha: date) -> ValorIBR:
        cache_key = f"ibr:{fecha.isoformat()}"
        cached = _cache.get(cache_key)
        if cached:
            return ValorIBR(
                fecha=cached["fecha"],
                overnight=cached["overnight"],
                un_mes=cached.get("un_mes"),
                tres_meses=cached.get("tres_meses"),
                fuente=FuenteDatos.CACHE,
                fecha_actualizacion=cached["fecha_actualizacion"],
                definicion="IBR overnight efectivo anual (% E.A.).",
            )

        try:
            records, fuente = await self._fetch_records_with_providers("ibr", date(2000, 1, 1), fecha)
            selected = self._pick_on_or_before(records, fecha)
            if not selected:
                raise IndicadorNoDisponibleError("No se encontró IBR oficial para la fecha solicitada")

            payload = {
                "fecha": selected["fecha"],
                "overnight": selected["valor"].quantize(Decimal("0.01")),
                "un_mes": None,
                "tres_meses": None,
                "fecha_actualizacion": datetime.now(),
            }
            _cache.set(cache_key, payload, TTL_HORAS["ibr"])
            return ValorIBR(
                fecha=payload["fecha"],
                overnight=payload["overnight"],
                un_mes=payload["un_mes"],
                tres_meses=payload["tres_meses"],
                fuente=fuente,
                fecha_actualizacion=payload["fecha_actualizacion"],
                definicion="IBR overnight efectivo anual (% E.A.).",
            )
        except IndicadorNoDisponibleError:
            stale = _cache.get_stale(cache_key)
            if stale:
                return ValorIBR(
                    fecha=stale["fecha"],
                    overnight=stale["overnight"],
                    un_mes=stale.get("un_mes"),
                    tres_meses=stale.get("tres_meses"),
                    fuente=FuenteDatos.CACHE_STALE,
                    fecha_actualizacion=stale["fecha_actualizacion"],
                    definicion="IBR overnight efectivo anual (% E.A.).",
                    warning="Se devolvió IBR desde caché vencida por indisponibilidad temporal del proveedor oficial.",
                )
            raise

    async def obtener_indicadores_hoy(self) -> IndicadoresFinancieros:
        cache_key = f"consolidados:{date.today().isoformat()}"
        cached = _cache.get(cache_key)
        if cached:
            return IndicadoresFinancieros(
                fecha=cached["fecha"],
                uvr=cached["uvr"],
                dtf=cached["dtf"],
                ibr_overnight=cached["ibr_overnight"],
                ipc_anual=cached["ipc_anual"],
                fuente=FuenteDatos.CACHE,
                fecha_actualizacion=cached["fecha_actualizacion"],
            )

        lock = _get_singleflight_lock(cache_key)
        async with lock:
            cached = _cache.get(cache_key)
            if cached:
                return IndicadoresFinancieros(
                    fecha=cached["fecha"],
                    uvr=cached["uvr"],
                    dtf=cached["dtf"],
                    ibr_overnight=cached["ibr_overnight"],
                    ipc_anual=cached["ipc_anual"],
                    fuente=FuenteDatos.CACHE,
                    fecha_actualizacion=cached["fecha_actualizacion"],
                )

            uvr, dtf, ibr, ipc = await asyncio.gather(
                self.obtener_uvr_actual(),
                self.obtener_dtf_actual(),
                self.obtener_ibr_actual(),
                self.obtener_ipc_actual(),
            )

            payload = {
                "fecha": date.today(),
                "uvr": uvr.valor,
                "dtf": dtf.valor,
                "ibr_overnight": ibr.overnight,
                "ipc_anual": ipc.variacion_anual,
                "fecha_actualizacion": datetime.now(),
            }
            _cache.set(cache_key, payload, TTL_HORAS["consolidados"])

            return IndicadoresFinancieros(
                fecha=payload["fecha"],
                uvr=payload["uvr"],
                dtf=payload["dtf"],
                ibr_overnight=payload["ibr_overnight"],
                ipc_anual=payload["ipc_anual"],
                fuente=uvr.fuente,
                fecha_actualizacion=payload["fecha_actualizacion"],
                warning=uvr.warning or dtf.warning or ibr.warning or ipc.warning,
            )

    def convertir_uvr_a_pesos(self, monto_uvr: Decimal, valor_uvr: Decimal) -> Decimal:
        return (monto_uvr * valor_uvr).quantize(Decimal("0.01"))

    def convertir_pesos_a_uvr(self, monto_pesos: Decimal, valor_uvr: Decimal) -> Decimal:
        if valor_uvr <= 0:
            raise ValueError("El valor de la UVR debe ser positivo")
        return (monto_pesos / valor_uvr).quantize(Decimal("0.0001"))

    def proyectar_uvr(self, uvr_actual: Decimal, meses: int, inflacion_anual: Decimal = Decimal("0.06")) -> Decimal:
        inflacion_mensual = (Decimal("1") + inflacion_anual) ** (Decimal("1") / Decimal("12")) - Decimal("1")
        factor = (Decimal("1") + inflacion_mensual) ** Decimal(meses)
        return (uvr_actual * factor).quantize(Decimal("0.0001"))


def crear_servicio_indicadores() -> IndicadoresFinancierosService:
    return IndicadoresFinancierosService()


_servicio_global: Optional[IndicadoresFinancierosService] = None


def obtener_servicio_indicadores() -> IndicadoresFinancierosService:
    global _servicio_global
    if _servicio_global is None:
        _servicio_global = crear_servicio_indicadores()
    return _servicio_global
