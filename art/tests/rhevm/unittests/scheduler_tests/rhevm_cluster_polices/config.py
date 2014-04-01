"""
Rhevm Cluster Policies Test configuration module
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "cluster_policies"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

base_name = PARAMETERS.get('test_name', TEST_NAME)
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
vm_for_migration = PARAMETERS.get('vm_for_migration', 'vm_%s' % base_name)
support_vm_1 = 'support_vm_1'
support_vm_2 = 'support_vm_2'
data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
hosts = PARAMETERS.as_list('vds')
host_user = PARAMETERS.get('host_user', 'root')
host_password = PARAMETERS.get('host_password', 'qum5net')
cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')
load_host_1 = hosts[0]
load_host_2 = hosts[1]
load_host_3 = hosts[2]
