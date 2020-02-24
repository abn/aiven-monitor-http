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
* Postgres and Kafka clients are configured using environment variables.

## Local Environment & Testing
In order to simplify testing and development a docker compose environment has been included. A 
working environment can be brought up using `docker-compose up` command.

Once this is up and running, you can ensure things are working by executing the test suite.

```sh
pytest tests/
```
