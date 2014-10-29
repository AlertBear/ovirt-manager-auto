from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd
from rhevmtests.storage.storage_full_import_export import config


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config=config.PARAMETERS, storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE, basename=config.TESTNAME)
    else:
        assert hl_sd.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_STORAGE_NAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if not config.GOLDEN_ENV:
        storagedomains.cleanDataCenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD)
    else:
        assert hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_STORAGE_NAME)
