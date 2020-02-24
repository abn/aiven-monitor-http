import asyncio
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from aiven.monitor.http.check import HTTPCheck


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Requires network connectivity")
async def test_checks_manager(manager, postgres):
    start_timestamp = datetime.now(tz=timezone.utc)
    check = HTTPCheck(url="https://aiven.io", interval=60)

    task = asyncio.create_task(manager.monitor("http", check))

    try:
        await asyncio.wait_for(task, timeout=0.5)
    except asyncio.TimeoutError:
        task.cancel()

    configs = await postgres.execute("SELECT id, type, config FROM public.checks")
    assert len(configs) == 1

    config = configs[0]
    assert config["id"] == 1
    assert config["type"] == "http"
    assert config["config"] == asdict(check)

    events = await postgres.execute(
        "SELECT timestamp, result FROM public.events WHERE check_id=$1", config["id"]
    )
    assert len(events) == 1

    event = events[0]
    assert start_timestamp < event["timestamp"] < datetime.now(tz=timezone.utc)

    result = event["result"]
    elapsed = result.pop("elapsed")
    test_time = datetime.now(tz=timezone.utc).timestamp() - start_timestamp.timestamp()
    assert elapsed < test_time

    assert result == {
        "connected": True,
        "content_verified": False,
        "error": None,
        "status": 200,
    }
