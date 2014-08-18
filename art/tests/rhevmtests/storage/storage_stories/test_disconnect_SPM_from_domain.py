import logging
from art.unittest_lib import StorageTest as TestCase, attr
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.high_level import datacenters
from utilities.utils import getIpAddressByHostName
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
import art.rhevm_api.utils.storage_api as st_api
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.utils.iptables as ip_action

from art.test_handler import exceptions
from sys import modules


import config

TCMS_PLAN_ID = '6458'
logger = logging.getLogger(__name__)
dc_type = config.STORAGE_TYPE
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]

LOGGER = logging.getLogger(__name__)

DC_API = get_api('data_center', 'datacenters')
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
SD_API = get_api('storage_domain', 'storagedomains')
CLUSTER_API = get_api('cluster', 'clusters')

GB = config.GB
TEN_GB = 10 * GB


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file

    for this TCMS plan we need 3 SD but only one of them should be created on
    setup. the other two SDs will be created manually in the test cases.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only one lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
        domain_path = config.PATH
        config.PARAMETERS['data_domain_path'] = [domain_path[0]]
    else:
        luns = config.LUNS
        config.PARAMETERS['lun'] = [luns[0]]

    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)

    datacenters.build_setup(config=config.PARAMETERS,
                            storage=config.PARAMETERS,
                            storage_type=config.STORAGE_TYPE,
                            basename=config.TESTNAME)

    if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
        config.PARAMETERS['data_domain_path'] = domain_path
    else:
        config.PARAMETERS['lun'] = luns


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    ll_st_domains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_test_case = None
    master_domain_ip = None
    engine_ip = None

    @classmethod
    def setup_class(cls):
        logger.info("DC name : %s", config.DATA_CENTER_NAME)

        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert found
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, cls.master_domain_ip = ll_st_domains.getDomainAddress(
            True, master_domain)
        assert found
        cls.master_domain_ip = cls.master_domain_ip['address']
        logger.info("Master domain ip found : %s", cls.master_domain_ip)

        cls.engine_ip = getIpAddressByHostName(config.VDC)


@attr(tier=0)
class TestCase174611(BaseTestCase):
    """
    * Block connection from one host to storage server.
    * Wait until host goes to non-operational.
    * Unblock connection.
    * Check that the host is UP again.
    https://tcms.engineering.redhat.com/case/174611/?from_plan=6458
    """
    __test__ = True
    tcms_test_case = '174611'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    @bz('842257')
    def test_disconnect_host_from_storage(self):
        """
        Block connection from one host to storage server.
        Wait until host goes to non-operational.
        Unblock connection.
        Check that the host is UP again.
        """
        ip_action.block_and_wait(config.FIRST_HOST, config.HOSTS_USER,
                                 config.HOSTS_PW, self.master_domain_ip,
                                 config.FIRST_HOST)

        ip_action.unblock_and_wait(config.FIRST_HOST, config.HOSTS_USER,
                                   config.HOSTS_PW,
                                   self.master_domain_ip,
                                   config.FIRST_HOST)

    @classmethod
    def teardown_class(cls):
        """
        unblock all connections that were blocked during the test
        """
        logger.info('Unblocking connections')
        try:
            st_api.unblockOutgoingConnection(config.FIRST_HOST,
                                             config.HOSTS_USER,
                                             config.HOSTS_PW,
                                             cls.master_domain_ip)
        except exceptions.NetworkException, msg:
            logging.info("Connection already unblocked. reason: %s", msg)
