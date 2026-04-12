import sys
import os
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models.analisis import AnalisisHipotecario

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/credit_analysis_db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    ids = ["263aad26-40aa-4dda-bfb6-b0429dc07ab9"]
    
    async with async_session() as session:
        result = await session.execute(select(AnalisisHipotecario).where(AnalisisHipotecario.id == ids[0]))
        a = result.scalars().first()
        if a:
            print(f"Osnaider [{a.id}]")
            print(f"total_por_pagar: {a.total_por_pagar}")
        else:
            print("Not found")

if __name__ == '__main__':
    asyncio.run(main())
