from art.rhevm_api.tests_lib.high_level import datacenters
from rhevmtests.storage.storage_full_import_export import config


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE, basename=config.TESTNAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
