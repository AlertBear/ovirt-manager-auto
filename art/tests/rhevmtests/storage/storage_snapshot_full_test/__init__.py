"""
Storage live snapshot sanity package
"""
from art.rhevm_api.tests_lib.high_level import datacenters
from rhevmtests.storage.storage_snapshot_full_test import config


def setup_package():
    """
    Prepares environment
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)


def teardown_package():
    """
    Cleans the environment
    """
    if not config.GOLDEN_ENV:
        assert datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME,
            vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
