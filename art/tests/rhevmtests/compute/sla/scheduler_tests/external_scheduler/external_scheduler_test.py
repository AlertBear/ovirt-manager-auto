"""
Ovirt Scheduler Proxy Test
"""
import pytest
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    run_once_vms,
    stop_vms,
    update_cluster,
    update_cluster_to_default_parameters
)

import config as conf
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    scheduling_policies as ll_sch,
    vms as ll_vms
)
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier3, SlaTest
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    create_new_scheduling_policy
)


@pytest.fixture(scope="module", autouse=True)
def prepare_environment(request):
    """
    1) Install the ovirt-scheduler-proxy package
    2) Copy external scheduler plugins on the engine
    3) Start the ovirt-scheduler-proxy service
    4) Enable the external scheduler via the engine-config
    """
    def fin():
        """
        1) Disable the external scheduler via the engine-config
        2) Remove external scheduler plugins from the engine
        3) Remove the ovirt-scheduler-proxy package from the engine
        4) Remove external scheduler units from the engine
        """
        results = list()
        cmd = "{0}={1}".format(conf.ENGINE_CONFIG_OVIRT_SCHEDULER_PROXY, False)
        testflow.teardown(
            "Disable the ovirt-scheduler-proxy via the engine config"
        )
        results.append(
            conf.ENGINE.engine_config(action="set", param=cmd).get("results")
        )

        for script_path in conf.PATH_EXTERNAL_SCHEDULER_PLUGINS:
            testflow.teardown(
                "Remove the script %s from the engine", script_path
            )
            results.append(conf.ENGINE_HOST.fs.remove(path=script_path))

        testflow.teardown(
            "Remove the package %s from the engine",
            conf.PACKAGE_OVIRT_SCHEDULER_PROXY
        )
        results.append(
            conf.ENGINE_HOST.package_manager.remove(
                package=conf.PACKAGE_OVIRT_SCHEDULER_PROXY
            )
        )

        policy_units_names = ll_sch.get_all_policy_units_names()
        for policy_unit in conf.EXTERNAL_SCHEDULER_POLICY_UNITS:
            if policy_unit in policy_units_names:
                results.append(
                    ll_sch.remove_scheduling_policy_unit(unit_name=policy_unit)
                )
        assert all(results)
    request.addfinalizer(fin)

    testflow.setup(
        "Install the package %s on the engine",
        conf.PACKAGE_OVIRT_SCHEDULER_PROXY
    )
    assert conf.ENGINE_HOST.package_manager.install(
        package=conf.PACKAGE_OVIRT_SCHEDULER_PROXY
    )

    for script_path, script_content in zip(
        conf.PATH_EXTERNAL_SCHEDULER_PLUGINS, conf.PLUGINS_EXTERNAL_SCHEDULER
    ):
        if conf.HOST_UUID in script_content:
            host_uuid = ll_hosts.get_host_object(
                host_name=conf.HOSTS[0]
            ).get_id()
            if conf.VM_UUID in script_content:
                vm_uuid = ll_vms.get_vm_obj(vm_name=conf.VM_NAME[0]).get_id()
                script_content = script_content.format(
                    host_uuid=host_uuid, vm_uuid=vm_uuid
                )
            else:
                script_content = script_content.format(host_uuid=host_uuid)
        testflow.setup(
            "Create the script %s on the engine", script_path
        )
        conf.ENGINE_HOST.fs.create_script(
            content=script_content, path=script_path
        )

    testflow.setup(
        "Start the service %s", conf.SERVICE_OVIRT_SCHEDULER_PROXY
    )
    assert conf.ENGINE_HOST.service(
        name=conf.SERVICE_OVIRT_SCHEDULER_PROXY
    ).start()

    cmd = "{0}={1}".format(conf.ENGINE_CONFIG_OVIRT_SCHEDULER_PROXY, True)
    testflow.setup(
        "Enable the ovirt-scheduler-proxy via the engine config"
    )
    conf.ENGINE.engine_config(action="set", param=cmd)


@pytest.fixture(scope="class")
def stop_ovirt_scheduler_proxy(request):
    """
    Stop the ovirt-scheduler-proxy service
    """
    ovirt_scheduler_proxy_service = conf.ENGINE_HOST.service(
        name=conf.SERVICE_OVIRT_SCHEDULER_PROXY
    )

    def fin():
        """
        Start the ovirt-scheduler-proxy service
        """
        testflow.teardown(
            "Start the %s service", conf.SERVICE_OVIRT_SCHEDULER_PROXY
        )
        assert ovirt_scheduler_proxy_service.start()
    request.addfinalizer(fin)

    testflow.setup(
        "Stop the %s service", conf.SERVICE_OVIRT_SCHEDULER_PROXY
    )
    assert ovirt_scheduler_proxy_service.stop()


class TestCorruptedPlugin(SlaTest):
    """
    Verify that the engine does not have the corrupted policy unit
    """

    @tier3
    @polarion("RHEVM3-9500")
    def test_policy_unit_existence(self):
        """
        Verify that the engine does not have the corrupted policy unit
        """
        policy_units_names = ll_sch.get_all_policy_units_names()
        testflow.step(
            "Verify tha the policy unit %s does not exist under the engine",
            conf.POLICY_UNIT_CORRUPTED
        )
        assert conf.POLICY_UNIT_CORRUPTED not in policy_units_names


@pytest.mark.usefixtures(
    create_new_scheduling_policy.__name__,
    update_cluster.__name__,
    stop_vms.__name__
)
class TestExternalSchedulerTimeout(SlaTest):
    """
    Verify that the engine skips the external scheduler module,
    if scheduler module takes too much time to consider
    on what host to start the VM
    """
    policy_name = conf.EXTERNAL_POLICY_TIMEOUT
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.EXTERNAL_POLICY_TIMEOUT
    }
    policy_units = {
        conf.POLICY_UNIT_TIMEOUT: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier3
    @polarion("RHEVM3-9501")
    def test_start_vm(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    create_new_scheduling_policy.__name__,
    update_cluster.__name__,
    run_once_vms.__name__
)
class TestExternalSchedulerFilter(SlaTest):
    """
    Verify that the engine starts VM on the correct host under external
    scheduler filter module
    """
    policy_name = conf.EXTERNAL_POLICY_FILTER
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.EXTERNAL_POLICY_FILTER
    }
    policy_units = {
        conf.POLICY_UNIT_FILTER: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER
        }
    }
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP}
    }

    @tier3
    @polarion("RHEVM3-9502")
    def test_vm_host(self):
        """
        Verify that the VM started on the host_0
        """
        testflow.step(
            "Verify that the VM %s started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) == conf.HOSTS[0]


@pytest.mark.usefixtures(
    create_new_scheduling_policy.__name__,
    update_cluster.__name__,
    run_once_vms.__name__
)
class TestExternalSchedulerWeight(SlaTest):
    """
    Verify that the engine starts VM on the correct host under external
    scheduler weight module
    """
    policy_name = conf.EXTERNAL_POLICY_WEIGHT
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.EXTERNAL_POLICY_WEIGHT
    }
    policy_units = {
        conf.POLICY_UNIT_WEIGHT: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_WEIGHT
        }
    }
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP}
    }

    @tier3
    @polarion("RHEVM3-9504")
    def test_vm_host(self):
        """
        Verify that the VM started on the host_0
        """
        testflow.step(
            "Verify that the VM %s started on the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(vm_name=conf.VM_NAME[0]) == conf.HOSTS[0]


@pytest.mark.usefixtures(
    create_new_scheduling_policy.__name__,
    update_cluster.__name__,
    run_once_vms.__name__
)
class TestExternalSchedulerBalance(SlaTest):
    """
    Verify that the engine balancing VM on the correct host under external
    scheduler balance module
    """
    policy_name = conf.EXTERNAL_POLICY_BALANCE
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.EXTERNAL_POLICY_BALANCE
    }
    policy_units = {
        conf.POLICY_UNIT_BALANCE: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_BALANCE
        }
    }
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP,
            conf.VM_RUN_ONCE_HOST: 1
        }
    }

    @tier3
    @polarion("RHEVM3-9503")
    def test_vm_host(self):
        """
        Verify that the engine balancing the VM to the host_0
        """
        testflow.step(
            "Verify that the engine balancing the VM %s to the host %s",
            conf.VM_NAME[0], conf.HOSTS[0]
        )
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1
        )


@pytest.mark.usefixtures(
    create_new_scheduling_policy.__name__,
    update_cluster.__name__,
    stop_ovirt_scheduler_proxy.__name__,
    stop_vms.__name__
)
class TestExternalSchedulerServiceStopped(SlaTest):
    """
    Verify that the engine skips the external scheduler module,
    if the ovirt-scheduler-proxy service stopped
    """
    policy_name = conf.EXTERNAL_POLICY_SERVICE_STOPPED
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.EXTERNAL_POLICY_SERVICE_STOPPED
    }
    policy_units = {
        conf.POLICY_UNIT_STOPPED: {
            conf.UNIT_TYPE: conf.SCH_UNIT_TYPE_FILTER
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier3
    @polarion("RHEVM3-9506")
    def test_start_vm(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])
