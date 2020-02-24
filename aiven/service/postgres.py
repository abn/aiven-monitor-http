import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator, List

import asyncpg
import ujson


logger = logging.getLogger(__name__)


class PostgresManager:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or self.get_env_dsn()
        self.pool = None

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
        self.pool = None

    @staticmethod
    def get_env_dsn() -> str:
        # TODO: expose this via cli
        postgres_host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
        postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))
        postgres_db = os.environ.get("POSTGRES_DB", "aiven")
        postgres_user = os.environ.get("POSTGRES_USER", "aiven")
        postgres_password = os.environ.get("POSTGRES_PASSWORD", "aiven")
        return os.environ.get(
            "POSTGRES_URL",
            f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
        )

    async def init(self) -> None:
        if self.pool is None:

            async def init_connection(conn):
                await conn.set_type_codec(
                    "jsonb",
                    encoder=ujson.dumps,
                    decoder=ujson.loads,
                    schema="pg_catalog",
                )

            self.pool = await asyncpg.create_pool(
                dsn=self.dsn, min_size=3, max_size=5, init=init_connection
            )

    @asynccontextmanager
    async def connection(self, warning_msg: str = None) -> AsyncGenerator:
        await self.init()
        try:
            async with self.pool.acquire() as connection:
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
