def setup_package():
    import rhevmtests.storage.helpers as storage_helpers
    storage_helpers.rhevm_helpers.storage_cleanup()
