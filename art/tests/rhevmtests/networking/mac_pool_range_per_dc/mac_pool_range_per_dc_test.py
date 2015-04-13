#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
MAC pool range per DC networking feature test
"""

import logging
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.vms as ll_vm
import utilities.utils as utils
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.high_level.mac_pool as hl_mac_pool
import art.rhevm_api.utils.test_utils as test_utils
from rhevmtests.networking import config
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
import art.test_handler.exceptions as exception


logger = logging.getLogger("MAC_Pool_Range_Per_DC_Cases")

EXT_DC_1 = config.EXTRA_DC[1]
ORIG_DC = config.DC_NAME[0]
NIC_NAME = config.NIC_NAME
DEFAULT_MAC_POOL = config.DEFAULT_MAC_POOL


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
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac_range])
        if test_utils.set_engine_properties(
            config.ENGINE, [cmd], restart=False
        ):
            raise exception.NetworkException(
                "Managed to configure MAC pool range when should be deprecated"
            )

        logger.info("Negative: Try to configure MaxMacCountPool")
        cmd = "=".join(["MaxMacCountPool", "100001"])
        if test_utils.set_engine_properties(
            config.ENGINE, [cmd], restart=False
        ):
            raise exception.NetworkException(
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
            raise exception.NetworkException(
                "Failed to get default MAC pool range"
            )
        default_mac_pool_range = default_mac_pool_range[0]

        low_mac = utils.MAC(default_mac_pool_range[0])
        high_mac = utils.MAC(default_mac_pool_range[1])

        logger.info("Extend the default MAC pool range by 4 MACs")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=DEFAULT_MAC_POOL, range_dict={
                default_mac_pool_range: (str(low_mac - 2), str(high_mac + 2))
            }
        ):
            raise exception.NetworkException(
                "Couldn't extend the Default MAC pool range"
            )

        logger.info("Shrink the updated default MAC pool range by 4 MACs")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=DEFAULT_MAC_POOL, range_dict={
                (str(low_mac - 2), str(high_mac + 2)):
                    (str(low_mac + 2), str(high_mac - 2))
            }
        ):
            raise exception.NetworkException(
                "Couldn't shrink the default MAC pool range"
            )

        logger.info("Add new ranges to the Default MAC pool")
        if not hl_mac_pool.add_ranges_to_mac_pool(
            mac_pool_name=DEFAULT_MAC_POOL,
            range_list=config.MAC_POOL_RANGE_LIST
        ):
            raise exception.NetworkException(
                "Couldn't add ranges to the Default MAC Pool"
            )
        logger.info("Remove added ranges from the Default MAC pool")
        if not hl_mac_pool.remove_ranges_from_mac_pool(
            mac_pool_name=DEFAULT_MAC_POOL,
            range_list=config.MAC_POOL_RANGE_LIST
        ):
            raise exception.NetworkException(
                "Couldn't remove the ranges from the Default MAC pool"
            )

        logger.info("Create a new DC %s", EXT_DC_1)
        if not ll_dc.addDataCenter(
            positive=True, name=EXT_DC_1,
            storage_type=config.STORAGE_TYPE, version=config.COMP_VERSION,
            local=False
        ):
            raise exception.NetworkException(
                "Couldn't add a new DC with default MAC pool to the setup"
            )

        logger.info(
            "Check that the new DC was created with the updated "
            "Default MAC pool"
        )

        if not (
                ll_mac_pool.get_default_mac_pool().get_id() ==
                ll_mac_pool.get_mac_pool_from_dc(EXT_DC_1).get_id()
        ):
            raise exception.NetworkException(
                "New DC was not created with the updated Default MAC pool "
                "values"
            )

        logger.info("Update the Default MAC pool to its original values")
        if not hl_mac_pool.update_ranges_on_mac_pool(
            mac_pool_name=DEFAULT_MAC_POOL, range_dict={
                (str(low_mac + 2), str(high_mac - 2)): default_mac_pool_range
            }
        ):
            raise exception.NetworkException(
                "Couldn't update Default MAC pool range to its original value"
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the DC
        """
        logger.info("Remove a DC %s", EXT_DC_1)
        if not ll_dc.removeDataCenter(positive=True, datacenter=EXT_DC_1):
            logger.error("Failed to remove DC")


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
                name=config.MAC_POOL_NAME[i],
                ranges=[config.MAC_POOL_RANGE_LIST[i]]
            ):
                raise exception.NetworkException(
                    "Cannot create new MAC pool %s" % config.MAC_POOL_NAME[i]
                )

        logger.info(
            "Update the DC %s with MAC pool %s", ORIG_DC,
            config.MAC_POOL_NAME[0]
        )
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(config.MAC_POOL_NAME[0])
        ):
            raise exception.NetworkException(
                "Couldn't update DC %s with MAC pool %s" %
                (ORIG_DC, config.MAC_POOL_NAME[0])
            )

        logger.info(
            "Adding %s to %s", NIC_NAME[1], config.VM_NAME[0]
        )
        if not ll_vm.addNic(
            positive=True, vm=config.VM_NAME[0], name=NIC_NAME[1]
        ):
            raise exception.NetworkException(
                "Failed to add %s to %s" %
                (NIC_NAME[1], config.VM_NAME[0])
            )

    def test_update_mac_pool_vm(self):
        """
        Check that for updated DC with new MAC pool, the NICs on the VM on
        that DC are created with MACs from the new MAC pool range
        """
        logger.info("Find the MAC of the VM NIC %s", NIC_NAME[1])
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=config.VM_NAME[0], nic=NIC_NAME[1]
        )
        if not nic_mac:
            raise exception.NetworkException(
                "MAC was not found on NIC %s" % NIC_NAME[1]
            )

        logger.info("Find the MAC range for %s", config.MAC_POOL_RANGE_LIST[0])
        mac_range = utils.MACRange(
            config.MAC_POOL_RANGE_LIST[0][0], config.MAC_POOL_RANGE_LIST[0][1]
        )
        if nic_mac not in mac_range:
            raise exception.NetworkException(
                "MAC %s is not in the MAC pool range for %s" %
                (nic_mac, config.MAC_POOL_NAME[0])
            )

        logger.info(
            "Update the DC %s with MAC pool %s", ORIG_DC,
            config.MAC_POOL_NAME[1]
        )
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(config.MAC_POOL_NAME[1])
        ):
            raise exception.NetworkException(
                "Couldn't update DC %s with MAC pool %s" %
                (ORIG_DC, config.MAC_POOL_NAME[1])
            )

        logger.info(
            "Adding %s to %s", NIC_NAME[2], config.VM_NAME[0]
        )
        if not ll_vm.addNic(
            positive=True, vm=config.VM_NAME[0], name=NIC_NAME[2]
        ):
            raise exception.NetworkException(
                "Failed to add %s to %s" %
                (NIC_NAME[2], config.VM_NAME[0])
            )

        logger.info("Find the MAC of the VM NIC %s", NIC_NAME[2])
        nic_mac = ll_vm.get_vm_nic_mac_address(
            vm=config.VM_NAME[0], nic=NIC_NAME[2]
        )
        if not nic_mac:
            raise exception.NetworkException(
                "MAC was not found on NIC %s" % NIC_NAME[2]
            )

        logger.info("Find the MAC range for %s", config.MAC_POOL_RANGE_LIST[1])
        mac_range = utils.MACRange(
            config.MAC_POOL_RANGE_LIST[1][0], config.MAC_POOL_RANGE_LIST[1][1]
        )
        if nic_mac not in mac_range:
            raise exception.NetworkException(
                "MAC %s is not in the MAC pool range for %s" %
                (nic_mac, config.MAC_POOL_NAME[1])
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM NICs
        Update DC with default MAC pool
        Remove created MAC pools
        """
        logger.info("Remove VNICs from %s", config.VM_NAME[0])
        for nic in NIC_NAME[1:3]:
            if not ll_vm.removeNic(
                positive=True, vm=config.VM_NAME[0], nic=nic
            ):
                logger.error("Couldn't remove VNIC %s from VM", nic)

        logger.info("Update DC %s with default MAC pool", ORIG_DC)
        if not ll_dc.updateDataCenter(
            positive=True, datacenter=ORIG_DC,
            mac_pool=ll_mac_pool.get_mac_pool(DEFAULT_MAC_POOL)
        ):
            logger.error(
                "Couldn't update DC %s with default MAC pool", ORIG_DC
            )

        logger.info("Remove MAC pools %s ", config.MAC_POOL_NAME[:2])
        for mac_pool in config.MAC_POOL_NAME[:2]:
            if not ll_mac_pool.remove_mac_pool(mac_pool):
                logger.error(
                    "Couldn't remove MAC pool %s", mac_pool
                )
