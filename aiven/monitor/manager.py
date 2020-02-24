import functools
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import ujson
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from aiven.monitor import Check, CheckResult
from aiven.service.kafka import KafkaManager
from aiven.service.postgres import PostgresManager

logger = logging.getLogger(__name__)


class CheckManager:
    def __init__(
        self,
        kafka: Optional[KafkaManager] = None,
        postgres: Optional[PostgresManager] = None,
        topic: str = "check.events",
    ):
        self.kafka = kafka or KafkaManager()
        self.postgres = postgres or PostgresManager()
        self.topic = topic

    async def publish_event(self, check_id: int, result: CheckResult) -> None:
        """
        Publish a check event/result.

        :param check_id: check id corresponding to config in database
        :param result: check result object to publish
        :return:
        """
        logger.info("Publishing event for check=%d", check_id)
        async with self.kafka.producer() as producer:  # type: AIOKafkaProducer
            value = {"check_id": check_id, "result": asdict(result)}
            await producer.send(
                topic=self.topic, value=ujson.dumps(value).encode("utf-8")
            )

    async def consume_events(self) -> None:
        """
        Consume events produced by any checks.
        """
        async with self.kafka.consumer(
            self.topic
        ) as consumer:  # type: AIOKafkaConsumer
            async for msg in consumer:
                value = ujson.loads(msg.value.decode("utf-8"))
                check_id = value.get("check_id")
                result = value.get("result")
                timestamp = result.pop(
                    "timestamp", datetime.now(tz=timezone.utc).timestamp()
                )
                logger.debug("Consumed message topic=%s value=%s", msg.topic, value)
                row = await self.postgres.execute(
                    """
                        INSERT INTO public.events (timestamp, check_id, result)
                            VALUES (to_timestamp($1), $2::INTEGER, $3::JSONB)
                        RETURNING id
                    """,
                    timestamp,
                    check_id,
                    result,
                )
                logger.info("Consumed event: %s", row[0]["id"])

    async def monitor(self, check_type: str, check: Check) -> None:
        """
        Method to persist a check configuration, retrieve id and start check loop.

        :param check_type: The check type to use when inserting to the configuration database
        :param check: A check instance implementing `aiven.monitor.Check.start` method.
        """
        row = await self.postgres.execute(
            """
                INSERT INTO public.checks (type, config)
                    VALUES ($1::TEXT, $2::JSONB)
                RETURNING id
            """,
            check_type,
            asdict(check),
        )
        check_id = row[0]["id"]

        # TODO: Fix typehints to support partial
        await check.start(callback=functools.partial(self.publish_event, check_id))
