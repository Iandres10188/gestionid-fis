#!/usr/bin/env bash
set -Eeuo pipefail

DATABASE_FILE="/var/lib/krb5kdc/principal"

required_variables=(
    KRB_REALM
    KRB_MASTER_PASSWORD
    KRB_ADMIN_PASSWORD
    KRB_USER_PASSWORD
)

for variable in "${required_variables[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
        echo "ERROR: La variable ${variable} no está definida."
        exit 1
    fi
done

mkdir -p /var/lib/krb5kdc
chmod 700 /var/lib/krb5kdc

if [[ ! -f "${DATABASE_FILE}" ]]; then
    echo "=========================================="
    echo "Creando base Kerberos para ${KRB_REALM}"
    echo "=========================================="

    printf '%s\n%s\n' \
        "${KRB_MASTER_PASSWORD}" \
        "${KRB_MASTER_PASSWORD}" \
        | kdb5_util create \
            -s \
            -r "${KRB_REALM}"

    echo
    echo "=========================================="
    echo "Creando principal administrativo"
    echo "=========================================="

    kadmin.local \
        -r "${KRB_REALM}" \
        -q "addprinc -pw ${KRB_ADMIN_PASSWORD} admin/admin"

    echo
    echo "=========================================="
    echo "Creando principals de usuarios"
    echo "=========================================="

    for user in ionate jperez malvan dnoboa; do
        kadmin.local \
            -r "${KRB_REALM}" \
            -q "addprinc -pw ${KRB_USER_PASSWORD} ${user}"
    done

    echo
    echo "Base Kerberos inicializada correctamente."
else
    echo "La base Kerberos ya existe. Se conservarán sus datos."
fi

echo
echo "=========================================="
echo "Iniciando krb5kdc"
echo "=========================================="

krb5kdc -n &
KDC_PID=$!

echo
echo "=========================================="
echo "Iniciando kadmind"
echo "=========================================="

kadmind -nofork &
KADMIND_PID=$!

cleanup() {
    echo "Deteniendo servicios Kerberos..."

    kill "${KDC_PID}" "${KADMIND_PID}" 2>/dev/null || true

    wait "${KDC_PID}" 2>/dev/null || true
    wait "${KADMIND_PID}" 2>/dev/null || true
}

trap cleanup SIGTERM SIGINT

wait -n "${KDC_PID}" "${KADMIND_PID}"
STATUS=$?

cleanup
exit "${STATUS}"
