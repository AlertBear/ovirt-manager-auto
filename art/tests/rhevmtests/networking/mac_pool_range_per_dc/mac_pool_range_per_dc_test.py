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
        default_mac_pool = ll_mac_pool.get_default_mac_pool()
        default_mac_pool_range = ll_mac_pool.get_mac_range_values(
            default_mac_pool
        )
        if not default_mac_pool_range:
            raise c.NET_EXCEPTION("Failed to get default MAC pool range")
        default_mac_pool_range = default_mac_pool_range[0]

        low_mac = utils.MAC(default_mac_pool_range[0])
        high_mac = utils.MAC(default_mac_pool_range[1])

        logger.info("Extend the default MAC pool range by 4 MACs")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, range_dict={
                default_mac_pool_range: (str(low_mac - 2), str(high_mac + 2))
            }
        ):
            raise c.NET_EXCEPTION("Couldn't extend the Default MAC pool range")

        logger.info("Shrink the updated default MAC pool range by 4 MACs")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, range_dict={
                (str(low_mac - 2), str(high_mac + 2)):
                    (str(low_mac + 2), str(high_mac - 2))
            }
        ):
            raise c.NET_EXCEPTION("Couldn't shrink the default MAC pool range")

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

        logger.info("Update the Default MAC pool to its original values")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=c.DEFAULT_MAC_POOL, range_dict={
                (str(low_mac + 2), str(high_mac - 2)): default_mac_pool_range
            }
        ):
            raise c.NET_EXCEPTION(
                "Couldn't update Default MAC pool range to its original value"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        logger.info("Remove a DC %s", c.EXT_DC_1)
        if not ll_dc.removeDataCenter(positive=True, datacenter=c.EXT_DC_1):
            logger.error("Failed to remove DC %s", c.EXT_DC_1)


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
        """
        logger.info("Create 2 MAC pools")
        for i in range(2):
            if not ll_mac_pool.create_mac_pool(
                name=c.MAC_POOL_NAME[i], ranges=[c.MAC_POOL_RANGE_LIST[i]]
            ):
                raise c.NET_EXCEPTION(
                    "Cannot create new MAC pool %s" % c.MAC_POOL_NAME[i]
                )

        logger.info(
            "Update the DC %s with MAC pool %s", c.ORIG_DC, c.MAC_POOL_NAME[0]
        )
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=c.ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[0])
        ):
            raise c.NET_EXCEPTION(
                "Couldn't update DC %s with MAC pool %s" %
                (c.ORIG_DC, c.MAC_POOL_NAME[0])
            )

        logger.info("Adding %s to %s", c.NIC_NAME[1], c.VM_NAME[0])
        if not ll_vm.addNic(
            positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[1]
        ):
            raise c.NET_EXCEPTION(
                "Failed to add %s to %s" % (c.NIC_NAME[1], c.VM_NAME[0])
            )

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

        logger.info("Adding %s to %s", c.NIC_NAME[2], c.VM_NAME[0])
        if not ll_vm.addNic(
            positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[2]
        ):
            raise c.NET_EXCEPTION(
                "Failed to add %s to %s" % (c.NIC_NAME[2], c.VM_NAME[0])
            )

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
            if not ll_vm.removeNic(positive=True, vm=c.VM_NAME[0], nic=nic):
                logger.error("Couldn't remove VNIC %s from VM", nic)

        logger.info("Update DC %s with default MAC pool", c.ORIG_DC)
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=c.ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(c.DEFAULT_MAC_POOL)
        ):
            logger.error(
                "Couldn't update DC %s with default MAC pool", c.ORIG_DC
            )

        logger.info("Remove MAC pools %s ", c.MAC_POOL_NAME[:2])
        for mac_pool in c.MAC_POOL_NAME[:2]:
            if not helper.remove_mac_pool(mac_pool_name=mac_pool):
                cls.test_failed = False


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

        if not helper.remove_mac_pool():
            cls.test_failed = False


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
            if not helper.remove_mac_pool(mac_pool_name=mac_pool):
                cls.test_failed = False


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
            logger.info(
                "Adding %s to %s", c.NIC_NAME[i+1], c.VM_NAME[0]
            )
            if not ll_vm.addNic(
                positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[i+1]
            ):
                raise c.NET_EXCEPTION(
                    "Failed to add %s to %s" %
                    (c.NIC_NAME[i+1], c.VM_NAME[0])
                )

        logger.info("Trying to add VNIC when there are no spare MACs to use")
        if ll_vm.addNic(
            positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[4]
        ):
            raise c.NET_EXCEPTION(
                "Succeeded to add %s to %s when shouldn't" %
                (c.NIC_NAME[4], c.VM_NAME[0])
            )

        logger.info("Extend the MAC pool range by 2 MACs")
        mac_pool = ll_mac_pool.get_mac_pool(c.MAC_POOL_NAME[0])
        mac_pool_range = ll_mac_pool.get_mac_range_values(mac_pool)[0]
        low_mac = utils.MAC(mac_pool_range[0])
        high_mac = utils.MAC(mac_pool_range[1])
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=c.MAC_POOL_NAME[0], range_dict={
                mac_pool_range: (low_mac - 1, high_mac + 1)
            }
        ):
            raise c.NET_EXCEPTION(
                "Couldn't extend the %s range" % c.MAC_POOL_NAME[0]
            )

        for i in range(4, 6):
            logger.info(
                "Adding %s to %s", c.NIC_NAME[i], c.VM_NAME[0]
            )
            if not ll_vm.addNic(
                positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[i]
            ):
                raise c.NET_EXCEPTION(
                    "Failed to add %s to %s" %
                    (c.NIC_NAME[i], c.VM_NAME[0])
                )

        logger.info("Trying to add VNIC when there are no spare MACs to use")
        if ll_vm.addNic(
            positive=True, vm=c.VM_NAME[0], name=c.NIC_NAME[6]
        ):
            raise c.NET_EXCEPTION(
                "Succeeded to add %s to %s when shouldn't" %
                (c.NIC_NAME[6], c.VM_NAME[0])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove 6 VNICs from the VM
        Update DC with the Default MAC pool
        Remove MAC pool
        """
        logger.info("Remove VNICs from VM")
        for nic in c.NIC_NAME[1:6]:
            if not ll_vm.removeNic(True, vm=c.VM_NAME[0], nic=nic):
                logger.error("Couldn't remove VNIC %s from VM", nic)
                cls.test_failed = False

        logger.info("Update DC %s with default MAC pool", c.DC_NAME[0])
        if not ll_dc.updateDataCenter(
            True, datacenter=c.DC_NAME[0],
            mac_pool=ll_mac_pool.get_mac_pool(c.DEFAULT_MAC_POOL)
        ):
            logger.error(
                "Couldn't update DC %s with default MAC pool",
                c.DC_NAME[0]
            )
            cls.test_failed = False

        if not helper.remove_mac_pool():
            cls.test_failed = False
