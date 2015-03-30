"""
https://tcms.engineering.redhat.com/plan/5849

Test suite for checking if setting advanced NFS options
(timeout, # retransmissions, NFS versions) works correctly

Test suite is valid only for RHEV-M 3.1+
"""
from art.test_handler import exceptions
from art.rhevm_api.tests_lib.high_level import datacenters as hl_dc
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts

from rhevmtests.storage.storage_advanced_nfs_options import config


def setup_module():
    """ creates datacenter, adds hosts, clusters, storages according to
    the config file
    """
    hl_dc.build_setup(config.PARAMETERS, config.STORAGE_CONF,
                      config.STORAGE_TYPE, basename=config.TESTNAME)

    if len(config.HOSTS) > 1:
        # we need one host for 3.0 data center
        if not ll_hosts.deactivateHost(True, config.HOST_FOR_30_DC):
            raise exceptions.HostException(
                "Cannot deactivate host for 3.0 dc!")
        if not ll_hosts.removeHost(True, config.HOST_FOR_30_DC):
            raise exceptions.HostException("Cannot remove host for 3.0 dc!")

    ll_st.waitForStorageDomainStatus(
        True, config.DATA_CENTER_NAME, 'nfs_0', 'active')


def teardown_module():
    """ removes created datacenter, storages etc.
    """
    hl_dc.clean_datacenter(True, config.DATA_CENTER_NAME)
