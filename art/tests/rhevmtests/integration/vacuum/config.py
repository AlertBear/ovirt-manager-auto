""" Test configuration - Vacuum constants """

import logging

from art.rhevm_api import resources
from art.test_handler.settings import ART_CONFIG

logger = logging.getLogger(__name__)

VACUUM_UTIL = "engine-vacuum"
VACUUM_DWH_UTIL = "dwh-vacuum"
VACUUM_TABLE = "vm_dynamic"
VACUUM_DWH_TABLE = "vm_daily_history"

DWH_DATABASE_CONFIG = (
    "/etc/ovirt-engine/engine.conf.d/10-setup-dwh-database.conf"
)
# parameters
FULL = "-f"
ANALYZE = "-a"
ANALYZE_ONLY = "-A"
TABLE = "-t"
VERBOSE = "-v"

# logging of verbose mode
VERBOSE_INFO = "INFO"

# SQL queries
# used in check_vacuum_stats() with .format(table)
SQL_VACUUM_STATS = (
    "select vacuum_count, analyze_count "
    "from pg_catalog.pg_stat_all_tables "
    "where relname = '{}';"
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

# changes in database can be visible after some time when vacuum finishes
GET_STATS_TIMEOUT = 2
GET_STATS_SLEEP = 0.5
