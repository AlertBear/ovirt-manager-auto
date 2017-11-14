#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per cluster networking feature test cases

The following elements will be used for the testing:
Data-Centers, clusters, MAC pools, storage domain, VM, templates, vNICs
"""

import pytest

import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import config as mac_pool_conf
import helper
import rhevmtests.networking.config as conf
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    mac_pool as ll_mac_pool,
    vms as ll_vms
)
from art.test_handler.tools import polarion
from art.unittest_lib import NetworkTest, testflow, tier2
from fixtures import (
    mac_pool_per_cl_prepare_setup,
    create_mac_pools,
    create_cluster_with_mac_pools,
    update_clusters_mac_pool,
    add_vnics_to_template,
    create_vm_from_template,
    set_stateless_vm,
    take_vms_snapshot,
    undo_snapshot_preview
)
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (
    add_vnics_to_vms,
    remove_vnics_from_vms
)


class TestMacPoolRange01(NetworkTest):
    """
    1.  Try to use old configuration with engine-config
    2.  Check that invalid engine config commands are deprecated
        (MacPoolRanges and MaxMacCountPool)
    """

    @tier2
    @polarion("RHEVM3-6442")
    def test_invalid_engine_commands(self):
        """
        1.  Negative: try to configure deprecated MacPoolRanges
        2.  Negative: try to configure deprecated MaxMacCountPool
        """
        mac_range = "00:1a:4a:4c:7a:00-00:1a:4a:4c:7a:ff"
        cmd1 = "=".join([mac_pool_conf.MAC_POOL_RANGE_CMD, mac_range])
        cmd2 = "=".join([mac_pool_conf.MAX_COUNT_POOL_CMD, "100001"])

        for cmd in (cmd1, cmd2):
            testflow.step("Negative: use dep cmd: %s ", cmd.split("=")[0])
            assert not conf.ENGINE.engine_config(
                action='set', param=cmd, restart=False
            ).get('results')


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    create_cluster_with_mac_pools.__name__,
)
class TestMacPoolRange02(NetworkTest):
    """
    1.  Recreate cluster with custom MAC pool and make sure it was recreated
        with the Default MAC pool
    2.  Try to remove default MAC pool
    3.  Extend and shrink Default MAC pool ranges
    """
    # General parameters
    ext_cl = mac_pool_conf.EXT_CL_1
    mac_pool = mac_pool_conf.MAC_POOL_NAME_0
    def_mac_pool = mac_pool_conf.DEFAULT_MAC_POOL
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        mac_pool: [range_list, False]
    }

    # create_cluster_with_mac_pools fixture parameters
    create_cl_with_mac_pools_params = {
        ext_cl: [mac_pool, True]
    }

    @tier2
    @polarion("RHEVM3-6462")
    def test_01_recreate_cluster(self):
        """
        1.  Recreate just removed cluster
        2.  Make sure that the cluster was recreated with the default MAC pool
        3.  Remove cluster
        4.  Make sure default MAC pool still exists
        """
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl)
        testflow.step("Recreate cluster without explicitly providing MAC pool")
        assert helper.create_cluster_with_mac_pool(mac_pool_name="")
        pool_id = ll_mac_pool.get_mac_pool_from_cluster(cluster=self.ext_cl).id
        assert ll_mac_pool.get_default_mac_pool().id == pool_id
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl)
        testflow.step("Make sure default MAC pool still exists")
        assert ll_mac_pool.get_mac_pool(pool_name=self.def_mac_pool)

    @tier2
    @polarion("RHEVM3-6457")
    def test_02_remove_default_mac_pool(self):
        """
        Negative: remove of Default MAC pool should fail
        """
        testflow.step("Negative: try to remove default MAC pool range.")
        assert not ll_mac_pool.remove_mac_pool(mac_pool_name=self.def_mac_pool)

    @tier2
    @polarion("RHEVM3-6443")
    def test_03_default_mac_pool(self):
        """`
        1.  Extend the default range values of Default MAC pool
        2.  Shrink the default range values of Default MAC pool
        3.  Add new ranges to the Default MAC pool
        4.  Remove added ranges from the Default MAC pool
        5.  Create a new cluster and check it was created with default MAC
            pool values
        """
        testflow.step("Extend and shrink the default MAC pool range")
        assert helper.update_mac_pool_range_size(
            mac_pool_name=self.def_mac_pool, size=(2, 2)
        )
        testflow.step("Shrink the default range values of Default MAC pool")
        assert helper.update_mac_pool_range_size(
            mac_pool_name=self.def_mac_pool, extend=False, size=(-2, -2)
        )
        testflow.step("Add new ranges to the Default MAC pool")
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.def_mac_pool, range_list=self.range_list
        )
        testflow.step("Remove added ranges from the Default MAC pool")
        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.def_mac_pool, range_list=self.range_list
        )
        testflow.step("Create a new cluster")
        assert helper.create_cluster_with_mac_pool(mac_pool_name='')
        testflow.step("Check it was created with default MAC pool values")
        mac_pool_id = ll_mac_pool.get_mac_pool_from_cluster(
            cluster=self.ext_cl
        ).get_id()
        assert ll_mac_pool.get_default_mac_pool().get_id() == mac_pool_id


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__
)
class TestMacPoolRange03(NetworkTest):
    """
    1.  Auto vs manual MAC assignment when allow duplicate is False
    2.  Add and remove ranges to/from MAC pool
    3.  Creating vNICs with updated MAC pool takes the MACs from the new pool
    4.  Negative: try to create a MAC pool with the already occupied name
    5.  Create a MAC pool with occupied MAC pool range
    6.  Creating pool with the same name
    7.  Creating pool with the same range
    """
    # General parameters
    ext_cl = mac_pool_conf.MAC_POOL_CL
    ext_cl_1 = mac_pool_conf.EXT_CL_1
    vm = mac_pool_conf.MP_VM_0
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    pool_1 = mac_pool_conf.MAC_POOL_NAME_1
    pool_2 = mac_pool_conf.MAC_POOL_NAME_2
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        pool_0: [[mac_pool_conf.MAC_POOL_RANGE_LIST[0]], False],
        pool_1: None,
        pool_2: None
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }

    @tier2
    @polarion("RHEVM3-6451")
    def test_01_auto_assigned_vs_manual(self):
        """
        1.  Add VNICs to the VM until MAC pool is exhausted
        2.  Fail on adding extra VNIC with auto assigned MAC to VM
        3.  Add MAC manually (not from a range) and succeed
        """
        manual_mac = "00:00:00:12:34:56"
        testflow.step("Add VNICs to the VM until MAC pool is exhausted")
        for nic in [mac_pool_conf.CASE_3_NIC_1, mac_pool_conf.CASE_3_NIC_2]:
            assert ll_vms.addNic(positive=True, vm=self.vm, name=nic)

        testflow.step("Fail on adding extra VNIC with auto assigned MAC to VM")
        assert ll_vms.addNic(
            positive=False, vm=self.vm, name=mac_pool_conf.CASE_3_NIC_3
        )

        testflow.step("Add MAC manually (not from a range) and succeed")
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=mac_pool_conf.CASE_3_NIC_3,
            mac_address=manual_mac
        )

    @tier2
    @polarion("RHEVM3-6449")
    def test_02_add_remove_ranges(self):
        """
        1.  Add 2 new MAC pool ranges
        2.  Remove one of the added MAC pool ranges
        3.  Check that the correct MAC pool ranges still exist in the range
            list
        """
        testflow.step("Add 2 new ranges")
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_0, range_list=self.range_list[1:3]
        )

        testflow.step("Remove one of the added ranges")
        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.range_list[1]]
        )
        ranges = ll_mac_pool.get_mac_range_values(
            mac_pool_obj=ll_mac_pool.get_mac_pool(pool_name=self.pool_0)
        )
        assert len(ranges) == 2
        assert self.range_list[1] not in ranges

        testflow.step("Check that the correct ranges still exists")
        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.range_list[2]]
        )

    @tier2
    @polarion("RHEVM3-6444")
    def test_03_update_mac_pool_vm(self):
        """
        1.  Check that VM NIC is created with MAC from the first MAC pool range
        2.  Check that for updated cluster with new MAC pool, the NICs on the
            VM on that cluster are created with MACs from the new MAC pool
            range
        """
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.range_list[1]]
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=mac_pool_conf.CASE_3_NIC_4
        )
        testflow.step(
            "Check that VM NIC is created with MAC from the first MAC pool "
            "range"
        )
        assert helper.check_mac_in_range(
            vm=self.vm, nic=mac_pool_conf.CASE_3_NIC_4,
            mac_range=self.range_list[1]
        )
        testflow.step(
            "Check that for updated cluster with new MAC pool, the NICs on "
            "the VM on that cluster are created with MACs from the new MAC "
            "pool range"
        )
        for vnic in mac_pool_conf.CASE_3_ALL_NICS:
            assert ll_vms.removeNic(positive=True, vm=self.vm, nic=vnic)

        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.range_list[1]]
        )

    @tier2
    @polarion("RHEVM3-6445")
    def test_04_creation_pool_same_name(self):
        """
        Test creation of a new pool with the same name, but different range
        """
        testflow.step("Create new pool with same name, but different range")
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=[self.range_list[0]], positive=False
        )

    @tier2
    @polarion("RHEVM3-6446")
    def test_05_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        testflow.step("Create new pool with same range, but different names")
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_1, ranges=[self.range_list[0]]
        )

    @tier2
    @polarion("RHEVM3-6458")
    def test_06_remove_used_mac_pool(self):
        """
        Negative: try to remove MAC pool that is already assigned to cluster
        """
        testflow.step(
            "Negative: try to remove MAC pool that is already assigned to "
            "cluster"
        )
        assert not ll_mac_pool.remove_mac_pool(self.pool_0)

    @tier2
    @polarion("RHEVM3-6459")
    def test_07_remove_unused_mac_pool(self):
        """
        1.  Assign another MAC pool to cluster
        2.  Remove the MAC pool previously attached to cluster
        """
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_2, ranges=[self.range_list[2]]
        )
        testflow.step("Assign another MAC pool to cluster")
        mac_pool = ll_mac_pool.get_mac_pool(self.pool_2)
        assert ll_clusters.updateCluster(
            positive=True, cluster=self.ext_cl, mac_pool=mac_pool
        )
        testflow.step("Remove the MAC pool previously attached to cluster")
        assert ll_mac_pool.remove_mac_pool(mac_pool_name=self.pool_0)

    @tier2
    @polarion("RHEVM3-6460")
    def test_08_remove_cluster(self):
        """
        1.  Remove cluster
        2.  Make sure that the MAC pool is not removed
        """
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=[self.range_list[0]]
        )
        assert helper.create_cluster_with_mac_pool()
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl_1)
        testflow.step("Make sure that the MAC pool is not removed")
        assert ll_mac_pool.get_mac_pool(self.pool_0)


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    remove_vnics_from_vms.__name__
)
class TestMacPoolRange04(NetworkTest):
    """
    1.  Shrink MAC pool range
    2.  Check that you can add VNICs if you don't reach the limit of the MAC
        pool range
    4.  Shrinking the MAC pool to the size equal to the number of VM NICs will
        not allow adding additional VNICs to VM
    5.  Extend MAC pool range
    6.  Check that you can add VNICs till you reach the limit of the MAC pool
        range
    7.  Extending the MAC pool range by 2 will let you add 2 additional VNICs
        only
    """
    # General parameters
    ext_cl = mac_pool_conf.MAC_POOL_CL
    vm = mac_pool_conf.MP_VM_0
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        pool_0: [[mac_pool_conf.MAC_POOL_RANGE_LIST[1]], False]
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {vm: {}}
    for i, nic in enumerate(mac_pool_conf.CASE_4_REMOVE_NICS):
        remove_vnics_vms_params[vm][i] = {
            "name": nic
        }

    @tier2
    @polarion("RHEVM3-6448")
    def test_01_range_limit_shrink(self):
        """
        1.  Add VNICs to the VM
        2.  Shrink the MAC pool, so you can add only one new VNIC
        3.  Add one VNIC and succeed
        4.  Try to add additional VNIC to VM and fail
        """
        testflow.step("Add VNICs to the VM and shrink the MAC pool")
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=mac_pool_conf.CASE_4_NIC_1
        )
        assert helper.update_mac_pool_range_size(extend=False, size=(0, -1))
        testflow.step("Add one VNIC and succeed")
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=mac_pool_conf.CASE_4_NIC_2
        )
        testflow.step("Try to add additional VNIC to VM and fail")
        assert ll_vms.addNic(
            positive=False, vm=self.vm, name=mac_pool_conf.CASE_4_NIC_3
        )

    @tier2
    @polarion("RHEVM3-6447")
    def test_02_range_limit_extend(self):
        """
        1.  Extend the MAC pool range
        2.  Add another VNICs (until you reach range limit again)
        3.  Fail when you try to overcome that limit
        """
        testflow.step("Extend the MAC pool range")
        assert helper.update_mac_pool_range_size()
        testflow.step("Add another VNICs (until you reach range limit again)")
        for vnic in [mac_pool_conf.CASE_4_NIC_3, mac_pool_conf.CASE_4_NIC_4]:
            assert ll_vms.addNic(positive=True, vm=self.vm, name=vnic)
        testflow.step("Fail when you try to overcome that limit")
        assert ll_vms.addNic(
            positive=False, vm=self.vm, name=mac_pool_conf.CASE_4_NIC_5
        )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__
)
class TestMacPoolRange05(NetworkTest):
    """
    1.  Non-Continues ranges in MAC pool
    2.  Check that you can add VNICs according to the number of MAC ranges when
        each MAC range has only one MAC address in the pool
    """
    # General settings
    ext_cl = mac_pool_conf.MAC_POOL_CL
    vm = mac_pool_conf.MP_VM_0
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    mac_pool_ranges = [
        ("00:00:00:10:10:10", "00:00:00:10:10:10"),
        ("00:00:00:10:10:20", "00:00:00:10:10:20"),
        ("00:00:00:10:10:30", "00:00:00:10:10:30"),
        ("00:00:00:10:10:40", "00:00:00:10:10:40"),
        ("00:00:00:10:10:50", "00:00:00:10:10:50"),
        ("00:00:00:10:10:60", "00:00:00:10:10:60")
    ]

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        pool_0: [mac_pool_ranges[:3], False]
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {vm: {}}
    for i, nic in enumerate(mac_pool_conf.CASE_5_SETUP_NICS):
        add_vnics_vms_params[vm][i] = {
            "name": nic
        }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = {vm: {}}
    for i, nic in enumerate(mac_pool_conf.CASE_5_ALL_NICS):
        remove_vnics_vms_params[vm][i] = {
            "name": nic
        }

    @tier2
    @polarion("RHEVM3-6450")
    def test_non_continuous_ranges(self):
        """
        Test VNICs have non-continuous MACs (according to the ranges values)
        """
        testflow.step(
            "Non-Continues ranges in MAC pool Check that you can add VNICs "
            "according to the number of MAC ranges when each MAC range has "
            "only one MAC address in the pool"
        )
        assert helper.check_single_mac_range_match(
            vm=self.vm, vm_vnics=mac_pool_conf.NICS_NAME[5][:3],
            mac_ranges=self.mac_pool_ranges[:3]
        )
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_0, range_list=self.mac_pool_ranges[3:5]
        )
        for vnic in [mac_pool_conf.CASE_5_NIC_4, mac_pool_conf.CASE_5_NIC_5]:
            assert ll_vms.addNic(positive=True, vm=self.vm, name=vnic)
        assert helper.check_single_mac_range_match(
            vm=self.vm, vm_vnics=mac_pool_conf.NICS_NAME[5][3:5],
            mac_ranges=self.mac_pool_ranges[3:5]
        )
        testflow.step(
            "Remove the last added range, add another one and check that "
            "a new vNIC takes MAC from the new added Range"
        )
        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.mac_pool_ranges[4]]
        )
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.mac_pool_ranges[5]]
        )
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=mac_pool_conf.CASE_5_NIC_6
        )
        nic_mac = ll_vms.get_vm_nic_mac_address(
            vm=self.vm, nic=mac_pool_conf.CASE_5_NIC_6
        )
        assert nic_mac == self.mac_pool_ranges[-1][0]


@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    add_vnics_to_template.__name__,
    create_vm_from_template.__name__
)
class TestMacPoolRange06(NetworkTest):
    """
    1.  Create VM from Template
    2.  Check that VNIC created from template uses the correct MAC POOL value
    3.  Add 2 more VNICs to template, so it will be impossible to create a new
        VM from that template
    4.  Check that creating new VM from template fails
    """
    # General parameters
    ext_cl = mac_pool_conf.MAC_POOL_CL
    cluster = mac_pool_conf.MAC_POOL_CL
    template = mac_pool_conf.MP_TEMPLATE
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    mp_vm = mac_pool_conf.MP_VM_CASE_6
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        pool_0: [[range_list[0]], False]
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }

    # add_vnics_to_template fixture parameters
    add_vnics_to_template_params = {
        template: [mac_pool_conf.CASE_6_NIC_1, mac_pool_conf.CASE_6_NIC_2]
    }

    # remove_vnics_from_template fixture parameters
    remove_vnics_from_template_params = add_vnics_to_template_params

    # create_vm_from_template fixture parameters
    create_vm_from_template_params = {
        mp_vm: template
    }

    @tier2
    @polarion("RHEVM3-6455")
    def test_vm_from_template(self):
        """
        1.  Check that the VNIC is created from template that uses the correct
            MAC pool values
        2.  Negative: try to create new VM from template when there are not
            enough MACs for its VNICs
        """
        testflow.step(
            "vNIC is created from template that uses the valid MAC pool values"
        )
        assert helper.check_mac_in_range(
            vm=self.mp_vm, nic=mac_pool_conf.CASE_6_NIC_1,
            mac_range=self.range_list[0]
        )
        testflow.step(
            "Negative: try to create new VM from template when there are not "
            "enough MACs for its VNICs"
        )
        assert ll_vms.createVm(
            positive=False, vmName="neg_vm", cluster=self.cluster,
            template=self.template
        )


@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    create_cluster_with_mac_pools.__name__
)
class TestMacPoolRange07(NetworkTest):
    """
    Removal of cluster with custom MAC pool when that MAC pool is assigned to
        2 clusters
    """
    # General parameters
    ext_cl_1 = mac_pool_conf.EXT_CL_2
    ext_cl_2 = mac_pool_conf.EXT_CL_3
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        pool_0: [[range_list[0]], False]
    }

    # create_cluster_with_mac_pools fixture parameters
    create_cl_with_mac_pools_params = {
        ext_cl_1: [pool_0, False],
        ext_cl_2: [pool_0, False]
    }

    @tier2
    @polarion("RHEVM3-6461")
    def test_remove_two_clusters(self):
        """
        1.  Remove clusters
        2.  Make sure that the MAC pool is not removed
        """
        for cl in [self.ext_cl_1, self.ext_cl_2]:
            assert ll_clusters.removeCluster(positive=True, cluster=cl)
            testflow.step(
                "Make sure %s exists after cluster removal" % self.pool_0
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(pool_name=self.pool_0)
            assert mac_pool_obj, "MAC pool was removed during %s removal" % cl

            if cl == self.ext_cl_1:
                testflow.step(
                    "Make sure %s is attached to %s after removal of the "
                    "first cluster", self.pool_0, self.ext_cl_2
                )
                mac_on_cl = ll_mac_pool.get_mac_pool_from_cluster(
                    cluster=self.ext_cl_2
                )
                assert mac_on_cl.name == mac_pool_obj.name


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__,
    set_stateless_vm.__name__,
    start_vm.__name__
)
class TestMacPoolRange08(NetworkTest):
    """
    Test VM stateless mode with MAC address changes:

    1. Verify that the VM MAC address is blocked from being used
    2. Verify that on VM shutdown, it restores the default MAC address
    """
    # general parameters
    vm_0_mac_address = mac_pool_conf.MAC_POOL_RANGE_LIST[0][0]
    vm_1_mac_address = mac_pool_conf.MAC_POOL_RANGE_LIST[1][0]
    arbitrary_mac_address = mac_pool_conf.MAC_POOL_RANGE_LIST[2][0]

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        mac_pool_conf.MAC_POOL_NAME_0: (
            [mac_pool_conf.MAC_POOL_RANGE_LIST, False]
        )
    }

    # set_stateless_vm fixture parameters
    set_stateless_vm_param = mac_pool_conf.MP_VM_0

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {
        mac_pool_conf.MP_VM_0: {
            "1": {
                "name": mac_pool_conf.CASE_8_NIC_1,
                "mac_address": vm_0_mac_address,
                "network": conf.MGMT_BRIDGE
            }
        },
        mac_pool_conf.MP_VM_1: {
            "1": {
                "name": mac_pool_conf.CASE_8_NIC_1,
                "mac_address": vm_1_mac_address,
                "network": conf.MGMT_BRIDGE
            }
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = add_vnics_vms_params

    # start_vm fixture parameters
    start_vms_dict = {
        mac_pool_conf.MP_VM_0: {}
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        mac_pool_conf.MAC_POOL_CL: mac_pool_conf.MAC_POOL_NAME_0
    }

    @tier2
    @polarion("RHEVM-23232")
    def test_01_mac_assignment_on_vnic_unplug(self):
        """
        1. Hot-unplug vNIC from MP_VM_0
        2. NEGATIVE: try to assign MP_VM_0 MAC address on MP_VM_1
        """
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_8_NIC_1, plugged=False
        )
        assert ll_vms.updateNic(
            positive=False, vm=mac_pool_conf.MP_VM_1,
            nic=mac_pool_conf.CASE_8_NIC_1, mac_address=self.vm_0_mac_address
        )

    @tier2
    @polarion("RHEVM-22434")
    def test_02_test_mac_assignment_on_running_stateless_vm(self):
        """
        1. Hot-unplug vNIC from MP_VM_0
        2. Remove vNIC from MP_0
        3. NEGATIVE: try to assign MP_VM_0 MAC address on MP_VM_1
        """
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_8_NIC_1, plugged=False
        )
        assert ll_vms.removeNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_8_NIC_1
        )
        assert ll_vms.updateNic(
            positive=False, vm=mac_pool_conf.MP_VM_1,
            nic=mac_pool_conf.CASE_8_NIC_1, mac_address=self.vm_0_mac_address
        )
        # Restore MP_VM_0 vNIC with differnet MAC address
        assert ll_vms.addNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            name=mac_pool_conf.CASE_8_NIC_1,
            mac_address=self.arbitrary_mac_address, network=conf.MGMT_BRIDGE,
            plugged=True
        )

    @tier2
    @polarion("RHEVM-22435")
    def test_03_mac_assignment_on_stopped_stateless_vm(self):
        """
        1. Assign arbitrary MAC address on vNIC on MP_VM_0 (done in previous
           test steps)
        2. Shutdown MP_VM_0
        3. Verify that the MAC address on MP_VM_0 is restored (VM is stateless)
        """
        testflow.step(
            "Shutting down VM: %s to restore state", mac_pool_conf.MP_VM_0
        )
        assert helper.shutdown_stateless_vm(
            vm=mac_pool_conf.MP_VM_0, dc=conf.DC_0
        )
        testflow.step(
            "Comparing VM: %s vNIC MAC address with original MAC address",
            mac_pool_conf.MP_VM_0
        )
        assert ll_vms.get_vm_nic_mac_address(
            vm=mac_pool_conf.MP_VM_0, nic=mac_pool_conf.CASE_8_NIC_1
        ) == self.vm_0_mac_address


@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    remove_vnics_from_vms.__name__,
    add_vnics_to_vms.__name__,
    take_vms_snapshot.__name__,
    undo_snapshot_preview.__name__,
    start_vm.__name__
)
class TestMacPoolRange09(NetworkTest):
    """
    Test VM with preview snapshot:

    1. Verify that the snapshot allocates new MAC when it is already allocated
    2. Verify that the snapshot restores the original MAC address on VM
    3. Verify that while VM is in snapshot preview state, other VM can't be
       assigned with its MAC address
    4. Verify that snapshot preview action fails when there no MAC are
       available on the pool
    """
    # General parameters
    vm_0_mac_address_1 = "00:00:00:10:10:10"
    vm_1_mac_address_1 = "00:00:00:10:10:11"
    out_of_scope_mac_address_1 = "00:00:00:10:10:12"
    out_of_scope_mac_address_2 = "00:00:00:10:10:13"
    mac_pool_snapshot = "MAC_pool_snapshot_c9"

    # undo_snapshot_preview, take_vms_snapshot fixture parameters
    vms_snapshot = {
        mac_pool_conf.MP_VM_0: mac_pool_snapshot,
        mac_pool_conf.MP_VM_1: mac_pool_snapshot
    }

    # create_mac_pools fixture parameters
    create_mac_pools_params = {
        mac_pool_conf.MAC_POOL_NAME_0: (
            [[mac_pool_conf.MAC_POOL_RANGE_LIST[0]], False]
        )
    }

    # add_vnics_to_vms fixture parameters
    add_vnics_vms_params = {
        mac_pool_conf.MP_VM_0: {
            1: {
                "name": mac_pool_conf.CASE_9_NIC_1,
                "mac_address": vm_0_mac_address_1,
                "network": conf.MGMT_BRIDGE
            }
        },
        mac_pool_conf.MP_VM_1: {
            "1": {
                "name": mac_pool_conf.CASE_9_NIC_1,
                "mac_address": vm_1_mac_address_1,
                "network": conf.MGMT_BRIDGE
            },
            "2": {
                "name": mac_pool_conf.CASE_9_NIC_2,
                "mac_address": out_of_scope_mac_address_1,
                "network": conf.MGMT_BRIDGE,
                "plugged": False
            }
        }
    }

    # remove_vnics_from_vms fixture parameters
    remove_vnics_vms_params = add_vnics_vms_params

    # start_vm fixture parameters
    start_vms_dict = {
        mac_pool_conf.MP_VM_0: {},
        mac_pool_conf.MP_VM_1: {}
    }

    # update_clusters_mac_pool fixture parameters
    update_cls_mac_pool_params = {
        mac_pool_conf.MAC_POOL_CL: mac_pool_conf.MAC_POOL_NAME_0
    }

    @tier2
    @polarion("RHEVM-22436")
    def test_01_test_mac_assignment_on_another_vm_with_snapshot(self):
        """
        1. Unplug MP_VM_0 vNIC and assign MAC: out_of_scope_mac_address_2
        2. Unplug MP_VM_1 vNIC and assign MAC: vm_0_mac_address_1
        3. Preview a snapshot on VM_0
        4. Verify that MP_VM_0 vNIC MAC address is renewed and allocated
           from the pool (already allocated to VM_1)
        5. Preparation step for test_03_test_mac_pool_full_with_snapshot test:
           Undo snapshot preview on VM_0
        6. Start MP_VM_0
        """
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_9_NIC_1,
            mac_address=self.out_of_scope_mac_address_2, plugged=False
        )
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_1,
            nic=mac_pool_conf.CASE_9_NIC_1,
            mac_address=self.vm_0_mac_address_1, plugged=False
        )
        testflow.step("Previewing VM: %s snaphost", mac_pool_conf.MP_VM_0)
        assert helper.preview_snapshot_on_vm(
            vm=mac_pool_conf.MP_VM_0, snapshot_desc=self.mac_pool_snapshot
        )
        vm_0_mac_address = ll_vms.get_vm_nic_mac_address(
            vm=mac_pool_conf.MP_VM_0, nic=mac_pool_conf.CASE_9_NIC_1
        )
        assert vm_0_mac_address == self.vm_1_mac_address_1, (
            "VM: %s vNIC assigned with reserved MAC address"
            % mac_pool_conf.MP_VM_0
        )
        testflow.step(
            "Undoing VM: %s snapshot: %s", mac_pool_conf.MP_VM_0,
            self.mac_pool_snapshot
        )
        assert helper.undo_snapshot_and_wait(
            vm=mac_pool_conf.MP_VM_0, snapshot_desc=self.mac_pool_snapshot
        )
        assert ll_vms.startVm(
            positive=True, vm=mac_pool_conf.MP_VM_0, wait_for_status="up"
        )

    @tier2
    @polarion("RHEVM-22437")
    def test_02_test_mac_assignment_with_snapshot(self):
        """
        1. Unplug MP_VM_1 vNIC and assign different MAC from what is used in
           its snapshot (already done in the previous test steps)
        2. Unplug MP_VM_0 vNIC and assign MAC: out_of_scope_mac_address_2
           (to allow next step to restore MP_VM_1 vNIC MAC address)
        3. Preview a snapshot on MP_VM_1
        4. Verify that the MAC address on MP_VM_1 is restored correctly
        """
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_9_NIC_1,
            mac_address=self.out_of_scope_mac_address_2, plugged=False
        )
        testflow.step("Previewing VM: %s snaphost", mac_pool_conf.MP_VM_1)
        assert helper.preview_snapshot_on_vm(
            vm=mac_pool_conf.MP_VM_1, snapshot_desc=self.mac_pool_snapshot
        )
        vm_1_mac_address = ll_vms.get_vm_nic_mac_address(
            vm=mac_pool_conf.MP_VM_1, nic=mac_pool_conf.CASE_9_NIC_1
        )
        assert vm_1_mac_address == self.vm_1_mac_address_1, (
            "VM: %s vNIC is assigned with unexpected MAC address: %s"
            % (mac_pool_conf.MP_VM_1, vm_1_mac_address)
        )

    @tier2
    @polarion("RHEVM-24249")
    def test_03_test_mac_asssignment_during_snapshot_preview(self):
        """
        1. Try to assign MP_VM_1 MAC address while it's in preview snapshot
           state
        2. Start VM
        """
        assert ll_vms.updateNic(
            positive=False, vm=mac_pool_conf.MP_VM_0,
            nic=mac_pool_conf.CASE_9_NIC_1,
            mac_address=self.vm_1_mac_address_1, plugged=False
        ), (
            "VM: %s is assigned with snapshot preview MAC: %s"
            % (mac_pool_conf.MP_VM_0, self.vm_1_mac_address_1)
        )
        assert ll_vms.startVm(
            positive=True, vm=mac_pool_conf.MP_VM_1, wait_for_status=conf.VM_UP
        )

    @tier2
    @polarion("RHEVM-23178")
    def test_04_test_mac_pool_full_with_snapshot(self):
        """
        1. Unplug MP_VM_0 vNIC and assign MAC: out_of_scope_mac_address_2
           (already done in previous test steps)
        2. Unplug MP_VM_1 second vNIC and assign MAC: vm_0_mac_address_1
        3. NEGATIVE: Try to preview a snapshot of VM_0 (should fail, because
           they are no available MACs to allocate from the pool)
        """
        assert ll_vms.updateNic(
            positive=True, vm=mac_pool_conf.MP_VM_1,
            nic=mac_pool_conf.CASE_9_NIC_2,
            mac_address=self.vm_0_mac_address_1, plugged=False
        )
        testflow.step("Previewing VM: %s snaphost", mac_pool_conf.MP_VM_0)
        assert helper.preview_snapshot_on_vm(
            vm=mac_pool_conf.MP_VM_0, snapshot_desc=self.mac_pool_snapshot,
            positive=False
        )
