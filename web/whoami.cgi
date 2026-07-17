#!/usr/bin/env bash

printf 'Content-Type: text/html\r\n\r\n'

cat <<HTML
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Acceso Kerberos</title>
</head>
<body>
    <h1>Autenticación Kerberos exitosa</h1>

    <p>
        <strong>Usuario:</strong>
        ${REMOTE_USER:-desconocido}
    </p>

    <p>
        <strong>Servidor:</strong>
        ${SERVER_NAME:-desconocido}
    </p>

    <p>
        <strong>Seguridad:</strong>
        HTTPS + Kerberos + GSSAPI
    </p>
</body>
</html>
HTML
