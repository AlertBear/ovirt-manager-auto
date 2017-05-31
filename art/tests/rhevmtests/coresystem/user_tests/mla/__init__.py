from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd

from rhevmtests.coresystem.user_tests.mla import config


def setup_package():
    config.MASTER_STORAGE = ll_sd.get_master_storage_domain_name(
        config.DC_NAME[0]
    )
