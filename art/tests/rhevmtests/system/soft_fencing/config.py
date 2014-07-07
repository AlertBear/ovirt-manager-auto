"""
Soft Fencing config module
"""

__test__ = False

from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG
from rhevmtests.system import config # flake8: noqa

TEST_NAME = "Soft Fencing"
#PARAMETERS = ART_CONFIG['PARAMETERS']
#ENUMS = opts['elements_conf']['RHEVM Enums']
#STORAGE_TYPE = PARAMETERS['storage_type']
#VDC = PARAMETERS.get('host', None)
#VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

#base_name = PARAMETERS.get('test_name', TEST_NAME)
DC_NAME = PARAMETERS.get('dc_name', 'datacenter_%s' % TEST_NAME)
CLUSTER_NAME = PARAMETERS.get('cluster_name', 'cluster_%s' % TEST_NAME)
#dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
#cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
DATA_PATHS = PARAMETERS.as_list('data_domain_path')
DATA_NAME = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(DATA_PATHS))]


#data_paths = PARAMETERS.as_list('data_domain_path')
#data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
#hosts = PARAMETERS.as_list('vds')
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

