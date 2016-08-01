"""
Test multiple pinning of VM under different conditions
"""
import logging

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers as pinning_helpers
import pytest
import rhevmtests.helpers as rhevm_helpers
import rhevmtests.sla.helpers as sla_helpers
from art.test_handler.tools import polarion, bz
from fixtures import (
    attach_host_device,
    create_vm_for_export_and_template_checks,
    export_vm,
    import_vm,
    make_template_from_vm,
    make_vm_from_template,
    numa_pinning,
    update_class_cpu_pinning
)
from rhevmtests.sla.fixtures import (
    activate_hosts,
    stop_vms,
    update_vms
)

logger = logging.getLogger(__name__)


class BaseMultiplePinning(u_libs.SlaTest):
    """
    Base class for all multiple pinning tests
    """
    test_vm = conf.VM_NAME[0]

    def _start_and_get_vm_host(self, wait_for_vm_state=conf.VM_POWERING_UP):
        """
        1) Start VM
        2) Get VM host
        """
        assert ll_vms.startVm(
            positive=True, vm=self.test_vm, wait_for_status=wait_for_vm_state
        )
        return ll_vms.get_vm_host(vm_name=self.test_vm)

    def _stop_vm_and_deactivate_vm_host(self, vm_host):
        """
        1) Stop VM
        2) Deactivate host

        Args:
            vm_host (str): Host to deactivate
        """
        assert ll_vms.stopVm(positive=True, vm=self.test_vm)
        assert ll_hosts.deactivateHost(positive=True, host=vm_host)


@u_libs.attr(tier=1)
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
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

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
            logger.info("Check if VM %s started on correct host", self.test_vm)
            assert vm_host in conf.HOSTS[:2]
            self._stop_vm_and_deactivate_vm_host(vm_host=vm_host)
        assert not ll_vms.startVm(positive=True, vm=self.test_vm)


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning02(BaseMultiplePinning):
    """
    Check, that VM pinned to two hosts, can not migrate
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-12074")
    def test_check_vm_migration(self):
        """
        1) Start VM
        2) Migrate VM
        """
        assert ll_vms.startVm(positive=True, vm=self.test_vm)
        assert not ll_vms.migrateVm(positive=True, vm=self.test_vm)


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning03(BaseMultiplePinning):
    """
    Check, that VM pinned to two hosts, can be 'High Available'
    """
    __test__ = True
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
        assert ll_hosts.kill_vm_process(
            resource=host_resource, vm_name=self.test_vm
        )

    @polarion("RHEVM3-12087")
    def test_check_ha_vm(self):
        """
        1) Update VM to be high available
        2) Start VM
        3) Kill VM on host
        4) Check that VM started again
        """
        logger.info("Update VM %s to be high available", self.test_vm)
        assert ll_vms.updateVm(
            positive=True, vm=self.test_vm, highly_available=True
        )
        self._start_and_kill_ha_vm()
        assert ll_vms.waitForVMState(
            vm=self.test_vm, state=conf.VM_POWERING_UP
        )


@u_libs.attr(tier=2)
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
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

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
            assert sla_helpers.check_vm_cpu_pinning(
                host_resource=host_resource,
                vm_name=self.test_vm,
                expected_pinning={
                    conf.VCPU: 0,
                    conf.CPU: host_online_cpu
                }
            )
            self._stop_vm_and_deactivate_vm_host(vm_host=vm_host)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    activate_hosts.__name__
)
class TestMultiplePinning05(BaseMultiplePinning):
    """
    Pin VM to two hosts and update VM CPU mode to pass-through
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2),
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]
    hosts_to_activate_indexes = range(2)

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
            assert (
                vm_cpu_info[conf.CPU_MODEL_NAME] ==
                host_cpu_info[conf.CPU_MODEL_NAME]
            )
            self._stop_vm_and_deactivate_vm_host(vm_host=vm_host)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning06(BaseMultiplePinning):
    """
    Negative: Pin VM to two host and add NUMA pinning to VM
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-12137")
    def test_check_numa_pinning(self):
        """
        1) Add NUMA node to VM
        """
        pinning_helpers.add_one_numa_node_to_vm(negative=True)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    numa_pinning.__name__
)
class TestMultiplePinning07(BaseMultiplePinning):
    """
    Negative: Pin VM to two host, when VM already has NUMA pinning
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(1)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

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


@u_libs.attr(tier=3)
class TestMultiplePinning08(BaseMultiplePinning):
    """
    Negative: Pin VM to host from another cluster
    """
    __test__ = True

    @polarion("RHEVM3-12401")
    def test_check_pinning_to_incorrect_host(self):
        """
        1) Pin VM to host from another cluster
        """
        if len(conf.HOSTS) < 4:
            pytest.skip("Golden environment does not have four hosts")
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_PINNED,
            placement_hosts=[conf.HOSTS[3]]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestMultiplePinning09(BaseMultiplePinning):
    """
    Negative: attach host device to VM, that pinned to two hosts
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(2)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-12405")
    def test_check_host_devices(self):
        """
        1) Attach host device to VM
        """
        host_device_name = ll_hosts.get_host_devices(
            host_name=conf.HOSTS[0]
        )[0].get_name()
        assert not ll_vms.add_vm_host_device(
            vm_name=conf.VM_NAME[0],
            device_name=host_device_name,
            host_name=conf.HOSTS[0]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__,
    attach_host_device.__name__
)
class TestMultiplePinning10(BaseMultiplePinning):
    """
    Pin VM to two host when VM has attached device
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: range(1)
        }
    }
    vms_to_stop = [conf.VM_NAME[0]]

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
        assert not ll_vms.get_vm_host_devices(vm_name=conf.VM_NAME[0])


@u_libs.attr(tier=2)
class TestImportExportTemplate(BaseMultiplePinning):
    """
    Import, export, and template of VM that pinned to two hosts
    """
    __test__ = True

    @pytest.mark.usefixtures(
        create_vm_for_export_and_template_checks.__name__,
        export_vm.__name__,
        import_vm.__name__
    )
    @polarion("RHEVM3-12406")
    def test_check_import_export(self):
        """
        Check if imported VM has correct pinning hosts
        """
        vm_placement_hosts = ll_vms.get_vm_placement_hosts(
            vm_name=conf.VM_IMPORTED
        )
        vm_placement_hosts.sort()
        assert vm_placement_hosts == conf.HOSTS[:2]

    @bz({"1333409": {}})
    @pytest.mark.usefixtures(
        create_vm_for_export_and_template_checks.__name__,
        make_template_from_vm.__name__,
        make_vm_from_template.__name__
    )
    @polarion("RHEVM3-12407")
    def test_check_template(self):
        """
        Check if VM created from template has correct pinning hosts
        """
        vm_placement_hosts = ll_vms.get_vm_placement_hosts(
            vm_name=conf.VM_FROM_TEMPLATE
        )
        vm_placement_hosts.sort()
        assert vm_placement_hosts == conf.HOSTS[:2]
