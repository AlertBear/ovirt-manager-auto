"""
Storage live snapshot sanity package
"""
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from rhevmtests.storage.storage_snapshot_full_test import config


def setup_package():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)
    else:
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_STORAGE_NAME)


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        assert storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME,
                                              vdc=config.VDC,
                                              vdc_password=config.VDC_PASSWORD)
    else:
        assert hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_STORAGE_NAME)
