[PARAMETERS]

# storage devices related
lun_target = force_list(default=None)
lun_address = force_list(default=None)
lun = force_list(default=None)

data_domain_path = force_list(default=None)
data_domain_address = force_list(default=None)

local_domain_path = force_list(default=None)

vfs_type = option('glusterfs', default='glusterfs')
gluster_domain_address = force_list(default=None)
gluster_domain_path = force_list(default=None)