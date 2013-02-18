"""
SLA test config module
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "SLA"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['data_center_type']

basename = PARAMETERS.get('test_name', TEST_NAME)
DC_name = PARAMETERS.get('dc_name', '%s_DC' % basename)
cluster_name = PARAMETERS.get('cluster_name', '%s_cluster' % basename)
cpu_name = PARAMETERS['cpu_name']
data_name = PARAMETERS.get('data_domain_name', '%s_storage' % basename)
data_paths = PARAMETERS.as_list('data_domain_path')
data_addresses = PARAMETERS.as_list('data_domain_address')
version = PARAMETERS['compatibility_version']
hosts = PARAMETERS.as_list('vds')
hosts_pw = PARAMETERS.as_list('vds_password')

cpupin_iter = int(PARAMETERS.get('cpu_iter', 4))