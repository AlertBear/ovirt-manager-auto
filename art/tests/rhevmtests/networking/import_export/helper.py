#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for import_export networks feature
"""

import logging

import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as ie_ex_conf
import rhevmtests.networking.config as conf

logger = logging.getLogger("Import_Export_Networks_Helper")


def add_nics_to_vm(net_list):
    """
    Adding NICs to VM

    :param net_list: Networks name
    :type net_list: list
    :raise: NetworkException
    """
    for net, nic in zip(net_list, conf.NIC_NAME):
        if not ll_vms.addNic(
            positive=True, vm=conf.IE_VM, name=nic, network=net,
            vnic_profile=net
        ):
            raise conf.NET_EXCEPTION()


def check_imported_vm_or_templates(net1, net2, vm=None, template=None):
    """
    Check for NICs on imported VM or template that appropriate vNICs
    exist after import

    :param net1: Network name
    :type net1: str or None
    :param net2: Network name
    :type net2: str or None
    :param vm: VM name to check the vNICs profiles on
    :type vm: str
    :param template: Name to check for VNIC profile name on
    :type template: str
    :return: True/False
    :rtype: bool
    """
    log = (
        "more than once" if vm is not conf.IE_VM and
        template is not conf.IE_TEMPLATE else ""
    )
    vm_template_log = "VM" if vm else "Template"
    logger.info(
        "Check NICs VNIC profiles for %s imported %s ",
        vm_template_log, log
    )
    for (nic, vnic) in (
        (conf.NIC_NAME[0], conf.MGMT_BRIDGE),
        (conf.NIC_NAME[1], net1),
        (conf.NIC_NAME[2], net2),
        (conf.NIC_NAME[3], ie_ex_conf.NETS[2])
    ):
        if vm:
            if not ll_vms.check_vnic_on_vm_nic(vm=vm, nic=nic, vnic=vnic):
                return False

        if template:
            if not ll_templates.check_vnic_on_template_nic(
                template=template, nic=nic, vnic=vnic
            ):
                return False
    return True
