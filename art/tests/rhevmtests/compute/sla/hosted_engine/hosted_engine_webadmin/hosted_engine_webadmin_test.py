"""
Test HE behaviour via the engine
"""
import pytest

import art.unittest_lib as u_libs
import time
import config as conf
import helpers
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_datacenters,
    hosts as ll_hosts,
    storagedomains as ll_sds,
    vms as ll_vms
)
from art.test_handler.tools import polarion, bz
from fixtures import (
    add_nic_to_he_vm,
    create_network,
    initialize_ge_constants,
    enable_global_maintenance,
    not_enough_cpus_skip_test,
    undeploy_he_host,
    update_he_vm,
    update_he_vm_cpus,
    update_he_vm_cpus_back,
    restart_he_vm
)
from rhevmtests.compute.sla.fixtures import (
    activate_hosts,
    create_quota,
    migrate_he_vm,
    update_datacenter
)

he_dst_host = 0


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    enable_global_maintenance.__name__,
    update_he_vm.__name__,
    restart_he_vm.__name__
)
class TestUpdateHeVmMemory(u_libs.SlaTest):
    """
    Update HE VM memory and check that HE VM has
    expected memory value via engine and via guest OS
    """
    he_params = {
        conf.VM_MEMORY: conf.EXPECTED_MEMORY,
        conf.VM_MEMORY_GUARANTEED: conf.EXPECTED_MEMORY,
        conf.VM_MAX_MEMORY: conf.HE_VM_MAX_MEMORY
    }

    @u_libs.tier2
    @polarion("RHEVM-15025")
    def test_he_vm_memory(self):
        """
        1) Check HE VM memory via the engine
        2) Check HE VM memory via guest OS
        """
        assert helpers.check_he_vm_memory_via_engine(
            expected_value=conf.EXPECTED_MEMORY
        )
        assert helpers.check_he_vm_memory_via_guest_os(
            expected_value=conf.EXPECTED_MEMORY
        )


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    enable_global_maintenance.__name__,
    not_enough_cpus_skip_test.__name__,
    update_he_vm.__name__,
    update_he_vm_cpus_back.__name__
)
@pytest.mark.incremental
class TestHotPlugAndUnplugCpus(u_libs.SlaTest):
    """
    Hotplug CPU's on HE VM and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """
    he_params = {
        conf.VM_MAX_MEMORY: conf.HE_VM_MAX_MEMORY
    }

    @staticmethod
    def update_and_check_cpus(sockets):
        """
        1) Update HE VM sockets number
        2) Check that HE VM has the expected number of sockets

        Args:
            sockets (int): Number of sockets
        """
        u_libs.testflow.step("Update HE VM sockets number to %s", sockets)
        assert ll_vms.updateVm(
            positive=True, vm=conf.HE_VM, cpu_socket=sockets
        )
        assert helpers.check_he_vm_cpu_via_engine(expected_value=sockets)
        assert helpers.check_he_vm_cpu_via_guest_os(expected_value=sockets)

    @u_libs.tier2
    @polarion("RHEVM-15027")
    def test_plug_cpu(self):
        """
        1) Check CPU hot plug
        """
        self.update_and_check_cpus(sockets=conf.EXPECTED_CPUS)

    @u_libs.tier2
    @polarion("RHEVM-19141")
    def test_unplug_cpu(self):
        """
        1) Check CPU hot unplug
        """
        self.update_and_check_cpus(sockets=conf.INIT_HE_VM_CPUS)


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    enable_global_maintenance.__name__,
    update_he_vm_cpus.__name__,
    restart_he_vm.__name__,
    update_he_vm_cpus_back.__name__,
)
class TestUpdateHeVmCpus(u_libs.SlaTest):
    """
    Update HE VM amount of CPU's and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """

    @u_libs.tier2
    @polarion("RHEVM-15023")
    def test_he_vm_cpus(self):
        """
        1) Check HE VM CPU's via the engine
        2) Check HE VM CPU's via guest OS
        """
        assert helpers.check_he_vm_cpu_via_engine(
            expected_value=conf.EXPECTED_CPUS
        )
        assert helpers.check_he_vm_cpu_via_guest_os(
            expected_value=conf.EXPECTED_CPUS
        )


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    enable_global_maintenance.__name__
)
class TestAddNicToHeVmWithManagementNetwork(u_libs.SlaTest):
    """
    Add with management network NIC to HE VM
    """

    @u_libs.tier2
    @polarion("RHEVM-17141")
    def test_add_nic(self):
        """
        Add NIC
        """
        u_libs.testflow.step(
            "Add NIC with the management network to the HE VM"
        )
        assert not ll_vms.addNic(
            positive=True,
            vm=conf.HE_VM,
            network=conf.MGMT_BRIDGE,
            name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    enable_global_maintenance.__name__,
    restart_he_vm.__name__,
    create_network.__name__,
    add_nic_to_he_vm.__name__
)
class TestAddNicToHeVmWithoutManagementNetwork(u_libs.SlaTest):
    """
    Add NIC to HE VM without management network and
    check if NIC appears under HE VM
    """

    @bz({"1539356": {}})
    @u_libs.tier2
    @polarion("RHEVM-15026")
    def test_he_vm_nic(self):
        """
        Check NIC via engine and via guest OS, before and after HE VM restart
        """
        assert helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        assert helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )

        assert helpers.apply_new_parameters_on_he_vm()

        assert helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        assert helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    migrate_he_vm.__name__,
    undeploy_he_host.__name__
)
class TestAddHostAndDeployHostedEngine(u_libs.SlaTest):
    """
    1) Add the host with HE deployment
    2) Undeploy the host
    3) Deploy the host
    """

    @u_libs.tier3
    @polarion("RHEVM-17142")
    def test_add_host(self):
        """
        Add the host and deploy HE on it
        """
        u_libs.testflow.step("Add the host %s to the engine", conf.HOSTS[1])
        assert ll_hosts.add_host(
            name=conf.HOSTS[1],
            address=conf.VDS_HOSTS[1].fqdn,
            root_password=conf.HOSTS_PW,
            cluster=conf.CLUSTER_NAME[0],
            comment=conf.VDS_HOSTS[1].ip,
            deploy_hosted_engine=True
        )

        u_libs.testflow.step(
            "Wait until the host %s will HE configured", conf.HOSTS[1]
        )
        assert helpers.wait_until_host_will_deploy_he(host_name=conf.HOSTS[1])
        assert helpers.deploy_hosted_engine_on_host(deploy=False)
        assert helpers.deploy_hosted_engine_on_host(deploy=True)
        u_libs.testflow.step(
            "Give %ss for sanlock lease update", conf.SLEEP_SANLOCK_UPDATE
        )
        time.sleep(conf.SLEEP_SANLOCK_UPDATE)


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    activate_hosts.__name__
)
class TestPutHostWithHAVmToMaintenance(u_libs.SlaTest):
    """
    Test that the HE agent has correct information
    when the user put the HE host to the maintenance via webadmin
    """
    hosts_to_activate_indexes = range(3)

    @u_libs.tier2
    @polarion("RHEVM-21316")
    def test_put_to_local_maintenance(self):
        """
        1) Put the host with HE VM to the maintenance
        2) Verify that the hosts has HE state LocalMaintenance and HE score 0
        3) Activate the host
        4) Verify that the HE host does not have
           local maintenance state and has HE score 3400
        """
        he_vm_host = ll_vms.get_vm_host(vm_name=conf.HE_VM)

        assert ll_hosts.deactivate_host(positive=True, host=he_vm_host)

        assert ll_hosts.activate_host(positive=True, host=he_vm_host)
        assert helpers.wait_for_hosts_he_attributes(
            hosts_names=[he_vm_host],
            expected_values={
                conf.PARAMS_HE_LOCAL_MAINTENANCE: False,
                conf.PARAMS_HE_SCORE: 3400
            },
            testflow_func=u_libs.testflow.step
        )


@pytest.mark.usefixtures(initialize_ge_constants.__name__)
class TestPutEnvironmentToGlobalMaintenance(u_libs.SlaTest):
    """
    Test that the HE agent has correct information when the user
    put the HE environment to the global maintenance via webadmin
    """

    @u_libs.tier2
    @polarion("RHEVM-21317")
    def test_put_to_global_maintenance(self):
        """
        1) Enable global maintenance
        2) Verify that the HE agent update HE information accordingly
        3) Disable global maintenance
        4) Verify that the HE agent update HE information accordingly
        """
        for enabled in (True, False):
            ll_vms.set_he_global_maintenance(
                vm_name=conf.HE_VM, enabled=enabled
            )
            assert helpers.wait_for_hosts_he_attributes(
                hosts_names=conf.HOSTS,
                expected_values={
                    conf.PARAMS_HE_GLOBAL_MAINTENANCE: enabled,
                    conf.PARAMS_HE_SCORE: 3400
                },
                testflow_func=u_libs.testflow.step
            )


@pytest.mark.usefixtures(initialize_ge_constants.__name__)
class TestNegativeHeVm(u_libs.SlaTest):
    """
    Negative hosted engine VM test cases

    1) Change the hosted engine VM name
    2) Poweroff the hosted engine VM name
    3) Create snapshot from the hosted engine VM
    4) Deactivate the primary hosted engine VM disk
    5) Unplug the primary hosted engine VM network interface
    """

    @u_libs.tier2
    @polarion("RHEVM-21318")
    def test_update_he_vm_name(self):
        """
        Update the hosted engine VM name
        """
        new_he_vm_name = "absolutely_new_he_vm"
        u_libs.testflow.step(
            "Update the hosted engine VM name to %s", new_he_vm_name
        )
        assert not ll_vms.updateVm(
            positive=True, vm=conf.HE_VM, name=new_he_vm_name
        )

    @u_libs.tier2
    @polarion("RHEVM-21320")
    def test_poweroff_he_vm(self):
        """
        Poweroff the hosted engine VM
        """
        u_libs.testflow.step("Poweroff the hosted engine VM")
        assert not ll_vms.stopVm(positive=True, vm=conf.HE_VM)

    @u_libs.tier2
    @polarion("RHEVM-21321")
    def test_make_snapshot_from_he_vm(self):
        """
        Make a snapshot from the hosted engine VM
        """
        u_libs.testflow.step("Make a snapshot from the hosted engine VM")
        assert not ll_vms.addSnapshot(
            positive=True,
            vm=conf.HE_VM,
            description="Hosted engine VM snapshot"
        )

    @u_libs.tier2
    @polarion("RHEVM-21322")
    def test_deactivate_he_vm_disk(self):
        """
        Deactivate the primary hosted engine VM disk
        """
        he_vm_disks_ids = ll_vms.get_vm_disks_ids(vm=conf.HE_VM)
        assert he_vm_disks_ids

        u_libs.testflow.step("Deactivate the primary hosted engine VM disk")
        assert not ll_vms.deactivateVmDisk(
            positive=True, vm=conf.HE_VM, diskId=he_vm_disks_ids[0]
        )

    @u_libs.tier2
    @polarion("RHEVM-21323")
    def test_unplug_he_vm_nic(self):
        """
        Unplug the primary hosted engine VM network interface
        """
        he_vm_nics = ll_vms.get_vm_nics_obj(vm_name=conf.HE_VM)
        assert he_vm_nics

        u_libs.testflow.step(
            "Unplug the primary hosted engine VM network interface"
        )
        assert not ll_vms.updateNic(
            positive=True,
            vm=conf.HE_VM,
            nic=he_vm_nics[0].get_name(),
            plugged=False
        )


@pytest.mark.usefixtures(initialize_ge_constants.__name__)
class TestNegativeHeStorageDomain(u_libs.SlaTest):
    """
    Negative HE storage domain tests

    1) Put the hosted engine storage domain to the maintenance
    """

    @u_libs.tier2
    @polarion("RHEVM-21324")
    def test_put_he_storage_domain_to_maintenance(self):
        """
        Put the hosted engine storage domain to the maintenance
        """
        u_libs.testflow.step(
            "Put the hosted engine storage domain to the maintenance"
        )
        assert not ll_sds.deactivateStorageDomain(
            positive=True,
            datacenter=conf.DC_NAME[0],
            storagedomain=conf.HE_STORAGE_DOMAIN
        )


@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    update_datacenter.__name__,
    create_quota.__name__
)
class TestNegativeHeQuota(u_libs.SlaTest):
    """
    Try to update HE VM quota and description when the datacenter
    has "Enforced" quota mode
    """
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_ENFORCED_MODE]
        }
    }
    quota_params = {
        conf.QUOTA_PARAMS_DC_NAME: conf.DC_NAME[0],
        conf.QUOTA_PARAMS_NAME: conf.TEST_PARAMS_QUOTA_NAME
    }

    @u_libs.tier1
    @polarion("RHEVM-25129")
    def test_update_he_vm(self):
        """
        Update HE VM quota and description
        """
        quota_id = ll_datacenters.get_quota_id_by_name(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.TEST_PARAMS_QUOTA_NAME
        )
        assert not ll_vms.updateVm(
            positive=True, vm=conf.HE_VM, quota=quota_id
        )
        assert ll_vms.updateVm(
            positive=True, vm=conf.HE_VM, description="Hosted-Engine VM"
        )
