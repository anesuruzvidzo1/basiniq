from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
import os

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
    f"/{os.getenv('POSTGRES_DB')}"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Well(Base):
    __tablename__ = "wells"

    id = Column(Integer, primary_key=True)
    license_number = Column(String, unique=True, index=True)
    well_name = Column(String)
    licensee = Column(String, index=True)
    formation = Column(String, index=True)
    field_name = Column(String)
    well_type = Column(String)
    well_status = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    license_date = Column(Date)
    substance = Column(String)
    region = Column(String, index=True)


class WellProduction(Base):
    __tablename__ = "well_production"

    id = Column(Integer, primary_key=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    year = Column(Integer)
    month = Column(Integer)
    oil_volume_m3 = Column(Float)
    gas_volume_e3m3 = Column(Float)
    water_volume_m3 = Column(Float)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_name = Column(String, index=True)
    document_type = Column(String)
    chunk_index = Column(Integer)
    page_number = Column(Integer, default=1)
    chunk_text = Column(Text)
    embedding = Column(Vector(384))


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    messages = Column(JSONB, nullable=False, default=list)


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER DEFAULT 1"
        ))
