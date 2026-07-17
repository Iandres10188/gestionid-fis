#!/usr/bin/env bash
set -euo pipefail

for file in \
    /bootstrap/web.keytab \
    /etc/apache2/tls/web.cert.pem \
    /etc/apache2/tls/web.key.pem
do
    if [[ ! -s "$file" ]]; then
        echo "ERROR: falta $file"
        exit 1
    fi
done

install \
    -o root \
    -g www-data \
    -m 640 \
    /bootstrap/web.keytab \
    /etc/apache2/web.keytab

echo "=== Principal HTTP ==="
klist -k /etc/apache2/web.keytab

echo "=== Validación de Apache ==="
apachectl configtest

echo "=== Apache HTTPS + Kerberos ==="
exec apachectl -D FOREGROUND
