"""
DataCenter Networks feature test
"""

from art.test_handler.exceptions import DataCenterException
from art.rhevm_api.tests_lib.low_level.datacenters import addDataCenter, \
    removeDataCenter


#################################################


def setup_package():
    """
    Prepare environment
    """
    import config
    if not (addDataCenter(positive=True, name=config.DC_NAME,
                          storage_type=config.STORAGE_TYPE,
                          version=config.VERSION, local=False) and
            addDataCenter(positive=True, name=config.DC_NAME2,
                          storage_type=config.STORAGE_TYPE,
                          version=config.VERSION, local=False)):
        raise DataCenterException("Cannot create DCs")


def teardown_package():
    """
    Cleans environment
    """
    import config
    if not (removeDataCenter(positive=True, datacenter=config.DC_NAME) and
            removeDataCenter(positive=True, datacenter=config.DC_NAME2)):
        raise DataCenterException("Cannot remove DCs")
