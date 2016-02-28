#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Helper for jumbo_frames job
"""

import logging
import config as conf
import rhevmtests.helpers as global_helper
from art.rhevm_api.utils import test_utils
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network


logger = logging.getLogger("Jumbo_Frame_Helper")


def check_logical_physical_layer(
    nic=None, host=None, network=None, vlan=None, bond=None,
    bond_nic1=None, bond_nic2=None, mtu=None, bridge=True, logical=True,
    physical=True
):
    """
    Check MTU on logical and physical layer on host

    :param nic: NIC name
    :type nic: str
    :param host: Host resource
    :type host: object
    :param network: network name
    :type network: str
    :param vlan: VLAN ID
    :type vlan: str
    :param bond: BOND name
    :type bond: str
    :param bond_nic1: BOND slave
    :type bond_nic1: str
    :param bond_nic2: BOND slave
    :type bond_nic2: str
    :param mtu: MTU size
    :type mtu: int
    :param bridge: True if network is bridge
    :type bridge: bool
    :param logical: True to check logical layer
    :type logical: bool
    :param physical: True to check physical layer
    :type physical: bool
    :raise: NetworkException
    """
    if host is None:
        host = conf.VDS_HOSTS[0]
    br_log = "" if bridge else "bridgeless"
    vlan_log = "with VLAN %s" % vlan if vlan else ""
    net_log = "network %s" % network if network else ""
    nic_log = "of NIC %s" % nic if nic else ""
    bond_log = "of BOND %s" % bond if bond else ""
    if logical:
        logger.info(
            "Checking logical layer of %s %s %s %s",
            br_log, net_log, vlan_log, nic_log
        )
        if not test_utils.check_mtu(
            vds_resource=host, mtu=mtu, bond=bond, physical_layer=False,
            network=network, nic=nic, vlan=vlan, bridged=bridge
        ):
            raise conf.NET_EXCEPTION(
                "(logical) MTU on host %s should be %s and it is not" % (
                    host.ip, mtu,
                )
            )

    if physical:
        logger.info("Checking physical layer %s %s", bond_log, nic_log)
        if not test_utils.check_mtu(
            vds_resource=host, mtu=mtu, nic=nic, bond=bond,
            bond_nic1=bond_nic1, bond_nic2=bond_nic2
        ):
            raise conf.NET_EXCEPTION(
                "(physical) MTU on host %s should be %s and it is not" % (
                    host.ip, mtu,
                )
            )


def add_vnics_to_vms(
    ips, mtu, network, nic_name=conf.NIC_NAME[1], set_ip=True
):
    """
    Adding NIC to config.VM_NAME[:2]

    :param ips: VMs IPs
    :type ips: list
    :param mtu: MTU to configure on the VM
    :type mtu: str
    :param network: Network to set for the NIC
    :type network: str
    :param nic_name: NIC name to add
    :type nic_name: str
    :param set_ip: Set IP on the NIC
    :type set_ip: bool
    :raise: NetworkException
    """
    mtu = str(mtu)
    for vm_name, ip in zip(conf.VM_NAME[:2], ips):
        vm_resource = global_helper.get_vm_resource(vm=vm_name)
        if not ll_vms.addNic(
            positive=True, vm=vm_name, name=nic_name, network=network
        ):
            raise conf.NET_EXCEPTION()

        if set_ip:
            logger.info("Get %s NICs", vm_name)
            vm_nics = vm_resource.network.all_interfaces()
            if not vm_nics:
                raise conf.NET_EXCEPTION("Failed to get %s NICs" % vm_name)

            if not test_utils.configure_temp_mtu(
                vds_resource=vm_resource, mtu=mtu, nic=vm_nics[1]
            ):
                raise conf.NET_EXCEPTION()

            if not test_utils.configure_temp_static_ip(
                vds_resource=vm_resource, ip=ip, nic=vm_nics[1]
            ):
                raise conf.NET_EXCEPTION()

            if not vm_resource.network.if_up(nic=vm_nics[1]):
                raise conf.NET_EXCEPTION()


def remove_vnics_from_vms(nic_name=conf.NIC_NAME[1]):
    """
    Remove NIC from config.VM_NAME[:2]

    :param nic_name: NIC name to remove
    :type nic_name: str
    """
    for vm_name in conf.VM_NAME[:2]:
        ll_vms.updateNic(
            positive=True, vm=vm_name, nic=nic_name, plugged=False
        )
        ll_vms.removeNic(positive=True, vm=vm_name, nic=nic_name)


def restore_mtu_and_clean_interfaces():
    """
    Restore Hosts NICs MTU by Attaching network on each host NIC with MTU 1500
    and remove the networks after restore
    """
    network_dict = {
        "1": {
            "network": conf.NETS[35][0],
            "nic": None
        },
        "2": {
            "network": conf.NETS[35][1],
            "nic": None
        },
        "3": {
            "network": conf.NETS[35][2],
            "nic": None
        }
    }

    for host, nics in zip(
        [conf.HOST_0_NAME, conf.HOST_1_NAME],
        [conf.HOST_0_NICS, conf.HOST_1_NICS]
    ):
        network_dict["1"]["nic"] = nics[1]
        network_dict["2"]["nic"] = nics[2]
        network_dict["3"]["nic"] = nics[3]

        hl_host_network.setup_networks(host_name=host, **network_dict)
        hl_host_network.clean_host_interfaces(host_name=host)
