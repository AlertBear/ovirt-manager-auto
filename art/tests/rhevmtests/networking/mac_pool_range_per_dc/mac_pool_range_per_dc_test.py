#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature test
"""


import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import utilities.utils as utils
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import helper
import config as c

import logging
logger = logging.getLogger("MAC_Pool_Range_Per_DC_Cases")


@attr(tier=1)
class TestMacPoolRange01(TestCase):
    """
    RHEVM3-6442 - Try to use old configuration with engine-config
    Check that invalid engine commands are deprecated:
        1) MAC pool range
        2) Max MAC count pool
    """
    __test__ = True

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


@attr(tier=1)
class TestMacPoolRange02(TestCase):
    """
    RHEVM3-6443 - Default MAC pool range
    """
    __test__ = True

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

        logger.info("Create a new DC %s", c.EXT_DC_1)
        if not ll_dc.addDataCenter(
            positive=True, name=c.EXT_DC_1, storage_type=c.STORAGE_TYPE,
            version=c.COMP_VERSION, local=False
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add a new DC with default MAC pool to the setup"
            )

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
        logger.info("Remove a DC %s", c.EXT_DC_1)
        if not ll_dc.removeDataCenter(positive=True, datacenter=c.EXT_DC_1):
            logger.error("Failed to remove DC %s", c.EXT_DC_1)
            cls.test_failed = True


@attr(tier=1)
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
            if not ll_mac_pool.create_mac_pool(
                name=c.MAC_POOL_NAME[i], ranges=[c.MAC_POOL_RANGE_LIST[i]]
            ):
                raise c.NET_EXCEPTION(
                    "Cannot create new MAC pool %s" % c.MAC_POOL_NAME[i]
                )

        helper.update_dc_with_mac_pool()
        helper.add_nic(name=c.NIC_NAME[1])

    def test_update_mac_pool_vm(self):
        """
        Check that for updated DC with new MAC pool, the NICs on the VM on
        that DC are created with MACs from the new MAC pool range
        """
        logger.info("Find the MAC of the VM NIC %s", c.NIC_NAME[1])
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=c.VM_NAME[0], nic=c.NIC_NAME[1]
        )
        if not nic_mac:
            raise c.NET_EXCEPTION(
                "MAC was not found on NIC %s" % c.NIC_NAME[1]
            )

        logger.info("Find the MAC range for %s", c.MAC_POOL_RANGE_LIST[0])
        mac_range = utils.MACRange(
            c.MAC_POOL_RANGE_LIST[0][0], c.MAC_POOL_RANGE_LIST[0][1]
        )
        if nic_mac not in mac_range:
            raise c.NET_EXCEPTION(
                "MAC %s is not in the MAC pool range for %s" %
                (nic_mac, c.MAC_POOL_NAME[0])
            )

        logger.info(
            "Update the DC %s with MAC pool %s", c.ORIG_DC, c.MAC_POOL_NAME[1]
        )
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=c.ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[1])
        ):
            raise c.NET_EXCEPTION(
                "Couldn't update DC %s with MAC pool %s" %
                (c.ORIG_DC, c.MAC_POOL_NAME[1])
            )

        helper.add_nic(name=c.NIC_NAME[2])

        logger.info("Find the MAC of the VM NIC %s", c.NIC_NAME[2])
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=c.VM_NAME[0], nic=c.NIC_NAME[2]
        )
        if not nic_mac:
            raise c.NET_EXCEPTION(
                "MAC was not found on NIC %s" % c.NIC_NAME[2]
            )

        logger.info("Find the MAC range for %s", c.MAC_POOL_RANGE_LIST[1])
        mac_range = utils.MACRange(
            c.MAC_POOL_RANGE_LIST[1][0], c.MAC_POOL_RANGE_LIST[1][1]
        )
        if nic_mac not in mac_range:
            raise c.NET_EXCEPTION(
                "MAC %s is not in the MAC pool range for %s" %
                (nic_mac, c.MAC_POOL_NAME[1])
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


@attr(tier=1)
class TestMacPoolRange04(TestCase):
    """
    RHEVM3-6444 - Define new DC with new MAC address pool
    Test creation of a new DC with non-Default MAC pool
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """

        helper.create_mac_pool(mac_pool_name=c.MAC_POOL_NAME[0])

    def test_creation_new_dc(self):
        """
        Test creation of a new DC with non-Default MAC pool
        """
        logger.info(
            "Create a new DC %s with MAC pool %s",
            c.EXT_DC_1, c.MAC_POOL_NAME[0]
        )
        mac_pool_obj = ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[0])
        if not ll_dc.addDataCenter(
            positive=True, name=c.EXT_DC_1, storage_type=c.STORAGE_TYPE,
            version=c.COMP_VERSION, local=False, mac_pool=mac_pool_obj
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add a new DC %s with non default MAC pool %s to "
                "the setup" % (c.EXT_DC_1, c.MAC_POOL_NAME[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove DC
        Remove MAC pool
        """
        logger.info("Remove a DC %s", c.EXT_DC_1)
        if not ll_dc.removeDataCenter(positive=True, datacenter=c.EXT_DC_1):
            logger.error("Failed to remove DC %s", c.EXT_DC_1)
            cls.test_failed = False

        helper.remove_mac_pool()


@attr(tier=1)
class TestMacPoolRange05(TestCase):
    """
    RHEVM3-6445 - Two pools with same name
     Negative: Try to create two pools with the same name
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """

        helper.create_mac_pool()

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

    def test_creation_pool_same_range(self):
        """
        Test creation of a new pool with the same range, but different names
        """
        logger.info(
            "Create a new MAC pool with the same range as "
            "existing one, but with different name"
        )
        helper.create_mac_pool(mac_pool_name=c.MAC_POOL_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        Remove MAC pools
        """
        logger.info("Remove MAC pools %s ", c.MAC_POOL_NAME[:2])
        for mac_pool in c.MAC_POOL_NAME[:2]:
            helper.remove_mac_pool(mac_pool_name=mac_pool)


@attr(tier=1)
class TestMacPoolRange06(TestCase):
    """
    RHEVM3-6447 - Extend MAC pool range
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

        logger.info("Update DC %s with default MAC pool", c.ORIG_DC)
        if not ll_dc.updateDataCenter(
            True, datacenter=c.ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(c.DEFAULT_MAC_POOL)
        ):
            logger.error(
                "Couldn't update DC %s with default MAC pool",
                c.ORIG_DC
            )
            cls.test_failed = False

        helper.remove_mac_pool()


@attr(tier=1)
class TestMacPoolRange07(TestCase):
    """
    RHEVM3-6447 - Extend MAC pool range
    Check that you can add VNICs till you reach the limit of the MAC pool range
    Extending the MAC pool range by 2 will let you add 2 additional VNICs only
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
            c.MAC_POOL_NAME[0], c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

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

        logger.info(
            "Update DC %s with default MAC pool and remove MAC pool %s",
            c.ORIG_DC, c.MAC_POOL_NAME[0]
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=1)
class TestMacPoolRange08(TestCase):
    """
    RHEVM3-6448 - Shrink MAC pool range
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
            c.MAC_POOL_NAME[0], c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=[c.MAC_POOL_RANGE_LIST[1]])
        helper.update_dc_with_mac_pool()

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
            c.ORIG_DC, c.MAC_POOL_NAME[0]
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()


@attr(tier=1)
class TestMacPoolRange09(TestCase):
    """
    RHEVM3-6449 - Add/remove ranges from pool
    Check that add and remove ranges from MAC pool is working as expected
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create a new MAC pool
        """
        helper.create_mac_pool()

    def test_add_remove_ranges(self):
        """
        Add 2 new ranges
        Remove one of the added ranges
        Check that the correct ranges still exist in the Range list
        """
        logger.info("Add new ranges to the %s", c.MAC_POOL_NAME[0])
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME[0],
            range_list=c.MAC_POOL_RANGE_LIST[1:3]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add ranges to the %s" % c.MAC_POOL_NAME[0]
            )
        logger.info(
            "Remove one of the added ranges from the %s",
            c.MAC_POOL_NAME[0]
        )
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME[0],
            range_list=[c.MAC_POOL_RANGE_LIST[1]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't remove the range from the %s",
                c.MAC_POOL_NAME[0]
            )

        logger.info(
            "Check that the correct ranges exist in the %s after add/remove "
            "ranges action", c.MAC_POOL_NAME[0]
        )
        ranges = ll_mac_pool.get_mac_range_values(
            ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[0])
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


@attr(tier=1)
class TestMacPoolRange10(TestCase):
    """
    RHEVM3-6450 - Non-Continues ranges in MAC pool
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
            c.MAC_POOL_NAME[0], c.ORIG_DC
        )
        helper.create_mac_pool(mac_pool_ranges=cls.MAC_POOL_RANGES[:3])
        helper.update_dc_with_mac_pool()

        for i in range(3):
            helper.add_nic(name=c.NIC_NAME[i+1])

    def test_non_continuous_ranges(self):
        """
        Test VNICs have non-continuous MACs (according to the Ranges values)
        """
        logger.info("Check that 3 MACs on the VNICs correspond to 3 Ranges")
        ranges = [i[0] for i in self.MAC_POOL_RANGES[:3]]
        for i in range(1, 4):
            nic_mac = ll_vm.get_vm_nic_mac_address(
                vm=c.VM_NAME[0], nic=c.NIC_NAME[i]
            )

            if nic_mac in ranges:
                ranges.remove(nic_mac)
            else:
                raise c.NET_EXCEPTION(
                    "VNIC MAC %s is not in the MAC pool range for %s" %
                    (nic_mac, c.MAC_POOL_NAME[0])
                )

        logger.info("Add 2 additional ranges to %s", c.MAC_POOL_NAME[0])
        if not hl_mac_pool.add_ranges_to_mac_pool(
            c.MAC_POOL_NAME[0], self.MAC_POOL_RANGES[3:5]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add 2 additional ranges to %s" %
                c.MAC_POOL_NAME[0]
            )

        for i in range(4, 6):
            helper.add_nic(name=c.NIC_NAME[i])

        logger.info(
            "Check that 2 MACs on the VNICs correspond to 2 added Ranges"
        )
        ranges = [i[0] for i in self.MAC_POOL_RANGES[3:5]]
        for i in range(4, 6):
            nic_mac = ll_vm.get_vm_nic_mac_address(
                vm=c.VM_NAME[0], nic=c.NIC_NAME[i]
            )

            if nic_mac in ranges:
                ranges.remove(nic_mac)
            else:
                raise c.NET_EXCEPTION(
                    "VNIC MAC %s is not in the MAC pool range for %s" %
                    (nic_mac, c.MAC_POOL_NAME[0])
                )

        logger.info("Remove the last added range and add another one")
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            c.MAC_POOL_NAME[0], [self.MAC_POOL_RANGES[4]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't remove the last added range from %s" %
                c.MAC_POOL_NAME[0]
            )
        if not hl_mac_pool.add_ranges_to_mac_pool(
            c.MAC_POOL_NAME[0], [self.MAC_POOL_RANGES[5]]
        ):
            raise c.NET_EXCEPTION(
                "Couldn't add  additional ranges to %s" %
                c.MAC_POOL_NAME[0]
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
                "VNIC MAC %s is not in the MAC pool range for %s" %
                (nic_mac, c.MAC_POOL_NAME[0])
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
            c.ORIG_DC, c.MAC_POOL_NAME[0]
        )
        helper.update_dc_with_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, teardown=True
        )
        helper.remove_mac_pool()
