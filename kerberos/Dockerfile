FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       krb5-kdc \
       krb5-admin-server \
       krb5-user \
       netcat-openbsd \
       procps \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY config/krb5.conf /etc/krb5.conf
COPY config/kdc.conf /etc/krb5kdc/kdc.conf
COPY config/kadm5.acl /etc/krb5kdc/kadm5.acl
COPY scripts/kdc-entrypoint.sh /usr/local/sbin/kdc-entrypoint.sh

RUN chmod 755 /usr/local/sbin/kdc-entrypoint.sh \
    && chmod 644 /etc/krb5.conf \
    && chmod 644 /etc/krb5kdc/kdc.conf \
    && chmod 600 /etc/krb5kdc/kadm5.acl

EXPOSE 88/tcp
EXPOSE 88/udp
EXPOSE 749/tcp

ENTRYPOINT ["/usr/local/sbin/kdc-entrypoint.sh"]
