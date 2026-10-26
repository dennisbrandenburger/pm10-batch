#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_password="$(cat /run/secrets/db_password)" <<'SQL'
CREATE ROLE pm10 LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
SELECT format('ALTER ROLE pm10 PASSWORD %L', :'app_password') \gexec
GRANT CONNECT, TEMPORARY ON DATABASE pm10 TO pm10;
GRANT USAGE, CREATE ON SCHEMA public TO pm10;
SQL
