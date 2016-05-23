#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature test
"""

import logging

import pytest

import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as mac_pool_conf
import helper
import rhevmtests.networking.config as conf
from art.test_handler.tools import bz, polarion  # pylint: disable=E0611
from art.unittest_lib import attr, testflow, NetworkTest
from fixtures import (
    fixture_mac_pool_range_case_02, fixture_mac_pool_range_case_03,
    fixture_mac_pool_range_case_04, fixture_mac_pool_range_case_05,
    fixture_mac_pool_range_case_07, fixture_mac_pool_range_case_09,
    mac_pool_range_06_fixture, mac_pool_range_08_fixture
)

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Cases")


@attr(tier=2)
class TestMacPoolRange01(NetworkTest):
    """
    Try to use old configuration with engine-config
    Check that invalid engine commands are deprecated:
        1) MAC pool range
        2) Max MAC count pool
    """
    __test__ = True

    @polarion("RHEVM3-6442")
    def test_invalid_engine_commands(self):
        """
        Negative:Try to configure MAC range (should be deprecated)
        Negative: Try to configure MaxMacCountPool (should be deprecated)
        """
        testflow.step(
            "Negative: Try to configure MAC pool range and MaxMacCountPool"
        )
        mac_range = "00:1a:4a:4c:7a:00-00:1a:4a:4c:7a:ff"
        cmd1 = "=".join([conf.MAC_POOL_RANGE_CMD, mac_range])
        cmd2 = "=".join(["MaxMacCountPool", "100001"])
        for cmd in (cmd1, cmd2):
            self.assertFalse(
                conf.test_utils.set_engine_properties(
                    conf.ENGINE, [cmd], restart=False
                )
            )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_02.__name__)
class TestMacPoolRange02(NetworkTest):
    """
    1) Recreate DC with custom MAC pool and make sure it was
    recreated with the Default MAC pool
    2) Try to remove default MAC pool
    3) Extend and shrink Default MAC pool ranges
    """
    __test__ = True
    def_mac_pool = conf.DEFAULT_MAC_POOL
    range = conf.MAC_POOL_RANGE_LIST[0]
    ext_dc = conf.EXT_DC_1
    mac_pool = mac_pool_conf.MAC_POOL_NAME_0
    range_list = conf.MAC_POOL_RANGE_LIST

    @polarion("RHEVM3-6462")
    def test_01_recreate_dc(self):
        """
        Recreate just removed DC
        Make sure that the DC was recreated with the Default MAC pool
        Remove DC
        Make sure Default MAC pool still exists
        """
        testflow.step("Recreate DC without explicitly providing MAC pool")
        helper.create_dc(mac_pool_name="")
        pool_id = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc).id
        self.assertEqual(ll_mac_pool.get_default_mac_pool().id, pool_id)
        self.assertTrue(
            ll_dc.remove_datacenter(positive=True, datacenter=self.ext_dc)
        )
        self.assertTrue(ll_mac_pool.get_mac_pool(self.def_mac_pool))

    @polarion("RHEVM3-6457")
    def test_02_remove_default_mac_pool(self):
        """
        Negative: Remove of Default MAC pool should fail
        """
        testflow.step("Try to remove default MAC pool range.")
        self.assertFalse(ll_mac_pool.remove_mac_pool(self.def_mac_pool))

    @polarion("RHEVM3-6443")
    def test_03_default_mac_pool(self):
        """`
        Extend the default range values of Default MAC pool
        Shrink the default range values of Default MAC pool
        Add new ranges to the Default MAC pool
        Remove added ranges from the Default MAC pool
        Create a new DC and check it was created with updated Default
        MAC pool values
        """
        testflow.step("Extend and shrink the default MAC pool range")
        self.assertTrue(
            helper.update_mac_pool_range_size(
                mac_pool_name=self.def_mac_pool, size=(2, 2)
            )
        )
        self.assertTrue(
            helper.update_mac_pool_range_size(
                mac_pool_name=self.def_mac_pool, extend=False, size=(-2, -2)
            )
        )
        self.assertTrue(
            hl_mac_pool.add_ranges_to_mac_pool(
                mac_pool_name=self.def_mac_pool, range_list=self.range_list
            )
        )

        self.assertTrue(
            hl_mac_pool.remove_ranges_from_mac_pool(
                mac_pool_name=self.def_mac_pool, range_list=self.range_list
            )
        )
        helper.create_dc(mac_pool_name='')
        mac_pool_id = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc).get_id()
        self.assertEqual(
            ll_mac_pool.get_default_mac_pool().get_id(), mac_pool_id
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_03.__name__)
class TestMacPoolRange03(NetworkTest):
    """
    1) Auto vs manual MAC assignment when allow duplicate is False
    2) Add and remove ranges to/from MAC pool
    3) Creating vNICs with updated MAC pool takes the MACs from the new pool
    Negative: Try to create a MAC pool with the already occupied name
    Create a MAC pool with occupied MAC pool range
    4) Creating pool with the same name
    5) Creating pool with the same range
    """
    __test__ = True
    range_list = conf.MAC_POOL_RANGE_LIST
    vm = conf.VM_0
    mp_vm = mac_pool_conf.MP_VM
    dc = conf.DC_0
    ext_dc = conf.EXT_DC_1
    vnic_1 = mac_pool_conf.NIC_NAME_1
    vnic_2 = mac_pool_conf.NIC_NAME_2
    vnic_3 = mac_pool_conf.NIC_NAME_3
    vnic_4 = mac_pool_conf.NIC_NAME_4
    mac_addr = "00:00:00:12:34:56"
    pool_names = mac_pool_conf.MAC_POOL_NAME
    pool_name_0 = mac_pool_conf.MAC_POOL_NAME_0
    pool_name_1 = mac_pool_conf.MAC_POOL_NAME_1
    pool_name_2 = mac_pool_conf.MAC_POOL_NAME_2
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @polarion("RHEVM3-6451")
    def test_01_auto_assigned_vs_manual(self):
        """
        Add VNICs to the VM till MAC pool is exhausted
        Try to add additional VNIC with auto assigned MAC to VM and fail
        Add MAC manually (not from a range) and succeed
        Remove vNICs from VM
        """
        testflow.step("Add VNICs to the VM till MAC pool is exhausted")
        for nic in [self.vnic_1, self.vnic_2]:
            self.assertTrue(ll_vms.addNic(positive=True, vm=self.vm, name=nic))
        testflow.step(
            "Try to add additional VNIC with auto assigned MAC to VM and fail"
        )
        self.assertTrue(
            ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3)
        )
        testflow.step("Add MAC manually (not from a range) and succeed")
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=self.vm, name=self.vnic_3,
                mac_address=self.mac_addr
            )
        )

    @polarion("RHEVM3-6449")
    def test_02_add_remove_ranges(self):
        """
        Add 2 new ranges
        Remove one of the added ranges
        Check that the correct ranges still exist in the Range list
        """
        testflow.step("Add 2 new ranges")
        self.assertTrue(
            hl_mac_pool.add_ranges_to_mac_pool(
                mac_pool_name=self.pool_name_0, range_list=self.range_list[1:3]
            )
        )
        testflow.step("Remove one of the added ranges")
        self.assertTrue(
            hl_mac_pool.remove_ranges_from_mac_pool(
                mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
            )
        )
        ranges = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(self.pool_name_0)
        )
        self.assertEqual(len(ranges), 2)
        self.assertNotIn(self.range_list[1], ranges)
        testflow.step(
            "Check that the correct ranges still exist in the Range list"
        )
        self.assertTrue(
            hl_mac_pool.remove_ranges_from_mac_pool(
                mac_pool_name=self.pool_name_0, range_list=[self.range_list[2]]
            )
        )

    @polarion("RHEVM3-6444")
    def test_03_update_mac_pool_vm(self):
        """
        Check that VM NIC is created with MAC from the first MAC pool range
        Check that for updated DC with new MAC pool, the NICs on the VM on
        that DC are created with MACs from the new MAC pool range
        """
        self.assertTrue(
            hl_mac_pool.add_ranges_to_mac_pool(
                mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
            )
        )
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_4)
        )
        testflow.step(
            "Check that VM NIC is created with MAC from the first MAC pool "
            "range"
        )
        self.assertTrue(
            helper.check_mac_in_range(
                vm=self.vm, nic=self.vnic_4, mac_range=self.range_list[1]
            )
        )
        testflow.step(
            "Check that for updated DC with new MAC pool, the NICs on the VM "
            "on that DC are created with MACs from the new MAC pool range"
        )
        for nic in [self.vnic_1, self.vnic_2, self.vnic_3, self.vnic_4]:
            self.assertTrue(ll_vms.removeNic(True, vm=self.vm, nic=nic))

        self.assertTrue(
            hl_mac_pool.remove_ranges_from_mac_pool(
                mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
            )
        )

    @polarion("RHEVM3-6445")
    def test_04_creation_pool_same_name(self):
        """
        Test creation of a new pool with the same name, but different range
        """
        testflow.step(
            "Test creation of a new pool with the same name, but different "
            "range"
        )
        self.assertTrue(
            ll_mac_pool.create_mac_pool(
                name=self.pool_name_0, ranges=[self.range_list[0]],
                positive=False
            )
        )

    @polarion("RHEVM3-6446")
    def test_05_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        testflow.step(
            "Test creation of a new pool with the same range, but different "
            "names"
        )
        self.assertTrue(
            ll_mac_pool.create_mac_pool(
                name=self.pool_name_1, ranges=[self.range_list[0]]
            )
        )

    @polarion("RHEVM3-6458")
    def test_06_remove_used_mac_pool(self):
        """
        Negative:Try to remove the MAC pool that is already assigned to DC
        """
        testflow.step(
            "Negative:Try to remove the MAC pool that is already assigned to "
            "DC"
        )
        self.assertFalse(ll_mac_pool.remove_mac_pool(self.pool_name_0))

    @polarion("RHEVM3-6459")
    def test_07_remove_unused_mac_pool(self):
        """
        Assign another MAC pool to DC
        Remove the MAC pool previously attached to DC
        """
        self.assertTrue(
            ll_mac_pool.create_mac_pool(
                name=self.pool_name_2, ranges=[self.range_list[2]]
            )
        )
        testflow.step("Assign another MAC pool to DC")
        self.assertTrue(
            ll_dc.update_datacenter(
                positive=True, datacenter=self.dc,
                mac_pool=ll_mac_pool.get_mac_pool(self.pool_name_2)
            )
        )
        testflow.step("Remove the MAC pool previously attached to DC")
        self.assertTrue(ll_mac_pool.remove_mac_pool(self.pool_name_0))

    @polarion("RHEVM3-6460")
    def test_08_remove_dc(self):
        """
        Remove DC
        Make sure that the MAC pool is not removed
        """
        testflow.step(
            "Remove DC and Make sure that the MAC pool is not removed"
        )
        self.assertTrue(
            ll_mac_pool.create_mac_pool(
                name=self.pool_name_0, ranges=[self.range_list[0]]
            )
        )
        helper.create_dc()
        self.assertTrue(
            ll_dc.remove_datacenter(positive=True, datacenter=self.ext_dc))

        self.assertTrue(ll_mac_pool.get_mac_pool(self.pool_name_0))


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_04.__name__)
class TestMacPoolRange04(NetworkTest):
    """
    1) Shrink MAC pool range
    Check that you can add VNICs if you don't reach the limit of the
    MAC pool range
    Shrinking the MAC pool to the size equal to the number of VM NICs
    will not allow adding additional VNICs to VM
    2) Extend MAC pool range
    Check that you can add VNICs till you reach the limit of the MAC pool range
    Extending the MAC pool range by 2 will let you add 2 additional VNICs only
    """
    __test__ = True
    range_list = conf.MAC_POOL_RANGE_LIST
    dc = conf.DC_0
    vm = conf.VM_0
    pool_name = mac_pool_conf.MAC_POOL_NAME_0
    def_mac_pool = conf.DEFAULT_MAC_POOL
    vnic_1 = mac_pool_conf.NIC_NAME_1
    vnic_2 = mac_pool_conf.NIC_NAME_2
    vnic_3 = mac_pool_conf.NIC_NAME_3
    vnic_5 = mac_pool_conf.NIC_NAME_5

    @polarion("RHEVM3-6448")
    def test_01_range_limit_shrink(self):
        """
        Add VNICs to the VM
        Shrink the MAC pool, so you can add only one new VNIC
        Add one VNIC and succeed
        Try to add additional VNIC to VM and fail
        """
        testflow.step(
            "Add VNICs to the VM and Shrink the MAC pool, so you can add only "
            "one new VNIC"
        )
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_1)
        )

        self.assertTrue(
            helper.update_mac_pool_range_size(extend=False, size=(0, -1))
        )
        testflow.step("Add one VNIC and succeed")
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_2)
        )
        testflow.step("Try to add additional VNIC to VM and fail")
        self.assertTrue(
            ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3)
        )

    @polarion("RHEVM3-6447")
    def test_02_range_limit_extend(self):
        """
        Extend the MAC pool range
        Add another VNICs (till you reach range limit again)
        Fail when you try to overcome that limit
        """
        testflow.step("Extend the MAC pool range")
        self.assertTrue(helper.update_mac_pool_range_size())
        testflow.step("Add another VNICs (till you reach range limit again)")
        for i in range(3, 5):
            self.assertTrue(
                ll_vms.addNic(positive=True, vm=self.vm, name=conf.NIC_NAME[i])
            )
        testflow.step("Fail when you try to overcome that limit")
        self.assertTrue(
            ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_5)
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_05.__name__)
class TestMacPoolRange05(NetworkTest):
    """
    Non-Continues ranges in MAC pool
    Check that you can add VNICs according to the number of MAC ranges when
    each MAC range has only one MAC address in the pool
    """
    __test__ = True
    mac_pool_ranges = [
        ("00:00:00:10:10:10", "00:00:00:10:10:10"),
        ("00:00:00:10:10:20", "00:00:00:10:10:20"),
        ("00:00:00:10:10:30", "00:00:00:10:10:30"),
        ("00:00:00:10:10:40", "00:00:00:10:10:40"),
        ("00:00:00:10:10:50", "00:00:00:10:10:50"),
        ("00:00:00:10:10:60", "00:00:00:10:10:60")
    ]
    nic7 = conf.NIC_NAME[6]
    pool_name = mac_pool_conf.MAC_POOL_NAME_0
    dc = conf.DC_0
    vm = conf.VM_0
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @polarion("RHEVM3-6450")
    def test_non_continuous_ranges(self):
        """
        Test VNICs have non-continuous MACs (according to the Ranges values)
        """
        testflow.step(
            "Non-Continues ranges in MAC pool Check that you can add VNICs "
            "according to the number of MAC ranges when each MAC range has "
            "only one MAC address in the pool"
        )
        self.assertTrue(
            helper.check_single_mac_range_match(
                mac_ranges=self.mac_pool_ranges[:3], start_idx=1, end_idx=4
            )
        )
        self.assertTrue(
            hl_mac_pool.add_ranges_to_mac_pool(
                mac_pool_name=self.pool_name,
                range_list=self.mac_pool_ranges[3:5]
            )
        )
        for i in range(4, 6):
            self.assertTrue(
                ll_vms.addNic(positive=True, vm=self.vm, name=conf.NIC_NAME[i])
            )
        self.assertTrue(
            helper.check_single_mac_range_match(
                mac_ranges=self.mac_pool_ranges[3:5], start_idx=4, end_idx=6
            )
        )
        testflow.step(
            "Remove the last added range, add another one and check that "
            "a new vNIC takes MAC from the new added Range"
        )
        self.assertTrue(
            hl_mac_pool.remove_ranges_from_mac_pool(
                mac_pool_name=self.pool_name,
                range_list=[self.mac_pool_ranges[4]]
            )
        )
        self.assertTrue(
            hl_mac_pool.add_ranges_to_mac_pool(
                mac_pool_name=self.pool_name,
                range_list=[self.mac_pool_ranges[5]]
            )
        )

        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm, name=self.nic7)
        )

        nic_mac = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=self.nic7)
        self.assertEqual(nic_mac, self.mac_pool_ranges[-1][0])


@attr(tier=2)
@pytest.mark.usefixtures(mac_pool_range_06_fixture.__name__)
class TestMacPoolRange06(NetworkTest):
    """
    1) Assign same pool to multiple DC's -Disallow Duplicates
    Check that if "Allow duplicates" is False, it's impossible to add VNIC
    with manual MAC allocation to VM

    2) Assign same pool to multiple DCs -Allow Duplicates
    Check that if "Allow duplicates" is True, it's possible to add vNIC
    with manual MAC allocation to VM
    """
    __test__ = True
    nic1 = mac_pool_conf.NIC_NAME_1
    nic2 = mac_pool_conf.NIC_NAME_2
    nic3 = mac_pool_conf.NIC_NAME_3
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    pool_1 = mac_pool_conf.MAC_POOL_NAME_1
    vm_0 = conf.VM_0
    mp_vm = mac_pool_conf.MP_VM
    range = conf.MAC_POOL_RANGE_LIST
    dc = conf.DC_0
    ext_dc = conf.EXT_DC_0
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @polarion("RHEVM3-6452")
    def test_01_auto_assigned_vs_manual(self):
        """
        Negative:Try to add a new VNIC to VM when explicitly providing MAC
        on the first VM NIC (manual MAC configuration) when allow duplicate
        is False
        Negative: Try to add this NIC to VM on another DC
        Add NIC to VM on the second DC with auto assignment and succeed
        Remove vNIC from both VMs
        """
        testflow.step(
            "Negative:Try to add a new VNIC to VM when explicitly providing "
            "MAC on the first VM NIC (manual MAC configuration) when allow "
            "duplicate is False"
        )
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm_0, name=self.nic1)
        )

        mac_address = ll_vms.get_vm_nic_mac_address(
            vm=self.vm_0, nic=self.nic1
        )
        assert mac_address

        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic1)
        )

        for vm in (self.vm_0, self.mp_vm):
            self.assertTrue(
                ll_vms.addNic(
                    positive=False, vm=vm, name=self.nic2,
                    mac_address=mac_address
                )
            )

        for vm in (self.vm_0, self.mp_vm):
            ll_vms.removeNic(positive=True, vm=vm, nic=self.nic1)

    @polarion("RHEVM3-6453")
    def test_02_allow_duplicates(self):
        """
        Update both DCs with MAC poll having allow duplicates
        Add VNIC with auto assignment to VM
        Add a new VNIC to VM with manual MAC configuration and
        allow_duplicates is True
        Add VNIC to VM on the second DC - the same MAC (manual configuration)
        Add NIC to VM on the second DC with auto assignment
        Fail on adding additional VNIC as MAC pool exhausted
        Succeed on adding VNIC with MAC pool manual configuration
        """
        testflow.step(
            "Update both DCs with MAC poll having allow duplicates"
        )
        for dc in (self.dc, self.ext_dc):
            self.assertTrue(
                ll_dc.update_datacenter(
                    positive=True, datacenter=dc,
                    mac_pool=ll_mac_pool.get_mac_pool(pool_name=self.pool_1)
                )
            )
        testflow.step("Add VNIC with auto assignment to VM")
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.vm_0, name=self.nic1)
        )
        mac_address = ll_vms.get_vm_nic_mac_address(
            vm=self.vm_0, nic=self.nic1
        )
        assert mac_address
        testflow.step(
            "Add a new VNIC to VM with manual MAC configuration and "
            "allow_duplicates is True"
        )
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=self.vm_0, name=self.nic2,
                mac_address=mac_address
            )
        )
        testflow.step(
            "Add VNIC to VM on the second DC - the same MAC "
            "(manual configuration)"
        )
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=self.mp_vm, name=self.nic1,
                mac_address=mac_address
            )
        )
        testflow.step("Add NIC to VM on the second DC with auto assignment")
        self.assertTrue(
            ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic2)
        )
        testflow.step("Fail on adding additional VNIC as MAC pool exhausted")
        self.assertTrue(
            ll_vms.addNic(positive=False, vm=self.mp_vm, name=self.nic3)
        )
        testflow.step(
            "Succeed on adding VNIC with MAC pool manual configuration"
        )
        self.assertTrue(
            ll_vms.addNic(
                positive=True, vm=self.mp_vm, name=self.nic3,
                mac_address=mac_address
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_07.__name__)
class NoTestMacPoolRange07(NetworkTest):
    """
    Combine MAC pool range of Unicast and multicast MAC's
    Check that when having a combined range of multicast and unicast
    addresses the new VNICs will be created with unicast addresses only
    """
    __test__ = False
    mac_pool_ranges = [("00:ff:ff:ff:ff:ff", "02:00:00:00:00:01")]
    pool_0 = mac_pool_conf.MAC_POOL_NAME_0
    dc = conf.DC_0
    nic_1 = mac_pool_conf.NIC_NAME_1
    nic_2 = mac_pool_conf.NIC_NAME_2
    nic_3 = mac_pool_conf.NIC_NAME_3
    vm = conf.VM_0
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @polarion("RHEVM3-6454")
    @bz({"1219383": {"engine": ["rest", "sdk", "java"]}})
    def multicast_unicast_mix(self):
        """
        Add 2 VNICs to VM
        Negative: Try to add 3rd VNIC and fail as all the available MACs
        in the MAC pool are multicast MACs
        """
        testflow.step("Add 2 VNICs to VM")
        for i in range(2):
            self.assertTrue(
                ll_vms.addNic(
                    positive=True, vm=self.vm, name=conf.NIC_NAME[i + 1]
                )
            )
        testflow.step(
            "Negative: Try to add 3rd VNIC and fail as all the available MACs"
        )
        self.assertTrue(
            ll_vms.addNic(positive=False, vm=self.vm, name=self.nic_3)
        )


@attr(tier=2)
@pytest.mark.usefixtures(mac_pool_range_08_fixture.__name__)
class TestMacPoolRange08(NetworkTest):
    """
    Create VM from Template
    Check that VNIC created from template uses the correct MAC POOL value
    Add 2 more VNICs to template, so it will be impossible to create a new VM
    from that template
    Check that creating new VM from template fails
    """
    __test__ = True
    range_list = conf.MAC_POOL_RANGE_LIST
    template = mac_pool_conf.MP_TEMPLATE
    mp_vm = mac_pool_conf.MP_VM_NAMES[1]
    cluster = mac_pool_conf.MAC_POOL_CL
    nic_1 = conf.NIC_NAME[0]

    @polarion("RHEVM3-6455")
    def test_vm_from_template(self):
        """
        Check that VNIC created from template uses the correct MAC POOL values
        Negative: Try to create new VM from template when there are not enough
        MACs for its VNICs
        """
        testflow.step(
            "Check that VNIC created from template uses the correct MAC POOL "
            "values"
        )
        self.assertTrue(
            helper.check_mac_in_range(
                vm=self.mp_vm, nic=self.nic_1, mac_range=self.range_list[0]
            )
        )
        testflow.step(
            "Negative: Try to create new VM from template when there are not "
            "enough MACs for its VNICs"
        )
        self.assertTrue(
            ll_vms.createVm(
                positive=False, vmName="neg_vm", cluster=self.cluster,
                template=self.template,
            )
        )


@attr(tier=2)
@pytest.mark.usefixtures(fixture_mac_pool_range_case_09.__name__)
class TestMacPoolRange09(NetworkTest):
    """
    Removal of DC with custom MAC pool when that MAC pool is assigned to 2 DCs
    """
    __test__ = True
    pool_name_0 = mac_pool_conf.MAC_POOL_NAME_0
    range_list = conf.MAC_POOL_RANGE_LIST
    ext_dc_1 = conf.EXTRA_DC[1]
    ext_dc_2 = conf.EXTRA_DC[2]

    @polarion("RHEVM3-6461")
    def test_remove_two_dcs(self):
        """
        Remove DCs
        Make sure that the MAC pool is not removed
        """
        testflow.step("Remove DCs")
        for dc in [self.ext_dc_1, self.ext_dc_2]:
            self.assertTrue(
                ll_dc.remove_datacenter(positive=True, datacenter=dc)
                )

            testflow.step(
                "Make sure %s exists after DC removal" % self.pool_name_0
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(self.pool_name_0)
            self.assertTrue(
                mac_pool_obj, "MAC pool was removed during %s removal" % dc
                )
            if dc == self.ext_dc_1:
                testflow.step(
                    "Make sure %s is attached to %s after removal of the "
                    "first DC", self.pool_name_0, self.ext_dc_2
                )
                mac_on_dc = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc_2)
                self.assertEqual(mac_on_dc.name, mac_pool_obj.name)
