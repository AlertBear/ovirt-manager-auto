import logging

import config
import helpers
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr

logger = logging.getLogger(__name__)
ENUMS = helpers.ENUMS
NFS = config.STORAGE_TYPE_NFS


def setup_module():
    """Prepare extra host for testing"""
    status, hsm_host = ll_hosts.getAnyNonSPMHost(
        config.HOSTS, cluster_name=config.CLUSTER_NAME
    )
    assert status, "Unable to get a hsm from cluster %s" % config.CLUSTER_NAME
    host_name = hsm_host['hsmHost']
    host_ip = ll_hosts.getHostIP(host_name)
    config.HOST_FOR_30_DC = {'name': host_name, 'ip': host_ip}
    assert ll_hosts.deactivateHost(True, host_name)
    assert ll_hosts.removeHost(True, host_name)
    config.HOSTS.remove(host_name)


def teardown_module():
    """Adding host back to the previous DC"""
    host_ip = config.HOST_FOR_30_DC['ip']
    host_name = config.HOST_FOR_30_DC['name']
    try:
        logger.info(
            "Trying to deactivate and remove the host %s in case there was a "
            "problem with the test's tearDown function", host_ip,
        )
        if ll_hosts.getHostState(host_ip) == config.HOST_UP:
            ll_hosts.deactivateHost(True, host_ip)
        ll_hosts.removeHost(True, host_ip)
    except EntityNotFound:
        pass

    logger.info(
        "Attaching host %s with ip %s to cluster %s",
        host_name, host_ip, config.CLUSTER_NAME)
    assert ll_hosts.addHost(
        True, name=host_name, root_password=config.HOSTS_PW,
        cluster=config.CLUSTER_NAME, address=host_ip,
    )
    config.HOSTS.append(host_name)


@attr(tier=2)
class TestCase4831(helpers.TestCaseStandardOperations):
    """
    Tests if data center with NFS storage domains with custom NFS options works
    correctly. Performed operations:
     * moving vm to another storage domain
     * moving vm disk to another storage domain
     * migrating vm to another host
     * exporting template
     * switching SPM
     * reconstruction of master storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options

    **Author**: Katarzyna Jachim
    """
    __test__ = NFS in opts['storages']
    polarion_test_case = '4831'
    sd_1 = 'test_%s_1' % polarion_test_case
    sd_2 = 'test_%s_2' % polarion_test_case
    sd_exp = 'test_%s_exp' % polarion_test_case
    disk_1 = 'test_%s_disk_1' % polarion_test_case
    disk_2 = 'test_%s_disk_2' % polarion_test_case
    vm_1 = 'vm_%s_1' % polarion_test_case
    vm_2 = 'vm_%s_2' % polarion_test_case
    template = 'templ_%s' % polarion_test_case

    # Bugzilla history:
    # 1248035: VM migration: migration failed since vdsm failed to run VM...
    # 1254230: Operation of exporting template to Export domain gets stuck

    @classmethod
    def setup_class(cls):
        """Defining host to use"""
        cls.host_for_dc = config.HOST_FOR_30_DC['ip']
        super(TestCase4831, cls).setup_class()

    @polarion("RHEVM3-4831")
    def test_functionality_with_custom_nfs_options(self):
        """ Tests basic data center functionality with storage domain with
        custom NFS options
        """
        self.perform_standard_operations(
            self.vm_1, self.vm_2, self.disk_2, self.sd_2, self.template,
            self.sd_exp, config.DATA_CENTER_NAME)
