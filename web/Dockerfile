FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apache2 \
        libapache2-mod-auth-gssapi \
        krb5-user \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
        /etc/apache2/tls \
        /bootstrap \
        /usr/lib/cgi-bin && \
    a2enmod ssl headers auth_gssapi cgid && \
    a2dissite 000-default

COPY apache-site.conf /etc/apache2/sites-available/miniidm.conf
COPY index.html /var/www/html/index.html
COPY whoami.cgi /usr/lib/cgi-bin/whoami.cgi
COPY entrypoint.sh /usr/local/sbin/web-entrypoint.sh

RUN chmod 755 \
        /usr/lib/cgi-bin/whoami.cgi \
        /usr/local/sbin/web-entrypoint.sh && \
    a2ensite miniidm

EXPOSE 443

ENTRYPOINT ["/usr/local/sbin/web-entrypoint.sh"]
