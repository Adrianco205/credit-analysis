import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.ext.declarative import declarative_base

import sys
import os
sys.path.append('backend')
from app.models.analisis import AnalisisHipotecario

async def main():
    uri = "postgresql+asyncpg://postgres:postgres@localhost:5432/credit_analysis_db"
    engine = create_async_engine(uri)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(AnalisisHipotecario).where(AnalisisHipotecario.id == "263aad26-40aa-4dda-bfb6-b0429dc07ab9"))
        a = result.scalars().first()
        if a:
            print(f"Osnaider [{a.id}]")
            for k, v in a.__dict__.items():
                if 'total' in k or 'pagar' in k or 'proyect' in k:
                    print(f"  {k}: {v}")

if __name__ == '__main__':
    asyncio.run(main())
