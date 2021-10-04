#!/usr/bin/env -S python3 -u
import os
import sys
import jinja2

#sql_path = '/usr/local/share/doc/pdns/'
sql_path = '/usr/share/doc/pdns-backend-mysql'
to_apply = [
    'schema.mysql.sql',
    'enable-foreign-keys.mysql.sql',
]
