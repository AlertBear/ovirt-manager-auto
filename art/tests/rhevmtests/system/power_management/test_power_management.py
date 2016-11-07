"""
Power Management test
"""
import pytest
import logging
from copy import copy
from rrmngmnt import Host, RootUser

from art.rhevm_api.tests_lib.low_level import (
    vms, hosts as ll_hosts, events, disks
)
from art.rhevm_api.tests_lib.high_level import hosts
from art.test_handler.tools import polarion, bz
from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow
from rhevmtests.helpers import get_pm_details

from rhevmtests.system.power_management import config

VDSM_PORT = "54321"
HOST_WITH_PM = None  # Filled in setup_module
HOST_WITH_PM_FQDN = None  # Filled in setup_module
HOST_1 = None  # Filled in setup_module
HOST_2 = None  # Filled in setup_module
SIZE = 10 * config.GB
VM_DESCRIPTION = 'test_vm'
ENGINE_LOG = '/var/log/ovirt-engine/engine.log'
fence_proxy_event = (
    '\"Executing power management start on Host {0} using Proxy Host {1}\"'
)
host_restart_event = None  # Filled in setup_module
logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def module_setup():
    """
    Prepare environment for Power Management tests
    """
    global HOST_WITH_PM, HOST_WITH_PM_FQDN, HOST_1, HOST_2, host_restart_event
    HOST_WITH_PM = config.HOSTS[0]
    HOST_WITH_PM_FQDN = config.VDS_HOSTS[0].fqdn
    HOST_1 = config.HOSTS[1]
    HOST_2 = config.HOSTS[2]
    host_restart_event = '\"Host %s was restarted by\"' % HOST_WITH_PM


def _fence_host(positive, fence_type):
    testflow.step("Wait for host %s power management operation", HOST_WITH_PM)
    assert ll_hosts.waitForHostPmOperation(
        host=HOST_WITH_PM,
        engine=config.ENGINE,
    )
    testflow.step(
        "Fence host %s, with action %s, expecting %s outcome",
        HOST_WITH_PM, fence_type, "positive" if positive else "negative"
    )
    assert (
        ll_hosts.fence_host(host=HOST_WITH_PM, fence_type=fence_type)
        is positive
    )
    testflow.step("Wait for host %s power management operation", HOST_WITH_PM)
    assert ll_hosts.waitForHostPmOperation(
        host=HOST_WITH_PM,
        engine=config.ENGINE,
    )


def _move_host_to_up(host):
    if not ll_hosts.isHostUp(True, host=host):
        assert ll_hosts.activate_host(True, host=host)


def _move_host_to_maintenance(host):
    assert hosts.deactivate_host_if_up(host=host)


def _block_outgoing_vdsm_port(host_num):
    host_obj = Host(config.VDS_HOSTS[host_num].fqdn)
    host_obj.users.append(RootUser(config.HOSTS_PW))
    host_obj.executor().run_cmd(
        ["iptables", "-A", "OUTPUT", "-p", "tcp", "--sport", VDSM_PORT,
         "-j", "DROP"]
    )
    ll_hosts.waitForHostsStates(
        True, config.HOSTS[host_num], config.HOST_NONRESPONSIVE
    )


def _unblock_outgoing_vdsm_port(host_num):
    host_obj = Host(config.VDS_HOSTS[host_num].fqdn)
    host_obj.users.append(RootUser(config.HOSTS_PW))
    host_obj.executor().run_cmd(
        ["iptables", "-D", "OUTPUT", "-p", "tcp", "--sport", VDSM_PORT,
         "-j", "DROP"]
    )
    ll_hosts.waitForHostsStates(True, config.HOSTS[host_num])


def _add_power_management(host_num=0, **kwargs):
    hostname = config.VDS_HOSTS[host_num].fqdn
    testflow.setup("Get power management details of host %s", hostname)
    host_pm = get_pm_details(hostname).get(hostname)
    if not host_pm:
        pytest.skip("The host %s does not have power management" % hostname)
    agent = {
        "agent_type": host_pm.get("pm_type"),
        "agent_address": host_pm.get("pm_address"),
        "agent_username": host_pm.get("pm_username"),
        "agent_password": host_pm.get("pm_password"),
        "concurrent": False,
        "order": 1
    }
    testflow.setup("Add power management to host %s", config.HOSTS[host_num])
    assert hosts.add_power_management(
        host_name=config.HOSTS[host_num], pm_agents=[agent], **kwargs
    )


def _remove_power_management(host=None):
    """
    Host variable can't be defined in parameters because with pytest
    it would be always None, since module setup goes after assignment
    of this functions parameters

    TODO: Find some better way to do this, maybe when we move away from pytest
    """
    if not host:
        host = HOST_WITH_PM
    testflow.teardown("Remove power management from host %s", host)
    assert hosts.remove_power_management(host_name=host)


@attr(tier=1, extra_reqs={'mgmt': True})
class TestWithHighAvailableVm(TestCase):
    """
    Base test class for tests with high available vm
    """
    __test__ = False

    vm_ha_name = 'vm_ha'
    vm2_name = 'vm_2'

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls, request):
        def fin():
            _remove_power_management()
            testflow.teardown(
                "Remove vms %s and %s", cls.vm_ha_name, cls.vm2_name
            )
            assert vms.removeVm(True, vm=cls.vm_ha_name, stopVM='true')
            assert vms.removeVm(True, vm=cls.vm2_name, stopVM='true')
        request.addfinalizer(fin)

        _add_power_management()
        testflow.setup(
            "Creating VM %s with high availability from template %s, "
            "with disk on host: %s",
            cls.vm_ha_name, config.TEMPLATE_NAME[0], HOST_WITH_PM
        )
        assert vms.createVm(
            True, vmDescription=VM_DESCRIPTION, vmName=cls.vm_ha_name,
            cluster=config.CLUSTER_NAME[0], template=config.TEMPLATE_NAME[0],
            storageDomainName=config.STORAGE_NAME[0], type=config.VM_TYPE,
            highly_available='true', placement_affinity=config.VM_MIGRATABLE,
            placement_host=HOST_WITH_PM, provisioned_size=SIZE,
            volumeFormat=config.FORMAT
        )
        disks.updateDisk(
            True, vmName=cls.vm_ha_name, alias=config.TEMPLATE_NAME[0],
            bootable=True
        )
        assert vms.runVmOnce(True, cls.vm_ha_name, host=HOST_WITH_PM)
        testflow.setup(
            "Creating VM %s from template %s, with disk on "
            "host: %s", cls.vm2_name, config.TEMPLATE_NAME[0], HOST_WITH_PM
        )
        assert vms.createVm(
            True, vmDescription=VM_DESCRIPTION, vmName=cls.vm2_name,
            cluster=config.CLUSTER_NAME[0], template=config.TEMPLATE_NAME[0],
            storageDomainName=config.STORAGE_NAME[0], type=config.VM_TYPE,
            placement_affinity=config.VM_MIGRATABLE,
            placement_host=HOST_WITH_PM, provisioned_size=SIZE,
            volumeFormat=config.FORMAT
        )
        disks.updateDisk(
            True, vmName=cls.vm2_name, alias=config.TEMPLATE_NAME[0],
            bootable=True
        )
        assert vms.runVmOnce(True, cls.vm2_name, host=HOST_WITH_PM)


@attr(tier=1, extra_reqs={'mgmt': True})
class TestPMWithBadParameters(TestCase):
    """
    Base class for tests with wrong parameters
    """
    __test__ = False

    t_agent = None
    bad_parameter = None

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls):
        testflow.setup(
            "Get power management details of host %s", HOST_WITH_PM_FQDN
        )
        host_pm = get_pm_details(HOST_WITH_PM_FQDN).get(HOST_WITH_PM_FQDN)
        agent = {
            "agent_type": host_pm.get("pm_type"),
            "agent_address": host_pm.get("pm_address"),
            "agent_username": host_pm.get("pm_username"),
            "agent_password": host_pm.get("pm_password"),
            "concurrent": False,
            "order": 1
        }
        cls.t_agent = copy(agent)
        testflow.setup("Change agent values to wrong parameters")
        for key, value in cls.bad_parameter.iteritems():
            cls.t_agent[key] = value


@attr(tier=1, extra_reqs={'fence': True})
class TestFenceOnHost(TestCase):
    """
    Base class for fence tests
    """
    __test__ = False

    up = False
    maintenance = False
    non_responsive = False

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls, request):
        def fin():
            _remove_power_management()
            _move_host_to_up(HOST_WITH_PM)
        request.addfinalizer(fin)

        _add_power_management()
        if cls.up:
            testflow.setup("Move host %s up", HOST_WITH_PM)
            _move_host_to_up(HOST_WITH_PM)
        elif cls.maintenance:
            testflow.setup("Move host %s to maintenance", HOST_WITH_PM)
            _move_host_to_maintenance(HOST_WITH_PM)


@attr(tier=1, extra_reqs={'mgmt': True})
class TestFenceHostWithTwoPMAgents(TestCase):
    """
    Base class for fence tests with two power management agents
    """
    __test__ = False

    host_pm = None
    pm1_address = None
    pm2_address = None

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls, request):
        def fin():
            _remove_power_management()
        request.addfinalizer(fin)

        testflow.setup(
            "Get power management details of host %s", HOST_WITH_PM_FQDN
        )
        cls.host_pm = get_pm_details(HOST_WITH_PM_FQDN).get(HOST_WITH_PM_FQDN)
        if not cls.host_pm:
            pytest.skip(
                "The host %s does not have power management" %
                HOST_WITH_PM_FQDN
            )
        pm_addr = cls.host_pm.get("pm_address")
        cls.pm1_address = pm_addr if not cls.pm1_address else cls.pm1_address
        cls.pm2_address = pm_addr if not cls.pm2_address else cls.pm2_address
        testflow.setup(
            "Set two power management agents on host %s", HOST_WITH_PM
        )
        agent_1 = (
            cls.host_pm.get("pm_type"),
            cls.pm1_address,
            cls.host_pm.get("pm_username"),
            cls.host_pm.get("pm_password"),
            None, False, 1
        )
        agent_2 = (
            cls.host_pm.get("pm_type"),
            cls.pm2_address,
            cls.host_pm.get("pm_username"),
            cls.host_pm.get("pm_password"),
            None, False, 2
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
        assert hosts.add_power_management(
            host_name=HOST_WITH_PM,
            pm_agents=agents,
            pm_proxies=['cluster', 'dc']
        ), ("Adding two power management agents to host %s failed" %
            HOST_WITH_PM
            )


@attr(tier=1, extra_reqs={'mgmt': True})
class TestFenceProxySelection(TestCase):
    """
    Base class for fencing proxy selection tests
    """
    __test__ = False

    hosts_state = None
    pm_proxies = ['cluster', 'dc']

    @classmethod
    @pytest.fixture(scope="function", autouse=True)
    def setup_function(cls, request):
        def fin():
            _remove_power_management()
            testflow.teardown(
                "Move host %s to cluster %s", HOST_2, config.CLUSTER_NAME[0]
            )
            hosts.move_host_to_another_cluster(HOST_2, config.CLUSTER_NAME[0])
            for host in cls.hosts_state:
                if cls.hosts_state[host]["state"] == config.HOST_NONRESPONSIVE:
                    testflow.teardown(
                        "Unblock host %s connection to storage", host
                    )
                    _unblock_outgoing_vdsm_port(
                        cls.hosts_state[host]["host_num"]
                    )
                _move_host_to_up(host)
        request.addfinalizer(fin)

        if not cls.hosts_state:
            cls.hosts_state = {
                HOST_1: {
                    "host_num": 1,
                    "state": config.HOST_UP
                },
                HOST_2: {
                    "host_num": 2,
                    "state": config.HOST_UP
                }
            }
        _add_power_management(pm_proxies=cls.pm_proxies)
        testflow.setup(
            "Move host %s to cluster %s", HOST_2, config.CLUSTER_NAME[1]
        )
        hosts.move_host_to_another_cluster(HOST_2, config.CLUSTER_NAME[1])
        for host in cls.hosts_state:
            if cls.hosts_state[host]["state"] == config.HOST_UP:
                testflow.setup("Move host %s up", host)
                _move_host_to_up(host)
            elif (
                cls.hosts_state[host]["state"] == config.HOST_MAINTENANCE
            ):
                testflow.setup("Move host %s to maintenance", host)
                _move_host_to_maintenance(host)
            else:
                testflow.setup("Move host %s to non operational", host)
                _block_outgoing_vdsm_port(
                    cls.hosts_state[host]["host_num"]
                )


class T01AddPMWithNoPassword(TestPMWithBadParameters):
    """
    Test adding power management with no password
    """
    __test__ = True
    bad_parameter = {'agent_password': ''}

    @polarion("RHEVM3-8919")
    def test_add_power_management_with_no_password(self):
        testflow.step("Add power management to host %s", HOST_WITH_PM)
        assert not hosts.add_power_management(
            host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
        ), "Adding PM with no password succeeded"


class T02AddPMWithNoUsername(TestPMWithBadParameters):
    """
    Test adding power management with no username
    """
    __test__ = True
    bad_parameter = {'agent_username': ''}

    @polarion("RHEVM3-8917")
    def test_add_power_management_with_no_username(self):
        testflow.step("Add power management to host %s", HOST_WITH_PM)
        assert not hosts.add_power_management(
            host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
        ), "Adding PM with no username succeeded"


class T03AddPMWithNoAddress(TestPMWithBadParameters):
    """
    Test adding power management with no address
    """
    __test__ = True
    bad_parameter = {'agent_address': ''}

    @polarion("RHEVM3-8918")
    def test_add_power_management_with_no_address(self):
        testflow.step("Add power management to host %s", HOST_WITH_PM)
        assert not hosts.add_power_management(
            host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
        ), "Adding PM with no address succeeded"


@bz({'1420302': {}})
class T04AddPMWithInvalidType(TestPMWithBadParameters):
    """
    Test adding power management with invalid type
    """
    __test__ = True
    bad_parameter = {'agent_type': 'invalid_type'}

    @polarion("RHEVM3-8916")
    def test_add_power_management_with_invalid_type(self):
        testflow.step("Add power management to host %s", HOST_WITH_PM)
        assert not hosts.add_power_management(
            host_name=HOST_WITH_PM, pm_agents=[self.t_agent]
        ), "Adding PM with invalid type succeeded"


class T05FenceHostWithHighAvailableVm(TestWithHighAvailableVm):
    """
    Test fencing host with high available VM running
    """
    __test__ = True

    @polarion("RHEVM3-12447")
    def test_fence_host_with_high_available_vm(self):
        _fence_host(True, fence_type=config.FENCE_RESTART)
        testflow.step("VM %s should be up", self.vm_ha_name)
        assert vms.waitForVmsStates(True, names=self.vm_ha_name), (
            "VM %s is not up" % self.vm_ha_name
        )
        testflow.step("VM %s should be down", self.vm2_name)
        assert vms.waitForVmsStates(
            True, names=self.vm2_name, states=config.VM_DOWN
        ), "VM %s is up" % self.vm2_name


class T06HostInNonResponsiveStatWithHighAvailableVM(TestWithHighAvailableVm):
    """
    Test non responsive host with high available VM running
    """
    __test__ = True

    service_network = 'network'
    stop_command = 'stop'

    @polarion("RHEVM3-12448")
    def test_host_in_non_responsive_state_with_high_available_vm(self):
        testflow.step("Stop network on host %s", HOST_WITH_PM)
        assert ll_hosts.runDelayedControlService(
            True, host=HOST_WITH_PM_FQDN, host_user=config.HOSTS_USER,
            host_passwd=config.HOSTS_PW, service=self.service_network,
            command=self.stop_command
        )
        testflow.step(
            "Wait for host %s to be in non responsive state", HOST_WITH_PM
        )
        assert ll_hosts.waitForHostsStates(
            True, names=HOST_WITH_PM, states=config.HOST_NONRESPONSIVE
        )
        testflow.step("Wait for host %s to be up", HOST_WITH_PM)
        assert ll_hosts.waitForHostsStates(
            True, names=HOST_WITH_PM, states=config.HOST_UP
        )
        assert vms.waitForVmsStates(True, names=self.vm_ha_name), (
            "VM %s is not up" % self.vm_ha_name
        )
        assert vms.waitForVmsStates(
                True, names=self.vm2_name, states=config.VM_DOWN
        ), "VM %s is up" % self.vm2_name


class T07StartHostInUpState(TestFenceOnHost):
    """
    Test starting a host in up state
    """
    __test__ = True

    up = True

    @polarion("RHEVM3-8914")
    def test_start_host_in_up_state(self):
        _fence_host(False, config.FENCE_START)


class T08StopThenStartHostInMaintenance(TestFenceOnHost):
    """
    Test stopping and then starting a host in maintenance
    """
    __test__ = True

    maintenance = True

    @polarion("RHEVM3-8927")
    def test_1_stop_host_in_maintenance(self):
        _fence_host(True, config.FENCE_STOP)

    @polarion("RHEVM3-8920")
    def test_2_start_host_in_down_state(self):
        _fence_host(True, config.FENCE_START)


class T09RestartHostInUpState(TestFenceOnHost):
    """
    Test restarting a host in up state
    """
    __test__ = True

    up = True

    @polarion("RHEVM3-8925")
    def test_restart_host_in_up_state(self):
        _fence_host(True, config.FENCE_RESTART)


class T10RestartHostInMaintenance(TestFenceOnHost):
    """
    Test restarting a host in maintenance
    """
    __test__ = True

    maintenance = True

    @polarion("RHEVM3-8923")
    def test_restart_host_in_maintenance(self):
        _fence_host(True, config.FENCE_RESTART)


class T11NoFallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):
    """
    Test restarting a host without fallback to secondary power management
    """
    __test__ = True

    pm2_address = 'blabla.blibli.com'

    @polarion("RHEVM3-8930")
    def test_no_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T12FallbackToSecondaryPMAgent(TestFenceHostWithTwoPMAgents):
    """
    Test restarting a host with fallback to secondary power management
    """
    __test__ = True

    pm1_address = 'blabla.blibli.com'

    @polarion("RHEVM3-8929")
    def test_fallback_to_secondary_pm_agent(self):
        _fence_host(True, config.FENCE_RESTART)


class T13ProxyChosenFromCluster(TestFenceProxySelection):
    """
    Tests default proxy selection: from same cluster as host to fence
    """
    __test__ = True

    event = None

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls):
        cls.event = fence_proxy_event.format(HOST_WITH_PM, HOST_1)

    @polarion("RHEVM3-9159")
    def test_proxy_chosen_from_cluster(self):
        _fence_host(True, config.FENCE_RESTART)
        testflow.step("Search for recent event %s", self.event)
        assert events.search_for_recent_event(
            True, win_start_query=self.event, query=host_restart_event,
            expected_count=1, max_events=1
        ), "Fence proxy wasn't chosen from cluster"


class T14ProxyChosenFromDataCenter(TestFenceProxySelection):
    """
    Tests proxy selection when DC is priority
    """
    __test__ = True

    event = None
    pm_proxies = ['dc', 'cluster']

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls):
        cls.event = fence_proxy_event.format(HOST_WITH_PM, HOST_2)

    @polarion("RHEVM3-9143")
    def test_proxy_chosen_from_data_center(self):
        _fence_host(True, config.FENCE_RESTART)
        testflow.step("Search for recent event %s", self.event)
        assert events.search_for_recent_event(
            True, win_start_query=self.event, query=host_restart_event,
            expected_count=1, max_events=1
        ), "Fence proxy wasn't chosen from data center"


class T15ProxyChosenFromSecondClusterAsFallback(TestFenceProxySelection):
    """
    Test proxy selection when priority is (cluster, dc) and host in cluster
    is non_operational.
    expected result: host in the second cluster in the dc is chosen as proxy

    TODO: add another host with pm to this test to allow further test cases
    """
    __test__ = True

    hosts_state = None
    event = None

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def setup_class(cls):
        cls.hosts_state = {
            HOST_1: {
                "host_num": 1,
                "state": config.HOST_NONRESPONSIVE
            },
            HOST_2: {
                "host_num": 2,
                "state": config.HOST_MAINTENANCE
            }
        }
        cls.event = fence_proxy_event.format(HOST_WITH_PM, HOST_2)

    @polarion("RHEVM3-9153")
    def test_proxy_chosen_from_second_cluster_as_fallback(self):
        _fence_host(True, config.FENCE_RESTART)
        testflow.step("Search for recent event %s", self.event)
        assert events.search_for_recent_event(
                True, win_start_query=self.event, query=host_restart_event,
                expected_count=1, max_events=1
        )
