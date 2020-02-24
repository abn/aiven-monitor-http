import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Coroutine, Callable


@dataclass
class CheckResult:
    timestamp: float = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).timestamp()
    )
    error: Optional[str] = field(default=None)


@dataclass
class Check:
    @abc.abstractmethod
    async def start(self, callback: Callable[[CheckResult], Coroutine]) -> None:
        """
        Start check and trigger a callback when a check result is available.

        :param callback: Callback to trigger when a result is available
        :return:
        """
        raise NotImplementedError
