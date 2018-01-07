from reports.config import *  # flake8: noqa

DEBUG_CONF = '/etc/ovirt-engine-dwh/ovirt-engine-dwhd.conf.d/logging.conf'
ENABLE_LOG = 'DWH_AGGREGATION_DEBUG=true'
DWH_LOG_BACKUP = '/tmp/dwhd.log'
SLEEP_TIME_SETTINGS = 10
SETTINGS_COUNT = 23

DWH_VARS = {
    "hoursToKeepDaily" : "0",
    "hoursToKeepHourly" : "720",
    "ovirtEngineDbPassword" : "******",
    "runDeleteTime" : "3",
    "runInterleave" : "60",
    "limitRows" : "limit 1000",
    "ovirtEngineHistoryDbUser" : "ovirt_engine_history",
    "ovirtEngineDbUser" : "engine",
    "deleteIncrement" : "10",
    "hoursToKeepSamples" : "24",
    "deleteMultiplier" : "1000",
    "ovirtEngineHistoryDbDriverClass" : "org.postgresql.Driver",
    "ovirtEngineHistoryDbPassword" : "******"
}
