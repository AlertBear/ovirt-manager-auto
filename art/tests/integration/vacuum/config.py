""" Test configuration - Vacuum constants """

import logging

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

logger = logging.getLogger(__name__)

VACUUM_UTIL = "engine-vacuum"
VM_DYNAMIC_TABLE = "vm_dynamic"

# parameters
FULL = "-f"
ANALYZE = "-a"
ANALYZE_ONLY = "-A"
TABLE = "-t"
VERBOSE = "-v"

# logging of verbose mode
VERBOSE_INFO = "INFO"

# SQL queries

SQL_VACUUM_RUNNING = (
    "select 1 from pg_stat_activity "
    "where usename='engine' and "
    "datname = 'engine' and "
    "regexp_replace(query,  '\s+$', '') "
    "ilike 'vacuum (full);';"
)
SQL_VACUUM_RUNNING_TABLE = (
    "select 1 from pg_stat_activity "
    "where usename='engine' and "
    "datname = 'engine' and "
    "regexp_replace(query,  '\s+$', '') "
    "ilike 'vacuum (full) vm_dynamic;';"
)
SQL_VACUUM_STATS = (
    "select vacuum_count, analyze_count "
    "from pg_catalog.pg_stat_all_tables "
    "where relname = 'vm_dynamic';"
)

# RHEVM related constants
PARAMETERS = ART_CONFIG['PARAMETERS']
REST_CONNECTION = ART_CONFIG['REST_CONNECTION']
VDC_PASSWORD = REST_CONNECTION['password']
VDC_PORT = REST_CONNECTION['port']
ENGINE_ENTRY_POINT = REST_CONNECTION['entry_point']

VDC_ADMIN_USER = 'admin'
VDC_ADMIN_DOMAIN = 'internal'

# ENGINE SECTION
VDC_HOST = REST_CONNECTION['host']
VDC_ROOT_PASSWORD = PARAMETERS.get('vdc_root_password')
ENGINE_HOST = resources.Host(VDC_HOST)
ENGINE_HOST.users.append(
    resources.RootUser(VDC_ROOT_PASSWORD)
)

ENGINE = resources.Engine(
    ENGINE_HOST,
    resources.ADUser(
        VDC_ADMIN_USER,
        VDC_PASSWORD,
        resources.Domain(VDC_ADMIN_DOMAIN),
    ),
    schema=REST_CONNECTION.get('schema'),
    port=VDC_PORT,
    entry_point=ENGINE_ENTRY_POINT,
)
