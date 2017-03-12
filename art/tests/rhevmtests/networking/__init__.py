# coding=utf-8
"""
network team init file
"""

import logging

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.mac_pool as ll_mac_pool
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.rhevm_api.utils.inventory import Inventory
from rhevmtests.networking import config
from rhevmtests.networking.helper import prepare_dummies

logger = logging.getLogger("GE_Network_cleanup")

DEFAULT_DC_CL = "Default"
BLANK_TEMPLATE = "Blank"


def ignore_exception(func):
    """
    Decorator to catch exception

    :param func: Function
    :return: function return
    :rtype: function return
    """
    def inner(**kwargs):
        """
        The call for the function

        :param kwargs: Function kwargs
        :type kwargs: dict
        """
        try:
            func(**kwargs)
        except Exception as e:
            logger.error(e)
    return inner


def network_cleanup():
    """
    Clean the setup in (for GE).
    Stop all VMs
    Remove unneeded VMs
    Remove unneeded VMs NICs
    Remove unneeded templates
    Remove unneeded templates NICs
    Setting all hosts up
    Clean all hosts interfaces (SN)
    Remove unneeded networks
    Remove unneeded vNIC profiles
    Remove unneeded clusters
    Remove unneeded DCs
    Remove all dummy interfaces from hosts
    Remove all QOS from setup
    Remove all non management bridges from hosts
    Remove unneeded NFS storage domains
    """
    logger.info("Running network cleanup")
    stop_all_vms()
    remove_unneeded_vms()
    remove_unneeded_vms_nics()
    remove_unneeded_templates()
    remove_unneeded_templates_nics()
    set_hosts_up()
    clean_hosts_interfaces()
    remove_unneeded_networks()
    remove_unneeded_vnic_profiles()
    remove_unneeded_clusters()
    remove_unneeded_dcs()
    set_default_mac_pool_for_dcs()
    remove_unneeded_mac_pools()
    delete_dummy_interfaces_from_hosts()
    remove_qos_from_setup()
    remove_bridges_from_hosts()


@ignore_exception
def set_hosts_up():
    """
    Set all hosts UP
    """
    logger.info("Setting hosts UP if needed")
    for host in config.HOSTS:
        if not hl_hosts.activate_host_if_not_up(host):
            logger.error("Failed to activate host: %s", host)


@ignore_exception
def stop_all_vms():
    """
    Stop all VMs
    """
    logger.info("Stop all VMs if needed")
    all_vms = ll_vms.VM_API.get(abs_link=False)
    for vm in all_vms:
        vm_name = vm.name
        vm_state = ll_vms.get_vm_state(vm_name)
        if vm_state != hl_networks.ENUMS["vm_state_down"]:
            logger.info("%s state is %s, stopping VM", vm_name, vm_state)
            if not ll_vms.stopVm(True, vm_name):
                logger.error("Failed to stop VM: %s", vm_name)


@ignore_exception
def remove_unneeded_vms_nics():
    """
    Remove all NICs from VM besides nic1
    """
    logger.info("Removing all NICs from VMs besides %s", config.NIC_NAME[0])
    mgmt_profiles_ids = []
    logger.info("Getting all %s vNIC profiles ids", config.MGMT_BRIDGE)
    for vnic_obj in ll_networks.get_vnic_profile_objects():
        if vnic_obj.name == config.MGMT_BRIDGE:
            mgmt_profiles_ids.append(vnic_obj.id)

    for vm in config.VM_NAME:
        vm_nics = ll_vms.get_vm_nics_obj(vm)
        for nic in vm_nics:
            if nic.name == config.NIC_NAME[0]:
                if nic.vnic_profile.id in mgmt_profiles_ids:
                    continue

                logger.info(
                    "Updating %s to %s profile on %s",
                    nic.name, config.MGMT_BRIDGE, vm
                )
                if not ll_vms.updateNic(
                    positive=True, vm=vm, nic=nic.name,
                    network=config.MGMT_BRIDGE,
                    vnic_profile=config.MGMT_BRIDGE, interface="virtio"
                ):
                    logger.error(
                        "Failed to update %s to profile %s on %s",
                        nic.name, config.MGMT_BRIDGE, vm
                    )
                logger.info("Found %s on %s. Not removing", nic.name, vm)

            else:
                logger.info("Removing %s from %s", nic.name, vm)
                if not ll_vms.removeNic(True, vm, nic.name):
                    logger.error("Failed to remove %s from %s", nic, vm)


@ignore_exception
def remove_unneeded_templates_nics():
    """
    Remove all NICs from templates besides nic1
    """
    logger.info(
        "Removing all NICs from templates besides %s", config.NIC_NAME[0]
    )
    for template in ll_templates.get_all_template_objects():
        if template.name == BLANK_TEMPLATE:
            continue

        template_nics = ll_templates.get_template_nics_objects(template.name)
        for nic in template_nics:
            if nic.name == config.NIC_NAME[0]:
                continue

            logger.info("Removing %s from %s", nic.name, template.name)
            if not ll_templates.removeTemplateNic(
                True, template.name, nic.name
            ):
                logger.error("Failed to remove %s from %s", nic, template.name)


@ignore_exception
def remove_unneeded_networks():
    """
    Remove all networks besides MGMT_BRIDGE
    """
    logger.info("Removing all networks besides %s", config.MGMT_BRIDGE)
    hl_networks.remove_net_from_setup(
        host=config.HOSTS, data_center=config.DC_NAME[0], all_net=True,
        mgmt_network=config.MGMT_BRIDGE
    )


@ignore_exception
def remove_unneeded_vnic_profiles():
    """
    Remove all vNIC profiles besides MGMT_PROFILE
    """
    logger.info(
        "Removing all vNIC profiles besides %s profile", config.MGMT_BRIDGE
    )
    for vnic in ll_networks.get_vnic_profile_objects():
        if vnic.name != config.MGMT_BRIDGE:
            logger.info("Removing %s profile", vnic.name)
            if not ll_networks.VNIC_PROFILE_API.delete(vnic, True):
                logger.error("Failed to remove %s profile", vnic.name)


@ignore_exception
def remove_unneeded_vms():
    """
    Remove all unneeded VMs
    """
    logger.info("Get all VMs")
    vms = [vm.name for vm in ll_vms.VM_API.get(abs_link=False)]
    vms_to_remove = [vm for vm in vms if "golden_env_mixed_virtio_" not in vm]
    if vms_to_remove:
        logger.warning("VMs to remove: %s", vms_to_remove)
        ll_vms.safely_remove_vms(vms=vms_to_remove)


@ignore_exception
def remove_unneeded_templates():
    """
    Remove all templates besides [config.TEMPLATE_NAME]
    """
    logger.info("Get all templates")
    all_templates = ll_templates.TEMPLATE_API.get(abs_link=False)
    for template in all_templates:
        if template.name == BLANK_TEMPLATE:
            continue

        if template.name not in config.TEMPLATE_NAME:
            if not ll_templates.remove_template(
                positive=True, template=template.name
            ):
                logger.info("Failed to remove %s", template.name)


@ignore_exception
def remove_unneeded_dcs():
    """
    Remove all DCs besides [config.DC_NAME]
    """
    logger.info("Get all DCs")
    all_dcs = ll_networks.DC_API.get(abs_link=False)
    for dc in all_dcs:
        if dc.name == DEFAULT_DC_CL:
            continue

        if dc.name not in config.DC_NAME:
            logger.info("Remove DC %s", dc.name)
            if not ll_datacenters.remove_datacenter(
                positive=True, datacenter=dc.name, force=True
            ):
                logger.error("Failed to delete DC %s", dc.name)


@ignore_exception
def remove_unneeded_clusters():
    """
    Remove all clusters besides [config.CLUSTER_NAME]
    """
    logger.info("Get all clusters")
    all_clusters = ll_vms.CLUSTER_API.get(abs_link=False)
    for cl in all_clusters:
        if cl.name == DEFAULT_DC_CL:
            continue

        if cl.name not in config.CLUSTER_NAME:
            if not ll_vms.CLUSTER_API.delete(cl, True):
                logger.error("Failed to delete %s", cl.name)


@ignore_exception
def clean_hosts_interfaces():
    """
    Clean all hosts interfaces
    """
    for host in config.HOSTS:
        hl_host_network.clean_host_interfaces(host_name=host)


@ignore_exception
def delete_dummy_interfaces_from_hosts():
    """
    Delete all dummy interfaces from hosts
    """
    for host in config.VDS_HOSTS:
        logger.info("Deleting dummy interfaces from %s", host.ip)
        if not hl_networks.delete_dummy_interfaces(host=host):
            logger.error("Failed to delete dummy interfaces from %s", host.ip)


@ignore_exception
def remove_qos_from_setup():
    """
    Remove all QoS from datacenters
    """
    for dc in config.DC_NAME:
        all_qos = ll_datacenters.get_qoss_from_datacenter(datacenter=dc)
        for qos in all_qos:
            qos_name = qos.get_name()
            if qos_name == config.DEFAULT_MGMT_QOS:
                continue
            ll_datacenters.delete_qos_from_datacenter(
                datacenter=dc, qos_name=qos_name
            )


@ignore_exception
def remove_bridges_from_hosts():
    """
    Remove all bridges except management bridge from hosts
    """
    for host in config.VDS_HOSTS:
        host_name = ll_hosts.get_host_name_from_engine(vds_resource=host)
        host_obj = ll_hosts.get_host_object(host_name=host_name)
        host_cluster = ll_general.get_object_name_by_id(
            object_api=ll_clusters.CLUSTER_API,
            object_id=host_obj.get_cluster().id
        )
        management_network = ll_networks.get_management_network(
            cluster_name=host_cluster
        ).name
        bridges_list = host.network.list_bridges()
        for br in bridges_list:
            br_name = br["name"]
            if br_name not in (management_network, ";vdsmdummy;"):
                logger.info("Remove %s from %s", br_name, host.ip)
                host.network.delete_bridge(bridge=br_name)


@ignore_exception
def remove_unneeded_mac_pools():
    """
    Remove unneeded MAC pools from setup (non Default MAC pool)
    """
    all_macs = ll_mac_pool.get_all_mac_pools()
    for mac in filter(lambda x: x.name != "Default", all_macs):
        ll_mac_pool.remove_mac_pool(mac_pool_name=mac.name)


@ignore_exception
def set_default_mac_pool_for_dcs():
    """
    Set 'Default' MAC pool for DCs
    """
    for cluster in config.CLUSTER_NAME:
        mac_pool_name = ll_mac_pool.get_mac_pool_from_cluster(
            cluster=cluster
        ).name
        if mac_pool_name != "Default":
            ll_clusters.updateCluster(
                positive=True, cluster=cluster,
                mac_pool=ll_mac_pool.get_mac_pool(pool_name="Default")
            )


def teardown_package():
    """
    Run inventory
    Remove dummies interfaces
    """
    network_cleanup()
    reporter = Inventory.get_instance()
    reporter.get_setup_inventory_report(
        print_report=True,
        check_inventory=True,
        rhevm_config_file=config
    )


def setup_package():
    """
    Run network cleanup
    Create dummies interfaces on 2 hosts
    """
    network_cleanup()
    for vds_host in config.VDS_HOSTS[:2]:
        num_dummy = 30 if vds_host.fqdn == config.VDS_HOSTS[0].fqdn else 8
        prepare_dummies(host_resource=vds_host, num_dummy=num_dummy)
        logger.info("Host %s. NICs: %s", vds_host.fqdn, vds_host.nics)
