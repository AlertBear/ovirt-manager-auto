from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains
from rhevmtests.system.guest_tools import config


def setup_package():
    if not config.GOLDEN_ENV:
        datacenters.build_setup(
            config.PARAMETERS, config.PARAMETERS,
            config.STORAGE_TYPE, config.TEST_NAME
        )
        storagedomains.importStorageDomain(
            True, type='export',
            storage_type='nfs',
            address=config.EXPORT_DOMAIN_ADDRESS,
            host=config.HOSTS[0],
            path=config.EXPORT_DOMAIN_PATH,
            clean_export_domain_metadata=True
        )
        storagedomains.attachStorageDomain(
            True, config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
        storagedomains.activateStorageDomain(
            True, config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
    storagedomains.importStorageDomain(
        True,
        type='iso',
        storage_type='nfs',
        address=config.ISO_DOMAIN_ADDRESS,
        host=config.HOSTS[0],
        path=config.ISO_DOMAIN_PATH
    )
    storagedomains.attachStorageDomain(
        True, config.DC_NAME[0], config.ISO_STORAGE_DOMAIN
    )
    storagedomains.activateStorageDomain(
        True, config.DC_NAME[0], config.ISO_STORAGE_DOMAIN
    )


def teardown_package():
    storagedomains.deactivateStorageDomain(
        True, datacenter=config.DC_NAME[0],
        storagedomain=config.ISO_STORAGE_DOMAIN
    )
    storagedomains.detachStorageDomain(
        True, datacenter=config.DC_NAME[0],
        storagedomain=config.ISO_STORAGE_DOMAIN
    )
    storagedomains.removeStorageDomain(
        True, storagedomain=config.ISO_STORAGE_DOMAIN,
        host=config.HOSTS[0], format='False'
    )
    if not config.GOLDEN_ENV:
        storagedomains.deactivateStorageDomain(
            True, datacenter=config.DC_NAME[0],
            storagedomain=config.EXPORT_STORAGE_DOMAIN
        )
        storagedomains.detachStorageDomain(
            True, datacenter=config.DC_NAME[0],
            storagedomain=config.EXPORT_STORAGE_DOMAIN
        )
        storagedomains.removeStorageDomain(
            True, storagedomain=config.EXPORT_STORAGE_DOMAIN,
            host=config.HOSTS[0], format='False'
        )
        datacenters.clean_datacenter(True, config.DC_NAME[0])
