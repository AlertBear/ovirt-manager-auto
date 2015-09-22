from rhevmtests.storage.storage_domain_lifecycle import config


def setup_package():
    config.FIRST_HOST = config.HOSTS[0]
