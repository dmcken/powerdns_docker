#!/usr/bin/env -S python3

import os
import jinja2
import logging
import subprocess
import sys

LOGGING_FORMAT = u'%(asctime)s - %(name)s - %(thread)d - %(levelname)s - %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)

def setup_mysql(settings):
    import pymysql.cursors

    db_host = '192.168.1.160' # os.getenv('PDNS_DB_HOSTNAME', 'mysql'), 
    db_user = os.getenv('PDNS_DB_USERNAME', 'pdns-auth')
    db_password = os.getenv('PDNS_DB_PASSWORD', '')
    db_database = os.getenv('PDNS_DB_DATABASE', 'powerdns-auth')

    # Attempt to connect using normal credentials
    try:
        connection = pymysql.connect(
            host = db_host,
            user = db_user,
            password = db_password,
            database = db_database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        logging.info("Connected with normal user")
    except pymysql.err.OperationalError:
        # The user doesn't exist / work, connect with root creds and create user (and likely db as well)
        logging.error("Failed to connect to normal user")
        connection = pymysql.connect(
            host = db_host,
            user = 'root',
            password = os.getenv('MYSQL_ROOT_PASSWORD', ''),
            database = '',
            cursorclass=pymysql.cursors.DictCursor,
        )
        with connection:
            with connection.cursor() as cursor:

                # Would love to use prepared statements with auto-escaping but
                # for certain parts I need it to just put what is sent in.
                sql = "CREATE DATABASE IF NOT EXISTS `{0}`;".format(db_database)
                logging.debug("Create Database SQL: {0}".format(sql))
                cursor.execute(sql)

                sql = "GRANT ALL ON `{0}`.* to `{1}`@'%' identified by '{2}';".\
                    format(db_user, db_database, db_password)
                logging.debug("GRANT ALL SQL: {0}".format(sql))
                cursor.execute(sql)

                sql = "FLUSH PRIVILEGES;"
                cursor.execute(sql)

            connection.commit()

        # Reconnect as the normal user
        connection = pymysql.connect(
            host = db_host,
            user = db_user,
            password = db_password,
            database = db_database,
            cursorclass=pymysql.cursors.DictCursor,
        )

    with connection:
        with connection.cursor() as cursor:
            sql = "SHOW TABLES;"
            cursor.execute(sql)
            result = cursor.fetchall()

            if len(result) == 0:
                # There are no tables, we need to import.
                logging.info("Importing tables from: {0}".format(settings['sql_path']))

                import_sql = open(settings['sql_path'], 'rt').read()

                statements = filter(lambda x: x != '', 
                    map(lambda x: x.strip(),  import_sql.split(';'))
                )

                for curr_statement in statements:
                    logging.info("Executing SQL:\n{0}".format(curr_statement))
                    cursor.execute(curr_statement)
            else:
                logging.info("Tables already exist")

        connection.commit()


def pre_startup():
    backend_data = {
        'mysql': {
            'setup_func': setup_mysql,
            'sql_path': '/usr/share/doc/pdns-backend-mysql/schema.mysql.sql',
        }
    }

    # Setup base config
    subprocess.run(['envtpl', '--keep-template', '/etc/powerdns/pdns.conf.tpl'])

    # Setup database
    backends = os.getenv('PDNS_BACKEND','sqlite3')

    for curr_backend in backends.split(' '):
        logging.info("Setting up backend: {0}".format(curr_backend))
        backend_data[curr_backend]['setup_func'](backend_data[curr_backend])
        logging.info("Generating config for backend: {0}".format(curr_backend))
        subprocess.run(['envtpl', '--keep-template',
            '/etc/powerdns/pdns.d/backend-{0}.conf.tpl'.format(curr_backend)])

    # Possibly look at wiping out the env variables once we are done with them as this is the container exposed to the outside world.
    # del os.environ['MYVAR']


pre_startup()
pdns_server = '/usr/sbin/pdns_server'
os.execv(pdns_server, [pdns_server])
