#!/usr/bin/env bash
set -euo pipefail

: "${KRB_REALM:?La variable KRB_REALM es obligatoria}"

KDC_DIR="/var/lib/krb5kdc"
STASH_FILE="${KDC_DIR}/.k5.${KRB_REALM}"

mkdir -p "${KDC_DIR}" /run/krb5kdc /etc/krb5kdc
chmod 700 "${KDC_DIR}"

if [[ ! -s /bootstrap/kdc2.keytab ]]; then
    echo "ERROR: no existe /bootstrap/kdc2.keytab"
    exit 1
fi

install -m 600 /bootstrap/kdc2.keytab /etc/krb5.keytab

if [[ ! -s "${STASH_FILE}" ]]; then
    if [[ ! -s /bootstrap/stash ]]; then
        echo "ERROR: no existe la copia del stash del KDC principal"
        exit 1
    fi

    install -m 600 /bootstrap/stash "${STASH_FILE}"
fi

terminate() {
    echo "Deteniendo KDC2..."
    kill "${KDC_PID:-}" "${KPROPD_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
}

trap terminate SIGTERM SIGINT EXIT

echo "Iniciando kpropd en el puerto 754..."

/usr/sbin/kpropd \
    -D \
    -P 754 \
    -r "${KRB_REALM}" \
    -a /etc/krb5kdc/kpropd.acl \
    -f "${KDC_DIR}/from_primary" &

KPROPD_PID=$!

echo "KDC2 está esperando la primera propagación..."

while [[ ! -s "${KDC_DIR}/principal" ]]; do
    if ! kill -0 "${KPROPD_PID}" 2>/dev/null; then
        echo "ERROR: kpropd terminó antes de recibir la base."
        exit 1
    fi

    sleep 2
done

echo "Base Kerberos recibida. Iniciando krb5kdc..."

/usr/sbin/krb5kdc -n &
KDC_PID=$!

wait -n "${KPROPD_PID}" "${KDC_PID}"
