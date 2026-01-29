#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

groupadd -g "$PGID" -o diettube 2>/dev/null || true
useradd -u "$PUID" -g "$PGID" -o -m diettube 2>/dev/null || true

chown -R "$PUID:$PGID" /app
chown -R "$PUID:$PGID" "${DIETTUBE_CONFIG_DIR:-/config}" 2>/dev/null || true
chown -R "$PUID:$PGID" "${DIETTUBE_TEMP_DIR:-/temp}" 2>/dev/null || true

exec gosu "$PUID:$PGID" "$@"
