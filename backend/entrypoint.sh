#!/bin/bash
set -euo pipefail

# RUN_MIGRATIONS gates whether this container runs `alembic upgrade
# head` before starting its main process. Only one service in
# docker-compose (the `backend` API) should have this set to "true" -
# if multiple containers (e.g. backend + celery_worker) raced to run
# migrations concurrently against SQL Server, they could conflict on
# DDL locks / the alembic_version table.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "[entrypoint] Running database migrations (alembic upgrade head)..."

    # mssql/mssql_init pass their healthcheck/completion before this
    # container starts (see docker-compose.yml depends_on conditions),
    # but a few retries add resilience against transient connection
    # blips on first boot.
    attempt=1
    max_attempts=5
    until alembic upgrade head; do
        if [ "$attempt" -ge "$max_attempts" ]; then
            echo "[entrypoint] Migrations failed after ${max_attempts} attempts. Exiting."
            exit 1
        fi
        echo "[entrypoint] Migration attempt ${attempt} failed, retrying in 5s..."
        attempt=$((attempt + 1))
        sleep 5
    done

    echo "[entrypoint] Migrations applied successfully."
else
    echo "[entrypoint] RUN_MIGRATIONS is not 'true' - skipping migrations for this container."
fi

echo "[entrypoint] Starting: $*"
exec "$@"
