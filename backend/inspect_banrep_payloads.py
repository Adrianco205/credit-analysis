import asyncio
import json

from app.services.indicadores_service import (
    BANREP_STATS_URL,
    SERIES_BANREP,
    IndicadoresFinancierosService,
)


async def main() -> None:
    service = IndicadoresFinancierosService()
    client = await service._get_client()
    try:
        for key in ["UVR", "DTF", "IBR", "IPC"]:
            serie = SERIES_BANREP[key]
            url = f"{BANREP_STATS_URL}/{serie}"
            params = {
                "fechaInicio": "01/01/2025",
                "fechaFin": "15/02/2026",
                "formato": "json",
            }
            headers = {
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://suameca.banrep.gov.co/estadisticas-economicas/",
                "Origin": "https://suameca.banrep.gov.co",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            }

            response = await client.get(url, params=params, headers=headers)
            print(f"=== {key} ===")
            print(f"status={response.status_code} content_type={response.headers.get('content-type')}")

            body = response.text.strip()
            if body.startswith("<"):
                print("html_body_prefix=", body[:180].replace("\n", " "))
                print()
                continue

            payload = json.loads(body)
            print("root_keys=", list(payload.keys())[:8])
            records = service.extract_records(payload)
            print("records=", len(records))
            if records:
                print("raw_sample=", records[0])
                normalized = service.normalize_records(records[:50])
                print("normalized_count_sample_window=", len(normalized))
                if normalized:
                    print("normalized_sample=", normalized[0])
            print()
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
