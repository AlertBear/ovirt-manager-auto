"""
Test multiple pinning of VM under different conditions
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import rhevmtests.compute.sla.helpers as sla_helpers
import rhevmtests.helpers as rhevm_helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier1, tier2, tier3, SlaTest
from fixtures import (
    change_host_cluster,
    update_class_cpu_pinning
)
from rhevmtests.compute.sla.fixtures import (
    activate_hosts,
    attach_host_device,
    create_equals_numa_nodes_on_vm,
    create_vm_without_disk,
    choose_specific_host_as_spm,
    export_vm,
    import_vm,
    make_template_from_vm,
    make_vm_from_template,
    migrate_he_vm,
    remove_all_numa_nodes_from_vm,
    skip_numa_tests,
    stop_vms,
    update_vms
)

host_as_spm = 2
he_dst_host = 2


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    choose_specific_host_as_spm.__name__
)
class BaseMultiplePinning(SlaTest):
    """
    Base class for all multiple pinning tests
    """
    test_vm = conf.VM_NAME[0]

    @staticmethod
    def _start_and_get_vm_host(wait_for_vm_state=conf.VM_POWERING_UP):
        """
        1) Start VM
        2) Get VM host
        """
        assert ll_vms.startVm(
            positive=True,
            vm=conf.VM_NAME[0],
            wait_for_status=wait_for_vm_state
        )
        testflow.step("Get the VM %s host", conf.VM_NAME[0])
        return ll_vms.get_vm_host(vm_name=conf.VM_NAME[0])

    @staticmethod
    def _stop_vm_and_deactivate_vm_host(vm_host, host_resource):
        """
        1) Stop VM
        2) Deactivate host

        Args:
            vm_host (str): Host to deactivate
        """
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0])
        assert ll_hosts.deactivate_host(
            positive=True, host=vm_host, host_resource=host_resource
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    activate_hosts.__name__
)
class TestMultiplePinning01(BaseMultiplePinning):
    """
    Check, that VM pinned to two hosts,
    can start only on this hosts(has three hosts in cluster)
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

    @tier1
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12073")
    def test_check_multiple_pinning(self):
        """
        1) Start VM and check if it started on correct host
        2) Stop VM and deactivate host where it started before
        3) Start VM and check if it started on correct host
        4) Stop VM and deactivate host where it started before
        5) Start VM
        """
        for _ in range(conf.PIN_TO_HOSTS_NUM):
            vm_host = self._start_and_get_vm_host()
            testflow.step(
                "Check if the VM %s starts on the correct host",
                conf.VM_NAME[0]
            )
            assert vm_host in conf.HOSTS[:2]
            self._stop_vm_and_deactivate_vm_host(
                vm_host=vm_host,
                host_resource=conf.VDS_HOSTS[conf.HOSTS.index(vm_host)]
            )
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning02(BaseMultiplePinning):
    """
    Check, that VM pinned to two hosts, can not migrate
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @tier1
    @polarion("RHEVM3-12074")
    def test_check_vm_migration(self):
        """
        1) Start VM
        2) Migrate VM
        """
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning03(BaseMultiplePinning):
    """
    Check, that VM pinned to two hosts, can be 'High Available'
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    def _start_and_kill_ha_vm(self):
        """
        1) Start HA VM
        2) Kill HA VM
        """
        vm_host = self._start_and_get_vm_host(wait_for_vm_state=conf.VM_UP)
        host_resource = rhevm_helpers.get_host_resource_by_name(
            host_name=vm_host
        )
        testflow.step(
            "%s: kill the VM %s process", host_resource, conf.VM_NAME[0]
        )
        assert ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=conf.VM_NAME[0]
        )

    @tier1
    @polarion("RHEVM3-12087")
    def test_check_ha_vm(self):
        """
        1) Update VM to be high available
        2) Start VM
        3) Kill VM on host
        4) Check that VM started again
        """
        assert ll_vms.updateVm(
            positive=True, vm=conf.VM_NAME[0], highly_available=True
        )
        self._start_and_kill_ha_vm()
        testflow.step(
            "Check that HA VM %s starts again", conf.VM_NAME[0]
        )
        assert ll_vms.waitForVMState(
            vm=conf.VM_NAME[0], state=conf.VM_POWERING_UP
        )


@pytest.mark.usefixtures(
    update_class_cpu_pinning.__name__,
    update_vms.__name__,
    stop_vms.__name__,
    activate_hosts.__name__
)
class TestMultiplePinning04(BaseMultiplePinning):
    """
    Pin VM to two hosts and add CPU pinning to VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

    @tier2
    @polarion("RHEVM3-12099")
    def test_check_vm_cpu_pinning(self):
        """
        1) Start VM
        2) Check VM CPU pinning
        """
        host_online_cpu = ll_sla.get_list_of_online_cpus_on_resource(
            resource=conf.VDS_HOSTS[0]
        )[0]
        for _ in range(conf.PIN_TO_HOSTS_NUM):
            vm_host = self._start_and_get_vm_host()
            host_resource = rhevm_helpers.get_host_resource_by_name(
                host_name=vm_host
            )
            expected_pinning = {conf.VCPU: 0, conf.CPU: host_online_cpu}
            testflow.step(
                "Check that VM %s has correct CPU pinning %s",
                conf.VM_NAME[0], expected_pinning
            )
            assert sla_helpers.check_vm_cpu_pinning(
                host_resource=host_resource,
                vm_name=conf.VM_NAME[0],
                expected_pinning=expected_pinning
            )
            self._stop_vm_and_deactivate_vm_host(
                vm_host=vm_host,
                host_resource=conf.VDS_HOSTS[conf.HOSTS.index(vm_host)]
            )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    activate_hosts.__name__
)
class TestMultiplePinning05(BaseMultiplePinning):
    """
    Pin VM to two hosts and update VM CPU mode to pass-through
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2),
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

    @tier2
    @polarion("RHEVM3-12101")
    def test_check_vm_cpu_mode(self):
        """
        1) Start VM
        2) Check VM CPU mode
        """
        for _ in range(conf.PIN_TO_HOSTS_NUM):
            vm_host = self._start_and_get_vm_host()
            host_resource = rhevm_helpers.get_host_resource_by_name(
                host_name=vm_host
            )
            host_cpu_info = sla_helpers.get_cpu_info(resource=host_resource)
            vm_resource = rhevm_helpers.get_vm_resource(
                vm=conf.VM_NAME[0], start_vm=False
            )
            vm_cpu_info = sla_helpers.get_cpu_info(resource=vm_resource)
            testflow.step(
                "Check that VM %s has host CPU model %s",
                conf.VM_NAME[0], host_cpu_info[conf.CPU_MODEL_NAME]
            )
            assert (
                vm_cpu_info[conf.CPU_MODEL_NAME] ==
                host_cpu_info[conf.CPU_MODEL_NAME]
            )
            self._stop_vm_and_deactivate_vm_host(
                vm_host=vm_host,
                host_resource=conf.VDS_HOSTS[conf.HOSTS.index(vm_host)]
            )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    stop_vms.__name__
)
class TestMultiplePinning06(BaseMultiplePinning):
    """
    Negative: Pin VM to two host and add NUMA pinning to VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-12137")
    def test_check_numa_pinning(self):
        """
        1) Add NUMA node to VM
        """
        numa_nodes = sla_helpers.create_number_of_equals_numa_nodes(
            resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            num_of_numa_nodes=1
        )
        assert not ll_vms.add_numa_node_to_vm(
            vm_name=conf.VM_NAME[0],
            host_name=conf.HOSTS[0],
            **numa_nodes[0]
        )


@pytest.mark.usefixtures(
    skip_numa_tests.__name__,
    update_vms.__name__,
    remove_all_numa_nodes_from_vm.__name__,
    stop_vms.__name__,
    create_equals_numa_nodes_on_vm.__name__
)
class TestMultiplePinning07(BaseMultiplePinning):
    """
    Negative: Pin VM to two host, when VM already has NUMA pinning
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(1)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    num_of_vm_numa_nodes = 1

    @tier2
    @polarion("RHEVM3-12450")
    def test_check_numa_pinning(self):
        """
        1) Pin VM to two hosts
        """
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_hosts=conf.HOSTS[:2]
        )


@pytest.mark.usefixtures(change_host_cluster.__name__)
class TestMultiplePinning08(BaseMultiplePinning):
    """
    Negative: Pin VM to host from another cluster
    """

    @tier3
    @polarion("RHEVM3-12401")
    def test_check_pinning_to_incorrect_host(self):
        """
        1) Pin VM to host from another cluster
        """
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_PINNED,
            placement_hosts=[conf.HOSTS[0]]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning09(BaseMultiplePinning):
    """
    Negative: attach host device to VM, that pinned to two hosts
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-12405")
    def test_check_host_devices(self):
        """
        1) Attach host device to VM
        """
        host_device_name = ll_hosts.get_host_devices(
            host_name=conf.HOSTS[0]
        )[0].get_name()
        testflow.step(
            "Attach the host device %s to VM %s",
            host_device_name, conf.VM_NAME[0]
        )
        assert not ll_vms.add_vm_host_device(
            vm_name=conf.VM_NAME[0],
            device_name=host_device_name,
            host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    attach_host_device.__name__
)
class TestMultiplePinning10(BaseMultiplePinning):
    """
    Pin VM to two host when VM has attached device
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(1)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @tier2
    @polarion("RHEVM3-12449")
    def test_check_host_devices(self):
        """
        1) Pin VM to two hosts
        2) Check that VM does not have host devices
        """
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_hosts=conf.HOSTS[:2]
        )
        testflow.step("Get VM %s host devices", conf.VM_NAME[0])
        assert not ll_vms.get_vm_host_devices(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    create_vm_without_disk.__name__,
    update_vms.__name__,
    export_vm.__name__,
    import_vm.__name__
)
class TestImportExport(BaseMultiplePinning):
    """
    Import and export the VM that pinned to two hosts
    """
    vms_to_params = {
        conf.VM_WITHOUT_DISK: {conf.VM_PLACEMENT_HOSTS: range(2)}
    }
    vm_to_export = conf.VM_WITHOUT_DISK
    vm_to_import = conf.VM_WITHOUT_DISK
    vm_import_name = conf.VM_IMPORTED

    @tier2
    @polarion("RHEVM3-12406")
    def test_check_import_export(self):
        """
        Check if imported VM has correct pinning hosts
        """
        vm_placement_hosts = ll_vms.get_vm_placement_hosts(
            vm_name=conf.VM_IMPORTED
        )
        vm_placement_hosts.sort()
        testflow.step("Check VM %s placement hosts", conf.VM_NAME[0])
        assert vm_placement_hosts == conf.HOSTS[:2]


@pytest.mark.usefixtures(
    create_vm_without_disk.__name__,
    update_vms.__name__,
    make_template_from_vm.__name__,
    make_vm_from_template.__name__
)
class TestTemplate(BaseMultiplePinning):
    """
    Create template from the VM that pinned to two host and
    create the VM from this template
    """
    vms_to_params = {
        conf.VM_WITHOUT_DISK: {conf.VM_PLACEMENT_HOSTS: range(2)}
    }
    vm_for_template = conf.VM_WITHOUT_DISK
    template_name = conf.VM_IMPORT_EXPORT_TEMPLATE
    vm_from_template_name = conf.VM_FROM_TEMPLATE

    @tier2
    @bz({"1333409": {}})
    @polarion("RHEVM3-12407")
    def test_check_template(self):
        """
        Check if VM created from template has correct pinning hosts
        """
        vm_placement_hosts = ll_vms.get_vm_placement_hosts(
            vm_name=conf.VM_FROM_TEMPLATE
        )
        vm_placement_hosts.sort()
        testflow.step(
            "Check VM %s placement hosts", conf.VM_FROM_TEMPLATE
        )
        assert vm_placement_hosts == conf.HOSTS[:2]
