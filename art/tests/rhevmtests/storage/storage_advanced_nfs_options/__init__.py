"""
https://tcms.engineering.redhat.com/plan/5849

Test suite for checking if setting advanced NFS options
(timeout, # retransmissions, NFS versions) works correctly

Test suite is valid only for RHEV-M 3.1+
"""
from art.rhevm_api.tests_lib.high_level import datacenters as hl_dc
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_st
from rhevmtests.storage.storage_advanced_nfs_options import config


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    if config.GOLDEN_ENV:
        assert hl_st.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME,
        )
    else:
        hl_dc.build_setup(config.PARAMETERS, config.STORAGE_CONF,
                          config.STORAGE_TYPE, basename=config.TESTNAME)


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    if config.GOLDEN_ENV:
        assert hl_st.attach_and_activate_domain(
            config.DATA_CENTER_NAME, config.EXPORT_DOMAIN_NAME,
        )
    else:
        hl_dc.clean_datacenter(True, config.DATA_CENTER_NAME)
