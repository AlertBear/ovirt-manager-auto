from art.rhevm_api.tests_lib.high_level import mac_pool as hl_mac_pool


def setup_package():
    # Update the Default mac pool object with mac range from mac broker
    hl_mac_pool.update_default_mac_pool()
