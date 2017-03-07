import config
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
)


def setup_package():
    config.HOST_FOR_MOUNT = config.HOSTS[-1]
    config.HOST_FOR_MOUNT_IP = ll_hosts.get_host_ip(config.HOST_FOR_MOUNT)
    config.HOSTS_FOR_TEST = config.HOSTS[:]
    config.HOSTS_FOR_TEST.remove(config.HOST_FOR_MOUNT)

    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()

    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    config.CONNECTIONS.append(config.ISCSI_STORAGE_ENTRIES.copy())
    # After each test, we logout from all the targets by looping through
    # CONNECTIONS. Add the default target/ip so the host will also logout
    # from it
    config.CONNECTIONS.append({
        'lun_address': config.UNUSED_LUN_ADDRESSES[0],
        'lun_target':  config.UNUSED_LUN_TARGETS[0],
    })
