"""
Power Management test
"""

from art.rhevm_api.tests_lib.low_level import vms
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase
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

HOST_WITH_PM = None  # Filled in setup_module
HOST_1 = None  # Filled in setup_module
HOST_2 = None  # Filled in setup_module
SIZE = 2147483648
NIC = 'nic1'
VM_DESCRIPTION = 'test_vm'
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
cluster_proxy_event = '\"Host {0} from cluster {1} was chosen as a proxy to' \
                      ' execute Start command on Host {2}\"'
data_center_proxy_event = '\"Host {0} from data center {1} was chosen as' \
                          ' a proxy to execute Start command on Host {2}\"'
host_restart_event = None  # Filled in setup_module
logger = logging.getLogger(__name__)


########################################################################
#                             Test Cases                               #
########################################################################


def setup_module():
    global HOST_WITH_PM, HOST_1, HOST_2, host_restart_event
    HOST_WITH_PM = config.HOSTS[0]
    HOST_1 = config.HOSTS[1]
    HOST_2 = config.HOSTS[2]
    host_restart_event = '\"Host %s was restarted by admin\"' % HOST_WITH_PM


def _create_vm(vm_name, highly_available):
    sd_name = storagedomains.getDCStorages(config.DC_NAME[0], False)[0].name
    if not vms.createVm(True, vmDescription=VM_DESCRIPTION, vmName=vm_name,
                        cluster=config.CLUSTER_NAME[0],
                        type=config.VM_TYPE, highly_available=highly_available,
                        placement_affinity=config.MIGRATABLE,
                        placement_host=HOST_WITH_PM, provisioned_size=SIZE,
                        volumeFormat=config.FORMAT, storageDomainName=sd_name,
                        nic=NIC, network=config.MGMT_BRIDGE, start='true'):
            raise VMException("cannot create vm with high availability"
                              " on host: %s" % HOST_WITH_PM)


def _waitForHostPmOperation():
    if not ll_hosts.waitForHostPmOperation(
        host=HOST_WITH_PM,
        engine=config.ENGINE,
    ):
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
    agent = {
        "agent_type": config.PM1_TYPE,
        "agent_address": config.PM1_ADDRESS,
        "agent_username": config.PM1_USER,
        "agent_password": config.PM1_PASS,
        "concurrent": False,
        "order": 1
    }
    return hosts.add_power_management(
        host_name=host, pm_agents=[agent], **kwargs
    )


@attr(tier=3, extra_reqs={'mgmt': True})
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
        if not _add_power_management(HOST_WITH_PM):
            raise HostException()
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
        hosts.remove_power_management(host_name=HOST_WITH_PM)
        logger.info("Removing vms: %s, %s", cls.vm_ha_name, cls.vm2_name)
        if not vms.removeVm(True, vm=cls.vm_ha_name, stopVM='true'):
            raise VMException("cannot remove vm: %s" % cls.vm_ha_name)
        if not vms.removeVm(True, vm=cls.vm2_name, stopVM='true'):
            raise VMException("cannot remove vm: %s" % cls.vm2_name)


@attr(tier=3, extra_reqs={'mgmt': True})
class TestPMWithBadParameters(TestCase):
    agent = {
        "agent_type": config.PM1_TYPE,
        "agent_address": config.PM1_ADDRESS,
        "agent_username": config.PM1_USER,
        "agent_password": config.PM1_PASS,
        "concurrent": False,
        "order": 1
    }
    t_agent = None
    bad_parameter = None

    @classmethod
    def setup_class(cls):
        cls.t_agent = dict(cls.agent)
        for key, value in cls.bad_parameter.iteritems():
            cls.t_agent[key] = value
        _move_host_to_up(HOST_WITH_PM)

    @classmethod
    def teardown_class(cls):
        hosts.remove_power_management(host_name=HOST_WITH_PM)
        _move_host_to_up(HOST_WITH_PM)


@attr(tier=3, extra_reqs={'fence': True})
class TestFenceOnHost(TestCase):

    __test__ = False

    up = False
    maintenance = False
    non_responsive = False

    @classmethod
    def setup_class(cls):
        if not _add_power_management(HOST_WITH_PM):
            raise HostException()
        if cls.up:
            _move_host_to_up(HOST_WITH_PM)
        elif cls.maintenance:
            _move_host_to_maintenance(HOST_WITH_PM)

    @classmethod
    def teardown_class(cls):
        _move_host_to_up(HOST_WITH_PM)
        logger.info("Removing power management from host: %s", HOST_WITH_PM)
        hosts.remove_power_management(host_name=HOST_WITH_PM)


@attr(tier=3, extra_reqs={'mgmt': True})
class TestFenceHostWithTwoPMAgents(TestCase):

    __test__ = False

    pm1_address = config.PM1_ADDRESS
    pm2_address = config.PM2_ADDRESS

    @classmethod
    def setup_class(cls):
        if config.COMP_VERSION >= '3.5':
            _move_host_to_up(HOST_WITH_PM)
            logger.info(
                "Set two power management agents on host: %s", HOST_WITH_PM
            )
            agent_1 = (
                config.PM1_TYPE,
                cls.pm1_address,
                config.PM1_USER,
                config.PM1_PASS,
                None, False, 1
            )
            agent_2 = (
                config.PM2_TYPE,
                cls.pm2_address,
                config.PM2_USER,
                config.PM2_PASS,
                {'port': config.PM2_SLOT},
                False, 2
            )
            agents = []
            for (
                agent_type,
                agent_address,
                agent_user,
                agent_password,
                agent_options,
                concurrent,
                order
            ) in (agent_1, agent_2):
                agent_d = {
                    "agent_type": agent_type,
                    "agent_address": agent_address,
                    "agent_username": agent_user,
                    "agent_password": agent_password,
                    "concurrent": concurrent,
                    "order": order,
                    "options": agent_options
                }
                agents.append(agent_d)

            if not hosts.add_power_management(
                host_name=HOST_WITH_PM,
                pm_agents=agents,
                pm_proxies=['cluster', 'dc']
            ):
                raise HostException(
                    "adding two power management agents to host %s failed" %
                    HOST_WITH_PM
                )

    @classmethod
    def teardown_class(cls):
        if config.COMP_VERSION >= '3.5':
            hosts.remove_power_management(host_name=HOST_WITH_PM)
            _move_host_to_up(HOST_WITH_PM)


@attr(tier=3, extra_reqs={'mgmt': True})
class TestFenceProxySelection(TestCase):

    __test__ = False

    hosts_state = None
    pm_proxies = ['cluster', 'dc']

    @classmethod
    def setup_class(cls):
        cls.hosts_state = {
            HOST_1: config.HOST_STATE_UP,
            HOST_2: config.HOST_STATE_UP,
        }
        _move_host_to_up(HOST_WITH_PM)
        if not _add_power_management(HOST_WITH_PM, pm_proxies=cls.pm_proxies):
            raise HostException()
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
        hosts.remove_power_management(host_name=HOST_WITH_PM)


class T01AddPMWithNoPassword(TestPMWithBadParameters):

    __test__ = True
    bad_parameter = {'agent_password': ''}

    @polarion("RHEVM3-8919")
    def test_add_power_management_with_no_password(self):
        self.assertFalse(
            hosts.add_power_management(
                host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
            )
        )


class T02AddPMWithNoUsername(TestPMWithBadParameters):

    __test__ = True
    bad_parameter = {'agent_username': ''}

    @polarion("RHEVM3-8917")
    def test_add_power_management_with_no_username(self):
        self.assertFalse(
            hosts.add_power_management(
                host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
            )
        )


class T03AddPMWithNoAddress(TestPMWithBadParameters):

    __test__ = True
    bad_parameter = {'agent_address': ''}

    @polarion("RHEVM3-8918")
    def test_add_power_management_with_no_address(self):
        self.assertFalse(
            hosts.add_power_management(
                host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
            )
        )


class T04AddPMWithInvalidType(TestPMWithBadParameters):

    __test__ = True
    bad_parameter = {'agent_type': 'invalid_type'}

    @polarion("RHEVM3-8916")
    def test_add_power_management_with_invalid_type(self):
        self.assertFalse(
            hosts.add_power_management(
                host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
            )
        )


class T05FenceHostWithHighAvailableVm(TestWithHighAvailableVm):

    __test__ = True

    @polarion("RHEVM3-12447")
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

    @polarion("RHEVM3-12448")
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

    @polarion("RHEVM3-8914")
    def test_start_host_in_up_state(self):
        _fence_host(False, config.FENCE_START)


class T08StopThenStartHostInMaintenance(TestFenceOnHost):

    __test__ = True

    maintenance = True

    @polarion("RHEVM3-8927")
    def test_1_stop_host_in_maintenance(self):
        _fence_host(True, config.FENCE_STOP)

    @polarion("RHEVM3-8920")
    def test_2_start_host_in_down_state(self):
        _fence_host(True, config.FENCE_START)


class T09RestartHostInUpState(TestFenceOnHost):

    __test__ = True

    up = True

    @polarion("RHEVM3-8925")
    def test_restart_host_in_up_state(self):
        _fence_host(True, config.FENCE_RESTART)


class T10RestartHostInMaintenance(TestFenceOnHost):

    __test__ = True

    maintenance = True

    @polarion("RHEVM3-8923")
    def test_restart_host_in_maintenance(self):
        _fence_host(True, config.FENCE_RESTART)


class T11NoFallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):

    __test__ = (config.COMP_VERSION >= '3.5')

    pm2_address = 'blabla.blibli.com'

    @polarion("RHEVM3-8930")
    def test_no_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T12FallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):

    __test__ = (config.COMP_VERSION >= '3.5')

    pm1_address = 'blabla.blibli.com'

    @polarion("RHEVM3-8929")
    def test_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T13ProxyChosenFromCluster(TestFenceProxySelection):
    """
    Tests default proxy selection: from same cluster as host to fence
    """
    __test__ = False

    event = None

    @classmethod
    def setup_class(cls):
        cls.event = cluster_proxy_event.format(
            HOST_1, config.CLUSTER_NAME[0], HOST_WITH_PM,
        )
        super(T13ProxyChosenFromCluster, cls).setup_class()

    @polarion("RHEVM3-9159")
    def test_proxy_chosen_from_cluster(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.search_for_recent_event(True, win_start_query=self.event,
                                              query=host_restart_event,
                                              expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)


class T14ProxyChosenFromDataCenter(TestFenceProxySelection):
    """
    Tests proxy selection when DC is priority
    """

    __test__ = False  # TODO: adjust case setup for test
    event = None
    pm_proxies = ['dc', 'cluster']

    @classmethod
    def setup_class(cls):
        cls.event = data_center_proxy_event.format(
            HOST_2, config.DC_NAME[0], HOST_WITH_PM,
        )
        super(T14ProxyChosenFromDataCenter, cls).setup_class()

    def test_proxy_chosen_from_data_center(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.search_for_recent_event(True, win_start_query=self.event,
                                              query=host_restart_event,
                                              expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)


class T15ProxyChosenNonOperationalButConnective(TestFenceProxySelection):
    """
    Test that the host from the same cluster is chosen even when
    non-operational but still connective
    """

    __test__ = False

    hosts_state = None
    event = None

    @classmethod
    def setup_class(cls):
        cls.hosts_state = {
            HOST_1: config.HOST_STATE_NONOP,
            HOST_2: config.HOST_STATE_UP,
        }
        cls.event = cluster_proxy_event.format(
            HOST_1, config.CLUSTER_NAME[0], HOST_WITH_PM,
        )
        super(T15ProxyChosenNonOperationalButConnective, cls).setup_class()

    def test_proxy_chosen_non_operational_but_connective(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.search_for_recent_event(True, win_start_query=self.event,
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

    hosts_state = None
    event = None

    @classmethod
    def setup_class(cls):
        cls.hosts_state = {
            HOST_1: config.HOST_STATE_NONOP,
            HOST_2: config.HOST_STATE_UP,
        }
        cls.event = data_center_proxy_event.format(
            HOST_2, config.DC_NAME[0], HOST_WITH_PM,
        )
        super(T16ProxyChosenFromSecondClusterAsFallback, cls).setup_class()

    def test_proxy_chosen_from_second_cluster_as_fallback(self):
        _fence_host(True, config.FENCE_RESTART)
        if not events.search_for_recent_event(True, win_start_query=self.event,
                                              query=host_restart_event,
                                              expected_count=1):
            raise HostException("Cannot fence host: %s" % HOST_WITH_PM)
