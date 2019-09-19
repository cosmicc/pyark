import sys

import psycopg2
import pytest
from modules.asyncdb import asyncDB
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user

sys.path.append('/home/ark/pyark')

