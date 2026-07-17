#!/usr/bin/env python3

import os
import re
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LDAP_BASE_DN = os.environ.get(
    "LDAP_BASE_DN",
    "dc=fis,dc=epn,dc=ec",
)

KRB_REALM = os.environ.get(
    "KRB_REALM",
    "FIS.EPN.EC",
)

KEYTAB = "/keytabs/monitor.keytab"
CA_FILE = "/etc/miniidm/ca.cert.pem"

LDAP_SERVERS = {
    "ldap1": "ldap1.fis.epn.edu.ec",
    "ldap2": "ldap2.fis.epn.edu.ec",
}

KDC_SERVERS = {
    "kdc1": "kdc1.fis.epn.edu.ec",
    "kdc2": "kdc2.fis.epn.edu.ec",
}

ldap_query_counters = {
    name: 0 for name in LDAP_SERVERS
}

kerberos_check_counters = {
    name: 0 for name in KDC_SERVERS
}


def run(command, timeout=6, environment=None):
    env = os.environ.copy()

    if environment:
        env.update(environment)

    started = time.monotonic()

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )

        duration = time.monotonic() - started

        return (
            process.returncode,
            process.stdout,
            process.stderr,
            duration,
        )

    except subprocess.TimeoutExpired:
        duration = time.monotonic() - started
        return 124, "", "timeout", duration


def parse_context_csn(output):
    matches = re.findall(
        r"contextCSN:\s*(\d{14})(?:\.(\d+))?Z",
        output,
    )

    timestamps = []

    for base_time, fraction in matches:
        parsed = datetime.strptime(
            base_time,
            "%Y%m%d%H%M%S",
        ).replace(tzinfo=timezone.utc)

        value = parsed.timestamp()

        if fraction:
            value += float(f"0.{fraction}")

        timestamps.append(value)

    return max(timestamps) if timestamps else 0.0


def ldap_probe(label, hostname):
    environment = {
        "LDAPTLS_CACERT": CA_FILE,
    }

    context_command = [
        "ldapsearch",
        "-x",
        "-LLL",
        "-o",
        "nettimeout=3",
        "-H",
        f"ldaps://{hostname}",
        "-b",
        LDAP_BASE_DN,
        "-s",
        "base",
        "contextCSN",
    ]

    ldap_query_counters[label] += 1

    code, output, _, duration = run(
        context_command,
        environment=environment,
    )

    if code != 0:
        return {
            "up": 0,
            "duration": duration,
            "context_timestamp": 0.0,
            "entries": 0,
        }

    count_command = [
        "ldapsearch",
        "-x",
        "-LLL",
        "-o",
        "nettimeout=3",
        "-H",
        f"ldaps://{hostname}",
        "-b",
        LDAP_BASE_DN,
        "(objectClass=*)",
        "dn",
    ]

    ldap_query_counters[label] += 1

    count_code, count_output, _, count_duration = run(
        count_command,
        environment=environment,
    )

    entries = 0

    if count_code == 0:
        entries = sum(
            1
            for line in count_output.splitlines()
            if line.startswith("dn:")
        )

    return {
        "up": 1,
        "duration": duration + count_duration,
        "context_timestamp": parse_context_csn(output),
        "entries": entries,
    }


def kerberos_probe(label, hostname):
    kerberos_check_counters[label] += 1

    config = f"""
[libdefaults]
    default_realm = {KRB_REALM}
    dns_lookup_kdc = false
    dns_lookup_realm = false
    rdns = false
    udp_preference_limit = 1

[realms]
    {KRB_REALM} = {{
        kdc = {hostname}
    }}
"""

    config_path = Path(
        f"/tmp/krb5-monitor-{label}.conf"
    )

    cache_path = Path(
        f"/tmp/krb5cc-monitor-{label}"
    )

    config_path.write_text(config)

    environment = {
        "KRB5_CONFIG": str(config_path),
        "KRB5CCNAME": f"FILE:{cache_path}",
    }

    command = [
        "kinit",
        "-k",
        "-t",
        KEYTAB,
        f"monitor@{KRB_REALM}",
    ]

    code, _, _, duration = run(
        command,
        timeout=6,
        environment=environment,
    )

    try:
        cache_path.unlink(missing_ok=True)
    except OSError:
        pass

    return {
        "up": 1 if code == 0 else 0,
        "duration": duration,
    }


def generate_metrics():
    ldap_results = {
        label: ldap_probe(label, hostname)
        for label, hostname in LDAP_SERVERS.items()
    }

    kerberos_results = {
        label: kerberos_probe(label, hostname)
        for label, hostname in KDC_SERVERS.items()
    }

    ldap1_timestamp = ldap_results[
        "ldap1"
    ]["context_timestamp"]

    ldap2_timestamp = ldap_results[
        "ldap2"
    ]["context_timestamp"]

    if ldap1_timestamp and ldap2_timestamp:
        replication_lag = abs(
            ldap1_timestamp - ldap2_timestamp
        )
    else:
        replication_lag = -1

    lines = [
        "# HELP miniidm_ldap_up LDAP responde correctamente.",
        "# TYPE miniidm_ldap_up gauge",
    ]

    for label, result in ldap_results.items():
        lines.append(
            f'miniidm_ldap_up{{server="{label}"}} '
            f'{result["up"]}'
        )

    lines.extend([
        "# HELP miniidm_ldap_query_duration_seconds "
        "Duración de consultas LDAP sintéticas.",
        "# TYPE miniidm_ldap_query_duration_seconds gauge",
    ])

    for label, result in ldap_results.items():
        lines.append(
            f'miniidm_ldap_query_duration_seconds'
            f'{{server="{label}"}} '
            f'{result["duration"]:.6f}'
        )

    lines.extend([
        "# HELP miniidm_ldap_entries "
        "Número de entradas visibles en LDAP.",
        "# TYPE miniidm_ldap_entries gauge",
    ])

    for label, result in ldap_results.items():
        lines.append(
            f'miniidm_ldap_entries'
            f'{{server="{label}"}} '
            f'{result["entries"]}'
        )

    lines.extend([
        "# HELP miniidm_ldap_contextcsn_timestamp_seconds "
        "Marca de tiempo del contextCSN.",
        "# TYPE miniidm_ldap_contextcsn_timestamp_seconds gauge",
    ])

    for label, result in ldap_results.items():
        lines.append(
            f'miniidm_ldap_contextcsn_timestamp_seconds'
            f'{{server="{label}"}} '
            f'{result["context_timestamp"]:.6f}'
        )

    lines.extend([
        "# HELP miniidm_ldap_replication_lag_seconds "
        "Diferencia entre los contextCSN.",
        "# TYPE miniidm_ldap_replication_lag_seconds gauge",
        f"miniidm_ldap_replication_lag_seconds "
        f"{replication_lag:.6f}",
        "# HELP miniidm_ldap_queries_total "
        "Consultas sintéticas realizadas por el monitor.",
        "# TYPE miniidm_ldap_queries_total counter",
    ])

    for label, value in ldap_query_counters.items():
        lines.append(
            f'miniidm_ldap_queries_total'
            f'{{server="{label}"}} {value}'
        )

    lines.extend([
        "# HELP miniidm_kerberos_up "
        "Autenticación real mediante keytab.",
        "# TYPE miniidm_kerberos_up gauge",
    ])

    for label, result in kerberos_results.items():
        lines.append(
            f'miniidm_kerberos_up'
            f'{{server="{label}"}} '
            f'{result["up"]}'
        )

    lines.extend([
        "# HELP miniidm_kerberos_auth_duration_seconds "
        "Duración de kinit contra cada KDC.",
        "# TYPE miniidm_kerberos_auth_duration_seconds gauge",
    ])

    for label, result in kerberos_results.items():
        lines.append(
            f'miniidm_kerberos_auth_duration_seconds'
            f'{{server="{label}"}} '
            f'{result["duration"]:.6f}'
        )

    lines.extend([
        "# HELP miniidm_kerberos_auth_checks_total "
        "Autenticaciones sintéticas realizadas.",
        "# TYPE miniidm_kerberos_auth_checks_total counter",
    ])

    for label, value in kerberos_check_counters.items():
        lines.append(
            f'miniidm_kerberos_auth_checks_total'
            f'{{server="{label}"}} {value}'
        )

    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            payload = b"OK\n"
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain",
            )
            self.send_header(
                "Content-Length",
                str(len(payload)),
            )
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        try:
            payload = generate_metrics().encode()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; version=0.0.4",
            )
            self.send_header(
                "Content-Length",
                str(len(payload)),
            )
            self.end_headers()
            self.wfile.write(payload)

        except Exception as error:
            payload = (
                f"Error generating metrics: {error}\n"
            ).encode()

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "text/plain",
            )
            self.end_headers()
            self.wfile.write(payload)

    def log_message(self, format_string, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("0.0.0.0", 9120),
        Handler,
    )

    print(
        "MiniIdM exporter escuchando en 0.0.0.0:9120",
        flush=True,
    )

    server.serve_forever()
