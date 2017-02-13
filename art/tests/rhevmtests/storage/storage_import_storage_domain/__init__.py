def setup_package():
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()


def teardown_package():
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()
