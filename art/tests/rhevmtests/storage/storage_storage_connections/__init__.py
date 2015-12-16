from rhevmtests.storage.storage_storage_connections import config
from art.rhevm_api.tests_lib.low_level import hosts


def setup_package():
    config.HOST_FOR_MOUNT = config.HOSTS[1]
    config.HOST_FOR_MOUNT_IP = hosts.getHostIP(config.HOST_FOR_MOUNT)
    config.HOSTS_FOR_TEST = config.HOSTS[:]
    config.HOSTS_FOR_TEST.remove(config.HOST_FOR_MOUNT)

    if config.GOLDEN_ENV:
        config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
        config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
        # After each test, we logout from all the targets by looping through
        # CONNECTIONS. Add the default target/ip so the host will also logout
        # from it
        config.CONNECTIONS.append({
            'lun_address': config.UNUSED_LUN_ADDRESSES[0],
            'lun_target':  config.UNUSED_LUN_TARGETS[0],
        })

        config.DOMAIN_ADDRESSES = config.UNUSED_DATA_DOMAIN_ADDRESSES[0:1]
        config.DOMAIN_PATHS = config.UNUSED_DATA_DOMAIN_PATHS[0:1]
        config.EXTRA_DOMAIN_ADDRESSES = config.UNUSED_DATA_DOMAIN_ADDRESSES[1:]
        config.EXTRA_DOMAIN_PATHS = config.UNUSED_DATA_DOMAIN_PATHS[1:]
    else:
        if config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
            config.CONNECTIONS.append({
                'lun_address': config.PARAMETERS.as_list('lun_address')[0],
                'lun_target': config.PARAMETERS.as_list('lun_target')[0],
                'lun_port': int(config.PARAMETERS.get('lun_port', 3260)),
                'luns': config.PARAMETERS.as_list('lun')})
            config.CONNECTIONS.append({
                'lun_address': config.PARAMETERS.as_list(
                    'another_lun_address'
                )[0],
                'lun_target': config.PARAMETERS.as_list(
                    'another_lun_target'
                )[0],
                'lun_port': int(config.PARAMETERS.get(
                    'another_lun_port', 3260
                )),
                'luns': config.PARAMETERS.as_list('another_lun')})

            config.PARAMETERS['lun'] = []
            config.PARAMETERS['lun_address'] = []
            config.PARAMETERS['lun_target'] = []
            config.PARAMETERS['lun_port'] = []

        if (
            config.STORAGE_TYPE == config.STORAGE_TYPE_NFS or
            config.STORAGE_TYPE.startswith('posixfs')
        ):
            config.DOMAIN_ADDRESSES = config.PARAMETERS.as_list(
                'data_domain_address'
            )[1:]
            config.DOMAIN_PATHS = config.PARAMETERS.as_list(
                'data_domain_path'
            )[1:]
            config.PARAMETERS[
                'data_domain_address'
            ] = config.PARAMETERS.as_list('data_domain_address')[0]
            config.PARAMETERS['data_domain_path'] = config.PARAMETERS.as_list(
                'data_domain_path'
            )[0]
            config.EXTRA_DOMAIN_ADDRESSES = config.PARAMETERS.as_list(
                'another_address'
            )
            config.EXTRA_DOMAIN_PATHS = config.PARAMETERS.as_list(
                'another_path'
            )
