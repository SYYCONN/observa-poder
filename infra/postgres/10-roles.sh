#!/bin/sh
set -eu
# The image invokes this during initialization of a new Observa Poder volume.
export DB_MIGRATE_PASSWORD="$(cat /run/secrets/db_migrate)"
export DB_READ_PASSWORD="$(cat /run/secrets/db_read)"
export DB_COLLECT_PASSWORD="$(cat /run/secrets/db_collect)"
psql -v ON_ERROR_STOP=1 -v VERBOSITY=terse --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv migrate_password DB_MIGRATE_PASSWORD
\getenv read_password DB_READ_PASSWORD
\getenv collect_password DB_COLLECT_PASSWORD
CREATE ROLE observa_migrate LOGIN PASSWORD :'migrate_password';
CREATE ROLE observa_read LOGIN PASSWORD :'read_password';
CREATE ROLE observa_collect LOGIN PASSWORD :'collect_password';
REVOKE ALL ON DATABASE observa FROM PUBLIC;
ALTER DATABASE observa OWNER TO observa_migrate;
GRANT CONNECT ON DATABASE observa TO observa_read, observa_collect;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO observa_read, observa_collect;
SQL
unset DB_MIGRATE_PASSWORD DB_READ_PASSWORD DB_COLLECT_PASSWORD
