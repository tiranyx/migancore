#!/bin/bash
# Entrypoint for non-root ADO API container
# Copies keys from read-only mount to writable tmpfs, then runs as ado user

set -e

# Create writable key directory in tmpfs
mkdir -p /tmp/ado_keys

# Copy keys from read-only mount to writable location
if [ -f /etc/ado/keys/private.pem ]; then
    cp /etc/ado/keys/private.pem /tmp/ado_keys/
    cp /etc/ado/keys/public.pem /tmp/ado_keys/
    chown ado:ado /tmp/ado_keys/*.pem
    chmod 600 /tmp/ado_keys/private.pem
    chmod 644 /tmp/ado_keys/public.pem
fi

# Update environment to use writable key path
export JWT_PRIVATE_KEY_PATH=/tmp/ado_keys/private.pem
export JWT_PUBLIC_KEY_PATH=/tmp/ado_keys/public.pem

# ONAMIX is bind-mounted from /opt/sidix/tools/hyperx-browser in production.
# If the checkout exists but node_modules was not restored on the host, install
# dependencies once while the container still runs as root.
ONAMIX_DIR="${ONAMIX_DIR:-/app/hyperx}"
if [ -f "$ONAMIX_DIR/package.json" ] && [ ! -d "$ONAMIX_DIR/node_modules" ]; then
    echo "Bootstrapping ONAMIX dependencies in $ONAMIX_DIR"
    (npm --prefix "$ONAMIX_DIR" ci --omit=dev || npm --prefix "$ONAMIX_DIR" install --omit=dev) \
        || echo "WARNING: ONAMIX dependency bootstrap failed; API will start and ONAMIX will report unavailable"
fi

# Run as non-root user
exec gosu ado uvicorn main:app --host 0.0.0.0 --port 8000
