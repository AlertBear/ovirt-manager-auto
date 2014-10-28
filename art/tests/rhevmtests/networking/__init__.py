# coding=utf-8
"""
network team init file
"""
import logging
import config
from art.rhevm_api.tests_lib.high_level.networks import (
    ENUMS, remove_net_from_setup, createAndAttachNetworkSN
)
from art.rhevm_api.tests_lib.low_level.hosts import get_host_name_from_engine
from art.rhevm_api.tests_lib.low_level.networks import(
    remove_label, get_vnic_profile_objects, VNIC_PROFILE_API, DC_API
)
from art.rhevm_api.tests_lib.low_level.templates import(
    get_all_template_objects, get_template_nics_objects, removeTemplateNic,
    TEMPLATE_API, removeTemplate
)
from art.rhevm_api.tests_lib.low_level.vms import(
    get_vm_state, get_vm_nics_obj, updateNic, removeNic, VM_API, CLUSTER_API,
    removeVm
)
from art.rhevm_api.tests_lib.high_level.hosts import activate_host_if_not_up
from art.rhevm_api.tests_lib.low_level.vms import stopVm

logger = logging.getLogger("GE_Network_cleanup")

DEFAULT_DC_CL = "Default"
BLANK_TEMPLATE = "Blank"


def network_cleanup():
    """
    Clean the setup in (for GE).
    Stop all VMs
    Remove unneeded VMs
    Remove unneeded VMs NICs
    Remove unneeded templates
    Remove unneeded templates NICs
    Clean hosts interfaces labels
    Remove unneeded networks
    Remove unneeded vNIC profiles
    Setting all hosts up
    Remove unneeded clusters
    Remove unneeded DCs
    Clean all hosts interfaces (SN)
    """
    stop_all_vms()
    remove_unneeded_vms()
    remove_unneeded_vms_nics()
    remove_unneeded_templates()
    remove_unneeded_templates_nics()
    clean_hosts_interfaces_labels()
    remove_unneeded_networks()
    remove_unneeded_vnic_profiles()
    set_hosts_up()
    remove_unneeded_clusters()
    remove_unneeded_dcs()
    clean_hosts_interfaces()


def set_hosts_up():
    """
    Set all hosts UP
    """
    logger.info("Setting hosts UP if needed")
    for host in config.HOSTS:
        if not activate_host_if_not_up(host):
            logger.error("Failed to activate host: %s", host)


def stop_all_vms():
    """
    Stop all VMs
    """
    logger.info("Stop all VMs if needed")
    all_vms = VM_API.get(absLink=False)
    for vm in all_vms:
        vm_name = vm.name
        vm_state = get_vm_state(vm_name)
        if vm_state != ENUMS["vm_state_down"]:
            logger.info("%s state is %s, stopping VM", vm_name, vm_state)
            if not stopVm(True, vm_name):
                logger.error("Failed to stop VM: %s", vm_name)


def clean_hosts_interfaces_labels():
    """
    Clean hosts interfaces labels
    """
    logger.info("Clean all labels for hosts interfaces")
    for host in config.VDS_HOSTS:
        host_name = get_host_name_from_engine(host.ip)
        logger.info("Removing labels from %s", host_name)
        if not remove_label(host_nic_dict={host_name: host.nics}):
            logger.error("Couldn't remove labels from %s", host_name)


def remove_unneeded_vms_nics():
    """
    Remove all NICs from VM besides nic1
    """
    logger.info("Removing all NICs from VMs besides %s", config.NIC_NAME[0])
    mgmt_profiles_ids = []
    logger.info("Getting all %s vNIC profiles ids", config.MGMT_BRIDGE)
    for vnic_obj in get_vnic_profile_objects():
        if vnic_obj.name == config.MGMT_BRIDGE:
            mgmt_profiles_ids.append(vnic_obj.id)

    for vm in config.VM_NAME:
        vm_nics = get_vm_nics_obj(vm)
        for nic in vm_nics:
            if nic.name == config.NIC_NAME[0]:
                if nic.vnic_profile.id in mgmt_profiles_ids:
                    continue

                logger.info(
                    "Updating %s to %s profile on %s",
                    nic.name, config.MGMT_BRIDGE, vm
                )
                if not updateNic(
                    True, vm, nic.name, network=config.MGMT_BRIDGE,
                    vnic_profile=config.MGMT_BRIDGE
                ):
                    logger.error(
                        "Failed to update %s to profile %s on %s",
                        nic.name, config.MGMT_BRIDGE, vm
                    )
                logger.info("Found %s on %s. Not removing", nic.name, vm)

            else:
                logger.info("Removing %s from %s", nic.name, vm)
                if not removeNic(True, vm, nic.name):
                    logger.error("Failed to remove %s from %s", nic, vm)


def remove_unneeded_templates_nics():
    """
    Remove all NICs from templates besides nic1
    """
    logger.info(
        "Removing all NICs from templates besides %s", config.NIC_NAME[0]
    )
    for template in get_all_template_objects():
        if template.name == BLANK_TEMPLATE:
            continue

        template_nics = get_template_nics_objects(template.name)
        for nic in template_nics:
            if nic.name == config.NIC_NAME[0]:
                continue

            logger.info("Removing %s from %s", nic.name, template.name)
            if not removeTemplateNic(True, template.name, nic.name):
                logger.error("Failed to remove %s from %s", nic, template.name)


def remove_unneeded_networks():
    """
    Remove all networks besides MGMT_NETWORK
    """
    logger.info("Removing all networks besides %s", config.MGMT_BRIDGE)
    remove_net_from_setup(
        host=config.VDS_HOSTS, auto_nics=[0],
        data_center=config.DC_NAME[0], all_net=True,
        mgmt_network=config.MGMT_BRIDGE
    )


def remove_unneeded_vnic_profiles():
    """
    Remove all vNIC profiles besides MGMT_PROFILE
    """
    logger.info(
        "Removing all vNIC profiles besides %s profile", config.MGMT_BRIDGE
    )
    for vnic in get_vnic_profile_objects():
        if vnic.name != config.MGMT_BRIDGE:
            logger.info("Removing %s profile", vnic.name)
            if not VNIC_PROFILE_API.delete(vnic, True):
                logger.error("Failed to remove %s profile", vnic.name)


def remove_unneeded_vms():
    """
    Remove all VMs besides [config.VM_NAME]
    """
    logger.info("Get all VMs")
    all_vms = VM_API.get(absLink=False)
    for vm in all_vms:
        if vm.name not in config.VM_NAME:
            if not removeVm(positive=True, vm=vm.name):
                logger.error("Failed to remove %s", vm.name)


def remove_unneeded_templates():
    """
    Remove all templates besides [config.TEMPLATE_NAME]
    """
    logger.info("Get all templates")
    all_templates = TEMPLATE_API.get(absLink=False)
    for template in all_templates:
        if template.name == BLANK_TEMPLATE:
            continue

        if template.name not in config.TEMPLATE_NAME:
            if not removeTemplate(positive=True, template=template.name):
                logger.info("Failed to remove %s", template.name)


def remove_unneeded_dcs():
    """
    Remove all DCs besides [config.DC_NAME]
    """
    logger.info("Get all DCs")
    all_dcs = DC_API.get(absLink=False)
    for dc in all_dcs:
        if dc.name == DEFAULT_DC_CL:
            continue

        if dc.name not in config.DC_NAME:
            if not DC_API.delete(dc, True):
                logger.error("Failed to delete %s", dc.name)


def remove_unneeded_clusters():
    """
    Remove all clusters besides [config.CLUSTER_NAME]
    """
    logger.info("Get all clusters")
    all_clusters = CLUSTER_API.get(absLink=False)
    for cl in all_clusters:
        if cl.name == DEFAULT_DC_CL:
            continue

        if cl.name not in config.CLUSTER_NAME:
            if not CLUSTER_API.delete(cl, True):
                logger.error("Failed to delete %s", cl.name)


def clean_hosts_interfaces():
    """
    Clean all hosts interfaces
    """
    if not createAndAttachNetworkSN(host=config.VDS_HOSTS, auto_nics=[0]):
        logger.error("Failed to clean hosts interfaces")
