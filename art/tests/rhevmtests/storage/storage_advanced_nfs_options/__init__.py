"""
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_1_Storage_NFS_Options

Test suite for checking if setting advanced NFS options
(timeout, # retransmissions, NFS versions) works correctly

Test suite is valid only for RHEV-M 3.1+
"""
import config
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
)


def setup_package():
    """
    Deactivates the GE's export domain
    """
    import rhevmtests.helpers as rhevm_helpers
    rhevm_helpers.storage_cleanup()
    assert hl_sd.detach_and_deactivate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME,
    )


def teardown_package():
    """
    Re-activates the GE's export domain
    """
    assert hl_sd.attach_and_activate_domain(
        config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME,
    )
