""" Test configuration - Vacuum constants """

from rhevmtests.config import *  # flake8: noqa

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

# changes in database can be visible after some time when vacuum finishes
GET_STATS_TIMEOUT = 2
GET_STATS_SLEEP = 0.5
