"""
Templates test config module
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "Templates"
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
domain_name = PARAMETERS.get('domain_name', 'internal')
cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')

# Storage names
nfs_storage_0 = PARAMETERS.get('storage_name_0', '%s_0' % STORAGE_TYPE)
nfs_storage_1 = PARAMETERS.get('storage_name_1', '%s_1' % STORAGE_TYPE)
export_storage = PARAMETERS.get('export_storage', 'export_domain')
