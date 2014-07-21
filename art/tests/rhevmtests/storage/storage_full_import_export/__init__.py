from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from rhevmtests.storage.storage_full_import_export import config


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    datacenters.build_setup(
        config=config.PARAMETERS, storage=config.PARAMETERS,
        storage_type=config.STORAGE_TYPE, basename=config.TESTNAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    storagedomains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)
