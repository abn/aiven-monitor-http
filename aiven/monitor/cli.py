import asyncio
import logging
from typing import List

import aiohttp
import click
from cafeteria.asyncio.commons import handle_signals

from aiven.monitor import Check
from aiven.monitor.http.check import HTTPCheck
from aiven.monitor.manager import CheckManager


logging.basicConfig(format="%(levelname)s %(name)s - %(message)s")
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def monitor():
    pass


@monitor.command()
@click.option(
    "-m",
    "--method",
    default="GET",
    type=click.Choice(aiohttp.ClientRequest.ALL_METHODS),
    help="HTTP method to use for check",
)
@click.option(
    "-r",
    "--regex",
    required=False,
    type=str,
    help="Python regex to use to verify content",
)
@click.option("-t", "--timeout", default=2.0, type=float, help="Check Timeout")
@click.option("-i", "--interval", default=30.0, type=float, help="Check Interval")
@click.option(
    "-H",
    "--header",
    multiple=True,
    type=str,
    help="Header to use for http requests made (eg: 'Authorization: Bearer token')",
)
@click.option(
    "--verify-ssl/--no-verify-ssl",
    default=True,
    help="Verify TLS certificate if https is used",
)
@click.option(
    "--debug/--no-debug", default=False, help="Enable or disable debugging",
)
@click.argument("url", required=True, nargs=-1)
def http(method, regex, timeout, interval, header, verify_ssl, debug, url):
    if debug:
        logging.root.setLevel(logging.DEBUG)

    headers = dict()
    for h in header:
        try:
            k, v = h.split(":")
        except ValueError:
            raise click.BadParameter("Headers should be of the form 'Key: Value'")
        headers[k.strip()] = v.strip()

    loop = asyncio.get_event_loop()
    handle_signals(loop)

    checks = [
        HTTPCheck(
            url=u,
            method=method,
            regex=regex,
            timeout=timeout,
            headers=headers,
            verify_ssl=verify_ssl,
            interval=interval,
        )
        for u in url
    ]

    loop.run_until_complete(run("http", checks))


async def run(check_type: str, checks: List[Check]):
    logger.info("Initialising checks manager")
    manager = CheckManager()
    # TODO: allow consumer and producer to be started independently
    consumer_task = asyncio.create_task(manager.consume_events())
    check_tasks = [manager.monitor(check_type, check) for check in checks]
    try:
        await asyncio.gather(*check_tasks, consumer_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    monitor()
