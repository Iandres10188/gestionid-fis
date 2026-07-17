#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_DIR}"

DUMP_FILE="/var/lib/krb5kdc/replica-dump"

echo "Creando volcado de la base Kerberos..."
docker compose exec -T kdc1 \
    kdb5_util dump "${DUMP_FILE}"

echo "Enviando la base a KDC2..."
docker compose exec -T kdc1 \
    kprop \
        -P 754 \
        -f "${DUMP_FILE}" \
        -s /replica-keytabs/kdc1.keytab \
        kdc2.fis.epn.edu.ec

echo "Propagación terminada."
