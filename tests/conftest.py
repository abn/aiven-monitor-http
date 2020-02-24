import asyncio
import logging

import pytest
from aioresponses import aioresponses
from cafeteria.asyncio.commons import handle_signals

from aiven.monitor.manager import CheckManager
from aiven.service.kafka import KafkaManager
from aiven.service.postgres import PostgresManager


@pytest.fixture(scope="session", autouse=True)
def set_log_level():
    logging.root.setLevel(logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop()
    handle_signals(loop)
    yield loop
    loop.stop()


@pytest.fixture(scope="session")
def kafka() -> KafkaManager:
    return KafkaManager()


@pytest.fixture(scope="session")
def postgres() -> PostgresManager:
    return PostgresManager()


@pytest.fixture(scope="session")
def manager(kafka, postgres) -> CheckManager:
    return CheckManager(kafka=kafka, postgres=postgres)


@pytest.fixture(autouse=True)
async def a_cleanup(postgres):
    await postgres.execute("DELETE FROM public.events WHERE TRUE")
    await postgres.execute("DELETE FROM public.checks WHERE TRUE")
    await postgres.execute("ALTER SEQUENCE checks_id_seq RESTART")


@pytest.fixture(autouse=True)
async def consumer(manager):
    task = asyncio.create_task(manager.consume_events())
    yield
    try:
        task.cancel()
    except asyncio.CancelledError:
        pass


@pytest.fixture
async def aioresponse():
    with aioresponses() as m:
        yield m
