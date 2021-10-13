# MariaDB Replication Configuration
[mariadb]
server_id={{ MYSQL_SERVER_ID | default(11) }}
log_bin=slave-bin
binlog-format=mixed
log_slave_updates=on
replicate_do_db=powerdns-auth