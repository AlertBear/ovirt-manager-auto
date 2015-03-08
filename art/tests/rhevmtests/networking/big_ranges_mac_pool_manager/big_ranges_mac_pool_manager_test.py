"""
Allow big ranges in MacPoolManager
"""

import logging
from art.rhevm_api.tests_lib.low_level.vms import(
    addNic, getVmMacAddress, removeVm, addVm
)
from art.rhevm_api.utils.test_utils import set_engine_properties
from rhevmtests.networking import config
from art.test_handler.tools import tcms  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking.big_ranges_mac_pool_manager import (
    ENGINE_DEFAULT_MAC_RANGE
)

logger = logging.getLogger("BigRangeMacPool_Cases")


class TestBigRangeMacPoolTearDown(TestCase):
    """
    Teardown class for BigRangeMacPool
    """
    @classmethod
    def teardown_class(cls):
        """
        Set default MAC range and MAC count
        """

        set_range_cmd = "=".join(
            [config.MAC_POOL_RANGE_CMD, ENGINE_DEFAULT_MAC_RANGE[0]]
        )
        logger.info("Set default MAC range: %s", set_range_cmd)
        if not set_engine_properties(config.ENGINE, [set_range_cmd]):
            logger.error(
                "Failed to set default MAC range: %s", set_range_cmd
            )


@attr(tier=1)
class TestBigRangeMacPool01(TestBigRangeMacPoolTearDown):
    """
    Invalid vs valid mac address ranges
    """
    __test__ = True

    @tcms(14176, 390973)
    def test_valid_and_invalid_mac(self):
        """
        set valid and invalid MAC pool ranges
        """
        macs_list_not_valid = ["FF:00:00:00:00:00-FF:00:00:00:00:01"]
        macs_list_valid = [
            "00:00:00:00:00:00-00:00:00:00:00:01,"
            "00:00:00:00:00:00-00:00:00:00:00:01",
            "00:00:00:00:00:00-00:00:00:10:00:00,"
            "00:00:00:02:00:00-00:03:00:00:00:00",
            "00:00:00:00:00:00-00:00:00:10:00:00,"
            "00:00:00:02:00:00-00:03:00:00:00:0a",
            "FF:00:00:00:00:00-FF:00:00:00:00:01,"
            "F0:00:00:00:00:00-F0:00:00:00:00:01",
            "FF:00:00:00:00:00-FF:00:00:00:00:01,"
            "00:00:00:00:00:00-00:00:00:00:00:01"
        ]

        logger.info("Check valid MAC range")
        for mac in macs_list_valid:
            logger.info("Setting valid MAC range: %s", mac)
            cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac])
            if not set_engine_properties(config.ENGINE, [cmd], restart=False):
                raise NetworkException("Failed to set MAC range: %s" % mac)

        logger.info("Check invalid MAC range")
        for mac in macs_list_not_valid:
            logger.info("Setting invalid MAC range: %s", mac)
            cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac])
            if set_engine_properties(config.ENGINE, [cmd], restart=False):
                raise NetworkException(
                    "Succeeded to set MAC range: %s. but shouldn't" % mac
                )


@attr(tier=1)
class TestBigRangeMacPool02(TestBigRangeMacPoolTearDown):
    """
    define several ranges and create VM with 6 NICs
    """
    __test__ = True

    mac_range = (
        "00:00:00:00:00:00-00:00:00:00:00:02,"
        "00:00:00:00:00:03-00:00:00:00:00:05,"
        "00:00:00:00:00:06-00:00:00:00:00:08"
    )
    macs1 = ["00:00:00:00:00:00", "00:00:00:00:00:01", "00:00:00:00:00:02"]
    macs2 = ["00:00:00:00:00:03", "00:00:00:00:00:04", "00:00:00:00:00:05"]
    macs3 = ["00:00:00:00:00:06", "00:00:00:00:00:07", "00:00:00:00:00:08"]
    vm_macs = []

    @classmethod
    def setup_class(cls):
        """
        Set MAC pool with 3 ranges
        Create VM with 8 NICs
        """
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, cls.mac_range])
        logger.info("Set MAC pool with several ranges: %s", cmd)
        if not set_engine_properties(config.ENGINE, [cmd]):
            raise NetworkException("Failed to set MAC range: %s" % cmd)

        logger.info("Creating VM: %s", config.BMPR_VM_NAME)
        if not addVm(
            positive=True, name=config.BMPR_VM_NAME,
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Failed to create VM: %s" % config.BMPR_VM_NAME
            )

        for i in xrange(8):
            nic_name = "nic{0}".format(i)
            logger.info("Adding %s to %s", nic_name, config.BMPR_VM_NAME)
            if not addNic(
                positive=True, vm=config.BMPR_VM_NAME, name=nic_name
            ):
                raise NetworkException(
                    "Failed to add %s to %s" % (nic_name, config.BMPR_VM_NAME)
                )

            logger.info("Get %s MAC", nic_name)
            vm_mac = getVmMacAddress(
                positive=True, vm=config.BMPR_VM_NAME, nic=nic_name
            )[1]["macAddress"]
            cls.vm_macs.append(vm_mac)

    @tcms(14176, 391278)
    def test_mac_from_all_ranges(self):
        """`
        Check the VM have nics with MACs from all ranges
        """
        macs1_match = False
        macs2_match = False
        macs3_match = False

        for x in self.vm_macs:
            if x in self.macs1:
                macs1_match = True
            if x in self.macs2:
                macs2_match = True
            if x in self.macs3:
                macs3_match = True

        if not (macs1_match and macs2_match and macs3_match):
            raise NetworkException(
                "Not all MACs from %s are used" % self.mac_range
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM
        """
        cls.vm_macs = []
        logger.info("Removing %s", config.BMPR_VM_NAME)
        if not removeVm(positive=True, vm=config.BMPR_VM_NAME):
            logger.error("Failed to remove %s", config.BMPR_VM_NAME)
        super(TestBigRangeMacPool02, cls).teardown_class()


@attr(tier=1)
class TestBigRangeMacPool03(TestBigRangeMacPoolTearDown):
    """
    Define Pool with full range of MACs
    """
    __test__ = True

    @tcms(14176, 379121)
    def test_full_range_macs_pool(self):
        """
        Check that engine is UP and can create VM with NIC
        """
        mac_range = "00:00:00:00:00:00-FF:FF:FF:FF:FF:FF"
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac_range])
        logger.info("Set MAC range: %s", cmd)
        if not set_engine_properties(config.ENGINE, [cmd]):
            raise NetworkException("Failed to set MAC range: %s" % cmd)

        logger.info("Creating %s", config.BMPR_VM_NAME)
        if not addVm(
                positive=True, name=config.BMPR_VM_NAME,
                cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Failed to create VM: %s" % config.BMPR_VM_NAME
            )

        logger.info("Adding %s to %s", config.NIC_NAME[0], config.BMPR_VM_NAME)
        if not addNic(
            positive=True, vm=config.BMPR_VM_NAME, name=config.NIC_NAME[0]
        ):
            raise NetworkException(
                "Failed to add %s to %s" %
                (config.NIC_NAME[0], config.BMPR_VM_NAME)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM
        """
        logger.info("Removing %s", config.BMPR_VM_NAME)
        if not removeVm(positive=True, vm=config.BMPR_VM_NAME):
            logger.error("Failed to remove %s", config.BMPR_VM_NAME)
        super(TestBigRangeMacPool03, cls).teardown_class()


@attr(tier=1)
class TestBigRangeMacPool04(TestBigRangeMacPoolTearDown):
    """
    limit MAC range to 1 valid MAC
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set max range to 1
        """
        mac_range = "00:1A:4A:01:00:01-00:1A:4A:01:00:01"
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac_range])
        logger.info("Setting MAC range: %s", cmd)
        if not set_engine_properties(config.ENGINE, [cmd]):
            raise NetworkException("Failed to set MAC range: %s" % cmd)

        logger.info("Creating %s", config.BMPR_VM_NAME)
        if not addVm(
            positive=True, name=config.BMPR_VM_NAME,
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Failed to create VM: %s" % config.BMPR_VM_NAME
            )

    @tcms(14176, 379125)
    def test_one_valid_mac_range(self):
        """
        Create VM with 1 NIC
        """
        logger.info(
            "Adding %s to %s", config.NIC_NAME[0], config.BMPR_VM_NAME
        )
        if not addNic(
            positive=True, vm=config.BMPR_VM_NAME, name=config.NIC_NAME[0]
        ):
            raise NetworkException(
                "Failed to add %s to %s" %
                (config.NIC_NAME[0], config.BMPR_VM_NAME)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM
        """
        logger.info("Removing %s", config.BMPR_VM_NAME)
        if not removeVm(positive=True, vm=config.BMPR_VM_NAME):
            logger.error("Failed to remove %s", config.BMPR_VM_NAME)
        super(TestBigRangeMacPool04, cls).teardown_class()


@attr(tier=1)
class TestBigRangeMacPool05(TestBigRangeMacPoolTearDown):
    """
    define range with 1 MAC which is multicast
    """
    __test__ = True

    @tcms(14176, 379201)
    def test_one_mac_multicast(self):
        """
        Define invalid range (multicast) with 1 MAC
        """
        mac_range = "01:00:5E:28:23:01-01:00:5E:28:23:01"
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac_range])
        logger.info("Set MAC pool range (multicast): %s", cmd)
        if set_engine_properties(config.ENGINE, [cmd]):
            raise NetworkException(
                "Succeeded to set MAC: %s. but shouldn't" % cmd
            )


@attr(tier=1)
class TestBigRangeMacPool06(TestBigRangeMacPoolTearDown):
    """
    Set two ranges with only 1 valid mac
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Set max range to 1
        """
        mac_range = (
            "FF:00:00:00:00:00-FF:00:00:00:00:00,"
            "00:00:00:00:00:00-00:00:00:00:00:00"
        )
        cmd = "=".join([config.MAC_POOL_RANGE_CMD, mac_range])
        logger.info("Setting MAC range: %s", cmd)
        if not set_engine_properties(config.ENGINE, [cmd]):
            raise NetworkException("Failed to set MAC range: %s" % cmd)

        logger.info("Creating %s", config.BMPR_VM_NAME)
        if not addVm(
            positive=True, name=config.BMPR_VM_NAME,
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException(
                "Failed to create VM: %s" % config.BMPR_VM_NAME
            )

    @tcms(14176, 379125)
    def test_two_ranges_only_one_valid(self):
        """
        Create VM with two NICs, only 1 nic should created
        """
        logger.info(
            "Adding %s to %s", config.NIC_NAME[0], config.BMPR_VM_NAME
        )
        if not addNic(
            positive=True, vm=config.BMPR_VM_NAME, name=config.NIC_NAME[0]
        ):
            raise NetworkException(
                "Failed to add %s to %s" %
                (config.NIC_NAME[0], config.BMPR_VM_NAME)
            )
        logger.info(
            "Adding %s to %s", config.NIC_NAME[1], config.BMPR_VM_NAME
        )
        if addNic(
            positive=True, vm=config.BMPR_VM_NAME, name=config.NIC_NAME[1]
        ):
            raise NetworkException(
                "%s was add to %s but shouldn't" %
                (config.NIC_NAME[1], config.BMPR_VM_NAME)
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VM
        """
        logger.info("Removing %s", config.BMPR_VM_NAME)
        if not removeVm(positive=True, vm=config.BMPR_VM_NAME):
            logger.error("Failed to remove %s", config.BMPR_VM_NAME)
        super(TestBigRangeMacPool06, cls).teardown_class()
