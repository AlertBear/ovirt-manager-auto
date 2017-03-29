#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Migration cases for SR-IOV
"""

from time import sleep

import pytest

from art.rhevm_api.tests_lib.high_level import (
    networks as hl_networks,
    vms as hl_vms
)
from art.rhevm_api.tests_lib.low_level import (
    networks as ll_networks,
    vms as ll_vms
)
import config as sriov_conf
import helper
import rhevmtests.helpers as global_helper
from rhevmtests.networking import (
    config as conf,
    helper as network_helper
)
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, attr, testflow
from fixtures import (
    SRIOV, init_fixture, reset_host_sriov_params, set_num_of_vfs,
    modify_ifcfg_nm_controlled
)
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import store_vms_params


@pytest.fixture(scope="module", autouse=True)
def prepare_setup_migration(request):
    """
    Prepare networks for migration cases
    """
    sriov_migration = SRIOV()
    vm = sriov_conf.SRIOV_MIGRATION_VM
    mgmt_net = conf.MGMT_BRIDGE
    vnic = conf.VM_NIC_0
    sriov_net_1 = sriov_conf.MIGRATION_NETS[1][0]
    sriov_vnic_1 = sriov_conf.MIGRATION_TEST_VNICS[1][0]
    results = list()

    def fin4():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=results)
    request.addfinalizer(fin4)

    def fin3():
        """
        Enable network filter on ovirtmgmt vNIC profile
        """
        testflow.teardown(
            "Enable network filter %s on vNIC profile %s",
            conf.VDSM_NO_MAC_SPOOFING, conf.MGMT_BRIDGE,
        )
        results.append(
            (
                ll_networks.update_vnic_profile(
                    name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
                    network_filter=conf.VDSM_NO_MAC_SPOOFING,
                    data_center=sriov_migration.dc_0
                ), "fin3: ll_networks.update_vnic_profile"
            )
        )
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove networks from setup
        """
        testflow.teardown("Remove networks from setup")
        results.append(
            (
                hl_networks.remove_net_from_setup(
                    host=sriov_migration.host_0_name, all_net=True,
                    data_center=sriov_migration.dc_0
                ), "fin2: hl_networks.remove_net_from_setup"
            )
        )
    request.addfinalizer(fin2)

    @global_helper.wait_for_jobs_deco(["Removing VM"])
    def fin1():
        """
        Remove VM
        """
        testflow.teardown("Remove Vm %s", vm)
        results.append(
            (ll_vms.removeVm(positive=True, vm=vm), "fin1: ll_vms.removeVm")
        )
    request.addfinalizer(fin1)

    assert ll_networks.update_vnic_profile(
        name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE, network_filter="None",
        data_center=sriov_migration.dc_0
    )

    testflow.setup(
        "Create networks %s on datacenter %s and cluster %s",
        sriov_conf.MIGRATION_DICT, sriov_migration.dc_0,
        sriov_migration.cluster_0
    )
    network_helper.prepare_networks_on_setup(
        networks_dict=sriov_conf.MIGRATION_DICT, dc=sriov_migration.dc_0,
        cluster=sriov_migration.cluster_0
    )
    testflow.step(
        "Disable network filter on vNIC profile %s", conf.MGMT_BRIDGE
    )
    assert ll_networks.update_vnic_profile(
        name=mgmt_net, network=mgmt_net, network_filter="None",
        data_center=sriov_migration.dc_0

    )
    testflow.setup("create VM %s", vm)
    ll_vms.createVm(
        positive=True, vmName=vm, template=conf.TEMPLATE_NAME[0],
        cluster=sriov_migration.cluster_0,
    )
    testflow.setup("Get vNIC %s MAC address", vnic)
    sriov_conf.MIGRATION_NIC_1_MAC = ll_vms.get_vm_nic_mac_address(
        vm=vm, nic=vnic
    )
    assert sriov_conf.MIGRATION_NIC_1_MAC
    testflow.setup(
        "Add vNIC %s on VM %s with SR-IOV network", sriov_vnic_1, sriov_net_1
    )
    testflow.setup("Update vNIC profile %s to have passthrough", sriov_net_1)
    assert ll_networks.update_vnic_profile(
        name=sriov_net_1, network=sriov_net_1, pass_through=True,
        data_center=sriov_migration.dc_0
    )
    assert ll_vms.addNic(
        positive=True, vm=vm, name=sriov_vnic_1, network=sriov_net_1,
        interface=conf.PASSTHROUGH_INTERFACE, vnic_profile=sriov_net_1,
    )


@attr(tier=2)
@pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT, reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    init_fixture.__name__,
    reset_host_sriov_params.__name__,
    set_num_of_vfs.__name__,
    start_vm.__name__,
    store_vms_params.__name__,
    modify_ifcfg_nm_controlled.__name__,
)
class TestSriovMigration01(NetworkTest):
    """
    Try to migrate when:
        1. The 'passthrough' vNIC has no 'migratable' property
        2. There are no available VFs on destination host
        3. Not all of the VM's vNICs marked as migratable
    Migrate only with vf vNIC(no connection)
    Migrate with vf and virtIO vNIcs (BOND on guest)
    """

    # General
    vm_name = sriov_conf.SRIOV_MIGRATION_VM
    sriov_net_1 = sriov_conf.MIGRATION_NETS[1][0]
    sriov_net_2 = sriov_conf.MIGRATION_NETS[1][1]
    vnic = conf.VM_NIC_0
    sriov_vnic_1 = sriov_conf.MIGRATION_TEST_VNICS[1][0]
    sriov_vnic_2 = sriov_conf.MIGRATION_TEST_VNICS[1][1]

    # set_num_of_vfs
    hosts = [0, 1]  # reset_host_sriov_params
    num_of_vfs = 2

    # start_vm
    start_vms_dict = {
        vm_name: {}
    }

    # store_vms_params
    vms_to_store = [vm_name]

    @polarion("RHEVM-17060")
    def test_01_migrate_without_migratable_enables(self):
        """
        Try to migrate when the 'passthrough' vNIC has no 'migratable' property
        """
        testflow.step(
            "Try to migrate VM %s when 'migratable' is not enabled",
            self.vm_name
        )
        assert ll_vms.migrateVm(positive=False, vm=self.vm_name)

    @polarion("RHEVM-17061")
    def test_02_migrate_without_available_pf_on_dest_host(self):
        """
        Try to migrate when there are no available VFs on destination host
        """
        # checking where vm running to disable VFs on destination host for
        # negative test.
        sriov_conf.HOST_NAME = ll_vms.get_vm_host(vm_name=self.vm_name)
        assert sriov_conf.HOST_NAME
        host = 0 if conf.HOST_0_NAME != sriov_conf.HOST_NAME else 1
        host_pf = "HOST_%s_PF_OBJECT_1" % host
        sriov_conf.PF_OBJECT = getattr(sriov_conf, host_pf)

        testflow.step(
            "Set number of VFs to 0 on host %s", sriov_conf.HOST_NAME
        )
        assert sriov_conf.PF_OBJECT.set_number_of_vf(0)
        testflow.step(
            "Set 'migratable' property on vNIC %s on VM %s",
            self.sriov_net_1, self.vm_name
        )
        assert ll_networks.update_vnic_profile(
            name=self.sriov_net_1, network=self.sriov_net_1, migratable=True
        )
        testflow.step(
            "Try to migrate VM %s when no VFs are available on the "
            "destination host", self.vm_name
        )
        assert ll_vms.migrateVm(positive=False, vm=self.vm_name)
        testflow.step(
            "Set number of VFs to 2 on host %s", sriov_conf.HOST_NAME
        )
        assert sriov_conf.PF_OBJECT.set_number_of_vf(2)

    @polarion("RHEVM-17177")
    def test_03_migrate_when_not_all_vnics_have_migratable_enabled(self):
        """
        Try to migrate when not all of the VM's vNICs marked as migratable
        """
        testflow.setup(
            "Update vNIC profile %s to have passthrough", self.sriov_net_2
        )
        assert ll_networks.update_vnic_profile(
            name=self.sriov_net_2, network=self.sriov_net_2, pass_through=True
        )
        testflow.setup(
            "Add vNIC %s on VM %s with SR-IOV network",
            self.sriov_vnic_2, self.sriov_net_2
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm_name, name=self.sriov_vnic_2,
            network=self.sriov_net_2, interface=conf.PASSTHROUGH_INTERFACE,
            vnic_profile=self.sriov_net_2
        )
        testflow.step(
            "Try to migrate VM %s when not all vNIC profiles have "
            "'migratable' property enabled", self.vm_name
        )
        assert ll_vms.migrateVm(positive=False, vm=self.vm_name)
        testflow.step("Update vNIC %s to be un-plugged", self.sriov_vnic_2)
        assert ll_vms.updateNic(
            positive=True, vm=self.vm_name, nic=self.sriov_vnic_2,
            plugged=False
        )
        testflow.step(
            "Remove vNIC %s from VM %s", self.sriov_vnic_2, self.vm_name
        )
        assert ll_vms.removeNic(
            positive=True, vm=self.vm_name, nic=self.sriov_vnic_2
        )

    @polarion("RHEVM-17056")
    def test_04_migrate_only_with_vf_vnic(self):
        """
        Migrate only with vf vNIC (no connection while migration)
        """
        vm_ip = conf.VMS_TO_STORE.get(self.vm_name).get("ip")
        testflow.step(
            "Check connectivity to VM %s before migration", self.vm_name
        )
        assert conf.ENGINE_HOST.network.send_icmp(dst=vm_ip)
        testflow.step("Migrate VM %s", self.vm_name)
        assert ll_vms.migrateVm(positive=True, vm=self.vm_name)
        testflow.step(
            "Check connectivity to VM %s after migration", self.vm_name
        )
        assert conf.ENGINE_HOST.network.send_icmp(dst=vm_ip)

    @polarion("RHEVM-19183")
    def test_05_check_vnic_plugged_after_migration(self):
        """
        Check that SR-IOV vNIC is plugged after migration
        """
        testflow.step("Check the vNIC %a is plugged after migration")
        assert ll_vms.get_vm_nic_plugged(
            vm=self.vm_name, nic=self.sriov_vnic_1
        )

    @polarion("RHEVM-17059")
    def test_06_migrate_with_bond_in_guest(self):
        """
        Migrate with vf and virtIO vNIcs (BOND on guest)
        """
        vm_resource = conf.VMS_TO_STORE.get(self.vm_name).get("resource")
        testflow.step("Create BOND on VM %s", self.vm_name)
        helper.create_bond_on_vm(
            vm_name=self.vm_name, vm_resource=vm_resource,
            vnics=[self.sriov_vnic_1, conf.VM_NIC_0]
        )
        testflow.step("Get VM %s IP after BOND creation", self.vm_name)
        vm_ip = hl_vms.get_vm_ip(vm_name=self.vm_name, start_vm=False)
        assert vm_ip
        testflow.step(
            "Check connectivity to VM %s before migration over BOND",
            self.vm_name
        )
        assert conf.ENGINE_HOST.network.send_icmp(dst=vm_ip)
        for i in xrange(2):
            vm_host = ll_vms.get_vm_host(vm_name=self.vm_name)
            assert vm_host
            ping_kwargs = {
                "src_resource": conf.ENGINE_HOST,
                "dst": vm_ip,
                "count": "30"
            }
            migrate_kwargs = {
                "vms_list": [self.vm_name],
                "src_host": vm_host,
                "vm_os_type": "rhel",
                "vm_user": conf.VMS_LINUX_USER,
                "vm_password": conf.VMS_LINUX_PW,
            }
            testflow.step(
                "Migrating VM: %s from host: %s and testing ping "
                "from Engine to the VM", self.vm_name, vm_host,
            )
            assert helper.check_ping_during_vm_migration(
                ping_kwargs=ping_kwargs, migration_kwargs=migrate_kwargs
            )
            sleep(5)
