#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p secrets runtime
chmod 700 secrets
if [ ! -s secrets/db_password.txt ]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/db_password.txt
fi
if [ ! -s secrets/admin_password.txt ]; then
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/admin_password.txt
fi
# Compose bind-mounts the files with their host ownership. PostgreSQL reads
# them as a different UID. The enclosing host directory stays owner-only.
chmod 444 secrets/db_password.txt secrets/admin_password.txt
if [ ! -e .env ]; then
  printf 'LOCAL_UID=%s\nLOCAL_GID=%s\n' "$(id -u)" "$(id -g)" > .env
fi
printf '%s\n' 'Lokale Verzeichnisse und Datenbankpasswort vorbereitet.'
