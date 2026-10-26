#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Docker Compose v2/v5 plugin or standalone binary.
compose() {
  if docker compose version >/dev/null 2>&1; then docker compose "$@";
  else docker-compose "$@"; fi
}
compose up -d --wait database
for year in "${@:-2024}"; do
  compose run --rm ingest ingest --year "$year"
  compose run --rm transform run --year "$year"
done
