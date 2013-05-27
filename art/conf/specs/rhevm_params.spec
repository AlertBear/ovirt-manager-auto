[RUN]
data_struct_mod = string(default='art.rhevm_api.data_struct.data_structures')

[HTTP_HEADERS]
Prefer = string(default='persistent-auth')

[PARAMETERS]
# general
cdrom_image = string(default='en_windows_7_enterprise_x64_dvd_x15-70749.iso')
floppy_image = string(default='win2k3.vfd')
cpu_name = option('Intel Nehalem Family', 'Intel Xeon w/o XD/NX', 'Intel Xeon', 'Intel Conroe Family', 'Intel Penryn Family', 'AMD Opteron G1 w/o NX', 'AMD Opteron G1', 'AMD Opteron G2', 'AMD Opteron G3', default='Intel Nehalem Family')
shared_iso_domain_path = string(default='/volumes/base/shared_iso_domain')
shared_iso_domain_address = domain_format(default='wolf.qa.lab.tlv.redhat.com')
vds_ovirt_port = integer(default='8443')
mgmt_bridge = string(default='rhevm')
compatibility_version = option('3.0', '3.1', '3.2', '3.3', default='3.1')
local_domain_path = string(default='/home/rest_test_domain')
product_name = string(default='Red Hat Enterprise Virtualization Manager')
vds_password = force_list(default=list('qum5net', 'qum5net'))
vds = is_alive()
data_center_type= option('nfs', 'iscsi', 'posixfs', 'localfs', 'none', default='none')
# This parameter will be used in order to choose nas protocol for iso and export domains
iso_export_domain_nas = option('nfs', 'posixfs', default='nfs')
host_nics = force_list(default=None)
vdc_root_password = string(default='qum5net')

#users
no_roles_user = string(default='larisa')
not_existing_user = string(default='not_existing_user')
new_user = string(default='istein')
wrong_domain_user = string(default='hateya')

# storage related
tests_iso_domain_path = force_list(default=None)
tests_iso_domain_address = force_list(default=None)
export_domain_address = force_list(default=None)
export_domain_path = force_list(default=None)

vm_windows_user = string(default='Administrator')
vm_windows_password = string(default='123456')
vm_linux_user = string(default='root')
vm_linux_password = string(default='qum5net')

useAgent = string(default='True')

# vm_os used in exportImport test. Options: Any supported os image name.
vm_os = string(default='Red Hat Enterprise Linux 6.x x64')
display_type = option('spice', 'vnc', 'rdesktop', default='spice')

# cobbler configuration
cobbler_address = is_alive(default='qa-cobbler.qa.lab.tlv.redhat.com')
cobbler_user = string(default='root')
cobbler_passwd = string(default='qum5net')

[MATRIX_TEST_RUNNER]
test_modules = force_list(default=list('art.rhevm_api',))
auto_discovery = boolean(default=True)

[STORAGE]
storage_pool=force_list(default=list('10.35.64.106', '10.35.160.7', '10.35.64.21'))
