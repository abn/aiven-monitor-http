import asyncio
from dataclasses import asdict
from typing import Optional

import pytest

from aiven.monitor.http.check import HTTPCheck, HTTPCheckResult


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Requires network connectivity")
async def test_http_check_aiven_io():
    results = []
    check = HTTPCheck(url="https://aiven.io/", regex=r"Aiven \w+ Blog")
    task: Optional[asyncio.Task] = None

    async def callback(result):
        assert isinstance(result, HTTPCheckResult)
        results.append(asdict(result))
        if task:
            task.cancel()

    task = asyncio.create_task(check.start(callback=callback))
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(results) == 1

    success = results[0]
    isinstance(success.pop("timestamp"), float)
    assert isinstance(success.pop("elapsed"), float)
    assert success == {
        "connected": True,
        "content_verified": True,
        "error": None,
        "status": 200,
    }


@pytest.mark.asyncio
async def test_http_check_simple(aioresponse):
    results = []
    check = HTTPCheck(
        url="http://somewhere/foo/bar", regex=r" Worl[d]+", interval=0.025
    )
    task: Optional[asyncio.Task] = None

    async def callback(result):
        assert isinstance(result, HTTPCheckResult)
        results.append(asdict(result))
        if task and len(results) == 2:
            task.cancel()

    aioresponse.get(check.url, status=200, body="Hello World")

    task = asyncio.create_task(check.start(callback=callback))
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(results) == 2

    success = results[0]
    success.pop("timestamp")
    success.pop("elapsed")
    assert success == {
        "connected": True,
        "content_verified": True,
        "error": None,
        "status": 200,
    }

    error = results[1]
    error.pop("timestamp")
    error.pop("elapsed")
    assert error == {
        "connected": False,
        "content_verified": False,
        "error": "Connection refused: GET http://somewhere/foo/bar",
        "status": None,
    }
