[RUN]
data_struct_mod = string(default='art.rhevm_api.data_struct.data_structures')

[HTTP_HEADERS]

[PARAMETERS]
# general
cdrom_image = string(default='en_windows_7_enterprise_x64_dvd_x15-70749.iso')
floppy_image = string(default='win2k3.vfd')
cpu_name = option('Intel Conroe Family', 'Intel Penryn Family', 'Intel Nehalem Family', 'Intel Westmere Family', 'Intel SandyBridge Family', 'Intel Haswell-noTSX Family', 'Intel Haswell Family', 'Intel Broadwell-noTSX Family', 'Intel Broadwell Family', 'AMD Opteron G1', 'AMD Opteron G2', 'AMD Opteron G3', 'AMD Opteron G4', 'AMD Opteron G5', 'IBM POWER8', 'IBM POWER8E', default='Intel Nehalem Family')
shared_iso_domain_path = string(default='/iso_domain')
shared_iso_domain_address = domain_format(default='vserver-production.qa.lab.tlv.redhat.com')
vds_ovirt_port = integer(default='8443')
mgmt_bridge = string(default='ovirtmgmt')
compatibility_version = option('3.6', '4.0', '4.1', '4.2', default='4.2')
local_domain_path = string(default='/home/rest_test_domain')
product_name = option('Red Hat Virtualization Manager', 'oVirt Engine', default='Red Hat Virtualization Manager')
vds_password = force_list(default=list('qum5net', 'qum5net'))
vds = is_alive()
# local replaces data_center_type. it is boolean, shared dc will be created when it is False and local dc will be created when it is True
local=boolean(default=False)
storage_type = option('nfs', 'iscsi', 'fcp', 'glusterfs', 'posixfs_nfs', 'posixfs_gluster', 'posixfs_mixed', 'localfs', 'posixfs_pnfs', 'none', default='none')
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

# polarion
polarion_user = string(default='ci-user')
polarion_project = string(default='RHEVM3')
polarion_response_myproduct = string(default='rhvm')

# upgrade GE
upgrade_version = string(default='4.3')

[STORAGE]
storage_pool=force_list(default=list())

# section for hosted engine details
[HOSTED_ENGINE]
additional_hosts = force_list(default=list())
