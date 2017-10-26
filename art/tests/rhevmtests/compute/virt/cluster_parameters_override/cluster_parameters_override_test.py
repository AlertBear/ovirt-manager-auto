#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Test setting cpu type on vm level overriding cluster level
"""
import copy

import pytest

import art.rhevm_api.tests_lib.high_level.vmpools as hl_vmpools
import config
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd,
    scheduling_policies as ll_sp,
    vmpools as ll_vmpools
)
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier2,
)
from art.rhevm_api.utils.test_utils import wait_for_tasks
from fixtures import (
    set_cpu_model_param,
    check_if_higher_cpu_model_tests_should_run,
    check_if_no_several_hosts_with_high_cpu_tests_should_run,
    check_if_no_different_hosts_tests_should_run,
    check_if_no_high_cpu_host_tests_should_run,
    revert_ge_vm_to_default_values, deactivate_redundant_hosts,
)
from rhevmtests import helpers
from rhevmtests.compute.virt.reg_vms.fixtures import (
    basic_teardown_fixture, add_vm_fixture, remove_vm_from_export_domain,
)
from rhevmtests.compute.virt.vm_pools import config as vm_pools_config
from rhevmtests.compute.virt import helper as virt_helper
from rhevmtests.compute.virt.vm_pools.fixtures import vm_pool_teardown
from art.core_api import apis_exceptions


@pytest.mark.usefixtures(
    basic_teardown_fixture.__name__
)
class TestClusterParamsOverrideBasicTest(VirtTest):
    """
    Tests basic configuration and inheritance of custom cpu model
    """
    pool_name = 'custom_cpu_type_vm_pool_cluster_params_override'
    pool_params = copy.deepcopy(vm_pools_config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    vm_name = 'virt_dummy_vm_cluster_params_override'
    add_disk = False
    cluster_lower = False

    @tier2
    @polarion("RHEVM3-10254")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_higher_cpu_model_tests_should_run.__name__,
        basic_teardown_fixture.__name__
    )
    def test_negative_start_vm_with_unsupported_cpu_type(self):
        """
        Negative - Create and start vm set with an unsupported cpu type for
        the cluster.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.HIGER_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Add VM %s - set cpu model to a model that is unsupported in the "
            "cluster", config.CPU_MODEL_VM
        )
        assert ll_vms.addVm(
            True,
            name=config.CPU_MODEL_VM,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            custom_cpu_model=cpu_model
        ), "failed to add VM %s" % config.CPU_MODEL_VM
        testflow.step("Start VM %s", config.CPU_MODEL_VM)
        assert not ll_vms.startVm(True, config.CPU_MODEL_VM)

    @tier2
    @polarion("RHEVM3-10292")
    @pytest.mark.usefixtures(basic_teardown_fixture.__name__)
    def test_negative_start_vm_with_non_existing_cpu_type(self):
        """
        Negative - Create and start vm set with non existing cpu type.
        """
        testflow.step(
            "Add VM %s with cpu model that does not exist: %s",
            config.CPU_MODEL_VM, config.NON_EXISTING_TYPE
        )
        assert ll_vms.addVm(
            True,
            name=config.CPU_MODEL_VM,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            custom_cpu_model=config.NON_EXISTING_TYPE
        ), "Failed to add VM %s" % config.CPU_MODEL_VM
        testflow.step("Start VM %s", config.CPU_MODEL_VM)
        assert not ll_vms.startVm(True, config.CPU_MODEL_VM)

    @tier2
    @polarion("RHEVM3-10376")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_higher_cpu_model_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_edit_vm_update_cpu_type_higher_than_cluster(self):
        """
        Edit vm with custom cpu type which is higher than cluster level
        (checks only configuration).
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.HIGER_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Update VM %s- set cpu type to a higher model than cluster",
            config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            True, config.VM_NAME[0], custom_cpu_model=cpu_model
        )

    @tier2
    @polarion("RHEVM3-10378")
    @pytest.mark.usefixtures(revert_ge_vm_to_default_values.__name__)
    def test_edit_vm_update_cpu_and_bad_values(self):
        """
        Checks that vm can be updated with non existing and unsupported
        cpu type (checks only configuration).
        """
        testflow.step(
            "Update VM %s - set cpu type with non existing values",
            config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            True, config.VM_NAME[0],
            custom_cpu_model=config.NON_EXISTING_TYPE,
        )

    @tier2
    @polarion("RHEVM3-10398")
    @pytest.mark.usefixtures(revert_ge_vm_to_default_values.__name__)
    def test_negative_runonce_vm_with_non_existing_cpu_type(self):
        """
        Negative - run once a vm - set cpu type to a non existing value
        """
        testflow.step(
            "Run once a VM %s and set cpu type to a non existing value",
            config.VM_NAME[0]
        )
        assert not ll_vms.runVmOnce(
            True, config.VM_NAME[0],
            custom_cpu_model=config.NON_EXISTING_TYPE,
        )

    @tier2
    @polarion("RHEVM3-11296")
    @pytest.mark.usefixtures(revert_ge_vm_to_default_values.__name__)
    def test_negative_runonce_vm_with_unsuppoted_cpu_type(self):
        """
        Negative - run once a vm - set cpu type to an unsupported type
        """
        testflow.step(
            "Run once a VM %s and set cpu type to an unsupported type",
            config.VM_NAME[0]
        )
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.HIGER_CPU_MODEL]['cpu']
        )
        assert not ll_vms.runVmOnce(
            True, config.VM_NAME[0], custom_cpu_model=cpu_model
        )

    @tier2
    @polarion("RHEVM3-12022")
    @pytest.mark.usefixtures(
        add_vm_fixture.__name__,
        remove_vm_from_export_domain.__name__
    )
    def test_import_export_vm_custom_cpu_inheritance(self):
        """
        Test inheritance of custom cpu type value from
        vm to exported vm and then back to re imported vm.
        """
        minimal_supported_cpu_model = (
            virt_helper.get_cpu_model_name_for_rest_api(
                config.CLUSTER_CPU_PARAMS[config.MIN_HOST_CPU]['cpu']
            )
        )
        testflow.step(
            "Update VM %s - set custom cpu model and with some "
            "supported values", config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            True, self.vm_name,
            custom_cpu_model=minimal_supported_cpu_model
        )
        testflow.step("Export VM %s", self.vm_name)
        assert ll_vms.exportVm(
            positive=True,
            vm=self.vm_name,
            storagedomain=config.EXPORT_DOMAIN_NAME
        )
        testflow.step("Remove source VM %s from storage domain", self.vm_name)
        assert ll_vms.safely_remove_vms([self.vm_name])
        master_sd = (
            ll_sd.get_master_storage_domain_name(
                datacenter_name=config.DC_NAME[0])
        )
        testflow.step(
            "Import VM %s from export domain back to storage domain",
            self.vm_name
        )
        assert ll_vms.importVm(
            positive=True,
            vm=self.vm_name,
            export_storagedomain=config.EXPORT_DOMAIN_NAME,
            import_storagedomain=master_sd,
            cluster=config.CLUSTER_NAME[0],
        )
        try:
            wait_for_tasks(
                engine=config.ENGINE,
                datacenter=config.DC_NAME[0]
            )
        except apis_exceptions.APITimeout:
            testflow.step(
                "Error - engine has async tasks that still running"
            )
            assert False, "The engine still has unfinished tasks"

    @tier2
    @polarion("RHEVM3-10662")
    def test_check_scheduling_policy_units_exist(self):
        """
        Checks that cpu model policy units exist in the systems's
        policy units list.
        """
        assert ll_sp.get_policy_unit(
            unit_name=config.EMULATED_MACHINE_POLICY_UNIT,
            unit_type='filter'
        )
        assert ll_sp.get_policy_unit(
            unit_name=config.CPU_MODEL_POLICY_UNIT,
            unit_type='filter'
        )


class TestClusterParamsOverrideHostHigherThanCluster(VirtTest):
    """
    Tests basic configuration and inheritance of custom cpu model
    """
    pool_name = 'custom_cpu_type_vm_pool'
    pool_params = copy.deepcopy(vm_pools_config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    vm_name = 'virt_dummy_vm'
    add_disk = False
    cluster_lower = True

    @tier2
    @polarion("RHEVM3-10255 ")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        basic_teardown_fixture.__name__
    )
    def test_vm_with_cpu_different_from_cluster(self):
        """
        Create and start vm - set cpu type to value
        different than cluster values.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )
        testflow.step(
            "Add VM %s- set cpu model to values higher than the cluster",
            config.CPU_MODEL_VM
        )
        assert ll_vms.addVm(
            True,
            name=config.CPU_MODEL_VM,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            custom_cpu_model=cpu_model,
        ), "Failed to add VM %s" % config.CPU_MODEL_VM
        testflow.step("Start VM %s", config.CPU_MODEL_VM)
        assert ll_vms.startVm(True, config.CPU_MODEL_VM)
        host_resource = helpers.get_host_resource_of_running_vm(
            config.CPU_MODEL_VM
        )
        assert virt_helper.check_vm_cpu_model(
            config.CPU_MODEL_VM, host_resource, cpu_model
        )

    @tier2
    @polarion("RHEVM3-10383 ")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_run_once_with_cpu_different_from_cluster(self):
        """
        run once vm - set cpu type to values different than cluster values.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )
        testflow.step(
            "Run once VM %s and set custom cpu model with some "
            "supported values", config.VM_NAME[0]
        )
        assert ll_vms.runVmOnce(
            positive=True,
            vm=config.VM_NAME[0],
            custom_cpu_model=cpu_model
        )

    @tier2
    @polarion("RHEVM3-10635")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        vm_pool_teardown.__name__
    )
    def test_vmpool_with_cpu_different_from_cluster(self):
        """
        Create and start vm - set cpu type type to values
        different than cluster values.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )
        testflow.step(
            "Creating a new VM pool %s - setting cpu model with some "
            "supported values", self.pool_name
        )
        self.pool_params['custom_cpu_model'] = cpu_model
        hl_vmpools.create_vm_pool(
            True, self.pool_name, self.pool_params
        )
        vm_name = ll_vmpools.get_vms_in_pool_by_name(self.pool_name)[0]
        testflow.step("Start VM %s", vm_name)
        assert ll_vms.startVm(True, vm_name)
        host_resource = helpers.get_host_resource_of_running_vm(vm_name)
        assert virt_helper.check_vm_cpu_model(
            vm_name, host_resource, cpu_model
        )

    @tier2
    @polarion("RHEVM3-10654")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        deactivate_redundant_hosts.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_negative_migrate_vm_with_1_host_supporting_cpu_model(self):
        """
        Negative - Try to migrate vm with cpu model > cluster default with
        only 1 host supporting the cpu model
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
        )
        testflow.step(
            "Update VM %s - set cpu type to a higher model than cluster: %s",
            config.VM_NAME[0], cpu_model
        )
        assert ll_vms.updateVm(
            True, config.VM_NAME[0], custom_cpu_model=cpu_model
        )
        testflow.step("Start VM %s", config.VM_NAME[0])
        assert ll_vms.startVm(True, config.VM_NAME[0])
        testflow.step(
            "Attempting to migrate VM %s - expecting failure", config.VM_NAME
        )
        assert not ll_vms.migrateVm(True, config.VM_NAME[0])

    @tier2
    @polarion("RHEVM3-10655")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_several_hosts_with_high_cpu_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_migrate_vm_with_custom_cpu_values_2_hosts_supporting(self):
        """
        Migrate vm with cpu model > cluster default with several hosts
        supporting the cpu model.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.HIGHEST_COMMON_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Update VM %s - set cpu type to a higher model than cluster",
            config.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=config.VM_NAME[0],
            custom_cpu_model=cpu_model,
        )
        testflow.step("Start VM %s", config.VM_NAME[0])
        assert ll_vms.startVm(True, config.VM_NAME[0])
        testflow.step(
            "Attempting to migrate VM %s - expecting failure",
            config.VM_NAME[0]
        )
        assert ll_vms.migrateVm(True, config.VM_NAME[0])

    @tier2
    @polarion("RHEVM3-10659")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_different_hosts_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_pin_vm_with_custom_cpu_to_host(self):
        """
        Pin vm to host with supported custom cpu model
        where vm has custom cpu type.
        """
        supporting_host = virt_helper.get_hosts_by_cpu_model(
            cpu_model_name=(
                config.CLUSTER_CPU_PARAMS[config.MAX_HOST_CPU]['cpu']
            ),
            cluster=config.CLUSTER_NAME[0]
        )[0]
        testflow.step(
            "Pin VM to host %s that does support the custom cpu model",
            config.VM_NAME[0], supporting_host
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=config.VM_NAME[0],
            placement_affinity=config.VM_PINNED,
            placement_host=supporting_host
        )
        testflow.step("Start VM %s", config.VM_NAME[0])
        assert ll_vms.startVm(True, config.VM_NAME[0])


class TestClusterParamsOverrideLowerThanCluster(VirtTest):
    """
    Tests basic configuration and inheritance of custom cpu model
    """
    pool_name = 'custom__cpu_type_vm_pool'
    pool_params = copy.deepcopy(vm_pools_config.VM_POOLS_PARAMS)
    pool_params['size'] = 1
    vm_name = 'virt_dummy_vm'
    add_disk = False
    cluster_lower = False

    @tier2
    @polarion("RHEVM3-10377")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_edit_vm_update_cpu_type_lower_than_cluster(self):
        """
        Edit vm with custom cpu type which is lower than cluster level
        (checks only configuration).
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Update VM %s- set cpu type to a lower model than cluster %s ",
            config.VM_NAME[0], cpu_model
        )
        assert ll_vms.updateVm(
            True, config.VM_NAME[0], custom_cpu_model=cpu_model
        )

    @tier2
    @polarion("RHEVM3-11293")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        basic_teardown_fixture.__name__
    )
    def test_vm_with_cpu_type_lower_than_cluster(self):
        """
        Create and start vm - set cpu type to value lower than cluster value.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Add VM %s - set cpu model to value lower than the cluster",
            config.CPU_MODEL_VM
        )
        assert ll_vms.addVm(
            True,
            name=config.CPU_MODEL_VM,
            template=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0],
            custom_cpu_model=cpu_model,
        ), "Failed to add VM %s" % config.CPU_MODEL_VM
        testflow.step("Start VM %s", config.CPU_MODEL_VM)
        assert ll_vms.startVm(True, config.CPU_MODEL_VM)
        host_resource = helpers.get_host_resource_of_running_vm(
            config.CPU_MODEL_VM
        )
        assert virt_helper.check_vm_cpu_model(
            config.CPU_MODEL_VM, host_resource, cpu_model
        )

    @tier2
    @polarion("RHEVM3-10384 ")
    @pytest.mark.usefixtures(
        set_cpu_model_param.__name__,
        check_if_no_high_cpu_host_tests_should_run.__name__,
        revert_ge_vm_to_default_values.__name__
    )
    def test_run_once_with_cpu_type_lower_than_cluster(self):
        """
        run once vm - set cpu type to values lower than cluster value.
        """
        cpu_model = virt_helper.get_cpu_model_name_for_rest_api(
            config.CLUSTER_CPU_PARAMS[config.LOWER_CPU_MODEL]['cpu']
        )
        testflow.step(
            "Run once VM %s and set custom cpu model type with lower value"
            " than cluster", config.VM_NAME[0]
        )
        assert ll_vms.runVmOnce(
            positive=True,
            vm=config.VM_NAME[0],
            custom_cpu_model=cpu_model
        )
