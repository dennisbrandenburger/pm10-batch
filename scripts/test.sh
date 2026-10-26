#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
compose() {
  if docker compose version >/dev/null 2>&1; then docker compose "$@";
  else docker-compose "$@"; fi
}
compose up -d --wait database
# A dedicated database makes the destructive rollback tests independent of results.
compose exec -T database psql -U pm10_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='pm10_test'" | grep -q 1 || compose exec -T database createdb -U pm10_admin -O pm10 pm10_test
compose run --rm -e PGDATABASE=pm10_test test "$@"
