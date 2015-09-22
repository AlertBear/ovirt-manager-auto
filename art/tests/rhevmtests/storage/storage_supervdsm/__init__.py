from rhevmtests.storage.storage_supervdsm import config


def setup_package():
    config.FIRST_HOST = config.HOSTS[0]
