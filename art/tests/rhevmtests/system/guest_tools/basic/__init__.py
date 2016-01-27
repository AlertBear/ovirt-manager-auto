from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sds
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dcs,
    storagedomains as hl_sds,
)
from rhevmtests.system.guest_tools import config


def setup_package():
    if not config.GOLDEN_ENV:
        hl_dcs.build_setup(
            config.PARAMETERS, config.PARAMETERS,
            config.STORAGE_TYPE, config.TEST_NAME
        )
        ll_sds.importStorageDomain(
            True, type='export',
            storage_type='nfs',
            address=config.EXPORT_DOMAIN_ADDRESS,
            host=config.HOSTS[0],
            path=config.EXPORT_DOMAIN_PATH,
            clean_export_domain_metadata=True
        )
        ll_sds.attachStorageDomain(
            True, config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
        ll_sds.activateStorageDomain(
            True, config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
        ll_sds.importStorageDomain(
            True,
            type='iso',
            storage_type='nfs',
            address=config.ISO_DOMAIN_ADDRESS,
            host=config.HOSTS[0],
            path=config.ISO_DOMAIN_PATH
        )
    ll_sds.attachStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )
    ll_sds.activateStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )


def teardown_package():
    hl_sds.detach_and_deactivate_domain(
        datacenter=config.DC_NAME[0], storagedomain=config.ISO_DOMAIN_NAME
    )
    if not config.GOLDEN_ENV:
        ll_sds.removeStorageDomain(
            True, storagedomain=config.ISO_DOMAIN_NAME,
            host=config.HOSTS[0], format='False'
        )
        hl_sds.detach_and_deactivate_domain(
            config.DC_NAME[0], config.EXPORT_STORAGE_DOMAIN
        )
        ll_sds.removeStorageDomain(
            True, storagedomain=config.EXPORT_STORAGE_DOMAIN,
            host=config.HOSTS[0], format='False'
        )
        hl_dcs.clean_datacenter(True, config.DC_NAME[0])
