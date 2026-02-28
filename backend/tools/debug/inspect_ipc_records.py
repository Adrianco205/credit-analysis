import asyncio
from datetime import date

from app.services.indicadores_service import IndicadoresFinancierosService


async def main() -> None:
    service = IndicadoresFinancierosService()
    try:
        records, source = await service._fetch_records_with_providers(
            "ipc", date(2024, 1, 1), date(2026, 2, 15)
        )
        print("source", source, "count", len(records))
        print("first5", records[:5])
        print("last10", records[-10:])

        by_month = {}
        for record in records:
            by_month[(record["fecha"].year, record["fecha"].month)] = record

        for key in [(2024, 11), (2025, 1), (2025, 11), (2025, 12), (2026, 1)]:
            print(key, by_month.get(key))

        ipc_2025_11 = await service.obtener_ipc(2025, 11)
        print(
            "ipc_2025_11",
            {
                "fecha": ipc_2025_11.fecha,
                "valor": ipc_2025_11.valor,
                "var_mensual": ipc_2025_11.variacion_mensual,
                "var_anual": ipc_2025_11.variacion_anual,
                "fuente": ipc_2025_11.fuente,
            },
        )
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
