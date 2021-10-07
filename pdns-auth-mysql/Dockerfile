FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

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

COPY startup.py /etc/powerdns/
RUN chmod +x /etc/powerdns/startup.py
COPY pdns.conf.tpl /etc/powerdns/
COPY pdns.d/*.tpl /etc/powerdns/pdns.d/

# DNS ports
EXPOSE 53/tcp 53/udp
# Management port
EXPOSE 8081/tcp

#ENTRYPOINT ["/bin/bash"]
ENTRYPOINT [ "/etc/powerdns/startup.py" ]