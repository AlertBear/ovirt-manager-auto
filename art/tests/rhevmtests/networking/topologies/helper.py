"""
Helper for topologies job
"""
import logging
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN
)
from art.rhevm_api.tests_lib.low_level.networks import check_bond_mode
from art.rhevm_api.tests_lib.low_level.vms import updateNic, waitForIP
from art.rhevm_api.utils.test_utils import check_icmp
from art.test_handler.exceptions import NetworkException
from rhevmtests.networking import config

logger = logging.getLogger("topologies_helper")


def update_vnic_driver(driver):
    """
    Description: Update vNIC driver for VM
    author: myakove
    Parameters:
        *  *driver* - driver to update the vNIC (virtio, e1000, rtl8139)
    """
    logger.info("Unplug vNIC")
    if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[0],
            plugged=False
    ):
        return False

    logger.info("Updating vNIC to %s driver", driver)
    if not updateNic(
            positive=True, vm=config.VM_NAME[0], nic=config.NIC_NAME[0],
            interface=driver, plugged=True
    ):
        return False
    return True


def check_connectivity(vlan=False, vm=True):
    """
    Description: Check connectivity for VM and non-VM networks
    Parameters:
        *  *vlan* - ping from host if True else ping from engine
        *  *vm* - Check connectivity to VM network if True, False for non-VM

    """
    vm_ip = None
    if vm:
        ip = waitForIP(vm=config.VM_NAME[0], timeout=300)
        if not ip[0]:
            return False
        vm_ip = ip[1]["ip"]
        host = config.ENGINE_HOST if not vlan else config.VDS_HOSTS[0]
    else:
        host = config.VDS_HOSTS[0]

    dst_ip = vm_ip if vm_ip is not None else config.DST_HOST_IP

    return check_icmp(host_obj=host, dst_ip=dst_ip)


def create_and_attach_bond(mode):
    """
    Description: Create and attach BOND.
    Parameters:
        *  *mode* - BOND mode.
    """
    (usages,
     address,
     netmask,
     bootproto,
     profile_required) = "vm", None, None, None, True

    slaves = [4, 5] if mode == 2 else [2, 3]

    # for modes bellow create bridgeless network with static IP
    if mode in [i for i in config.BOND_MODES if str(i) in (
            "0", "3", "5", "6"
    )]:
        usages = ""
        address = [config.ADDR_AND_MASK[0]]
        netmask = [config.ADDR_AND_MASK[1]]
        bootproto = "static"
        profile_required = False

    local_dict = {config.NETWORKS[0]: {"nic": config.BOND[int(mode)],
                                       "mode": mode,
                                       "slaves": slaves,
                                       "usages": usages,
                                       "address": address,
                                       "netmask": netmask,
                                       "bootproto": bootproto,
                                       "required": False,
                                       "profile_required": profile_required}}

    if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict, auto_nics=[0]
    ):
        return False
    if not check_bond_mode(
            host=config.HOSTS_IP[0], user=config.HOSTS_USER,
            password=config.HOSTS_PW, interface=config.BOND[int(mode)],
            mode=mode
    ):
        logger.error("BOND mode should be %s but it's not", mode)
        return False
    return True


def check_connectivity_log(
        driver=None, mode=None, info=False, error=False, vlan=False
):
    """
    Description: Generate string for info/errors.
    Parameters:
        *  *mode* - BOND mode.
        *  *driver* - driver of the interface
        *  *info* - Info string if True
        *  *error* - raise string if True
        *  *vlan* - vlan network in string if True
    """
    output = "info or error not sent, nothing to do"
    interface = "BOND mode %s" % mode if mode else ""
    vlan_info = "VLAN over" if vlan else ""
    driver_info = "with %s driver" % driver if driver else ""
    if info:
        output = (
            "Check connectivity to %s %s network %s"
            % (vlan_info, interface, driver_info)
        )

    if error:
        output = (
            "Connectivity failed to %s %s network %s"
            % (vlan_info, interface, driver_info)
        )

    return output


def check_vm_connect_and_log(driver=None, mode=None, vlan=False, vm=True):
    """
    Description: Check VM connectivity with logger info and raise error if
    fail
    Parameters:
        *  *mode* - BOND mode.
        *  *driver* - driver of the interface
        *  *vlan* - ping from host if True else ping from engine
        *  *vm* - Check connectivity to VM network if True, False for non-VM
    """
    logger.info(check_connectivity_log(
        mode=mode, driver=driver, info=True, vlan=vlan)
    )

    if not check_connectivity(vlan=vlan, vm=vm):
        raise NetworkException(check_connectivity_log(
            mode=mode, driver=driver, error=True, vlan=vlan)
        )
    return True
