#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature test
"""

from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase

import helper
import config as c

import logging
logger = logging.getLogger("MAC_Pool_Range_Per_DC_Cases")


@attr(tier=2)
class TestMacPoolRange01(TestCase):
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
        mac_range = '00:1a:4a:4c:7a:00-00:1a:4a:4c:7a:ff'
        logger.info("Negative: Try to configure MAC pool range")
        cmd = "=".join([c.MAC_POOL_RANGE_CMD, mac_range])
        if c.test_utils.set_engine_properties(c.ENGINE, [cmd], restart=False):
            raise c.NET_EXCEPTION(
                "Managed to configure MAC pool range when should be deprecated"
            )

        logger.info("Negative: Try to configure MaxMacCountPool")
        cmd = "=".join(["MaxMacCountPool", "100001"])
        if c.test_utils.set_engine_properties(c.ENGINE, [cmd], restart=False):
            raise c.NET_EXCEPTION(
                "Managed to configure Max Mac Count Pool value when should be "
                "deprecated"
            )


@attr(tier=2)
class TestMacPoolRange02(TestCase):
    """
    Default MAC pool range
    """
    __test__ = True

    @polarion("RHEVM3-6443")
    def test_default_mac_pool(self):
        """`
        Extend the default range values of Default MAC pool
        Shrink the default range values of Default MAC pool
        Add new ranges to the Default MAC pool
        Remove added ranges from the Default MAC pool
        Create a new DC and check it was created with updated Default
        MAC pool values
        Update the MAC pool to its original default values
        """
        logger.info("Extend and shrink the default MAC pool range")
        helper.update_mac_pool_range_size(
            mac_pool_name=c.DEFAULT_MAC_POOL, size=(2, 2)
        )
        helper.update_mac_pool_range_size(
            mac_pool_name=c.DEFAULT_MAC_POOL, size=(-2, -2)
        )

        logger.info("Add new ranges to the Default MAC pool")
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, range_list=c.MAC_POOL_RANGE_LIST
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add ranges to the Default MAC Pool"
            )

        logger.info("Remove added ranges from the Default MAC pool")
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, range_list=c.MAC_POOL_RANGE_LIST
        ):
            raise c.NET_EXCEPTION(
                "Couldn't remove the ranges from the Default MAC pool"
            )

        helper.create_dc(mac_pool_name='')

        logger.info(
            "Check that the new DC was created with the updated "
            "Default MAC pool"
        )
        if not (
                ll_mac_pool.get_default_mac_pool().get_id() ==
                ll_mac_pool.get_mac_pool_from_dc(c.EXT_DC_1).get_id()
        ):
            raise c.NET_EXCEPTION(
                "New DC was not created with the updated Default MAC pool "
                "values"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        helper.remove_dc()


@attr(tier=2)
class TestMacPoolRange03(TestCase):
    """
    Creating VNICs with updated MAC pool takes the MACs from the new pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 MAC pools
        Update DC with 1 of created MAC pools
        Add vNIC to VM
        """
        logger.info("Create 2 MAC pools")
        for i in range(2):
            helper.create_mac_pool(
                mac_pool_name=c.MAC_POOL_NAME[i],
                mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[i]]
            )

        helper.update_dc_with_mac_pool()
        helper.add_nic(name=c.NIC_NAME_1)

    @polarion("RHEVM3-6444")
    def test_update_mac_pool_vm(self):
        """
        Check that for updated DC with new MAC pool, the NICs on the VM on
        that DC are created with MACs from the new MAC pool range
        """
        helper.check_mac_in_range(vm=c.VM_NAME[0])
        helper.update_dc_with_mac_pool(mac_pool_name=c.MAC_POOL_NAME_1)

        helper.add_nic(name=c.NIC_NAME[2])
        helper.check_mac_in_range(
            vm=c.VM_NAME[0], nic=c.NIC_NAME[2],
            mac_range=c.MAC_POOL_RANGE_LIST[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM NICs
        Update DC with default MAC pool
        Remove created MAC pools
        """
        logger.info("Remove VNICs from %s", c.VM_NAME[0])
        for nic in c.NIC_NAME[1:3]:
            helper.remove_nic(nic=nic)

        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )

        logger.info("Remove MAC pools %s ", c.MAC_POOL_NAME[:2])
        for mac_pool in c.MAC_POOL_NAME[:2]:
            helper.remove_mac_pool(mac_pool_name=mac_pool)


@attr(tier=2)
class TestMacPoolRange04(TestCase):
    """
    Define new DC with new MAC address pool
    Test creation of a new DC with non-Default MAC pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """

        helper.create_mac_pool(mac_pool_name=c.MAC_POOL_NAME_0)

    def test_creation_new_dc(self):
        """
        Test creation of a new DC with non-Default MAC pool
        """
        helper.create_dc()

    @classmethod
    def teardown_class(cls):
        """
        Remove DC
        Remove MAC pool
        """
        helper.remove_dc()
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange05(TestCase):
    """
     Two pools with same name
     Negative: Try to create two pools with the same name
     Create two pools with the same range
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """

        helper.create_mac_pool()

    @polarion("RHEVM3-6445")
    def test_creation_pool_same_name(self):
        """
        Test creation of a new pool with the same name, but different range
        """
        logger.info(
            "Negative: Try to create a new MAC pool with the same name as "
            "existing one, but with different range"
        )
        helper.create_mac_pool(
            mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]], positive=False
        )

    @polarion("RHEVM3-6446")
    def test_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        logger.info(
            "Create a new MAC pool with the same range as "
            "existing one, but with different name"
        )
        helper.create_mac_pool(mac_pool_name=c.MAC_POOL_NAME_1)

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pools
        """
        logger.info("Remove MAC pools %s ", c.MAC_POOL_NAME[:2])
        for mac_pool in c.MAC_POOL_NAME[:2]:
            helper.remove_mac_pool(mac_pool_name=mac_pool)


@attr(tier=2)
class TestMacPoolRange06(TestCase):
    """
    Extend MAC pool range
    Check that you can add VNICs till you reach the limit of the MAC pool range
    Extending the MAC pool range by 2 will let you add 2 additional VNICs only
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with this MAC pool
        """
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6447")
    def test_range_limit_extend(self):
        """
        Add 3 VNICs to the VM till you reach the MAC pool range limit
        Add another VNIC and fail
        Extend the MAC pool range
        Add another VNICs (till you reach range limit again)
        Fail when you try to overcome that limit
        """
        for i in range(3):
            helper.add_nic(name=c.NIC_NAME[i+1])

        logger.info("Trying to add VNIC when there are no spare MACs to use")
        helper.add_nic(positive=False, name=c.NIC_NAME[4])

        helper.update_mac_pool_range_size()

        for i in range(4, 6):
            helper.add_nic(name=c.NIC_NAME[i])

        logger.info("Trying to add VNIC when there are no spare MACs to use")
        helper.add_nic(positive=False, name=c.NIC_NAME[6])

    @classmethod
    def teardown_class(cls):
        """
        Remove 6 VNICs from the VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in c.NIC_NAME[1:6]:
            helper.remove_nic(nic=nic)

        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange07(TestCase):
    """
    Shrink MAC pool range
    Check that you can add VNICs if you don't reach the limit of the
    MAC pool range
    Shrinking the MAC pool to the size equal to the number of VM NICs
    will not allow adding additional VNICs to VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with a new MAC pool
        """
        logger.info(
            "Create a new MAC pool %s and update with it DC %s",
            c.MAC_POOL_NAME_0, c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6448")
    def test_range_limit_shrink(self):
        """
        Add VNICs to the VM
        Shrink the MAC pool, so you can add only one new VNIC
        Add one VNIC and succeed
        Try to add additional VNIC to VM and fail
        """
        helper.add_nic()

        helper.update_mac_pool_range_size(extend=False, size=(0, -1))
        helper.add_nic(name=c.NIC_NAME[2])

        logger.info("Trying to add VNIC when there are no spare MACs to use")
        helper.add_nic(positive=False, name=c.NIC_NAME[3])

    @classmethod
    def teardown_class(cls):
        """
        Remove 2 VNICs from the VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in c.NIC_NAME[1:3]:
            helper.remove_nic(nic=nic)

        logger.info(
            "Update DC %s with default MAC pool and remove MAC pool %s",
            c.ORIG_DC, c.MAC_POOL_NAME_0
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange08(TestCase):
    """
    Add/remove ranges from pool
    Check that add and remove ranges from MAC pool is working as expected
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """
        helper.create_mac_pool()

    @polarion("RHEVM3-6449")
    def test_add_remove_ranges(self):
        """
        Add 2 new ranges
        Remove one of the added ranges
        Check that the correct ranges still exist in the Range list
        """
        logger.info("Add new ranges to the %s", c.MAC_POOL_NAME_0)
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME_0,
            range_list=c.MAC_POOL_RANGE_LIST[1:3]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add ranges to the %s" % c.MAC_POOL_NAME_0
            )
        logger.info(
            "Remove one of the added ranges from the %s",
            c.MAC_POOL_NAME_0
        )
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME_0,
            range_list=[c.MAC_POOL_RANGE_LIST[1]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't remove the range from the %s",
                c.MAC_POOL_NAME_0
            )

        logger.info(
            "Check that the correct ranges exist in the %s after add/remove "
            "ranges action", c.MAC_POOL_NAME_0
        )
        ranges = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME_0)
        )
        if len(ranges) != 2 or (
                c.MAC_POOL_RANGE_LIST[1] in ranges
        ):
            raise c.NET_EXCEPTION(
                "Ranges are incorrect after add/remove ranges action"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pool
        """

        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange09(TestCase):
    """
    Non-Continues ranges in MAC pool
    Check that you can add VNICs according to the number of MAC ranges when
    each MAC range has only one MAC address in the pool
    """
    __test__ = True
    MAC_POOL_RANGES = [
        ("00:00:00:10:10:10", "00:00:00:10:10:10"),
        ("00:00:00:10:10:20", "00:00:00:10:10:20"),
        ("00:00:00:10:10:30", "00:00:00:10:10:30"),
        ("00:00:00:10:10:40", "00:00:00:10:10:40"),
        ("00:00:00:10:10:50", "00:00:00:10:10:50"),
        ("00:00:00:10:10:60", "00:00:00:10:10:60")
    ]

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with new MAC pool
        Add 3 VNICs to VM on that DC
        """
        logger.info(
            "Create a new MAC pool %s and update with it DC %s",
            c.MAC_POOL_NAME_0, c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=cls.MAC_POOL_RANGES[:3])
        helper.update_dc_with_mac_pool()

        for i in range(3):
            helper.add_nic(name=c.NIC_NAME[i+1])

    @polarion("RHEVM3-6450")
    def test_non_continuous_ranges(self):
        """
        Test VNICs have non-continuous MACs (according to the Ranges values)
        """
        helper.check_single_mac_range_match(
            mac_ranges=self.MAC_POOL_RANGES[:3], start_idx=1, end_idx=4
        )

        logger.info("Add 2 additional ranges to %s", c.MAC_POOL_NAME_0)
        if not hl_mac_pool.add_ranges_to_mac_pool(
            c.MAC_POOL_NAME_0, self.MAC_POOL_RANGES[3:5]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add 2 additional ranges to %s" %
                c.MAC_POOL_NAME_0
            )

        for i in range(4, 6):
            helper.add_nic(name=c.NIC_NAME[i])

        helper.check_single_mac_range_match(
            mac_ranges=self.MAC_POOL_RANGES[3:5], start_idx=4, end_idx=6
        )

        logger.info("Remove the last added range and add another one")
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            c.MAC_POOL_NAME_0, [self.MAC_POOL_RANGES[4]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't remove the last added range from %s" %
                c.MAC_POOL_NAME_0
            )
        if not hl_mac_pool.add_ranges_to_mac_pool(
            c.MAC_POOL_NAME_0, [self.MAC_POOL_RANGES[5]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add  additional ranges to %s" %
                c.MAC_POOL_NAME_0
            )

        helper.add_nic(name=c.NIC_NAME[6])

        logger.info(
            "Check that adding VNIC takes MAC from the last added Range"
        )
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=c.VM_NAME[0], nic=c.NIC_NAME[6]
        )

        if nic_mac != self.MAC_POOL_RANGES[-1][0]:
            raise c.NET_EXCEPTION(
                "vNIC MAC %s is not in the MAC pool range for %s" %
                (nic_mac, c.MAC_POOL_NAME_0)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VNICs from VM
        Update DC with default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in c.NIC_NAME[1:7]:
            helper.remove_nic(nic=nic)

        logger.info(
            "Update DC %s with default MAC pool and remove MAC pool %s",
            c.ORIG_DC, c.MAC_POOL_NAME_0
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange10(TestCase):
    """
    Manually assign MAC from/not from MAC pool range
    Check that when MAC pool is exhausted, adding new VNIC to VM is possible
    only with manual MAC configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with a new MAC pool
        """
        logger.info(
            "Create a new MAC pool %s and update with it DC %s",
            c.MAC_POOL_NAME_0, c.ORIG_DC
        )
        helper.create_mac_pool()
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6451")
    def test_auto_assigned_vs_manual(self):
        """
        Add VNICs to the VM till MAC pool is exhausted
        Try to add additional VNIC with autoassigned MAC to VM and fail
        Add MAC manually (not from a range) and succeed
        """
        for i in range(2):
            helper.add_nic(name=c.NIC_NAME[i+1])

        helper.add_nic(positive=False, name=c.NIC_NAME[3])
        helper.add_nic(name=c.NIC_NAME[3], mac_address="00:00:00:12:34:56")

    @classmethod
    def teardown_class(cls):
        """
        Remove 3 VNICs from the VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in c.NIC_NAME[1:4]:
            helper.remove_nic(nic=nic)

        logger.info(
            "Update DC %s with default MAC pool and remove MAC pool %s",
            c.ORIG_DC, c.MAC_POOL_NAME_0
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True)
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange11(TestCase):
    """
    Assign same pool to multiple DC's -Disallow Duplicates
    Check that if "Allow duplicates" is False, it's impossible to add VNIC
    with manual MAC allocation to VM
    """
    __test__ = True
    log = "%s: Check adding vNIC to VM on DC %s when allow duplicates is False"

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update 2 DCs with a new MAC pool
        Add vNIC with auto assignment to VM
        """
        helper.create_mac_pool()

        for dc in (c.DC_NAME[0], c.EXT_DC_0):
            helper.update_dc_with_mac_pool(dc=dc)

        helper.add_nic(name=c.NIC_NAME_1)

    @polarion("RHEVM3-6452")
    def test_auto_assigned_vs_manual(self):
        """
        Negative:Try to add a new VNIC to VM when explicitly providing MAC
        on the first VM NIC (manual MAC configuration) when allow duplicate
        is False
        Negative: Try to add this NIC to VM on another DC
        Add NIC to VM on the second DC with auto assignment
        """
        logger.info("Getting MAC address for NIC %s", c.NIC_NAME_1)
        mac_address = ll_vm.get_vm_nic_mac_address(
            vm=c.VM_NAME[0], nic=c.NIC_NAME_1
        )
        if not mac_address:
            raise c.NET_EXCEPTION(
                "Failed to get MAC from %s on %s" %
                (c.NIC_NAME_1, c.VM_NAME[0])
            )

        logger.info(self.log, "Negative", c.DC_NAME[0])
        helper.add_nic(
            positive=False, name=c.NIC_NAME[2], mac_address=mac_address
        )

        logger.info(self.log, "Negative", c.EXT_DC_0)
        helper.add_nic(
            positive=False, vm=c.MP_VM, name=c.NIC_NAME_1,
            mac_address=mac_address
        )

        helper.add_nic(vm=c.MP_VM, name=c.NIC_NAME_1)

    @classmethod
    def teardown_class(cls):
        """
        Remove VNIC from both VMs
        Update DCs with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for vm in (c.VM_NAME[0], c.MP_VM):
            helper.remove_nic(vm=vm)

        for dc in (c.DC_NAME[0], c.EXT_DC_0):
            logger.info(
                "Update DC %s with default MAC pool", dc
            )
            helper.update_dc_with_mac_pool(
                dc=dc, mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
            )

        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange12(TestCase):
    """
    Assign same pool to multiple DCs -Allow Duplicates
    Check that if "Allow duplicates" is True, it's possible to add vNIC
    with manual MAC allocation to VM
    """
    __test__ = True
    bz = {"1212461": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    log = "Check adding vNIC to VM on DC %s when allow duplicates is True"

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update 2 DCs with a new MAC pool
        """
        helper.create_mac_pool(allow_duplicates=True)

        for dc in (c.DC_NAME[0], c.EXT_DC_0):
            helper.update_dc_with_mac_pool(dc=dc)
        helper.add_nic()

    @polarion("RHEVM3-6453")
    def test_allow_duplicates(self):
        """
        Add VNIC with auto assignment to VM
        Add a new VNIC to VM with manual MAC configuration and
        allow_duplicates is True
        Add VNIC to VM on another DC with the same MAC (manual configuration)
        Add NIC to VM on the second DC with auto assignment
        Fail on adding additional VNIC as MAC pool exhausted
        Succeed on adding VNIC with MAC pool manual configuration
        """
        logger.info("Getting MAC address for NIC %s", c.NIC_NAME_1)
        mac_address = ll_vm.get_vm_nic_mac_address(
            vm=c.VM_NAME[0], nic=c.NIC_NAME_1
        )
        if not mac_address:
            raise c.NET_EXCEPTION(
                "Failed to get MAC from %s on %s" %
                (c.NIC_NAME_1, c.VM_NAME[0])
            )

        logger.info(self.log, c.DC_NAME[0])
        helper.add_nic(name=c.NIC_NAME[2], mac_address=mac_address)

        logger.info(self.log, c.EXT_DC_0)
        helper.add_nic(
            vm=c.MP_VM, name=c.NIC_NAME_1, mac_address=mac_address
        )

        helper.add_nic(vm=c.MP_VM, name=c.NIC_NAME[2])
        helper.add_nic(positive=False, vm=c.MP_VM, name=c.NIC_NAME[3])

        logger.info(self.log, c.EXT_DC_0)
        helper.add_nic(
            vm=c.MP_VM, name=c.NIC_NAME[3], mac_address=mac_address
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove VNIC from both VMs
        Update DCs with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VMs")
        for vm in (c.VM_NAME[0], c.MP_VM):
            for nic in (c.NIC_NAME_1, c.NIC_NAME[2]):
                helper.remove_nic(vm=vm, nic=nic)

        helper.remove_nic(vm=c.MP_VM, nic=c.NIC_NAME[3])

        for dc in (c.DC_NAME[0], c.EXT_DC_0):
            logger.info("Update DC %s with default MAC pool", dc)
            helper.update_dc_with_mac_pool(
                dc=dc, mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
            )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange13(TestCase):
    """
    Combine MAC pool range of Unicast and multicast MAC's
    Check that when having a combined range of multicast and unicast addresses
    the new VNICs will be created with unicast addresses only
    """
    __test__ = True
    bz = {"1219383": {"engine": ["rest", "sdk", "java"], "version": ["3.6"]}}
    MAC_POOL_RANGES = [
        ("00:ff:ff:ff:ff:ff", "02:00:00:00:00:01")
    ]

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool with range having multicast and unicast MACs
        Update DC with a new MAC pool
        """
        helper.create_mac_pool(mac_pool_ranges=cls.MAC_POOL_RANGES)
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6454")
    def test_multicast_unicast_mix(self):
        """
        Add 2 VNICs to VM
        Negative: Try to add 3rd VNIC and fail as all the available MACs
        in the MAC pool are multicast MACs
        """
        logger.info("Add 2 VNICs to %s", c.VM_NAME[0])
        for i in range(2):
            helper.add_nic(name=c.NIC_NAME[i+1])

        logger.info(
            "Negative: Try to add 3rd VNIC when MAC pool has only "
            "multicast MACs available"
        )
        helper.add_nic(positive=False, name=c.NIC_NAME[3])

    @classmethod
    def teardown_class(cls):
        """
        Remove VNIC from VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in (c.NIC_NAME_1, c.NIC_NAME[2]):
            helper.remove_nic(nic=nic)

        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange14(TestCase):
    """
    Create VM from Template
    Check that VNIC created from template uses the correct MAC POOL value
    Add 2 more VNICs to template, so it will be impossible to create a new VM
    from that template
    Check that creating new VM from template fails
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with a new MAC pool
        Create VM from template
        Add 2 more NICs to template
        """
        logger.info(
            "Create a new MAC pool %s and update with it DC %s",
            c.MAC_POOL_NAME_0, c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

        logger.info(
            "Create VM %s from template %s",
            c.MP_VM_NAMES[1], c.TEMPLATE_NAME[0]
        )
        if not ll_vm.createVm(
            positive=True, vmName=c.MP_VM_NAMES[1], vmDescription="linux vm",
            cluster=c.CLUSTER_NAME[0], template=c.TEMPLATE_NAME[0],
            placement_host=c.HOSTS[0], network=c.MGMT_BRIDGE
        ):
            raise c.NET_EXCEPTION(
                "Failed to create VM %s from template" % c.MP_VM_NAMES[1]
            )

        logger.info(
            "Add 2 additional NICs to template %s", c.TEMPLATE_NAME[0]
        )
        for i in range(2):
            if not ll_templates.addTemplateNic(
                True, c.TEMPLATE_NAME[0], name=c.NIC_NAME[i + 1],
                data_center=c.ORIG_DC
            ):
                raise c.NET_EXCEPTION(
                    "Cannot add NIC %s to Template" % c.NIC_NAME[i+1]
                )

    @polarion("RHEVM3-6455")
    def test_vm_from_template(self):
        """
        Check that VNIC created from template uses the correct MAC POOL values
        Negative: Try to create new VM from template when there are not enough
        MACs for its VNICs
        """
        helper.check_mac_in_range(
            vm=c.MP_VM_NAMES[1], nic=c.NIC_NAME[0],
            mac_range=c.MAC_POOL_RANGE_LIST[1]
        )

        logger.info(
            "Negative: Try to create new VM from template when there are "
            "not enough MACs for its VNICs"
        )
        if ll_vm.createVm(
            positive=True, vmName="neg_vm", vmDescription="linux vm",
            cluster=c.CLUSTER_NAME[0], template=c.TEMPLATE_NAME[0],
            placement_host=c.HOSTS[0]
        ):
            raise c.NET_EXCEPTION(
                "Succeeded to create VM  from template when there are not "
                "enough MACs for its VNICs"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM
        Remove VNICs from template
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info(
            "Remove %s from DC: %s", c.MP_VM_NAMES[1], c.ORIG_DC
        )
        if not ll_vm.removeVm(positive=True, vm=c.MP_VM_NAMES[1]):
            logger.error(
                "Couldn't remove imported VM %s" % c.MP_VM_NAMES[1]
            )
            cls.test_failed = True

        logger.info("Remove VNICs from template")
        for i in range(2):
            if not ll_templates.removeTemplateNic(
                positive=True, template=c.TEMPLATE_NAME[0], nic=c.NIC_NAME[i+1]
            ):
                logger.error(
                    "Couldn't remove %s from template" % c.NIC_NAME[i+1]
                )
                cls.test_failed = True

        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange15(TestCase):
    """
    Negative: Try to remove the default MAC pool
    """
    __test__ = True

    @polarion("RHEVM3-6457")
    def test_remove_default_mac_pool(self):
        """
        Negative: Remove of Default MAC pool should fail
        """
        logger.info("Try to remove default MAC pool range.")
        if ll_mac_pool.remove_mac_pool(c.DEFAULT_MAC_POOL):
            raise c.NET_EXCEPTION(
                "Could remove the default MAC pool when shouldn't"
            )


@attr(tier=2)
class TestMacPoolRange16(TestCase):
    """
    Removal of MAC pool assigned to DC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        Update DC with new MAC pool
        """
        logger.info(
            "Create a new MAC pool %s and update with it DC %s",
            c.MAC_POOL_NAME_0, c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6458")
    def test_remove_used_mac_pool(self):
        """
        Negative:Try to remove the MAC pool that is already assigned to DC
        """
        logger.info(
            "Negative: Try to remove MAC pool %s ", c.MAC_POOL_NAME_0)
        if ll_mac_pool.remove_mac_pool(c.MAC_POOL_NAME_0):
            raise c.NET_EXCEPTION(
                "Could remove MAC pool %s though it's attached to DC %s" %
                (c.MAC_POOL_NAME_0, c.ORIG_DC)
            )

    @classmethod
    def teardown_class(cls):
        """
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange17(TestCase):
    """
    Removal of MAC pool that is not assigned to DC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create 2 MAC pools
        Update DC with the first MAC pool
        """
        logger.info("Create 2 MAC pools %s", c.MAC_POOL_NAME[:2])
        for i in range(2):
            helper.create_mac_pool(
                mac_pool_name=c.MAC_POOL_NAME[i],
                mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[i]]
            )
        helper.update_dc_with_mac_pool()

    @polarion("RHEVM3-6459")
    def test_remove_unused_mac_pool(self):
        """
        Remove the MAC pool that is not assigned to any DC
        Add new MAC pool
        Assign it to DC
        Remove the MAC pool previously attached to DC
        """
        helper.remove_mac_pool(mac_pool_name=c.MAC_POOL_NAME_1)
        helper.create_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME[2],
            mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[2]]
        )
        helper.update_dc_with_mac_pool(mac_pool_name=c.MAC_POOL_NAME[2])
        helper.remove_mac_pool()

    @classmethod
    def teardown_class(cls):
        """
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool(mac_pool_name=c.MAC_POOL_NAME[2])


@attr(tier=2)
class TestMacPoolRange18(TestCase):
    """
    Removal of DC with custom MAC pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        Create a new DC with MAC pool
        """
        helper.create_mac_pool()
        helper.create_dc()

    @polarion("RHEVM3-6460")
    def test_remove_dc(self):
        """
        Remove DC
        Make sure that the MAC pool is not removed
        """
        helper.remove_dc()

        logger.info(
            "Make sure %s exists after DC removal" % c.MAC_POOL_NAME_0
        )
        if not ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME_0):
            raise c.NET_EXCEPTION(
                "MAC pool was removed during DC removal"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pool
        """
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange19(TestCase):
    """
    Removal of DC with custom MAC pool when that MAC pool is assigned to 2 DCs
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        Create 2 new DCs with MAC pool
        """
        helper.create_mac_pool()

        logger.info("Create 2 new DCs with %s", c.MAC_POOL_NAME_0)
        for i in range(1, 3):
            helper.create_dc(dc_name=c.EXTRA_DC[i])

    @polarion("RHEVM3-6461")
    def test_remove_two_dcs(self):
        """
        Remove DCs
        Make sure that the MAC pool is not removed
        """
        for i in range(1, 3):
            helper.remove_dc(dc_name=c.EXTRA_DC[i])

            logger.info(
                "Make sure %s exists after DC removal" % c.MAC_POOL_NAME_0
            )
            mac_pool_obj = ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME_0)
            if not mac_pool_obj:
                raise c.NET_EXCEPTION(
                    "MAC pool was removed during %s removal" % c.EXTRA_DC[i]
                )
            if i == 1:
                logger.info(
                    "Make sure %s is attached to %s after removal of the "
                    "first DC", c.MAC_POOL_NAME_0, c.EXTRA_DC[i+1]
                )
                mac_on_dc = ll_mac_pool.get_mac_pool_from_dc(c.EXTRA_DC[2])
                if not mac_on_dc.name == mac_pool_obj.name:
                    raise c.NET_EXCEPTION(
                        "MAC pool on the DC %s changed after removal of the DC"
                        " %s" % (c.EXTRA_DC[2], c.EXTRA_DC[1])
                    )

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pool
        """
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange20(TestCase):
    """
    Recreate DC with custom MAC pool and make sure it was
    recreated with the Default MAC pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool
        Create a new DC with MAC pool
        Remove a created DC
        """
        helper.create_mac_pool()
        helper.create_dc()
        helper.remove_dc()

    @polarion("RHEVM3-6462")
    def test_recreate_dc(self):
        """
        Recreate just removed DC
        Make sure that the DC was recreated with the Default MAC pool
        Remove DC
        Make sure Default MAC pool still exists
        """
        logger.info(
            "Recreate removed DC without explicitly providing MAC pool"
        )
        helper.create_dc(mac_pool_name="")

        logger.info(
            "Check that the new DC was created with the Default MAC pool"
        )
        if not (
            ll_mac_pool.get_default_mac_pool().id ==
            ll_mac_pool.get_mac_pool_from_dc(c.EXT_DC_1).id
        ):
            raise c.NET_EXCEPTION(
                "New DC was not created with the Default MAC pool values"
            )

        helper.remove_dc()

        logger.info(
            "Make sure %s exists after DC removal", c.DEFAULT_MAC_POOL
        )
        if not ll_mac_pool.get_mac_pool(c.DEFAULT_MAC_POOL):
            raise c.NET_EXCEPTION("MAC pool was removed during DC removal")

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pool
        """
        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange21(TestCase):
    """
    MAC pool support for DCs with versions less than 3.6
    """
    __test__ = True
    DC_VER_NAME = ["_".join(["MAC_POOL_DC", str(i)]) for i in range(1, 6)]

    @classmethod
    def setup_class(cls):
        """
        Create MAC pool

        """
        helper.create_mac_pool()

    @polarion("RHEVM3-6463")
    def test_create_dc_all_ver(self):
        """
        Create DCs with version 3.1 and up with non-Default MAC pool
        """
        logger.info(
            "Create DCs with versions 3.1 and up with %s MAC pool",
            c.MAC_POOL_NAME_0
        )
        for i in range(1, 6):
            helper.create_dc(dc_name=c.EXTRA_DC[i], version=c.VERSION[i])

    @classmethod
    def teardown_class(cls):
        """
        Remove all created DCs
        Remove MAC pool
        """
        logger.info("Remove DCs with version less that 3.6")
        for i in range(1, 6):
            helper.remove_dc(dc_name=c.EXTRA_DC[i])

        helper.remove_mac_pool()


@attr(tier=2)
class TestMacPoolRange22(TestCase):
    """
     Assign MAC's for vNIC's from custom MAC pool range for DC with 3.5 version
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Update additional DC to be 3.5
        Create a new MAC pool
        Update DCs with a new MAC pool
        Add NIC to VM
        """
        logger.info("Update DC %s to have 3.5 version", c.EXT_DC_0)
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=c.EXT_DC_0, version="3.5"
        ):
            raise c.NET_EXCEPTION(
                "Couldn't update DC %s to have 3.5 version" % c.EXT_DC_0
            )

        helper.create_mac_pool()

        for dc in (c.ORIG_DC, c.EXT_DC_0):
            helper.update_dc_with_mac_pool(dc=dc)

        helper.add_nic(vm=c.MP_VM)

    @polarion("RHEVM3-6464")
    def test_dif_ver_dcs(self):
        """
        Add additional VNIC to VM and succeed
        Negative: Try to add 3rd VNIC and fail
        """
        helper.check_mac_in_range()

        logger.info(
            "Add VNIC to VM %s on DC %s", c.VM_NAME[0], c.DC_NAME[0]
        )
        helper.add_nic()

        logger.info(
            "Negative: Try to add VNIC to VM %s on DC %s when no available "
            "MAC exists in the MAC pool used by both DCs",
            c.VM_NAME[0], c.ORIG_DC
        )

        helper.add_nic(positive=False, name=c.NIC_NAME[2])

    @classmethod
    def teardown_class(cls):
        """
        Update additional DC to have 3.6 version
        Remove VNICs from both VMs
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Update DC %s to have 3.6 version", c.EXT_DC_0)
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=c.EXT_DC_0, version=c.COMP_VERSION
        ):
            logger.error(
                "Couldn't update DC %s to have 3.5 version" % c.EXT_DC_0
            )

        for vm in (c.VM_NAME[0], c.MP_VM):
            helper.remove_nic(vm=vm)

        logger.info(
            "Update DCs %s with default MAC pool"
        )
        for dc in (c.ORIG_DC, c.EXT_DC_0):
            helper.update_dc_with_mac_pool(
                dc=dc, mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
            )

        helper.remove_mac_pool()
