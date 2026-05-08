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

# Run as non-root user
exec gosu ado uvicorn main:app --host 0.0.0.0 --port 8000
