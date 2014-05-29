"""
Virt - Migration Test configuration module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG

TEST_NAME = "migration"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)
TCMS_PLAN_ID = PARAMETERS.get('tcms_plan_id', '10421')
MAX_WORKERS = PARAMETERS.get('max_workers', 10)
VM_LINUX_USER = PARAMETERS['vm_linux_user']
VM_LINUX_PASSWORD = PARAMETERS['vm_linux_password']

MB = 1024 ** 2
GB = 1024 ** 3
# Vm disk size
DISK_SIZE = 3 * GB

base_name = PARAMETERS.get('test_name', TEST_NAME)
cpu_name = PARAMETERS.get('cpu_name')
compatibility_version = PARAMETERS.get('compatibility_version')
# Datacenter names
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
second_dc_name = PARAMETERS.get('second_dc_name', 'second_datacenter_%s'
                                                  % base_name)
# Cluster names
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
additional_cluster_names = ['%s_%d' %
                            (cluster_name, i) for i in range(2)]
# Storage names
storage_name = PARAMETERS.get('storage_name', '%s_%d' % (STORAGE_TYPE, 0))

# Vm names
vm_name_basic = '%s_vm' % (base_name)
vm_names = ['%s-%d' % (vm_name_basic, i) for i in range(15)]
migration_vm = vm_names[0]
vm_description = PARAMETERS.get('vm_description', '%s_test' % base_name)
data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%s_%d" % (base_name, STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
source_host = PARAMETERS.get('source_host', 'localhost')
hosts = PARAMETERS.as_list('vds')
migration_host_0 = hosts[0]
migration_host_1 = hosts[1]
hosts_str = "".join([migration_host_0, ',', migration_host_1])
host_user = PARAMETERS.get('host_user', 'root')
host_password = PARAMETERS.get('host_password', 'qum5net')
cluster_network = PARAMETERS.get('mgmt_bridge', 'rhevm')
installation = PARAMETERS.get('installation', 'true')
# Cobbler info
image = PARAMETERS.get('cobbler_profile')
cobblerAddress = PARAMETERS.get('cobbler_address', None)
cobblerUser = PARAMETERS.get('cobbler_user', None)
cobblerPasswd = PARAMETERS.get('cobbler_passwd', None)
