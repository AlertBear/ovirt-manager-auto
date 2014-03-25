"""
Virt - Regression Vms Test configuration file
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "reg_vms"
PARAMETERS = ART_CONFIG['PARAMETERS']
STORAGE_TYPE = PARAMETERS['storage_type']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('vdc_root_password', None)

base_name = PARAMETERS.get('Reg_Vms', TEST_NAME)

# Datacenter names
dc_name = PARAMETERS.get('dc_name', 'datacenter_%s' % base_name)
second_dc_name = PARAMETERS.get('second_dc_name', 'second_datacenter_%s'
                                                  % base_name)
# Cluster names
cluster_name = PARAMETERS.get('cluster_name', 'cluster_%s' % base_name)
additional_cluster_names = ['%s_%d' %
                            (cluster_name, i) for i in range(2)]

# Cluster properties
cpu_name = PARAMETERS.get('cpu_name')
compatibility_version = PARAMETERS.get('compatibility_version')

data_paths = PARAMETERS.as_list('data_domain_path')
data_name = ["%s_%d" % (STORAGE_TYPE.lower(), index) for index in
             range(len(data_paths))]
hosts = PARAMETERS.as_list('vds')
host_user = PARAMETERS.get('host_user', 'root')
cluster_network = PARAMETERS.get('mgmt_bridge')
host_0 = hosts[0]
host_1 = hosts[1]

# Storage names
nfs_storage_0 = PARAMETERS.get('storage_name_0', '%s_%d' % (STORAGE_TYPE, 0))
nfs_storage_1 = PARAMETERS.get('storage_name_1', '%s_%d' % (STORAGE_TYPE, 1))
export_storage = 'export_domain'

# ISO storage domain
shared_iso_domain_address = PARAMETERS.get('shared_iso_domain_address')
shared_iso_domain_path = PARAMETERS.get('shared_iso_domain_path')
shared_iso_domain_name = PARAMETERS.get('shared_iso_domain_name')

# Run once parameters
user_domain = PARAMETERS.get('user_domain')
username = PARAMETERS.get('username')
password = PARAMETERS.get('password')
cdrom_image_1 = PARAMETERS.get('cdrom_image_1')
cdrom_image_2 = PARAMETERS.get('cdrom_image_2')
floppy_image = PARAMETERS.get('floppy_image')
