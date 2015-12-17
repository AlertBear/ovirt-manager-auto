from art.rhevm_api.utils import aaa
from art.rhevm_api.tests_lib.high_level import mac_pool as hl_mac_pool

from rhevmtests.system import config


LDAP = aaa.ADTLV(config.ENGINE_HOST, config.ENGINE)


def setup_package():
    # Install AAA extension properties
    LDAP.add()

    # Update the Default mac pool object with mac range from mac broker
    hl_mac_pool.update_default_mac_pool()


def teardown_package():
    # Wipe out AAA extension properties
    LDAP.remove()
