import asyncio
import re
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union, Coroutine, Callable

import aiohttp

from aiven.monitor import Check, CheckResult


@dataclass
class HTTPCheckResult(CheckResult):
    status: Optional[int] = field(default=None)
    connected: bool = field(default=False)
    content_verified: bool = field(default=False)
    elapsed: float = field(default=None)


async def on_request_start(_, trace_config_ctx, __):
    trace_config_ctx.start = asyncio.get_event_loop().time()


async def on_request_end(_, trace_config_ctx, __):
    check_result: HTTPCheckResult = trace_config_ctx.trace_request_ctx.get(
        "check_result"
    )
    if check_result:
        check_result.elapsed = asyncio.get_event_loop().time() - trace_config_ctx.start


# Trace configuration to make use of aiohttp's event tracing
trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_request_start)
trace_config.on_request_end.append(on_request_end)


@dataclass
class HTTPCheck(Check):
    url: str
    method: str = field(default="GET")
    regex: Optional[str] = field(default=None)
    timeout: Union[int, float] = field(default=2.0)
    headers: Dict[str, Any] = field(default_factory=dict)
    verify_ssl: bool = field(default=True)
    interval: Union[int, float] = field(default=30.0)

    def __post_init__(self):
        self.method = self.method.upper().strip()
        if self.method not in aiohttp.ClientRequest.ALL_METHODS:
            raise ValueError(f"Unsupported http method specified: {self.method}")

    async def start(self, callback: Callable[[CheckResult], Coroutine]) -> None:
        pattern = re.compile(self.regex) if self.regex else None
        connector = aiohttp.TCPConnector(
            limit=1,
            verify_ssl=self.verify_ssl,
            enable_cleanup_closed=True,
            force_close=True,
        )
        async with aiohttp.ClientSession(
            connector=connector,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            trace_configs=[trace_config],
        ) as session:
            while True:
                result = HTTPCheckResult()
                try:
                    async with session.request(
                        method=self.method,
                        url=self.url,
                        trace_request_ctx={"check_result": result},
                    ) as resp:
                        result.connected = True
                        result.status = resp.status
                        if pattern:
                            result.content_verified = bool(
                                pattern.search(await resp.text())
                            )
                except aiohttp.ServerDisconnectedError as e:
                    result.connected = True
                    result.error = e.message
                except (
                    aiohttp.ClientConnectionError,
                    aiohttp.ClientConnectorError,
                    socket.gaierror,
                ) as e:
                    result.error = str(e)
                except asyncio.CancelledError:
                    break
                await callback(result)
                await asyncio.sleep(self.interval)
