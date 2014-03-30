"""
Virt - Payloads Test configuration module
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "payloads"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
TCMS_PLAN_ID = PARAMETERS.get('tcms_plan_id')

base_name = PARAMETERS.get('test_name', TEST_NAME)
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
template_vm = PARAMETERS.get('template_vm', 'template_vm_%s' % base_name)
template_image = PARAMETERS.get('cobbler_profile')
payload_vm = PARAMETERS.get('payload_vm', '%s_vm' % base_name)
vm_user = PARAMETERS.get('vm_username', 'root')
vm_password = PARAMETERS.get('vm_password', 'qum5net')
template_name = PARAMETERS.get('template_name', 'template_%s' % base_name)
vm_display_type = PARAMETERS.get('vm_display_type')
data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
source_host = PARAMETERS.get('source_host', 'localhost')
hosts = PARAMETERS.as_list('vds')
host_user = PARAMETERS.get('host_user', 'root')
host_password = PARAMETERS.get('host_password', 'qum5net')
cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')
