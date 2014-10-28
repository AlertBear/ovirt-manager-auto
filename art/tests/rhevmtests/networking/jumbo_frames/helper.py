"""
Helper for jumbo_frames job
"""
import logging
from art.rhevm_api import resources
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config
import art.rhevm_api.utils.test_utils as utils
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger("Jumbo_Frame_Helper")


def get_vm_nic_names(vm, password):
    """
    Get list of interface names from inside the VM
    This function is required as each new vNIC added to host is named as eth[
    n] so it can occur that VM has for example interfaces: eth0, eth4, eth6

    :param vm: virtual machine ip address or fqdn
    :type vm: string
    :param password: password for root user
    :type password: string
    :return: list of VM interfaces or None
    :rtype: list
    """
    vm_exec = resources.VDS(vm, password).executor()
    cmd = [
        "ls", "/sys/class/net/", "|", "grep", "-v", "lo"
    ]
    rc, out, error = vm_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to get %s interfaces ERR: %s %s", vm, error, out
        )
        return []
    return out.splitlines()


def check_logical_physical_layer(
    nic=None, host=config.VDS_HOSTS[0], network=None, vlan=None, bond=None,
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
        if not utils.checkMTU(
            host=host.ip, user=config.HOSTS_USER,
            password=config.HOSTS_PW, mtu=mtu, bond=bond,
            physical_layer=False, network=network,
            nic=nic, vlan=vlan, bridged=bridge
        ):
            raise NetworkException(
                "(logical) MTU on host %s should be %s and it is not" % (
                    host.ip, mtu,
                )
            )

    if physical:
        logger.info(
            "Checking physical layer %s %s", bond_log, nic_log
        )
        if not utils.checkMTU(
            host=host.ip, user=config.HOSTS_USER, password=config.HOSTS_PW,
            mtu=mtu, nic=nic, bond=bond, bond_nic1=bond_nic1,
            bond_nic2=bond_nic2
        ):
            raise NetworkException(
                "(physical) MTU on host %s should be %s and it is not" % (
                    host.ip, mtu,
                )
            )


def add_vnics_to_vms(
    ips, mtu, network=config.VLAN_NETWORKS[0], nic_name=config.NIC_NAME[1],
    set_ip=True
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
    for i in range(2):
        vm_name = config.VM_NAME[i]
        vm_ip = config.VM_IP_LIST[i]
        logger.info(
            "Adding %s with MTU %s on %s of %s",
            network, mtu, nic_name, vm_name
        )
        if not ll_vms.addNic(
            positive=True, vm=vm_name, name=nic_name, network=network
        ):
            raise NetworkException(
                "Cannot add vNIC %s to VM %s" % (nic_name, vm_name)
            )
        if set_ip:
            logger.info("Get %s NICs", vm_name)
            vm_nics = get_vm_nic_names(vm=vm_ip, password=config.HOSTS_PW)
            if not vm_nics:
                raise NetworkException("Failed to get %s NICs" % vm_name)

            logger.info("Set MTU %s on %s for %s", mtu, nic_name, vm_name)
            if not utils.configure_temp_mtu(
                host=vm_ip, user=config.HOSTS_USER, nic=vm_nics[1],
                password=config.HOSTS_PW, mtu=mtu,
            ):
                raise NetworkException(
                    "Unable to configure VM's %s %s with MTU %s" % (
                        vm_name, vm_nics[1], mtu,
                    )
                )
            logger.info("Setting up temp IP %s on VM %s", ips[i], vm_name)
            if not utils.configure_temp_static_ip(
                host=vm_ip, user=config.HOSTS_USER,
                password=config.HOSTS_PW, ip=ips[i], nic=vm_nics[1]
            ):
                raise NetworkException(
                    "Couldn't configure temp IP %s on VMs %s" % (ips[i], vm_ip)
                )
            if not ll_hosts.ifupNic(
                host=vm_ip, root_password=config.HOSTS_PW, nic=vm_nics[1]
            ):
                raise NetworkException(
                    "Cannot set interface %s on VM %s UP" % (vm_nics[1], vm_ip)
                )


def remove_vnics_from_vms(nic_name=config.NIC_NAME[1]):
    """
    Remove NIC from config.VM_NAME[:2]

    :param nic_name: NIC name to remove
    :type nic_name: str
    """
    for i in range(2):
        vm_name = config.VM_NAME[i]
        logger.info("Unplugging %s from %s", nic_name, vm_name)
        if not ll_vms.updateNic(
            positive=True, vm=vm_name, nic=nic_name, plugged=False
        ):
            logger.error("Unplug %s failed", nic_name)

        logger.info("Removing %s from %s", nic_name, vm_name)
        if not ll_vms.removeNic(positive=True, vm=vm_name, nic=nic_name):
            logger.error("Cannot remove vNIC from %s", vm_name)
