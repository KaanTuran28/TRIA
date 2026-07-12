import os
import socket

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/tria_db")


def _normalize_database_url(url: str) -> str:
    if "@database:" not in url:
        return url
    # Docker icinde host "database" dogru; local debug calismasinda DNS cozumlenmezse localhost'a don.
    try:
        socket.getaddrinfo("database", 5432)
        return url
    except socket.gaierror:
        fixed = url.replace("@database:", "@localhost:")
        return fixed


DATABASE_URL = _normalize_database_url(DATABASE_URL)

# echo=False yaparak log kirliliğini kapattık
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session