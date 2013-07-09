[PARAMETERS]

# storage devices related
lun_target = force_list(default=None)
lun_address = force_list(default=None)
lun = force_list(default=None)

data_domain_path = force_list(default=None)
data_domain_address = force_list(default=None)
data_domain_real_storage_type = force_list(default=None)

local_domain_path = force_list(default=None)

vfs_type = option('nfs', 'glusterfs', default='glusterfs')
