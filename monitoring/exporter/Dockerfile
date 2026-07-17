FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        ldap-utils \
        krb5-user \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
    /app \
    /keytabs \
    /etc/miniidm

COPY exporter.py /app/exporter.py

RUN chmod 755 /app/exporter.py

EXPOSE 9120

CMD ["python3", "/app/exporter.py"]
