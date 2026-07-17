#!/usr/bin/env bash
set -euo pipefail

cd "$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
)"

ERRORS=0

echo "=== AUDITORÍA DE SECRETOS ==="

if [[ -f .env ]]; then
  while IFS='=' read -r NAME VALUE; do
    NAME="${NAME//[[:space:]]/}"

    [[ -z "$NAME" ]] && continue
    [[ "$NAME" == \#* ]] && continue
    [[ -z "$VALUE" ]] && continue

    # Evitar falsos positivos con valores muy cortos.
    if [[ ${#VALUE} -lt 8 ]]; then
      continue
    fi

    MATCHES=$(
      grep -RIlF \
        --exclude='.env' \
        --exclude='.env.example' \
        --exclude-dir='.git' \
        --exclude-dir='prometheus-data' \
        --exclude-dir='grafana-data' \
        -- "$VALUE" . 2>/dev/null || true
    )

    if [[ -n "$MATCHES" ]]; then
      echo "PELIGRO: el valor de ${NAME} aparece en:"
      echo "$MATCHES"
      ERRORS=1
    fi
  done < .env
fi

if git rev-parse --is-inside-work-tree \
  >/dev/null 2>&1; then

  DANGEROUS=$(
    git ls-files |
    grep -Ei \
      '(^|/)\.env$|\.keytab$|\.key\.pem$|(^|/)stash$|/\.k5\.' \
      || true
  )

  if [[ -n "$DANGEROUS" ]]; then
    echo
    echo "PELIGRO: archivos sensibles preparados para Git:"
    echo "$DANGEROUS"
    ERRORS=1
  fi
fi

if [[ "$ERRORS" -ne 0 ]]; then
  echo
  echo "AUDITORÍA FALLIDA."
  exit 1
fi

echo "OK: no se detectaron secretos publicados."
