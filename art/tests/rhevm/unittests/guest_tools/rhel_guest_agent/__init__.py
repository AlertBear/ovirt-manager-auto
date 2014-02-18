from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains as h_sd
from art.rhevm_api.tests_lib.low_level import storagedomains


def setup_package():
    import config
    datacenters.build_setup(
        config.PARAMETERS, config.PARAMETERS,
        config.STORAGE_TYPE, config.TESTNAME)
    storagedomains.importStorageDomain(
        True, type='export',
        storage_type='nfs',
        address=config.EXPORT_DOMAIN_ADDRESS,
        host=config.VDS[0],
        path=config.EXPORT_DOMAIN_PATH)
    h_sd.attach_and_activate_domain(config.DATA_CENTER_NAME,
                                    config.EXPORT_STORAGE_DOMAIN)


def teardown_package():
    import config
    h_sd.remove_storage_domain(config.EXPORT_STORAGE_DOMAIN,
                               config.DATA_CENTER_NAME, config.VDS[0])
    storagedomains.cleanDataCenter(True, config.DATA_CENTER_NAME)
