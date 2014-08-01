"""
Soft Fencing config module
"""

__test__ = False

from rhevmtests.system.config import *  # flake8: noqa


TEST_NAME = "Soft Fencing"
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TEST_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TEST_NAME)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]
PM_ADDRESS = PARAMETERS['pm_address']
PM_TYPE_IPMILAN = PARAMETERS['pm_type_ipmilan']
PM_PASSWORD = PARAMETERS['pm_password']
PM_USER = PARAMETERS['pm_user']
host_with_pm = HOSTS[0]
host_without_pm = HOSTS[1]
job_description = 'Executing SSH Soft Fencing on host'

db_user = PARAMETERS['db_user']
db_pass = PARAMETERS['db_pass']
db_name = PARAMETERS['db_name']
PRODUCT_RHEVM = 'rhevm'
job_finished = ENUMS['job_finished']
job_failed = ENUMS['job_failed']
service_vdsmd = 'vdsmd'
service_network = 'network'
