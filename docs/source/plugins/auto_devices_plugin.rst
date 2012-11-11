
-------------------
Auto Devices Plugin
-------------------

This plugin creates storage devices before the test starts and remove all
these devices after the test finishes.

Configuration Options
---------------------
To enable this plugin add the following parameter to the RUN section:
    * auto_devices=yes

In your settings.conf file add a section STORAGE and fill it with
the following parameters:

    [STORAGE]
    # possible keys for nfs devices:
    nfs_server = <nfs_server_name>
    nfs_devices = <number_of_nfs_devices>

    # possible keys for export nfs devices:
    export_server = <nfs_server_name>
    export_devices = <number_of_export_devices>

    # possible keys for iso nfs devices:
    iso_server = <nfs_server_name>
    iso_devices = <number_of_iso_devices>

    # possible keys for iscsi devices:
    iscsi_server = <iscsi_server_name>
    iscsi_devices = <number_of_iscsi_devices>
    devices_capacity = <devices_capacity>

    # possible keys for local
    local_devices = <device_path>
    local_server = <host_name> # optional, default is first vds server

