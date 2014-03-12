"""
Soft Fencing config module
"""

__test__ = False

from art.test_handler.settings import opts
from art.test_handler.settings import ART_CONFIG

TEST_NAME = "Soft Fencing"
PARAMETERS = ART_CONFIG['PARAMETERS']
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

base_name = PARAMETERS.get('test_name', TEST_NAME)
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
hosts = PARAMETERS.as_list('vds')
pm_address = PARAMETERS.get('pm_address')
pm_type_ipmilan = PARAMETERS.get('pm_type_ipmilan')
pm_password = PARAMETERS.get('pm_password')
pm_user = PARAMETERS.get('pm_user')
host_user = PARAMETERS.get('host_user')
host_password = PARAMETERS.get('host_password')
host_with_pm = hosts[0]
host_without_pm = hosts[1]
job_description = 'Executing SSH Soft Fencing on host'
MGMT_BRIDGE = PARAMETERS['mgmt_bridge']
db_user = PARAMETERS['db_user']
db_pass = PARAMETERS['db_pass']
db_name = PARAMETERS['db_name']
PRODUCT_RHEVM = 'rhevm'
job_finished = ENUMS['job_finished']
job_failed = ENUMS['job_failed']
service_vdsmd = 'vdsmd'
service_network = 'network'
