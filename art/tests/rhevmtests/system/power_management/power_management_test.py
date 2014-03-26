"""
Power Management test
"""

from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.tools import tcms
from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.high_level import hosts
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import events
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.high_level import storagedomains as SD
from rhevmtests.system.power_management import config
import logging
from art.test_handler.exceptions import HostException, VMException,\
    StorageDomainException
from art.rhevm_api.utils import storage_api
from art.core_api.apis_utils import getDS


Options = getDS('Options')
Option = getDS('Option')

HOST_WITH_PM = config.HOSTS[0]
HOST_1 = config.HOSTS[1]
HOST_2 = config.HOSTS[2]
SIZE = 2147483648
NIC = 'nic1'
VM_DESCRIPTION = 'test_vm'
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
cluster_proxy_event = '\"Host {0} from cluster {1} was chosen as a proxy to' \
                      ' execute Start command on Host {2}\"'
data_center_proxy_event = '\"Host {0} from data center {1} was chosen as' \
                          ' a proxy to execute Start command on Host {2}\"'
host_restart_event = '\"Host ' + HOST_WITH_PM + ' was restarted by admin\"'
logger = logging.getLogger(__name__)


########################################################################
#                             Test Cases                               #
########################################################################


def _create_vm(vm_name, highly_available):
    sd_name = storagedomains.getDCStorages(config.DC_NAME[0], False)[0].name
    if not vms.createVm(True, vmDescription=VM_DESCRIPTION, vmName=vm_name,
                        cluster=config.CLUSTER_NAME[0],
                        type=config.VM_TYPE, highly_available=highly_available,
                        placement_affinity=config.MIGRATABLE,
                        placement_host=HOST_WITH_PM, size=SIZE,
                        volumeFormat=config.FORMAT, storageDomainName=sd_name,
                        nic=NIC, network=config.MGMT_BRIDGE, start='true'):
            raise VMException("cannot create vm with high availability"
                              " on host: %s" % HOST_WITH_PM)


def _waitForHostPmOperation():
    if not ll_hosts.waitForHostPmOperation(
            host=HOST_WITH_PM,
            vdc_password=config.VDC_ROOT_PASSWORD,
            vdc=config.VDC_HOST,
            dbuser=config.DB_ENGINE_USER,
            dbname=config.DB_ENGINE_NAME,
            dbpassword=config.DB_ENGINE_PASSWORD,
            product=config.PRODUCT_NAME):
        raise HostException("cannot get last PM operation time for host: %s" %
                            HOST_WITH_PM)


def _fence_host(positive, fence_type):
    _waitForHostPmOperation()
    if not ll_hosts.fenceHost(positive=positive, host=HOST_WITH_PM,
                              fence_type=fence_type):
        raise HostException("Cannot %s host: %s using power management" %
                            (fence_type, HOST_WITH_PM))
    _waitForHostPmOperation()


def _move_host_to_up(host):
    if not ll_hosts.isHostUp(True, host=host):
        if not ll_hosts.activateHost(True, host=host):
            raise HostException("cannot activate host: %s" % host)


def _move_host_to_maintenance(host):
    if not hosts.deactivate_host_if_up(host=host):
        raise HostException("Cannot put host: %s to maintenance" %
                            host)


def _move_host_to_non_operational(host):
    master_domain_ip = SD.get_master_storage_domain_ip(config.DC_NAME[0])
    if not (storage_api.blockOutgoingConnection(source=host,
                                                userName=config.HOSTS_USER,
                                                password=config.HOSTS_PW,
                                                dest=master_domain_ip) and
            storage_api.blockIncomingConnection(source=host,
                                                userName=config.HOSTS_USER,
                                                password=config.HOSTS_PW,
                                                dest=master_domain_ip)):
        raise StorageDomainException("Cannot move host: %s to non-operational"
                                     " state by blocking it's connection to"
                                     " master storage domain" % host)
    ll_hosts.waitForHostsStates(True, host, config.HOST_STATE_NONOP)


def _unblock_connection_of_host_to_storage(host=None):
    master_domain_ip = SD.get_master_storage_domain_ip(config.DC_NAME[0])
    if not (storage_api.unblockOutgoingConnection(
            source=host,
            userName=config.HOSTS_USER,
            password=config.HOSTS_PW,
            dest=master_domain_ip) and storage_api.unblockIncomingConnection(
            source=host,
            userName=config.HOSTS_USER,
            password=config.HOSTS_PW,
            dest=master_domain_ip)):
        raise StorageDomainException("Cannot connect host: %s back to "
                                     "master storage domain" % host)


def _add_power_management(host=None, **kwargs):
    hosts.add_power_management(host=host, pm_type=config.PM1_TYPE,
                               pm_address=config.PM1_ADDRESS,
                               pm_user=config.PM1_USER,
                               pm_password=config.PM1_PASS, **kwargs)


class TestWithHighAvailableVm(TestCase):
    """
    Base test class for tests with high available vm
    """

    vm_ha_name = 'vm_ha'
    vm2_name = 'vm_2'

    __test__ = False

    @classmethod
    def setup_class(cls):
        _move_host_to_up(HOST_WITH_PM)
        _move_host_to_up(HOST_1)
        _add_power_management(HOST_WITH_PM)
        logger.info("Creating a vm with high availability, disk and nic on"
                    " host: %s", HOST_WITH_PM)
        _create_vm(vm_name=cls.vm_ha_name, highly_available='true')
        logger.info("Creating a vm with default parameters, disk and nic on"
                    " host: %s", HOST_WITH_PM)
        _create_vm(vm_name=cls.vm2_name, highly_available=None)

    @classmethod
    def teardown_class(cls):
        _move_host_to_up(HOST_WITH_PM)
        _move_host_to_up(HOST_1)
        logger.info("Removing power management from host: %s", HOST_WITH_PM)
        hosts.remove_power_management(host=HOST_WITH_PM,
                                      pm_type=config.PM1_TYPE)
        logger.info("Removing vms: %s, %s", cls.vm_ha_name, cls.vm2_name)
        if not vms.removeVm(True, vm=cls.vm_ha_name, stopVM='true'):
            raise VMException("cannot remove vm: %s" % cls.vm_ha_name)
        if not vms.removeVm(True, vm=cls.vm2_name, stopVM='true'):
            raise VMException("cannot remove vm: %s" % cls.vm2_name)


class TestPMWithBadParameters(TestCase):

    __test__ = False

    @classmethod
    def setup_class(cls):
        _move_host_to_up(HOST_WITH_PM)

    @classmethod
    def teardown_class(cls):
        if not hosts.remove_power_management(host=HOST_WITH_PM,
                                             pm_type=config.PM_TYPE_DEFAULT):
            hosts.remove_power_management(host=HOST_WITH_PM,
                                          pm_type=config.PM1_TYPE)
        _move_host_to_up(HOST_WITH_PM)


class TestFenceOnHost(TestCase):

    __test__ = False

    up = False
    maintenance = False
    non_responsive = False

    @classmethod
    def setup_class(cls):
        _add_power_management(HOST_WITH_PM)
        if cls.up:
            _move_host_to_up(HOST_WITH_PM)
        elif cls.maintenance:
            _move_host_to_maintenance(HOST_WITH_PM)

    @classmethod
    def teardown_class(cls):
        _move_host_to_up(HOST_WITH_PM)
        logger.info("Removing power management from host: %s", HOST_WITH_PM)
        hosts.remove_power_management(host=HOST_WITH_PM,
                                      pm_type=config.PM1_TYPE)


class TestFenceHostWithTwoPMAgents(TestCase):

    __test__ = False

    pm1_address = config.PM1_ADDRESS
    pm2_address = config.PM2_ADDRESS

    @classmethod
    def setup_class(cls):

        pmOptions = Options()
        op = Option(name='port', value=config.PM2_SLOT)
        pmOptions.add_option(op)
        if config.COMP_VERSION >= '3.5':
            _move_host_to_up(HOST_WITH_PM)
            logger.info("Set two power management agents on host: %s",
                        HOST_WITH_PM)
            if not ll_hosts.updateHost(True, host=HOST_WITH_PM, pm='true',
                                       pm_proxies=['cluster', 'dc'],
                                       agents=[(config.PM1_TYPE,
                                                cls.pm1_address,
                                                config.PM1_USER,
                                                config.PM1_PASS,
                                                None, False, 1),
                                               (config.PM2_TYPE,
                                                cls.pm2_address,
                                                config.PM2_USER,
                                                config.PM2_PASS,
                                                pmOptions, False, 2)]):
                raise HostException("adding two power management agents to "
                                    "host %s failed" % HOST_WITH_PM)

    @classmethod
    def teardown_class(cls):
        if config.COMP_VERSION >= '3.5':
            if not hosts.remove_power_management(host=HOST_WITH_PM,
                                                 pm_type=config.PM2_TYPE):
                hosts.remove_power_management(host=HOST_WITH_PM,
                                              pm_type=config.PM1_TYPE)
            _move_host_to_up(HOST_WITH_PM)


class TestFenceProxySelection(TestCase):

    __test__ = False

    hosts_state = {HOST_1: config.HOST_STATE_UP, HOST_2: config.HOST_STATE_UP}
    pm_proxies = ['cluster', 'dc']

    @classmethod
    def setup_class(cls):
        _move_host_to_up(HOST_WITH_PM)
        _add_power_management(HOST_WITH_PM, pm_proxies=cls.pm_proxies)
        for host in cls.hosts_state:
            if cls.hosts_state[host] == config.HOST_STATE_UP:
                _move_host_to_up(host)
            elif cls.hosts_state[host] == config.HOST_STATE_DOWN:
                _move_host_to_maintenance(host)
            else:
                _move_host_to_non_operational(host)

    @classmethod
    def teardown_class(cls):
        for host in cls.hosts_state:
            if cls.hosts_state[host] == config.HOST_STATE_NONOP:
                _unblock_connection_of_host_to_storage(host)
            _move_host_to_up(host)
        _move_host_to_up(HOST_WITH_PM)
        logger.info("Removing power management from host: %s", HOST_WITH_PM)
        hosts.remove_power_management(host=HOST_WITH_PM,
                                      pm_type=config.PM1_TYPE)


class T01AddPMWithNoPassword(TestPMWithBadParameters):

    __test__ = True

    @tcms('3480', '356456')
    def test_add_power_management_with_no_password(self):
        self.assertRaises(HostException, hosts.add_power_management,
                          host=HOST_WITH_PM, pm_type=config.PM1_TYPE,
                          pm_address=config.PM1_ADDRESS,
                          pm_user=config.PM1_USER, pm_password='')


class T02AddPMWithNoUsername(TestPMWithBadParameters):

    __test__ = True

    @tcms('3480', '356459')
    def test_add_power_management_with_no_username(self):
        self.assertRaises(HostException, hosts.add_power_management,
                          host=HOST_WITH_PM, pm_type=config.PM1_TYPE,
                          pm_address=config.PM1_ADDRESS, pm_user='',
                          pm_password=config.PM1_PASS)


class T03AddPMWithNoAddress(TestPMWithBadParameters):

    __test__ = True

    @tcms('3480', '356458')
    def test_add_power_management_with_no_address(self):
        self.assertRaises(HostException, hosts.add_power_management,
                          host=HOST_WITH_PM, pm_type=config.PM1_TYPE,
                          pm_address='', pm_user=config.PM1_USER,
                          pm_password=config.PM1_PASS)


class T04AddPMWithInvalidType(TestPMWithBadParameters):

    __test__ = True

    invalid_type = 'invalid_type'

    @tcms('3480', '356458')
    def test_add_power_management_with_invalid_type(self):
        self.assertRaises(HostException, hosts.add_power_management,
                          host=HOST_WITH_PM, pm_type=self.invalid_type,
                          pm_address=config.PM1_ADDRESS,
                          pm_user=config.PM1_USER, pm_password=config.PM1_PASS)


class T05FenceHostWithHighAvailableVm(TestWithHighAvailableVm):

    __test__ = True

    @tcms('9988', '289119')
    def test_fence_host_with_high_available_vm(self):
        _fence_host(True, fence_type=config.FENCE_RESTART)
        if not vms.waitForVmsStates(True, names=self.vm_ha_name):
            raise VMException("vm: %s didn't migrate and is down" %
                              self.vm_ha_name)
        if not vms.waitForVmsStates(True, names=self.vm2_name,
                                    states=config.VM_STATE_DOWN):
            raise VMException("vm: %s should be down after host: %s restart " %
                              (self.vm2_name, HOST_WITH_PM))


class T06HostInNonResponsiveStatWithHighAvailableVM(TestWithHighAvailableVm):

    __test__ = True

    service_network = 'network'
    stop_command = 'stop'

    @tcms('9988', '289120')
    def test_host_in_non_responsive_state_with_high_available_vm(self):
        self.assertTrue(ll_hosts.runDelayedControlService(
            True, host=HOST_WITH_PM, host_user=config.HOSTS_USER,
            host_passwd=config.HOSTS_PW, service=self.service_network,
            command=self.stop_command))
        self.assertTrue(ll_hosts.waitForHostsStates(
            True, names=HOST_WITH_PM, states=config.HOST_STATE_NON_RES))
        self.assertTrue(ll_hosts.waitForHostsStates(
            True, names=HOST_WITH_PM, states=config.HOST_STATE_UP))
        if not vms.waitForVmsStates(True, names=self.vm_ha_name):
            raise VMException("vm: %s didn't migrate and is down" %
                              self.vm_ha_name)
        if not vms.waitForVmsStates(True, names=self.vm2_name,
                                    states=config.VM_STATE_DOWN):
            raise VMException("vm: %s should be down after host: %s"
                              " was at non-responsive state " %
                              (self.vm2_name, HOST_WITH_PM))


class T07StartHostInUpState(TestFenceOnHost):

    __test__ = True

    up = True

    @tcms('3480', '79327')
    def test_start_host_in_up_state(self):
        _fence_host(False, config.FENCE_START)


class T08StopThenStartHostInMaintenance(TestFenceOnHost):

    __test__ = True

    maintenance = True

    @tcms('3480', '79329')
    def test_1_stop_host_in_maintenance(self):
        _fence_host(True, config.FENCE_STOP)

    @tcms('3480', '286195')
    def test_2_start_host_in_down_state(self):
        _fence_host(True, config.FENCE_START)


class T09RestartHostInUpState(TestFenceOnHost):

    __test__ = True

    up = True

    @tcms('3480', '79332')
    def test_restart_host_in_up_state(self):
        _fence_host(True, config.FENCE_RESTART)


class T10RestartHostInMaintenance(TestFenceOnHost):

    __test__ = True

    maintenance = True

    @tcms('3480', '79334')
    def test_restart_host_in_maintenance(self):
        _fence_host(True, config.FENCE_RESTART)


class T11NoFallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):

    __test__ = (config.COMP_VERSION >= '3.5')

    pm2_address = 'blabla.blibli.com'

    @tcms('8177', '235276')
    def test_no_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T12FallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):

    __test__ = (config.COMP_VERSION >= '3.5')

    pm1_address = 'blabla.blibli.com'

    @tcms('8177', '235277')
    def test_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T13ProxyChosenFromCluster(TestFenceProxySelection):
    """
    Tests default proxy selection: from same cluster as host to fence
    """
    __test__ = False

    event = cluster_proxy_event.format(HOST_1, config.CLUSTER_NAME[0],
                                       HOST_WITH_PM)

    @tcms('8173', '234134')
    def test_proxy_chosen_from_cluster(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.searchForRecentEvent(True, win_start_query=self.event,
                                           query=host_restart_event,
                                           expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)


class T14ProxyChosenFromDataCenter(TestFenceProxySelection):
    """
    Tests proxy selection when DC is priority
    """

    __test__ = False  # TODO: adjust case setup for test

    event = data_center_proxy_event.format(HOST_2, config.DC_NAME[0],
                                           HOST_WITH_PM)
    pm_proxies = ['dc', 'cluster']

    def test_proxy_chosen_from_data_center(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.searchForRecentEvent(True, win_start_query=self.event,
                                           query=host_restart_event,
                                           expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)


class T15ProxyChosenNonOperationalButConnective(TestFenceProxySelection):
    """
    Test that the host from the same cluster is chosen even when
    non-operational but still connective
    """

    __test__ = False

    hosts_state = {HOST_1: config.HOST_STATE_NONOP,
                   HOST_2: config.HOST_STATE_UP}
    event = cluster_proxy_event.format(HOST_1, config.CLUSTER_NAME[0],
                                       HOST_WITH_PM)

    def test_proxy_chosen_non_operational_but_connective(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.searchForRecentEvent(True, win_start_query=self.event,
                                           query=host_restart_event,
                                           expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)


class T16ProxyChosenFromSecondClusterAsFallback(TestFenceProxySelection):
    """
    Test proxy selection when priority is (cluster, dc) and host in cluster
    is non_operational.
    expected result: host in the second cluster in the dc is chosen as proxy
    """

    # this test case requires the host in the cluster to be non connective
    # only then the host from DC will be chosen as proxy. should implement
    # with a host with pm as the host in cluster, to handle it's connectivity
    # easily.
    # TODO: add another host with pm to this test to allow further test cases

    __test__ = False

    hosts_state = {HOST_1: config.HOST_STATE_NONOP,
                   HOST_2: config.HOST_STATE_UP}

    event = data_center_proxy_event.format(HOST_2, config.DC_NAME[0],
                                           HOST_WITH_PM)

    def test_proxy_chosen_from_second_cluster_as_fallback(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.searchForRecentEvent(True, win_start_query=self.event,
                                           query=host_restart_event,
                                           expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)
