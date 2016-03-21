[REMOVE_PACKAGES]
enabled = boolean(default=True)

[HOSTS_CLEANUP]
enabled = boolean(default=True)

[ERROR_FETCHER]
enabled = boolean(default=True)

[PUPPET]
enabled = boolean(default=True)

[HOST_NICS_RESOLUTION]
enabled = boolean(default=True)

[CPU_NAME_RESOLUTION]
enabled = boolean(default=True)

[LOG_CAPTURE]
enabled = boolean(default=True)
fmt = string(default='#(asctime)s - #(threadName)s - #(name)s - #(levelname)s - #(message)s')

[BUGZILLA]
enabled = boolean(default=True)

[GENERATE_DS]
enabled = boolean(default=True)

[VERSION_FETCHER]
enabled = boolean(default=True)
host = string_list(default=list())
vds = string_list(default=list('vdsm', 'libvirt'))

[PROVISIONING_TOOLS]
enabled = boolean(default=True)
