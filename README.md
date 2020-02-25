# Aiven Monitor: HTTP Check Sample (Kafka + PostgreSQL)
This is a simple tool built to test [Aiven](https://aiven.io)'s hosted services. In 
particular, [Kafka](https://kafka.apache.org/) and [PostgreSQL](https://www.postgresql.org/).
This should work with any Kafka and Postgres deployments as well.

## Working Details
The tool, given one or more http urls, will perform "monitoring" checks against the site 
and optionally verify its contents if a regex is provided. Upon completion of a check,
the results along with timestamp and check duration (elapsed time) is dispatched to a 
Kafka topic.

This event is then picked up by a consumer that persists the event in a Postgres table.

## Assumptions & Simplifications
This is not to be considered a feature-rich tool. With that consideration, we have made
the following assumptions and simplifications.

* Postgres schema is already initalised and available (see [migration](database/000_initial_migration.up.sql)).
* Each instance of the check will create a new configuration entry in the `public.checks` table.
* Each event will create an entry in the `public.events` table referencing to the corresponding `check_id` from `public.checks`.
* Database optimisation (indices, partitioning etc.) are considered out-of-scope.
* Postgres and Kafka clients are configured using environment variables (see below).

## Local Environment & Testing
The project uses [Poetry](https://python-poetry.org/) for packaging and dependency management.
Setup virtual environment by simply executing `poetry install`.

### Docker Compose
In order to simplify testing and development a docker compose environment has been included. A 
working environment can be brought up using `docker-compose up` command.

### Test suite
Once the compose environment is up and running, you can ensure things are working by 
executing the test suite.

```sh
poetry run pytest tests/
```

## Setting up Aiven Services
You can either use the web console or the [Aiven Client](https://github.com/aiven/aiven-client) to 
provision required services. The CLI examples are shown below. See the client project's 
readme for information on login etc.

### Create required services
```sh
avn service create --service-type kafka --cloud google-europe-west1 --plan startup-2 monitor-kafka
avn service create --service-type pg --cloud google-europe-west1 --plan hobbyist monitor-pg
```

### Credentials
Once this is done you will need to retrieve the required credentials. You can do so as shown below.
```sh
mkdir -p .aiven/{kafka,pg}

pushd .aiven/kafka
avn service user-creds-download --username avnadmin monitor-kafka
popd

# note: this did not work as expected due to a client error, use web console instead
# this is also not strictly required
pushd .aiven/pg
avn service user-creds-download --username avnadmin monitor-pg
popd
```

Once you are done you wil have the following files on your system.
```
$ tree .aiven/
.aiven/
├── kafka
│   ├── ca.pem
│   ├── service.cert
│   └── service.key
└── pg
    └── ca.pem

2 directories, 4 files
```

### Checking service status
Using `avn service list`, you can check if the services are up and running.
```
SERVICE_NAME   SERVICE_TYPE  STATE    CLOUD_NAME           PLAN       GROUP_LIST  CREATE_TIME           UPDATE_TIME         
=============  ============  =======  ===================  =========  ==========  ====================  ====================
monitor-kafka  kafka         RUNNING  google-europe-west1  startup-2  default     2020-02-24T23:06:10Z  2020-02-25T00:20:39Z
monitor-pg     pg            RUNNING  google-europe-west1  hobbyist   default     2020-02-24T23:07:52Z  2020-02-25T00:09:40Z
```

### Creating kafka topic
We need to create the required topic prior to proceeding as auto create is not enabled.
```sh
avn service topic-create monitor-kafka check.events --partitions 1 --replication 3
```

### Initialise database schema
You can use the following command from the source root directory to initialise the 
database schema.

```sh
psql $(avn service get monitor-pg --json | jq -r .service_uri) -f database/000_initial_migration.up.sql
```


## Testing with Aiven Services
### Development environment
```sh
poetry install
poetry run aiven-monitor http --help
```

### Using docker container
You can use the latest version of the provided container as shown below. This will start 
checks against both https://aiven.io/ and https://google.com/ every default interval 
(30 seconds).

```sh
docker run --rm -it \
    -v `pwd`/.aiven/:/credentials/:Z \
    -e KAFKA_SECURITY_PROTOCOL=SSL \
    -e KAFKA_BOOTSTRAP_SERVERS=$(avn service get monitor-kafka --json | jq -r .service_uri) \
    -e KAFKA_SSL_CAFILE=/credentials/kafka/ca.pem \
    -e KAFKA_SSL_CERTFILE=/credentials/kafka/service.cert \
    -e KAFKA_SSL_KEYFILE=/credentials/kafka/service.key \
    -e POSTGRES_URL=$(avn service get monitor-pg --json | jq -r .service_uri) \
    quay.io/abn/aiven-monitor-http:latest \
    -m GET https://aiven.io/ https://google.com/
```

## Cleanup Aiven Services
Once you are done you can cleanup the created services using the following commands.
