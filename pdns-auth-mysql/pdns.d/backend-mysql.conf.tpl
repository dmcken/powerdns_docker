# MySQL Configuration
#
# Launch gmysql backend
launch+=gmysql

# gmysql parameters
gmysql-host={{ PDNS_DB_HOSTNAME | default("mysql") }}
gmysql-port={{ PDNS_DB_PORT | default(3306) }}
gmysql-dbname={{ PDNS_DB_DATABASE | default("powerdns-auth") }}
gmysql-user={{ PDNS_DB_USERNAME | default("powerdns-auth") }}
gmysql-password={{ PDNS_DB_PASSWORD | default("") }}
gmysql-dnssec={{ PDNS_DB_DNSSEC | default("yes") }}
