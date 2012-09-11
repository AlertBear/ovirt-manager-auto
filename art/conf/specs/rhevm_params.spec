[HTTP_HEADERS]
Prefer = string(default='persistent-auth')

[PARAMETERS]
# general
cdrom_image = string(default='en_windows_7_enterprise_x64_dvd_x15-70749.iso')
floppy_image = string(default='win2k3.vfd')
cpu_name = string(default='Intel Nehalem Family')
shared_iso_domain_path = string(default='/volumes/base/shared_iso_domain')
shared_iso_domain_address = string(default='wolf.qa.lab.tlv.redhat.com')
vds_ovirt_port = integer(default='8443')
mgmt_bridge = string(default='rhevm')
compatibility_version = option('3.0', '3.1', default='3.1')
local_domain_path = string(default='/home/rest_test_domain')
product_name = string(default='Red Hat Enterprise Virtualization')
vds_password = force_list(default=None)
vds = force_list(default=None)
data_center_type= option('nfs', 'iscsi', 'none', default='none')

#users
no_roles_user = string(default='larisa')
not_existing_user = string(default='not_existing_user')
new_user = string(default='istein')
wrong_domain_user = string(default='hateya')


# storage devices related - doesn't work properly due to bug in ConfigObj
lun_target = force_list(default=None)
lun_address = force_list(default=None)
lun = force_list(default=None)
tests_iso_domain_path = force_list(default=None)
tests_iso_domain_address = force_list(default=None)
export_domain_address = force_list(default=None)
export_domain_path = force_list(default=None)
data_domain_path = force_list(default=None)
data_domain_address = force_list(default=None)

