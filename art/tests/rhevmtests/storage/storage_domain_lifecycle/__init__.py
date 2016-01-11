import config


def setup_package():
    from rhevmtests.storage import helpers as storage_helpers
    config.FIRST_HOST = config.HOSTS[0]
    storage_helpers.storage_cleanup()
