import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, InitVar
from ssl import SSLContext
from typing import List, Optional, Dict, Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context


@dataclass
class KafkaManager:
    # TODO: expose configuration parameters via cli
    bootstrap_servers: List[str] = field(
        default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
    )
    client_id: Optional[str] = field(default=os.environ.get("KAFKA_CLIENT_ID"))
    group_id: Optional[str] = field(default=os.environ.get("KAFKA_GROUP_ID"))
    security_protocol: str = field(
        default=os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    )
    ssl_cafile: InitVar[Optional[str]] = field(
        default=os.environ.get("KAFKA_SSL_CAFILE")
    )
    ssl_certfile: InitVar[Optional[str]] = field(
        default=os.environ.get("KAFKA_SSL_CERTFILE")
    )
    ssl_keyfile: InitVar[Optional[str]] = field(
        default=os.environ.get("KAFKA_SSL_KEYFILE")
    )
    ssl_password: InitVar[Optional[str]] = field(
        default=os.environ.get("KAFKA_SSL_PASSWORD")
    )
    ssl_context: SSLContext = field(default=None, init=False)
    sasl_mechanism: str = field(default=os.environ.get("KAFKA_SASL_MECHANISM", "PLAIN"))
    sasl_plain_password: str = field(
        default=os.environ.get("KAFKA_SASL_PLAIN_PASSWORD")
    )
    sasl_plain_username: str = field(
        default=os.environ.get("KAFKA_SASL_PLAIN_USERNAME")
    )
    sasl_kerberos_service_name: str = field(
        default=os.environ.get("KAFKA_SASL_KERBEROS_SERVICE_NAME", "kafka")
    )
    sasl_kerberos_domain_name: str = field(
        default=os.environ.get("KAFKA_SASL_KERBEROS_DOMAIN_NAME")
    )
    _client_kwargs: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(
        self,
        ssl_cafile: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_keyfile: Optional[str] = None,
        ssl_password: Optional[str] = None,
    ) -> None:
        if ssl_cafile or ssl_certfile or ssl_keyfile:
            self.ssl_context = create_ssl_context(
                cafile=ssl_cafile,
                certfile=ssl_certfile,
                keyfile=ssl_keyfile,
                password=ssl_password,
            )

        if isinstance(self.bootstrap_servers, str):
            self.bootstrap_servers = [
                s.strip() for s in self.bootstrap_servers.split(",")
            ]

        self._client_kwargs = dict(
            bootstrap_servers=self.bootstrap_servers,
            ssl_context=self.ssl_context,
            sasl_mechanism=self.sasl_mechanism,
            sasl_plain_password=self.sasl_plain_password,
            sasl_plain_username=self.sasl_plain_username,
            sasl_kerberos_service_name=self.sasl_kerberos_service_name,
            sasl_kerberos_domain_name=self.sasl_kerberos_domain_name,
        )
        if self.client_id:
            self._client_kwargs["client_id"] = self.client_id

    @property
    def client_configuration(self) -> Dict[str, Any]:
        return self._client_kwargs

    @asynccontextmanager
    async def producer(self) -> AIOKafkaProducer:
        try:
            producer = AIOKafkaProducer(
                loop=asyncio.get_event_loop(), **self._client_kwargs
            )
        except ValueError as e:
            raise RuntimeError(f"Invalid Kafka configuration: {e}")

        try:
            await producer.start()
            yield producer
        finally:
            await producer.stop()

    @asynccontextmanager
    async def consumer(self, *topics, **kwargs) -> AIOKafkaConsumer:
        try:
            kwargs = {**self.client_configuration, "group_id": self.group_id, **kwargs}
            consumer = AIOKafkaConsumer(
                *topics, loop=asyncio.get_event_loop(), **kwargs,
            )
        except ValueError as e:
            raise RuntimeError(f"Invalid Kafka configuration: {e}")

        try:
            await consumer.start()
            yield consumer
        finally:
            await consumer.stop()
