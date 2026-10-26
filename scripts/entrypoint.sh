#!/bin/sh
set -eu
# A bind-mounted directory belongs to the host UID. Give that UID a name for
# Hadoop's Unix login without changing /etc/passwd or running as root.
if ! getent passwd "$(id -u)" >/dev/null; then
  for lib in /usr/lib/*/libnss_wrapper.so; do
    if [ -f "$lib" ]; then
      NSS_WRAPPER_PASSWD=$(mktemp)
      NSS_WRAPPER_GROUP=$(mktemp)
      printf 'worker:x:%s:%s:PM10 worker:/tmp:/bin/false\n' "$(id -u)" "$(id -g)" > "$NSS_WRAPPER_PASSWD"
      printf 'worker:x:%s:\n' "$(id -g)" > "$NSS_WRAPPER_GROUP"
      LD_PRELOAD=$lib
      export LD_PRELOAD NSS_WRAPPER_PASSWD NSS_WRAPPER_GROUP
      break
    fi
  done
fi
exec "$@"
