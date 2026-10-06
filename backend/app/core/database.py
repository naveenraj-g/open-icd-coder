import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


def _install_query_listeners(engine) -> None:
    """Instrument every statement this engine executes. Emits:

      - `db.query` at DEBUG for every statement, when logging.sql_echo is on
      - `db.slow_query` at WARNING for anything over logging.slow_query_ms

    Listeners bind to the *sync* engine underneath the async one, which is
    where SQLAlchemy's cursor events actually fire.
    """
    slow_ms = settings.logging.slow_query_ms
    echo = settings.logging.sql_echo

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_query_start", []).append(time.perf_counter())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        stack = conn.info.get("_query_start")
        if not stack:
            return
        duration_ms = round((time.perf_counter() - stack.pop()) * 1000, 2)

        if duration_ms >= slow_ms:
            logger.warning(
                "Slow query",
                extra={
                    "event": "db.slow_query",
                    "duration_ms": duration_ms,
                    "threshold_ms": slow_ms,
                    # Statement only — never the bound parameters, which may
                    # carry clinical note text.
                    "statement": " ".join(statement.split())[:500],
                },
            )
        elif echo:
            logger.debug(
                "Query executed",
                extra={
                    "event": "db.query",
                    "duration_ms": duration_ms,
                    "statement": " ".join(statement.split())[:500],
                },
            )


class Database:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        _install_query_listeners(self.engine)

    async def disconnect(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self.session_maker()
        try:
            yield session
        except Exception:
            logger.exception("Session rollback because of exception")
            await session.rollback()
            raise
        finally:
            await session.close()
