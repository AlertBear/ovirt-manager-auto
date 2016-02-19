from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sds
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sds
from rhevmtests.system.wgt import config


def setup_package():
    ll_sds.attachStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )
    ll_sds.activateStorageDomain(
        True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
    )


def teardown_package():
    hl_sds.detach_and_deactivate_domain(
        datacenter=config.DC_NAME[0],
        domain=config.ISO_DOMAIN_NAME,
    )
