[PARAMETERS]

# storage devices related
lun_target = force_list(default=None)
lun_address = force_list(default=None)
lun = force_list(default=None)
data_domain_path = force_list(default=None)
data_domain_address = force_list(default=None)

[STORAGE]
storage_pool=force_list(default=list('10.35.64.102', '10.35.64.106', '10.35.66.10', '10.35.64.81', '10.35.160.7'))