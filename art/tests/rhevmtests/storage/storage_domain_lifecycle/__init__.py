import config


def setup_package():
    import rhevmtests.helpers as rhevm_helpers
    config.FIRST_HOST = config.HOSTS[0]
    rhevm_helpers.storage_cleanup()
