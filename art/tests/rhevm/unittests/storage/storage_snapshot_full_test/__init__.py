"""
Storage live snapshot sanity package
"""
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains


def setup_package():
    """
    Prepares environment
    """
    import config
    datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                            config.STORAGE_TYPE, config.TESTNAME)


def teardown_package():
    """
    Cleans the environment
    """
    import config
    assert storagedomains.cleanDataCenter(True, config.DC_NAME,
                                          vdc=config.VDC,
                                          vdc_password=config.VDC_PASSWORD)
