#!/usr/bin/env -S python3
'''
Setup script for PowerDNS server
'''

import os
#import jinja2
import logging
import subprocess
import sys

import pymysql.cursors



def setup_mysql_master_tables(cursor, sql_path, schema_file_name):
    '''
    Setup MySQL backend for PowerDNS authoritative master


    '''
    # There are no tables, we need to import.
    full_sql_path = os.path.join(sql_path, schema_file_name)
    logging.info(f"Importing tables from: {full_sql_path}")

    import_sql = open(full_sql_path, 'rt', encoding='utf-8').read()

    statements = filter(lambda x: x != '', 
        map(lambda x: x.strip(),  import_sql.split(';'))
    )

    for curr_statement in statements:
        logging.info(f"Executing SQL:\n{curr_statement}")
        cursor.execute(curr_statement)

def setup_mysql_slave_tables():
    '''
    Setup MySQL backend for PowerDNS authoritative slave


    '''
    tmp_dump_sql = '/tmp/dump.sql'

    db_root_pass = os.getenv('MYSQL_ROOT_PASSWORD', '')

    repl_host = os.getenv('PDNS_REPL_HOSTNAME', '')
    repl_user = os.getenv('PDNS_REPL_USERNAME', '')
    repl_pass = os.getenv('PDNS_REPL_PASSWORD', '')
    #repl_db   = os.getenv('PDNS_REPL_DATABASE', '')

    logging.info("Setting up slave database")

    master_conn_data = {
        'host': repl_host,
        'user': os.getenv('PDNS_REPL_ROOT_USER', 'root'),
        'password': os.getenv('PDNS_REPL_ROOT_PASSWORD', ''),
        'database': 'mysql',
        'cursorclass': pymysql.cursors.DictCursor,
    }

    with pymysql.connect(**master_conn_data) as master_connection:
        with master_connection.cursor() as master_cursor:
            # Setup replication user
            master_cursor.execute(f"""
                GRANT REPLICATION SLAVE ON *.* 
                TO '{repl_user}'@'%'
                IDENTIFIED BY '{repl_pass}';
            """)
            master_cursor.execute("FLUSH PRIVILEGES;")

            # Fetch backup
            logging.info("Dumping database from master")
            res = subprocess.run([
                    'mysqldump',
                    '--master-data', # --source-data is newer version
                    '--all-databases',
                    '--single-transaction',
                    '-h', master_conn_data['host'],
                    '-u', master_conn_data['user'],
                    f"--password={master_conn_data['password']}",
                ],
                stdout=open(tmp_dump_sql, 'w', encoding='utf-8'),
                check=True
            )
            if res.returncode != 0:
                logging.error(f"Got error fetching dump from master: {res.returncode}")
                raise RuntimeError("Unable to dump master server")

            # Restore backup to the local db
            logging.info("Importing backup into local db")
            res = subprocess.run([
                    # 'cat', tmp_dump_sql,
                    # '|',
                    'mysql',
                    '-h', 'db',
                    '-u', 'root',
                    f'-p{db_root_pass}',
                ],
                stdin=open(tmp_dump_sql, 'r', encoding='utf-8'),
                check=True,
            )

            # Setup replication
            logging.info("Setup MASTER replication")
            sql = f"""
                CHANGE MASTER TO
                    MASTER_HOST='{repl_host}',
                    MASTER_USER='{repl_user}',
                    MASTER_PASSWORD='{repl_pass}',
                    MASTER_PORT=3306,
                    MASTER_CONNECT_RETRY=10;
            """
            logging.debug(f"CHANGE MASTER sql:\n{sql}")
            master_cursor.execute(sql)

            master_cursor.execute("START SLAVE;")

    return

def setup_mysql(op_mode, **argvs):
    '''
    Setup MySQL DB setup
    '''
    # TODO: Break this entire fucntion out to a separate file just to
    # handle each driver, MySQL, Postgres and sqlite

    db_host     = os.getenv('PDNS_DB_HOSTNAME', 'mysql')
    db_user     = os.getenv('PDNS_DB_USERNAME', 'pdns-auth')
    db_password = os.getenv('PDNS_DB_PASSWORD', '')
    db_database = os.getenv('PDNS_DB_DATABASE', 'powerdns-auth')

    db_root_pass = os.getenv('MYSQL_ROOT_PASSWORD', '')

    # Attempt to connect using normal credentials
    try:
        logging.debug(
            f"Connecting to {db_user}:{db_password}@{db_host}/{db_database}"
        )
        connection = pymysql.connect(
            host = db_host,
            user = db_user,
            password = db_password,
            database = db_database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        logging.info("Connected with normal user")
    except pymysql.err.OperationalError:
        # The user doesn't exist / work, connect with root creds and create
        # user (and likely db as well).
        logging.error("Failed to connect to normal user")
        connection = pymysql.connect(
            host = db_host,
            user = 'root',
            password = db_root_pass,
            database = '',
            cursorclass=pymysql.cursors.DictCursor,
        )
        with connection:
            with connection.cursor() as cursor:

                # Would love to use prepared statements with auto-escaping but
                # for certain parts I need it to just put what is sent in.
                sql = f"CREATE DATABASE IF NOT EXISTS `{db_database}`;"
                logging.debug(f"Create Database SQL: {sql}")
                cursor.execute(sql)

                sql = f"""
                    GRANT REPLICATION
                        SLAVE,ALL
                    ON 
                        `{db_user}`.* to `{db_database}`@'%' 
                    IDENTIFIED BY
                        '{db_password}';
                """
                logging.debug(f"GRANT ALL SQL: {sql}")
                cursor.execute(sql)

                sql = f"GRANT REPLICATION SLAVE ON *.* TO '{db_user}'@'%';"
                logging.debug(f"GRANT Replication SQL: {sql}")
                cursor.execute(sql)

                sql = "FLUSH PRIVILEGES;"
                cursor.execute(sql)

            connection.commit()

        # Now reconnect as the normal user again.
        connection = pymysql.connect(
            host = db_host,
            user = db_user,
            password = db_password,
            database = db_database,
            cursorclass=pymysql.cursors.DictCursor,
        )

    with connection:
        with connection.cursor() as cursor:
            logging.info("Checking tables")
            sql = "SHOW TABLES;"
            cursor.execute(sql)
            result = cursor.fetchall()

            if len(result) == 0:
                if op_mode == 'master':
                    setup_mysql_master_tables(
                        cursor,
                        argvs['sql_path'],
                        argvs['schema_file_name']
                    )
                elif op_mode == 'slave':
                    setup_mysql_slave_tables()
                else:
                    logging.error(f"Unknown operational mode: '{op_mode}")
            else:
                logging.info("Tables already exist")

        connection.commit()


def master_setup():
    '''
    Setup master DNS server
    '''
    logging.info("Setting up master server")
    backend_data = {
        'mysql': {
            'setup_func': 'setup_mysql',
            'args': {
                'sql_path': 'usr/share/pdns-backend-mysql/schema/',
                'schema_file_name': 'schema.mysql.sql',
            }
        },
    }

    # Setup base config
    subprocess.run([
        'envtpl',
        '--keep-template',
        '/etc/powerdns/pdns.conf.tpl'
    ], check=True)

    # Setup database, sqlite3 is default
    backends = os.getenv('PDNS_BACKEND','sqlite3')

    for curr_backend in backends.split(' '):
        bk_end = backend_data[curr_backend]

        # Setup the backend
        logging.info(f"Setting up backend: {curr_backend}")
        setup_func = globals()[bk_end['setup_func']]
        setup_func(op_mode='master', **bk_end['args'])

        # Now generate the config files for the backend
        logging.info(f"Generating config for backend: {curr_backend}")
        subprocess.run([
            'envtpl',
            '--keep-template',
            f'/etc/powerdns/pdns.d/backend-{curr_backend}.conf.tpl'
        ], check=True)

    # Possibly look at wiping out the env variables once we are done with them
    # as this is the container exposed to the outside world. If there is a zero
    # day we don't want to expose any unneccesary data. Use a debug mode or
    # similar to disable this for debugging the container.
    # del os.environ['MYVAR']

def slave_setup():
    '''
    Setup slave server
    '''
    logging.info("Setting up slave server")
    backend_data = {
        'mysql': {
            'setup_func': setup_mysql,
            'args': {}
        },
    }

    # Setup base config
    subprocess.run([
        'envtpl',
        '--keep-template',
        '/etc/powerdns/pdns.conf.tpl'
    ], check=True)

    backends = os.getenv('PDNS_BACKEND','mysql')

    for curr_backend in backends.split(' '):
        bk_end = backend_data[curr_backend]

        # Setup the actual backend
        logging.info(f"Setting up backend: {curr_backend}")
        bk_end['setup_func'](op_mode='slave', **bk_end['args'])

        # Now generate the config files for the backend
        logging.info(f"Generating config for backend: {curr_backend}")
        subprocess.run([
            'envtpl',
            '--keep-template',
            f'/etc/powerdns/pdns.d/backend-{curr_backend}.conf.tpl'
        ], check=True)

# Main starts here
LOGGING_FORMAT = '%(asctime)s - %(name)s - %(thread)d - %(levelname)s - %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)

operational_mode = os.getenv('PDNS_AUTH_MYSQL_MODE')
if operational_mode == 'master':
    master_setup()
elif operational_mode == 'slave':
    slave_setup()
else:
    logging.error(f"Unknown operational mode: {operational_mode}")
    sys.exit(-2)

# Now startup PowerDNS server and replace this
PDNS_SERVER_EXECUTABLE = '/usr/sbin/pdns_server'
os.execv(PDNS_SERVER_EXECUTABLE, [PDNS_SERVER_EXECUTABLE])
