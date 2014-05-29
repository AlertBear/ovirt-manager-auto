"""
SLA test config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG

TEST_NAME = "SLA"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

basename = PARAMETERS.get('test_name', TEST_NAME)
DC_name = PARAMETERS.get('dc_name', '%s_DC' % basename)
cluster_name = PARAMETERS.get('cluster_name', '%s_cluster' % basename)
cpu_name = PARAMETERS['cpu_name']
data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
data_addresses = PARAMETERS.as_list('data_domain_address')
version = PARAMETERS['compatibility_version']
hosts = PARAMETERS.as_list('vds')
hosts_pw = PARAMETERS.as_list('vds_password')

cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')
cpupin_iter = int(PARAMETERS.get('cpu_iter', 4))
