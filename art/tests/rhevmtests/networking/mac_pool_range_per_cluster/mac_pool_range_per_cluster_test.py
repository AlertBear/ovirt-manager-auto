#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per cluster networking feature test cases

The following elements will be used for the testing:
Data-Centers, clusters, MAC pools, storage domain, VM, templates, vNICs
"""

import pytest

import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as mac_pool_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import bz, polarion
from art.unittest_lib import attr, testflow, NetworkTest
from fixtures import (
    mac_pool_per_cl_prepare_setup, create_mac_pools,
    create_cluster_with_mac_pools, update_clusters_mac_pool,
    remove_vnics_from_vms, add_vnics_to_vm, remove_non_default_mac_pool,
    add_vnics_to_template, create_vm_from_template
)


@attr(tier=2)
class TestMacPoolRange01(NetworkTest):
    """
    1.  Try to use old configuration with engine-config
    2.  Check that invalid engine config commands are deprecated
        (MacPoolRanges and MaxMacCountPool)
    """
    __test__ = True

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


@attr(tier=2)
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
    __test__ = True

    ext_cl = mac_pool_conf.EXT_CL_1
    mac_pool = mac_pool_conf.MAC_POOL_NAME_0
    def_mac_pool = mac_pool_conf.DEFAULT_MAC_POOL
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST

    create_mac_pools_params = {
        mac_pool: [range_list, False]
    }
    create_cl_with_mac_pools_params = {
        ext_cl: [mac_pool, True]
    }

    @polarion("RHEVM3-6462")
    def test_01_recreate_cluster(self):
        """
        1.  Recreate just removed cluster
        2.  Make sure that the cluster was recreated with the default MAC pool
        3.  Remove cluster
        4.  Make sure default MAC pool still exists
        """
        testflow.step("Removing existing cluster from setup")
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl)
        testflow.step("Recreate cluster without explicitly providing MAC pool")
        assert helper.create_cluster_with_mac_pool(mac_pool_name="")
        pool_id = ll_mac_pool.get_mac_pool_from_cluster(cluster=self.ext_cl).id
        assert ll_mac_pool.get_default_mac_pool().id == pool_id
        testflow.step("Remove cluster")
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl)
        testflow.step("Make sure default MAC pool still exists")
        assert ll_mac_pool.get_mac_pool(pool_name=self.def_mac_pool)

    @polarion("RHEVM3-6457")
    def test_02_remove_default_mac_pool(self):
        """
        Negative: remove of Default MAC pool should fail
        """
        testflow.step("Negative: try to remove default MAC pool range.")
        assert not ll_mac_pool.remove_mac_pool(mac_pool_name=self.def_mac_pool)

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


@attr(tier=2)
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
    __test__ = True

    ext_cl = mac_pool_conf.MAC_POOL_CL
    ext_cl_1 = mac_pool_conf.EXT_CL_1
    vm = mac_pool_conf.MP_VM_0
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    pool_1 = mac_pool_conf.MAC_POOL_NAME_1
    pool_2 = mac_pool_conf.MAC_POOL_NAME_2
    vnic_1 = mac_pool_conf.NIC_NAME_1
    vnic_2 = mac_pool_conf.NIC_NAME_2
    vnic_3 = mac_pool_conf.NIC_NAME_3
    vnic_4 = mac_pool_conf.NIC_NAME_4
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST
    create_mac_pools_params = {
        pool_0: [[mac_pool_conf.MAC_POOL_RANGE_LIST[0]], False],
        pool_1: None,
        pool_2: None
    }
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }

    @polarion("RHEVM3-6451")
    def test_01_auto_assigned_vs_manual(self):
        """
        1.  Add VNICs to the VM until MAC pool is exhausted
        2.  Fail on adding extra VNIC with auto assigned MAC to VM
        3.  Add MAC manually (not from a range) and succeed
        """
        manual_mac = "00:00:00:12:34:56"
        testflow.step("Add VNICs to the VM until MAC pool is exhausted")
        for nic in [self.vnic_1, self.vnic_2]:
            assert ll_vms.addNic(positive=True, vm=self.vm, name=nic)

        testflow.step("Fail on adding extra VNIC with auto assigned MAC to VM")
        assert ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3)

        testflow.step("Add MAC manually (not from a range) and succeed")
        assert ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vnic_3, mac_address=manual_mac
        )

    @polarion("RHEVM3-6449")
    def test_02_add_remove_ranges(self):
        """
        1.  Add 2 new ranges
        2.  Remove one of the added ranges
        3.  Check that the correct ranges still exist in the range list
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
        assert ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_4)
        testflow.step(
            "Check that VM NIC is created with MAC from the first MAC pool "
            "range"
        )
        assert helper.check_mac_in_range(
            vm=self.vm, nic=self.vnic_4, mac_range=self.range_list[1]
        )
        testflow.step(
            "Check that for updated cluster with new MAC pool, the NICs on "
            "the VM on that cluster are created with MACs from the new MAC "
            "pool range"
        )
        for nic in [self.vnic_1, self.vnic_2, self.vnic_3, self.vnic_4]:
            assert ll_vms.removeNic(True, vm=self.vm, nic=nic)

        assert hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_0, range_list=[self.range_list[1]]
        )

    @polarion("RHEVM3-6445")
    def test_04_creation_pool_same_name(self):
        """
        Test creation of a new pool with the same name, but different range
        """
        testflow.step("Create new pool with same name, but different range")
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=[self.range_list[0]], positive=False
        )

    @polarion("RHEVM3-6446")
    def test_05_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        testflow.step("Create new pool with same range, but different names")
        assert ll_mac_pool.create_mac_pool(
            name=self.pool_1, ranges=[self.range_list[0]]
        )

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
        testflow.step("Remove cluster")
        assert ll_clusters.removeCluster(positive=True, cluster=self.ext_cl_1)
        testflow.step("Make sure that the MAC pool is not removed")
        assert ll_mac_pool.get_mac_pool(self.pool_0)


@attr(tier=2)
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
    __test__ = True

    ext_cl = mac_pool_conf.MAC_POOL_CL
    vm = mac_pool_conf.MP_VM_0
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    vnic_1 = mac_pool_conf.NIC_NAME_1
    vnic_2 = mac_pool_conf.NIC_NAME_2
    vnic_3 = mac_pool_conf.NIC_NAME_3
    vnic_5 = mac_pool_conf.NIC_NAME_5
    create_mac_pools_params = {
        pool_0: [[mac_pool_conf.MAC_POOL_RANGE_LIST[1]], False]
    }
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }
    remove_vnics_from_vms_params = {
        vm: [mac_pool_conf.NICS_NAME[i] for i in range(1, 5)]
    }

    @polarion("RHEVM3-6448")
    def test_01_range_limit_shrink(self):
        """
        1.  Add VNICs to the VM
        2.  Shrink the MAC pool, so you can add only one new VNIC
        3.  Add one VNIC and succeed
        4.  Try to add additional VNIC to VM and fail
        """
        testflow.step("Add VNICs to the VM and shrink the MAC pool")
        assert ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_1)
        assert helper.update_mac_pool_range_size(extend=False, size=(0, -1))
        testflow.step("Add one VNIC and succeed")
        assert ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_2)
        testflow.step("Try to add additional VNIC to VM and fail")
        assert ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3)

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
        for i in range(3, 5):
            assert ll_vms.addNic(
                positive=True, vm=self.vm, name=mac_pool_conf.NICS_NAME[i]
            )
        testflow.step("Fail when you try to overcome that limit")
        assert ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_5)


@attr(tier=2)
@pytest.mark.incremental
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    add_vnics_to_vm.__name__
)
class TestMacPoolRange05(NetworkTest):
    """
    1.  Non-Continues ranges in MAC pool
    2.  Check that you can add VNICs according to the number of MAC ranges when
        each MAC range has only one MAC address in the pool
    """
    __test__ = True

    ext_cl = mac_pool_conf.MAC_POOL_CL
    vm = mac_pool_conf.MP_VM_0
    nic7 = mac_pool_conf.NIC_NAME_6
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    mac_pool_ranges = [
        ("00:00:00:10:10:10", "00:00:00:10:10:10"),
        ("00:00:00:10:10:20", "00:00:00:10:10:20"),
        ("00:00:00:10:10:30", "00:00:00:10:10:30"),
        ("00:00:00:10:10:40", "00:00:00:10:10:40"),
        ("00:00:00:10:10:50", "00:00:00:10:10:50"),
        ("00:00:00:10:10:60", "00:00:00:10:10:60")
    ]
    create_mac_pools_params = {
        pool_0: [mac_pool_ranges[:3], False]
    }
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }
    remove_vnics_from_vms_params = {
        vm: [mac_pool_conf.NICS_NAME[i] for i in range(1, 7)]
    }
    add_vnics_to_vm_params = {
        vm: [mac_pool_conf.NICS_NAME[i] for i in range(1, 4)]
    }

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
            mac_ranges=self.mac_pool_ranges[:3], start_idx=1, end_idx=4
        )
        assert hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_0, range_list=self.mac_pool_ranges[3:5]
        )
        for i in range(4, 6):
            assert ll_vms.addNic(
                positive=True, vm=self.vm, name=mac_pool_conf.NICS_NAME[i]
            )
        assert helper.check_single_mac_range_match(
            mac_ranges=self.mac_pool_ranges[3:5], start_idx=4, end_idx=6
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
        assert ll_vms.addNic(positive=True, vm=self.vm, name=self.nic7)
        nic_mac = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=self.nic7)
        assert nic_mac == self.mac_pool_ranges[-1][0]


@attr(tier=2)
@bz({"1219383": {}})
class TestMacPoolRange06(NetworkTest):
    """
    1.  Combine MAC pool range of Unicast and multicast MAC's
    2.  Check that when having a combined range of multicast and unicast
        addresses the new VNICs will be created with unicast addresses only
    """
    __test__ = True

    mac_pool_ranges = [("00:ff:ff:ff:ff:ff", "02:00:00:00:00:01")]
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0

    @polarion("RHEVM3-6454")
    def test_big_range(self):
        """
        Try to add big range
        """
        testflow.step("Try to add big range - MAC range with 2^31 addresses")
        assert not ll_mac_pool.create_mac_pool(
            name=self.pool_0, ranges=self.mac_pool_ranges
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    remove_non_default_mac_pool.__name__,
    create_mac_pools.__name__,
    update_clusters_mac_pool.__name__,
    add_vnics_to_template.__name__,
    create_vm_from_template.__name__
)
class TestMacPoolRange07(NetworkTest):
    """
    1.  Create VM from Template
    2.  Check that VNIC created from template uses the correct MAC POOL value
    3.  Add 2 more VNICs to template, so it will be impossible to create a new
        VM from that template
    4.  Check that creating new VM from template fails
    """
    __test__ = True

    ext_cl = mac_pool_conf.MAC_POOL_CL
    nic_0 = mac_pool_conf.NIC_NAME_0
    nic_1 = mac_pool_conf.NIC_NAME_1
    cluster = mac_pool_conf.MAC_POOL_CL
    template = mac_pool_conf.MP_TEMPLATE
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    mp_vm = mac_pool_conf.MP_VM_1
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST
    create_mac_pools_params = {
        pool_0: [[range_list[0]], False]
    }
    update_cls_mac_pool_params = {
        ext_cl: pool_0
    }
    add_vnics_to_template_params = {
        template: [nic_0, nic_1]
    }
    create_vm_from_template_params = {
        mp_vm: template
    }

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
            vm=self.mp_vm, nic=self.nic_0, mac_range=self.range_list[0]
        )
        testflow.step(
            "Negative: try to create new VM from template when there are not "
            "enough MACs for its VNICs"
        )
        assert ll_vms.createVm(
            positive=False, vmName="neg_vm", cluster=self.cluster,
            template=self.template
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    mac_pool_per_cl_prepare_setup.__name__,
    create_mac_pools.__name__,
    create_cluster_with_mac_pools.__name__
)
class TestMacPoolRange08(NetworkTest):
    """
    Removal of cluster with custom MAC pool when that MAC pool is assigned to
        2 clusters
    """
    __test__ = True

    ext_cl_1 = mac_pool_conf.EXT_CL_2
    ext_cl_2 = mac_pool_conf.EXT_CL_3
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    range_list = mac_pool_conf.MAC_POOL_RANGE_LIST
    create_mac_pools_params = {
        pool_0: [[range_list[0]], False]
    }
    create_cl_with_mac_pools_params = {
        ext_cl_1: [pool_0, False],
        ext_cl_2: [pool_0, False]
    }

    @polarion("RHEVM3-6461")
    def test_remove_two_clusters(self):
        """
        1.  Remove clusters
        2.  Make sure that the MAC pool is not removed
        """
        testflow.step("Remove clusters")
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
