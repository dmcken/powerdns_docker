# MariaDB Replication Configuration
[mariadb]
server_id={{ MYSQL_SERVER_ID | default(1) }}
log_bin=master-bin
binlog-format=mixed
log_slave_updates=on
expire-logs-days=30