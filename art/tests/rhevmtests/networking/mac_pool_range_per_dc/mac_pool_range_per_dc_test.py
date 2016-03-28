#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature test
"""

import logging

import helper
from art.core_api import apis_exceptions
from art.test_handler.tools import bz, polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest
from art.unittest_lib import attr
from fixtures import *  # flake8: noqa
from rhevmtests import networking

logger = logging.getLogger("MAC_Pool_Range_Per_DC_Cases")


def setup_module():
    """
    Initialize params
    Network cleanup
    """
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.HOST_1_NAME = conf.HOSTS[1]
    networking.network_cleanup()


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
        logger.info(
            "Negative: Try to configure MAC pool range and MaxMacCountPool"
        )
        mac_range = "00:1a:4a:4c:7a:00-00:1a:4a:4c:7a:ff"
        cmd1 = "=".join([conf.MAC_POOL_RANGE_CMD, mac_range])
        cmd2 = "=".join(["MaxMacCountPool", "100001"])
        for cmd in (cmd1, cmd2):
            if conf.test_utils.set_engine_properties(
                conf.ENGINE, [cmd], restart=False
            ):
                raise conf.NET_EXCEPTION()


@attr(tier=2)
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
    mac_pool = conf.MAC_POOL_NAME_0
    range_list = conf.MAC_POOL_RANGE_LIST

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        Create a new DC with MAC pool
        Remove a created DC
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.mac_pool, ranges=[cls.range]
        ):
            raise conf.NET_EXCEPTION()

        helper.create_dc()
        if not ll_dc.remove_datacenter(positive=True, datacenter=cls.ext_dc):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6462")
    def test_01_recreate_dc(self):
        """
        Recreate just removed DC
        Make sure that the DC was recreated with the Default MAC pool
        Remove DC
        Make sure Default MAC pool still exists
        """
        logger.info("Recreate DC without explicitly providing MAC pool")
        helper.create_dc(mac_pool_name="")
        pool_id = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc).id
        if not (ll_mac_pool.get_default_mac_pool().id == pool_id):
            raise conf.NET_EXCEPTION()

        if not ll_dc.remove_datacenter(positive=True, datacenter=self.ext_dc):
            raise conf.NET_EXCEPTION()

        if not ll_mac_pool.get_mac_pool(self.def_mac_pool):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6457")
    def test_02_remove_default_mac_pool(self):
        """
        Negative: Remove of Default MAC pool should fail
        """
        logger.info("Try to remove default MAC pool range.")
        if ll_mac_pool.remove_mac_pool(self.def_mac_pool):
            raise conf.NET_EXCEPTION(
                "Could remove the default MAC pool when shouldn't"
            )

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
        logger.info("Extend and shrink the default MAC pool range")
        helper.update_mac_pool_range_size(
            mac_pool_name=self.def_mac_pool, size=(2, 2)
        )
        helper.update_mac_pool_range_size(
            mac_pool_name=self.def_mac_pool, extend=False, size=(-2, -2)
        )

        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.def_mac_pool, range_list=self.range_list
        ):
            raise conf.NET_EXCEPTION()

        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.def_mac_pool, range_list=self.range_list
        ):
            raise conf.NET_EXCEPTION()

        helper.create_dc(mac_pool_name='')
        mac_pool_id = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc).get_id()
        if not (ll_mac_pool.get_default_mac_pool().get_id() == mac_pool_id):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        Remove MAC pool
        """
        ll_dc.remove_datacenter(positive=True, datacenter=cls.ext_dc)
        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.mac_pool)


@attr(tier=2)
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
    mp_vm = conf.MP_VM
    dc = conf.DC_0
    ext_dc = conf.EXT_DC_1
    vnic_1 = conf.NIC_NAME_1
    vnic_2 = conf.NIC_NAME_2
    vnic_3 = conf.NIC_NAME_3
    vnic_4 = conf.NIC_NAME_4
    mac_addr = "00:00:00:12:34:56"
    pool_names = conf.MAC_POOL_NAME
    pool_name_0 = conf.MAC_POOL_NAME_0
    pool_name_1 = conf.MAC_POOL_NAME_1
    pool_name_2 = conf.MAC_POOL_NAME_2
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @classmethod
    def setup_class(cls):
        """
        Create 1 MAC pool
        Update DC with 1 of created MAC pool
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_name_0, ranges=[cls.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.pool_name_0)
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6451")
    def test_01_auto_assigned_vs_manual(self):
        """
        Add VNICs to the VM till MAC pool is exhausted
        Try to add additional VNIC with auto assigned MAC to VM and fail
        Add MAC manually (not from a range) and succeed
        Remove vNICs from VM
        """
        for nic in [self.vnic_1, self.vnic_2]:
            if not ll_vms.addNic(positive=True, vm=self.vm, name=nic):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.vm, name=self.vnic_3,
            mac_address=self.mac_addr
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6449")
    def test_02_add_remove_ranges(self):
        """
        Add 2 new ranges
        Remove one of the added ranges
        Check that the correct ranges still exist in the Range list
        """
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_name_0, range_list=self.range_list[1:3]
        ):
            raise conf.NET_EXCEPTION()

        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
        ):
            raise conf.NET_EXCEPTION()

        ranges = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(self.pool_name_0)
        )
        if len(ranges) != 2 or self.range_list[1] in ranges:
            raise conf.NET_EXCEPTION()

        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_name_0, range_list=[self.range_list[2]]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6444")
    def test_03_update_mac_pool_vm(self):
        """
        Check that VM NIC is created with MAC from the first MAC pool range
        Check that for updated DC with new MAC pool, the NICs on the VM on
        that DC are created with MACs from the new MAC pool range
        """
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_4):
            raise conf.NET_EXCEPTION()

        helper.check_mac_in_range(
            vm=self.vm, nic=self.vnic_4, mac_range=self.range_list[1]
        )

        for nic in [self.vnic_1, self.vnic_2, self.vnic_3, self.vnic_4]:
            if not ll_vms.removeNic(True, vm=self.vm, nic=nic):
                raise conf.NET_EXCEPTION()

        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_name_0, range_list=[self.range_list[1]]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6445")
    def test_04_creation_pool_same_name(self):
        """
        Test creation of a new pool with the same name, but different range
        """
        if not ll_mac_pool.create_mac_pool(
            name=self.pool_name_0, ranges=[self.range_list[0]], positive=False
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6446")
    def test_05_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        if not ll_mac_pool.create_mac_pool(
            name=self.pool_name_1, ranges=[self.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6458")
    def test_06_remove_used_mac_pool(self):
        """
        Negative:Try to remove the MAC pool that is already assigned to DC
        """
        if ll_mac_pool.remove_mac_pool(self.pool_name_0):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6459")
    def test_07_remove_unused_mac_pool(self):
        """
        Assign another MAC pool to DC
        Remove the MAC pool previously attached to DC
        """
        if not ll_mac_pool.create_mac_pool(
            name=self.pool_name_2, ranges=[self.range_list[2]]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_dc.update_datacenter(
            positive=True, datacenter=self.dc,
            mac_pool=ll_mac_pool.get_mac_pool(self.pool_name_2)
        ):
            raise conf.NET_EXCEPTION()

        if not ll_mac_pool.remove_mac_pool(self.pool_name_0):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6460")
    def test_08_remove_dc(self):
        """
        Remove DC
        Make sure that the MAC pool is not removed
        """
        if not ll_mac_pool.create_mac_pool(
            name=self.pool_name_0, ranges=[self.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

        helper.create_dc()
        if not ll_dc.remove_datacenter(positive=True, datacenter=self.ext_dc):
            raise conf.NET_EXCEPTION()

        if not ll_mac_pool.get_mac_pool(self.pool_name_0):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Update DC with default MAC pool
        Remove created MAC pools
        """
        ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.def_mac_pool)
        )
        for mac_pool in (cls.pool_name_0, cls.pool_name_1, cls.pool_name_2):
            try:
                ll_mac_pool.remove_mac_pool(mac_pool_name=mac_pool)
            except apis_exceptions.EntityNotFound:
                pass


@attr(tier=2)
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
    pool_name = conf.MAC_POOL_NAME_0
    def_mac_pool = conf.DEFAULT_MAC_POOL
    vnic_1 = conf.NIC_NAME_1
    vnic_2 = conf.NIC_NAME_2
    vnic_3 = conf.NIC_NAME_3
    vnic_5 = conf.NIC_NAME_5

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with this MAC pool
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_name, ranges=[cls.range_list[1]]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(cls.pool_name)
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6448")
    def test_01_range_limit_shrink(self):
        """
        Add VNICs to the VM
        Shrink the MAC pool, so you can add only one new VNIC
        Add one VNIC and succeed
        Try to add additional VNIC to VM and fail
        """
        if not ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_1):
            raise conf.NET_EXCEPTION()

        helper.update_mac_pool_range_size(extend=False, size=(0, -1))
        if not ll_vms.addNic(positive=True, vm=self.vm, name=self.vnic_2):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=False, vm=self.vm, name=self.vnic_3):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6447")
    def test_02_range_limit_extend(self):
        """
        Extend the MAC pool range
        Add another VNICs (till you reach range limit again)
        Fail when you try to overcome that limit
        """
        helper.update_mac_pool_range_size()
        for i in range(3, 5):
            if not ll_vms.addNic(
                positive=True, vm=self.vm, name=conf.NIC_NAME[i]
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=False, vm=self.vm, name=self.vnic_5
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove 4 VNICs from the VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        for nic in conf.NIC_NAME[1:5]:
            ll_vms.removeNic(positive=True, vm=cls.vm, nic=nic)

        ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.def_mac_pool)
        )
        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.pool_name)


@attr(tier=2)
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
    pool_name = conf.MAC_POOL_NAME_0
    dc = conf.DC_0
    vm = conf.VM_0
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with new MAC pool
        Add 3 VNICs to VM on that DC
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_name, ranges=cls.mac_pool_ranges[:3]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_dc.update_datacenter(
            positive=True, datacenter=conf.DC_0,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.pool_name)
        ):
            raise conf.NET_EXCEPTION()

        for i in range(3):
            if not ll_vms.addNic(
                positive=True, vm=cls.vm, name=conf.NIC_NAME[i + 1]
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6450")
    def test_non_continuous_ranges(self):
        """
        Test VNICs have non-continuous MACs (according to the Ranges values)
        """
        helper.check_single_mac_range_match(
            mac_ranges=self.mac_pool_ranges[:3], start_idx=1, end_idx=4
        )

        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_name, range_list=self.mac_pool_ranges[3:5]
        ):
            raise conf.NET_EXCEPTION()

        for i in range(4, 6):
            if not ll_vms.addNic(
                positive=True, vm=self.vm, name=conf.NIC_NAME[i]
            ):
                raise conf.NET_EXCEPTION()

        helper.check_single_mac_range_match(
            mac_ranges=self.mac_pool_ranges[3:5], start_idx=4, end_idx=6
        )

        logger.info(
            "Remove the last added range, add another one and check that "
            "a new vNIC takes MAC from the new added Range"
        )
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=self.pool_name, range_list=[self.mac_pool_ranges[4]]
        ):
            raise conf.NET_EXCEPTION()

        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=self.pool_name, range_list=[self.mac_pool_ranges[5]]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=True, vm=self.vm, name=self.nic7):
            raise conf.NET_EXCEPTION()

        nic_mac = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=self.nic7)
        if nic_mac != self.mac_pool_ranges[-1][0]:
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove VNICs from VM
        Update DC with default MAC pool
        Remove MAC pool
        """
        for nic in conf.NIC_NAME[1:7]:
            ll_vms.removeNic(positive=True, vm=cls.vm, nic=nic)

        ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.def_mac_pool)
        )
        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.pool_name)


@attr(tier=2)
@pytest.mark.usefixtures("mac_pool_range_06_fixture")
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
    nic1 = conf.NIC_NAME_1
    nic2 = conf.NIC_NAME_2
    nic3 = conf.NIC_NAME_3
    pool_0 = conf.MAC_POOL_NAME_0
    pool_1 = conf.MAC_POOL_NAME_1
    vm_0 = conf.VM_0
    mp_vm = conf.MP_VM
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
        if not ll_vms.addNic(positive=True, vm=self.vm_0, name=self.nic1):
            raise conf.NET_EXCEPTION()

        mac_address = ll_vms.get_vm_nic_mac_address(
            vm=self.vm_0, nic=self.nic1
        )
        if not mac_address:
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic1):
            raise conf.NET_EXCEPTION()

        for vm in (self.vm_0, self.mp_vm):
            if not ll_vms.addNic(
                positive=False, vm=vm, name=self.nic2, mac_address=mac_address
            ):
                raise conf.NET_EXCEPTION()

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
        for dc in (self.dc, self.ext_dc):
            if not ll_dc.update_datacenter(
                positive=True, datacenter=dc,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name=self.pool_1)
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=True, vm=self.vm_0, name=self.nic1):
            raise conf.NET_EXCEPTION()

        mac_address = ll_vms.get_vm_nic_mac_address(
            vm=self.vm_0, nic=self.nic1
        )
        if not mac_address:
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.vm_0, name=self.nic2,
            mac_address=mac_address
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.mp_vm, name=self.nic1,
            mac_address=mac_address
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=True, vm=self.mp_vm, name=self.nic2):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=False, vm=self.mp_vm, name=self.nic3):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=self.mp_vm, name=self.nic3,
            mac_address=mac_address
        ):
            raise conf.NET_EXCEPTION()


@attr(tier=2)
class NoTestMacPoolRange07(NetworkTest):
    """
    Combine MAC pool range of Unicast and multicast MAC's
    Check that when having a combined range of multicast and unicast
    addresses the new VNICs will be created with unicast addresses only
    """
    __test__ = False
    mac_pool_ranges = [("00:ff:ff:ff:ff:ff", "02:00:00:00:00:01")]
    pool_0 = conf.MAC_POOL_NAME_0
    dc = conf.DC_0
    nic_1 = conf.NIC_NAME_1
    nic_2 = conf.NIC_NAME_2
    nic_3 = conf.NIC_NAME_3
    vm = conf.VM_0
    def_mac_pool = conf.DEFAULT_MAC_POOL

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool with range having multicast and unicast MACs
        Update DC with a new MAC pool
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_0, ranges=cls.mac_pool_ranges
        ):
            raise conf.NET_EXCEPTION()

        if not ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.pool_0)
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6454")
    @bz({"1219383": {"engine": ["rest", "sdk", "java"]}})
    def multicast_unicast_mix(self):
        """
        Add 2 VNICs to VM
        Negative: Try to add 3rd VNIC and fail as all the available MACs
        in the MAC pool are multicast MACs
        """
        for i in range(2):
            if not ll_vms.addNic(
                positive=True, vm=self.vm, name=conf.NIC_NAME[i + 1]
            ):
                raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=False, vm=self.vm, name=self.nic_3):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove VNIC from VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        for nic in (cls.nic_1, cls.nic_2):
            ll_vms.removeNic(positive=True, vm=cls.vm, nic=nic)

        ll_dc.update_datacenter(
            positive=True, datacenter=cls.dc,
            mac_pool=ll_mac_pool.get_mac_pool(pool_name=cls.def_mac_pool)
        )

        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.pool_0)


@attr(tier=2)
@pytest.mark.usefixtures("mac_pool_range_08_fixture")
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
    template = conf.MP_TEMPLATE
    mp_vm = conf.MP_VM_NAMES[1]
    cluster = conf.MAC_POOL_CL
    nic_1 = conf.NIC_NAME[0]

    @polarion("RHEVM3-6455")
    def test_vm_from_template(self):
        """
        Check that VNIC created from template uses the correct MAC POOL values
        Negative: Try to create new VM from template when there are not enough
        MACs for its VNICs
        """
        helper.check_mac_in_range(
            vm=self.mp_vm, nic=self.nic_1, mac_range=self.range_list[0]
        )

        if not ll_vms.createVm(
            positive=False, vmName="neg_vm", cluster=self.cluster,
            template=self.template,
        ):
            raise conf.NET_EXCEPTION()


@attr(tier=2)
class TestMacPoolRange09(NetworkTest):
    """
    Removal of DC with custom MAC pool when that MAC pool is assigned to 2 DCs
    """
    __test__ = True
    pool_name_0 = conf.MAC_POOL_NAME_0
    range_list = conf.MAC_POOL_RANGE_LIST
    ext_dc_1 = conf.EXTRA_DC[1]
    ext_dc_2 = conf.EXTRA_DC[2]

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        Create 2 new DCs with MAC pool
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_name_0, ranges=[cls.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

        logger.info("Create 2 new DCs with %s", cls.pool_name_0)
        for dc in [cls.ext_dc_1, cls.ext_dc_2]:
            helper.create_dc(dc_name=dc)

    @polarion("RHEVM3-6461")
    def test_remove_two_dcs(self):
        """
        Remove DCs
        Make sure that the MAC pool is not removed
        """
        for dc in [self.ext_dc_1, self.ext_dc_2]:
            if not ll_dc.remove_datacenter(positive=True, datacenter=dc):
                raise conf.NET_EXCEPTION()

            logger.info(
                "Make sure %s exists after DC removal" % self.pool_name_0
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(self.pool_name_0)
            if not mac_pool_obj:
                raise conf.NET_EXCEPTION(
                    "MAC pool was removed during %s removal" % dc
                )
            if dc == self.ext_dc_1:
                logger.info(
                    "Make sure %s is attached to %s after removal of the "
                    "first DC", self.pool_name_0, self.ext_dc_2
                )
                mac_on_dc = ll_mac_pool.get_mac_pool_from_dc(self.ext_dc_2)
                if not mac_on_dc.name == mac_pool_obj.name:
                    raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pool
        """
        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.pool_name_0)


@attr(tier=2)
class TestMacPoolRange10(NetworkTest):
    """
    MAC pool support for DCs with versions less than 3.6
    """
    __test__ = True
    dc_ver_name = ["_".join(["MAC_POOL_DC", str(i)]) for i in range(1, 6)]
    pool_name_0 = conf.MAC_POOL_NAME_0
    range_list = conf.MAC_POOL_RANGE_LIST

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        """
        if not ll_mac_pool.create_mac_pool(
            name=cls.pool_name_0, ranges=[cls.range_list[0]]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-6463")
    def test_create_dc_all_ver(self):
        """
        Create DCs with version 3.1 and up with non-Default MAC pool
        """
        logger.info(
            "Create DCs with versions 3.1 and up with %s MAC pool",
            self.pool_name_0
        )
        for i in range(1, 6):
            helper.create_dc(dc_name=conf.EXTRA_DC[i], version=conf.VERSION[i])

    @classmethod
    def teardown_class(cls):
        """
        Remove all created DCs
        Remove MAC pool
        """
        logger.info("Remove DCs with version less that 3.6")
        for i in range(1, 6):
            ll_dc.remove_datacenter(positive=True, datacenter=conf.EXTRA_DC[i])

        ll_mac_pool.remove_mac_pool(mac_pool_name=cls.pool_name_0)


@attr(tier=2)
@pytest.mark.usefixtures("mac_pool_range_11_fixture")
class TestMacPoolRange11(NetworkTest):
    """
     Assign MAC's for vNIC's from custom MAC pool range for DC with 3.5 version
    """
    __test__ = True
    vm = conf.VM_0
    nic_1 = conf.NIC_NAME_1
    nic_2 = conf.NIC_NAME_2

    @polarion("RHEVM3-6464")
    def test_dif_ver_dcs(self):
        """
        Add additional VNIC to VM and succeed
        Negative: Try to add 3rd VNIC and fail
        """
        helper.check_mac_in_range()
        if not ll_vms.addNic(positive=True, vm=self.vm, name=self.nic_1):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(positive=False, vm=self.vm, name=self.nic_2):
            raise conf.NET_EXCEPTION()
