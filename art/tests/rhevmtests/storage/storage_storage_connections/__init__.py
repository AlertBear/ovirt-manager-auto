from rhevmtests.storage.storage_storage_connections import config
from art.rhevm_api.tests_lib.low_level import hosts


def setup_package():
    config.HOST_FOR_MOUNT = config.HOSTS[1]
    config.HOST_FOR_MOUNT_IP = hosts.getHostIP(config.HOST_FOR_MOUNT)
    config.HOSTS_FOR_TEST = config.HOSTS[:]
    config.HOSTS_FOR_TEST.remove(config.HOST_FOR_MOUNT)
