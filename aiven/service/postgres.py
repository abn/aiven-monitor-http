import logging
import os
import ssl
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, List, Optional

import asyncpg
import ujson

logger = logging.getLogger(__name__)


@dataclass
class PostgresManager:
    url: str = field(
        default=os.environ.get(
            "POSTGRES_URL", "postgresql://aiven:aiven@127.0.0.1:5432/aiven"
        )
    )
    ssl_cafile: Optional[str] = field(default=os.environ.get("POSTGRES_CAFILE"))
    ssl_context: Optional[ssl.SSLContext] = field(default=None, init=False, repr=False)
    _pool: Optional[asyncpg.pool.Pool] = field(default=None, repr=False)

    def __post_init__(self):
        if self.ssl_cafile:
            self.ssl_context = ssl.create_default_context(
                purpose=ssl.Purpose.SERVER_AUTH, cafile=self.ssl_cafile
            )

    async def close(self):
        if self._pool is not None:
            await self._pool.close()
        self._pool = None

    async def init(self) -> None:
        if self._pool is None:

            async def init_connection(conn):
                await conn.set_type_codec(
                    "jsonb",
                    encoder=ujson.dumps,
                    decoder=ujson.loads,
                    schema="pg_catalog",
                )

            self._pool = await asyncpg.create_pool(
                dsn=self.url,
                ssl=self.ssl_context,
                min_size=1,
                max_size=3,
                init=init_connection,
            )

    @asynccontextmanager
    async def connection(self, warning_msg: str = None) -> AsyncGenerator:
        await self.init()
        try:
            async with self._pool.acquire() as connection:
                yield connection
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(e)
            if warning_msg:
                logger.warning(warning_msg)
        except Exception as e:
            logger.exception(e)

    async def execute(self, *args, **kwargs) -> List[asyncpg.Record]:
        """
        Helper method to execute an sql query and fetch results within a transaction.
        """
        async with self.connection() as connection:  # type: asyncpg.Connection
            async with connection.transaction():
                return await connection.fetch(*args, **kwargs)
