#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Predictable vNIC order feature test cases
"""

import helper
import logging
import config as conf
from art.unittest_lib import attr
import art.unittest_lib as unittest_lib
from art.test_handler.tools import polarion  # pylint: disable=E0611
import rhevmtests.networking.helper as net_help
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger("Predictable_vNIC_Order_Cases")


def setup_module():
    """
    Seal the VM
    Remove all vNICs from the VM
    """
    if not helper.seal_vm_and_remove_vnics():
        raise conf.NET_EXCEPTION(
            "Failed to seal %s and remove vNICs" % conf.VM_NAME
        )


def teardown_module():
    """
    Add vNIC to the VM
    Seal the VM
    """
    if not ll_vms.addNic(
        positive=True, vm=conf.VM_NAME, name=conf.NIC_NAME[0],
        network=conf.MGMT_BRIDGE
    ):
        logger.error(
            "Failed to add %s to %s", conf.NIC_NAME[0], conf.VM_NAME
        )
    logger.info("Sealing %s", conf.VM_NAME)
    if not net_help.seal_vm(vm=conf.VM_NAME, root_password=conf.VMS_LINUX_PW):
        logger.error("Failed to seal %s", conf.VM_NAME)


class TestPredictableVnicOrderBase(unittest_lib.NetworkTest):
    """
    Base class for Predictable vNIC Order cases
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Add 4 vNICs to the VM
        Reorder the vNICs
        """
        helper.add_vnics_to_vm()
        logger.info("Reorder %s vNICs", conf.VM_NAME)
        if not ll_vms.reorder_vm_mac_address(vm_name=conf.VM_NAME):
            raise conf.NET_EXCEPTION(
                "Failed to reorder MACs on %s" % conf.VM_NAME
            )

    @classmethod
    def teardown_class(cls):
        """
        Seal the VM
        Remove vNICs from the VM
        """
        helper.seal_vm_and_remove_vnics()


@attr(tier=2)
class TestPredictableVnicOrder01(TestPredictableVnicOrderBase):
    """
    Check vNICs order for new VM
    """
    __test__ = True

    @polarion("RHEVM3-4095")
    def test_check_vnics_order_vm(self):
        """
        Get vNICs names and MACs before start VM
        Start the VM
        Check vNICs MAC order
        """
        setup_dict = helper.get_vnics_names_and_macs()
        logger.info("Start %s", conf.VM_NAME)
        if not ll_vms.startVm(
            positive=True, vm=conf.VM_NAME, wait_for_ip=True
        ):
            raise conf.NET_EXCEPTION("Failed to start %s" % conf.VM_NAME)

        case_dict = helper.get_vnics_names_and_macs()
        logger.info("Check vNICs MAC ordering")
        if setup_dict != case_dict:
            raise conf.NET_EXCEPTION("vNICs not in order on %s" % conf.VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        Stop VM
        """
        logger.info("Stop %s", conf.VM_NAME)
        if not ll_vms.stopVm(positive=True, vm=conf.VM_NAME):
            logger.error("Failed to stop %s", conf.VM_NAME)
        super(TestPredictableVnicOrder01, cls).teardown_class()
