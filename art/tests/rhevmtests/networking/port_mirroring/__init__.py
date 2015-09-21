#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Port Mirroring init.
"""

import logging
import helper as helper
import rhevmtests.helpers as helpers
import rhevmtests.networking as networking
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as net_help
import art.test_handler.exceptions as exceptions
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks

logger = logging.getLogger("Port_Mirroring_Init")


def setup_package():
    """
    Prepare environment
    """
    networking.network_cleanup()
    logger.info(
        "Create %s, %s on %s/%s and attach them to %s",
        conf.VLAN_NETWORKS[0],
        ".".join([conf.BOND[0], conf.VLAN_NETWORKS[1]]),
        conf.DC_NAME[0], conf.CLUSTER_NAME[0], conf.HOSTS[:2]
    )
    network_params = {
        None: {
            "nic": conf.BOND[0],
            "mode": 1,
            "slaves": [2, 3]
        },
        conf.VLAN_NETWORKS[0]: {
            "vlan_id": conf.VLAN_ID[0],
            "nic": 1,
            "required": "false"
        },
        conf.VLAN_NETWORKS[1]: {
            "vlan_id": conf.VLAN_ID[1],
            "nic": conf.BOND[0],
            "required": "false"
        }
    }
    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_NAME[0], cluster=conf.CLUSTER_NAME[0],
        host=conf.VDS_HOSTS[:2], network_dict=network_params,
        auto_nics=[0, 1]
    ):
        raise exceptions.NetworkException("Cannot create and attach networks")

    logger.info(
        "Create vNIC profiles with port mirroring for %s network and %s" % (
            conf.MGMT_BRIDGE, conf.VLAN_NETWORKS[0]
        )
    )
    for i, network in enumerate((conf.MGMT_BRIDGE, conf.VLAN_NETWORKS[0])):
        if not ll_networks.addVnicProfile(
            positive=True, name=conf.PM_VNIC_PROFILE[i],
            cluster=conf.CLUSTER_NAME[0],
            network=network, port_mirroring=True
        ):
            raise exceptions.NetworkException(
                "Failed to create VNIC profile %s with port mirroring." %
                conf.PM_VNIC_PROFILE[i]
            )
    for vmName in conf.VM_NAME[:conf.NUM_VMS]:
        logger.info("sealing %s", vmName)
        helper.ge_seal_vm(vm=vmName)
        add_profile = True
        for i in (0, 1):
            if vmName == conf.VM_NAME[0] and add_profile:
                logger.info(
                    "Setting %s with profile %s on %s", conf.NIC_NAME[0],
                    conf.MGMT_BRIDGE + "_PM", vmName
                )
                helper.set_port_mirroring(
                    conf.VM_NAME[0], conf.NIC_NAME[0], conf.MGMT_BRIDGE
                )
                vnic_profile = conf.PM_VNIC_PROFILE[1]
                add_profile = False
            else:
                vnic_profile = conf.VLAN_NETWORKS[i]

            logger.info("Adding %s to %s", conf.NIC_NAME[i + 1], vmName)
            if not ll_vms.addNic(
                True, vm=vmName, name=conf.NIC_NAME[i + 1],
                interface=conf.NIC_TYPE_VIRTIO,
                network=conf.VLAN_NETWORKS[i],
                vnic_profile=vnic_profile
            ):
                raise exceptions.NetworkException(
                    "Failed to add nic to %s" % vmName
                )
        logger.info("Starting %s", vmName)
        if not net_help.run_vm_once_specific_host(
            vm=vmName, host=conf.HOSTS[0], wait_for_ip=True
        ):
            raise exceptions.NetworkException("Failed to start %s." % vmName)

    logger.info("Configure IPs for each VM")
    for i, vm in enumerate(conf.VM_NAME[:conf.NUM_VMS]):
        logger.info("Getting MGMT network IP for %s.", vm)
        rc, out = ll_vms.waitForIP(vm=vm, timeout=180, sleep=10)

        if not rc:
            raise exceptions.NetworkException(
                "Failed to get VM IP on MGMT network"
            )
        local_mgmt_ip = out["ip"]
        logger.info(
            "Update the list of MGMT network IPs with %s from %s",
            local_mgmt_ip, vm
        )
        conf.MGMT_IPS.append(local_mgmt_ip)
        vm_resource = helpers.get_host_resource_with_root_user(
            ip=local_mgmt_ip, root_password=conf.VMS_LINUX_PW
        )
        logger.info("Configure IPs on %s for nic1 and nic2", vm)
        for nicIndex, ip in enumerate(
                (conf.NET1_IPS[i], conf.NET2_IPS[i]), start=1
        ):
            params = {
                "IPADDR": ip,
                "BOOTPROTO": "static",
                "NETMASK": "255.255.0.0"
            }
            ifcfg_path = "/etc/sysconfig/network-scripts/"
            vm_resource.network.create_ifcfg_file(
                nic="eth%s" % nicIndex, params=params, ifcfg_path=ifcfg_path
            )
        logger.info("Restarting network service on %s", vm)
        if not vm_resource.service("network").restart():
            raise exceptions.NetworkException(
                "Failed to restart network service on %s" % vm
            )
    logger.info("Stop iptables service on hosts")
    for host in conf.VDS_HOSTS[:2]:
        if not host.service(conf.FIREWALL_SRV).stop():
            raise exceptions.NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Clean the environment
    """
    for ip in conf.MGMT_IPS:
        vm_resource = helpers.get_host_resource_with_root_user(
            ip=ip, root_password=conf.VMS_LINUX_PW
        )
        for idx in (1, 2):
            vm = conf.VM_NAME[conf.MGMT_IPS.index(ip)]
            logger.info("Removing ifcfg-eth%s file from %s", idx, vm)
            ifcfg_file = "/etc/sysconfig/network-scripts/ifcfg-eth%s" % idx
            vm_resource.fs.remove(ifcfg_file)

    logger.info("Stopping %s", conf.VM_NAME[:conf.NUM_VMS])
    if not ll_vms.stopVms(conf.VM_NAME):
        logger.error("Failed to stop VMs")

    for vm in conf.VM_NAME:
        vm_nics = ll_vms.get_vm_nics_obj(vm)
        for nic in vm_nics:
            if nic.name == conf.NIC_NAME[0]:
                logger.info(
                    "Setting %s profile on %s in %s",
                    conf.MGMT_BRIDGE, nic.name, vm
                )
                if not ll_vms.updateNic(
                        True, vm, conf.NIC_NAME[0],
                        network=conf.MGMT_BRIDGE,
                        vnic_profile=conf.MGMT_BRIDGE
                ):
                    logger.error(
                        "Failed to update %s in %s to profile "
                        "without port mirroring", conf.NIC_NAME[0], vm
                    )
            else:
                logger.info("Removing %s from %s", nic.name, vm)
                if not ll_vms.removeNic(True, vm, nic.name):
                    logger.error(
                        "Failed to remove %s from %s", nic, vm
                    )
    logger.info("Removing all networks from DC/Cluster and hosts")
    if not hl_networks.remove_net_from_setup(
        host=conf.HOSTS[0], data_center=conf.DC_NAME[0], all_net=True,
        mgmt_network=conf.MGMT_BRIDGE
    ):
        logger.error("Cannot remove network from setup")
