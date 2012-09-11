[PARAMETERS]
# vm_os used in exportImport test. Options: Any supported os image name.
vm_os = string(default='Red Hat Enterprise Linux 6.x x64')
vm_windows_user = string(default='Administrator')
vm_windows_password = string(default='123456')
vm_linux_user = string(default='root')
vm_linux_password = string(default='qum5net')

# cobbler configuration
cobbler_address = string(default='qa-cobbler.qa.lab.tlv.redhat.com')
cobbler_user = string(default='root')
cobbler_passwd = string(default='qum5net')
cobbler_profile = string(default='short_agent_rhel6.x_jenkins-x86_64')

useAgent = string(default='False')

[NFS]
vds = force_list(default=None)
vds_password = force_list(default=None)
data_domain_address = force_list(default=None)
data_domain_path = force_list(default=None)

[ISCSI]
vds = force_list(default=None)
vds_password = force_list(default=None)
lun = force_list(default=None)
lun_target = force_list(default=None)
lun_address = force_list(default=None)

