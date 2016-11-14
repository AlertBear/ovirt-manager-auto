#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
helper file for import_export networks feature
"""

import logging

import art.rhevm_api.tests_lib.high_level.templates as hl_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as import_export_conf
import rhevmtests.networking.config as network_conf

logger = logging.getLogger("Import_Export_Networks_Helper")


def add_nics_to_vm(net_list):
    """
    Adding NICs to VM

    :param net_list: Networks name
    :type net_list: list
    :raise: NetworkException
    """
    for net, nic in zip(net_list, import_export_conf.VNICS):
        assert ll_vms.addNic(
            positive=True, vm=import_export_conf.IE_VM_NAME, name=nic,
            network=net, vnic_profile=net
        )


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
        "more than once" if vm is not import_export_conf.IE_VM_NAME and
        template is not import_export_conf.IE_TEMPLATE_NAME else ""
    )
    vm_template_log = "VM" if vm else "Template"
    logger.info(
        "Check NICs VNIC profiles for %s imported %s ",
        vm_template_log, log
    )
    for (nic, vnic) in (
        (import_export_conf.VNICS[0], network_conf.MGMT_BRIDGE),
        (import_export_conf.VNICS[1], net1),
        (import_export_conf.VNICS[2], net2),
        (import_export_conf.VNICS[3], import_export_conf.NETS[2])
    ):
        if vm:
            if not ll_vms.check_vnic_on_vm_nic(vm=vm, nic=nic, vnic=vnic):
                return False

        if template:
            if not hl_templates.check_vnic_on_template_nic(
                template=template, nic=nic, vnic=vnic
            ):
                return False
    return True
