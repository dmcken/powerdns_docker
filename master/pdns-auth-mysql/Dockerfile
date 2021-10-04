FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update

RUN apt install -y pdns-server pdns-backend-mysql python3-pip python3-setuptools && \
    rm -rf /var/lib/apt/lists/* && \
    apt clean

RUN pip3 install --no-cache-dir envtpl PyMySQL jinja2

EXPOSE 53 53/udp

RUN mkdir -p /etc/powerdns/pdns.d /etc/powerdns/templates.d

# Work with pdns user - not root
#RUN adduser --system --disabled-password --disabled-login --no-create-home --group pdns --uid 953
#RUN chown pdns:pdns /var/run/pdns /var/lib/powerdns /etc/powerdns/pdns.d /etc/powerdns/templates.d
#USER pdns

#COPY pdns.conf.j2 /
#COPY docker-entrypoint.sh /

#ENTRYPOINT [ "setup-conf.py" ]

#CMD [ "/usr/sbin/pdns_server" ]

CMD ["/bin/bash"]