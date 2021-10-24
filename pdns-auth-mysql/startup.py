#!/usr/bin/env -S python3

import os
import jinja2
import logging
import subprocess
import sys

LOGGING_FORMAT = u'%(asctime)s - %(name)s - %(thread)d - %(levelname)s - %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)

def setup_mysql(op_mode, **argvs):
    '''
    '''
    import pymysql.cursors

    tmp_dump_sql = '/tmp/dump.sql'

    db_host     = os.getenv('PDNS_DB_HOSTNAME', 'mysql')
    db_user     = os.getenv('PDNS_DB_USERNAME', 'pdns-auth')
    db_password = os.getenv('PDNS_DB_PASSWORD', '')
    db_database = os.getenv('PDNS_DB_DATABASE', 'powerdns-auth')

    db_root_pass = os.getenv('MYSQL_ROOT_PASSWORD', '')

    # Attempt to connect using normal credentials
    try:
        #logging.debug("Connecting to {0}:{1}@{2}/{3}".format(db_user, db_password, db_host, db_database))
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
                sql = "CREATE DATABASE IF NOT EXISTS `{0}`;".format(db_database)
                logging.debug("Create Database SQL: {0}".format(sql))
                cursor.execute(sql)

                sql = "GRANT REPLICATION SLAVE,ALL ON `{0}`.* to `{1}`@'%' identified by '{2}';".\
                    format(db_user, db_database, db_password)
                logging.debug("GRANT ALL SQL: {0}".format(sql))
                cursor.execute(sql)

                sql = "GRANT REPLICATION SLAVE ON *.* TO '{0}'@'%';".format(db_user)
                logging.debug("GRANT Replication SQL: {0}".format(sql))
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
                    # There are no tables, we need to import.
                    logging.info("Importing tables from: {0}".format(settings['sql_path']))

                    import_sql = open(settings['sql_path'], 'rt').read()

                    statements = filter(lambda x: x != '', 
                        map(lambda x: x.strip(),  import_sql.split(';'))
                    )

                    for curr_statement in statements:
                        logging.info("Executing SQL:\n{0}".format(curr_statement))
                        cursor.execute(curr_statement)
                elif op_mode == 'slave':
                    repl_host = os.getenv('PDNS_REPL_HOSTNAME', '')
                    repl_user = os.getenv('PDNS_REPL_USERNAME', '')
                    repl_pass = os.getenv('PDNS_REPL_PASSWORD', '')
                    repl_db = os.getenv('PDNS_REPL_DATABASE', '')

                    logging.info("Setting up slave database")

                    master_conn_data = {
                        'host': repl_host,
                        'user': os.getenv('PDNS_REPL_ROOT_USER', 'root'),
                        'password': os.getenv('PDNS_REPL_ROOT_PASSWORD', ''),
                        'database': 'mysql',
                        'cursorclass': pymysql.cursors.DictCursor,
                    }
                    master_connection = pymysql.connect(**master_conn_data)
                    with master_connection:
                        with master_connection.cursor() as master_cursor:
                            # Setup replication user
                            master_cursor.execute("""
                                GRANT REPLICATION SLAVE ON *.* 
                                TO '{0}'@'%'
                                IDENTIFIED BY '{1}';
                            """.format(repl_user, repl_pass))
                            master_cursor.execute("FLUSH PRIVILEGES;")
                    
                            # Fetch backup
                            logging.info("Dumping database from master")
                            res = subprocess.run([
                                'mysqldump',
                                '--master-data', # --source-data is newer version
                                '-h', master_conn_data['host'],
                                '-u', master_conn_data['user'], 
                                '--password={0}'.format(master_conn_data['password']),
                                '--databases', repl_db,
                            ], stdout=open(tmp_dump_sql, 'w'))

                            # Restore backup
                            logging.info("Importing backup into local db")
                            res = subprocess.run([
                                # 'cat', tmp_dump_sql,
                                # '|',
                                'mysql', '-u', 'root',
                                '-p{0}'.format(db_root_pass),
                            ], stdin=open(tmp_dump_sql, 'r'))
                    
                            # Setup replication
                            logging.info("Setup MASTER replication")
                            sql = """
                                CHANGE MASTER TO
                                    MASTER_HOST='{0}',
                                    MASTER_USER='{1}',
                                    MASTER_PASSWORD='{2}',
                                    MASTER_PORT=3306,
                                    MASTER_CONNECT_RETRY=10; 
                            """.format(
                                repl_host,
                                repl_user,
                                repl_pass,
                            )
                            logging.debug("CHANGE MASTER sql:\n{0}".format(sql))
                            master_cursor.execute(sql)

                            master_cursor.execute("START SLAVE;")
                else:
                    logging.error("Unknown operational mode: '{0}".format(op_mode))
            else:
                logging.info("Tables already exist")

        connection.commit()


def master_setup():
    backend_data = {
        'mysql': {
            'setup_func': setup_mysql,
            'args': {
                'sql_path': '/usr/share/doc/pdns-backend-mysql/schema.mysql.sql',
            }
        },
    }

    # Setup base config
    subprocess.run(['envtpl', '--keep-template', '/etc/powerdns/pdns.conf.tpl'])

    # Setup database
    backends = os.getenv('PDNS_BACKEND','sqlite3')

    for curr_backend in backends.split(' '):
        bk_end = backend_data[curr_backend]

        # Setup the backend
        logging.info("Setting up backend: {0}".format(curr_backend))
        bk_end['setup_func'](op_mode='master', **bk_end['args'])

        # Now generate the config files for the backend
        logging.info("Generating config for backend: {0}".format(curr_backend))
        subprocess.run(['envtpl', '--keep-template',
            '/etc/powerdns/pdns.d/backend-{0}.conf.tpl'.format(curr_backend)])

    # Possibly look at wiping out the env variables once we are done with them as this is the container exposed to the outside world.
    # del os.environ['MYVAR']

def slave_setup():
    backend_data = {
        'mysql': {
            'setup_func': setup_mysql,
            'args': {}
        },
    }

    # Setup base config
    subprocess.run(['envtpl', '--keep-template', '/etc/powerdns/pdns.conf.tpl'])

    backends = os.getenv('PDNS_BACKEND','mysql')

    for curr_backend in backends.split(' '):
        bk_end = backend_data[curr_backend]

        # Setup the actual backend
        logging.info("Setting up backend: {0}".format(curr_backend))
        bk_end['setup_func'](op_mode='slave', **bk_end['args'])

        # Now generate the config files for the backend
        logging.info("Generating config for backend: {0}".format(curr_backend))
        subprocess.run(['envtpl', '--keep-template',
            '/etc/powerdns/pdns.d/backend-{0}.conf.tpl'.format(curr_backend)])

# Main starts here
operational_mode = os.getenv('PDNS_AUTH_MYSQL_MODE')
if operational_mode == 'master':
    master_setup()
elif operational_mode == 'slave':
    slave_setup()
else:
    logging.error("Unknown operational mode: {0}".format())
    sys.exit(-2)

# Now startup PowerDNS server and replace this
pdns_server = '/usr/sbin/pdns_server'
os.execv(pdns_server, [pdns_server])
