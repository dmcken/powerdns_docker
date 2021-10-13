# syntax=docker/dockerfile:1

FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive


LABEL org.opencontainers.image.title="Zabbix proxy (SQLite3)" \
      org.opencontainers.image.authors="Alexey Pustovalov <alexey.pustovalov@zabbix.com>" \
      org.opencontainers.image.vendor="Zabbix LLC" \
      org.opencontainers.image.url="https://zabbix.com/" \
      org.opencontainers.image.description="Zabbix proxy with SQLite3 database support" \
      org.opencontainers.image.licenses="GPL v2.0" \
      org.opencontainers.image.documentation="https://www.zabbix.com/documentation/${MAJOR_VERSION}/manual/installation/containers" \
      org.opencontainers.image.version="${ZBX_VERSION}" \
      org.opencontainers.image.source="${ZBX_SOURCES}"

# STOPSIGNAL SIGTERM


RUN apt update

RUN apt install -y pdns-server pdns-backend-mysql python3-pip python3-setuptools iputils-ping && \
    rm -rf /var/lib/apt/lists/* && \
    apt clean

RUN pip3 install --no-cache-dir envtpl PyMySQL jinja2

RUN mkdir -p /etc/powerdns/pdns.d
RUN rm -f /etc/powerdns/pdns.d/bind.conf

# Work with pdns user - not root
# RUN chown pdns:pdns /var/run/pdns /var/lib/powerdns /etc/powerdns/pdns.d /etc/powerdns/templates.d
# USER pdns

# Startup script
COPY startup.py /etc/powerdns/
RUN chmod +x /etc/powerdns/startup.py

# Copy templates 
COPY pdns.conf.tpl /etc/powerdns/
COPY pdns.d/*.tpl /etc/powerdns/pdns.d/

# DNS ports
EXPOSE 53/tcp 53/udp
# Management port
EXPOSE 8081/tcp

CMD [ "/etc/powerdns/startup.py" ]