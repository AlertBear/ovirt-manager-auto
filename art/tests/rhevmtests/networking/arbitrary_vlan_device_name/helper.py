"""
Helper for arbitrary_vlan_device_name job
"""
import logging
import os
import libvirt

from random import randint
from rhevmtests.networking import config
from art.test_handler.exceptions import NetworkException
from art.rhevm_api.tests_lib.low_level.events import get_max_event_id
from art.rhevm_api.tests_lib.low_level.hosts import(
    getHostNicsList, refresh_host_capabilities, get_host_name_from_engine,
)


logger = logging.getLogger("ArbitraryVlanDeviceName_Helper")

LIBVIRTD_CONF = "/etc/libvirt/libvirtd.conf"
SASL_OFF = "none"
SASL_ON = "sasl"
LIBVIRTD_SERVICE = "libvirtd"
VDSMD_SERVICE = "vdsmd"
VLAN_NAMES = ["vlan10", "vlan20", "vlan30"]
VLAN_IDS = ["10", "20", "30"]
BRIDGE_NAMES = ["br_vlan10", "br_vlan20", "br_vlan30"]
SSH_DIR_PATH = "~/.ssh"
AUTHORIZED_KEYS = os.path.join(SSH_DIR_PATH, "authorized_keys")
KNOWN_HOSTS = os.path.join(SSH_DIR_PATH, "known_hosts")


def job_tear_down():
    """
    tear_down for ArbitraryVlanDeviceName job
    """
    host_name = get_host_name_from_engine(config.VDS_HOSTS[0].ip)
    for x, y in zip(VLAN_NAMES, BRIDGE_NAMES):
        logger.info("Delete VLAN: %s on %s", x, host_name)
        host_delete_vlan(host_obj=config.VDS_HOSTS[0], vlan_name=x)

        logger.info("Delete virsh BRIDGE: %s on %s", y, host_name)
        virsh_delete_bridge(host_obj=config.VDS_HOSTS[0], bridge=y)

        logger.info("Delete BRIDGE: %s on %s", y, host_name)
        try:
            config.VDS_HOSTS[0].network.delete_bridge(bridge=y)
        except NetworkException:
            logger.error(
                "Failed to delete BRIDGE: %s on %s", y, host_name
            )
            return False


def host_add_vlan(host_obj, vlan_id, vlan_name, nic):
    """
    Create VLAN interface on hosts
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param vlan_id: VLAN ID
    :type vlan_id: str
    :param nic: Interface index (from host_obj.nics) or str (for bond nic)
    :type nic: int or str
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: True/False
    :rtype: bool
    """
    interface = host_obj.nics[nic] if isinstance(nic, int) else nic
    cmd = [
        "ip", "link", "add", "dev", vlan_name, "link", interface, "name",
        vlan_name, "type", "vlan", "id", vlan_id
    ]
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to create %s. err: %s. out: %s", vlan_name, err, out
        )
        return False
    return True


def host_delete_vlan(host_obj, vlan_name):
    """
    Delete VLAN from host
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: True/False
    :rtype: bool
    """
    cmd = ["ip", "link", "delete", "dev", vlan_name]
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to delete %s. err: %s. out: %s", vlan_name, err, out
        )
        return False
    return True


def virsh_add_bridge(host_obj, bridge):
    """
    Add bridge to virsh via xml file
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param bridge: Bridge name
    :type bridge: str
    :return: True/False
    :rtype: bool
    """
    host_ip = host_obj.ip
    libvirt_conn = get_libvirt_connection(host_ip)

    rand_uuid = randint(1000, 9999)
    vdsm_bridge_name = "vdsm-{0}".format(bridge)
    vdsm_bridge_line = "<name>{0}</name>".format(vdsm_bridge_name)
    bridge_name_line = "<bridge name='{0}'/>".format(bridge)
    uuid_line = "<uuid>a2de77bc-{0}-4ec5-a37a-f8f2dbdf91c9</uuid>".format(
        str(rand_uuid)
    )
    xml_str = ("<network>{0}{1}<forward mode='bridge'/>{2}</network>".format(
        vdsm_bridge_line, uuid_line, bridge_name_line))
    try:
        libvirt_conn.networkCreateXML(xml_str)
    except libvirt.libvirtError as e:
        logger.error("Failed to add network to libvirt from XML. ERR: %s", e)
        return False

    if vdsm_bridge_name not in [
        i.name() for i in libvirt_conn.listAllNetworks(0)
    ]:
        logger.error("%s not found among libvirt networks", vdsm_bridge_name)
        return False

    return True


def virsh_delete_bridge(host_obj, bridge):
    """
    Delete bridge to virsh via xml file
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param bridge: Bridge name
    :type bridge: str
    :return: True/False
    :rtype: bool
    """
    host_ip = host_obj.ip
    vdsm_bridge_name = "vdsm-{0}".format(bridge)
    libvirt_conn = get_libvirt_connection(host_ip)
    try:
        all_networks = libvirt_conn.listAllNetworks(0)
        for net in all_networks:
            if vdsm_bridge_name == net.name():
                net.destroy()
                return True
    except libvirt.libvirtError as e:
        logger.error("Failed to delete bridge from virsh. ERR: %s", e)

    logger.error("%s not found among libvirt networks", vdsm_bridge_name)
    return False


def set_libvirtd_sasl(host_obj, sasl=True):
    """
    Set auth_unix_rw="none" in libvirtd.conf to enable passwordless
    connection to libvirt command line (virsh)
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param sasl: True to enable sasl, False to disable
    :type sasl: bool
    :return: True/False
    :rtype: bool
    """
    sasl_off = 'auth_unix_rw="{0}"'.format(SASL_OFF)
    sasl_on = 'auth_unix_rw="{0}"'.format(SASL_ON)
    sed_arg = "'s/{0}/{1}/g'".format(
        sasl_on if not sasl else sasl_off, sasl_off if not sasl else sasl_on
    )

    # following sed procedure is needed by RHEV-H and its read only file system
    # TODO: add persist after config.VDS_HOST.os is available see
    # https://projects.engineering.redhat.com/browse/RHEVM-2049
    sed_cmd = [
        "sed", sed_arg, LIBVIRTD_CONF
    ]
    host_exec = host_obj.executor()
    logger_str = "Enable" if sasl else "Disable"
    logger.info(
        "%s sasl in %s", logger_str, LIBVIRTD_CONF
    )
    rc, sed_out, err = host_exec.run_cmd(sed_cmd)
    if rc:
        logger.error(
            "Failed to run sed %s %s err: %s. out: %s",
            sed_arg, LIBVIRTD_CONF, logger_str, err, sed_out
        )
        return False
    cat_cmd = [
        "echo", "%s" % sed_out, ">", LIBVIRTD_CONF
    ]
    rc, cat_out, err = host_exec.run_cmd(cat_cmd)

    if rc:
        logger.error(
            "Failed to %s sasl in libvirt. err: %s. out: %s", logger_str,
            err, cat_out
        )
        return False

    logger.info(
        "Stop %s service", LIBVIRTD_SERVICE
    )
    if not host_obj.service(
            LIBVIRTD_SERVICE).stop(

    ):
        logger.error(
            "Failed to restart %s service", LIBVIRTD_SERVICE
        )
        return False

    logger.info(
        "Restarting %s server", VDSMD_SERVICE
    )
    if not host_obj.service(
            VDSMD_SERVICE).restart(
    ):
        logger.error(
            "Failed to restart %s service", VDSMD_SERVICE
        )
        return False
    return True


def get_libvirt_connection(host):
    """
    Create libvirt connection to host
    :param host: Host IP or FQDN
    :type host: str
    :return: libvirt connection object
    :rtype: object
    """
    remote_uri = "qemu+ssh://root@{0}/system".format(host)
    return libvirt.open(remote_uri)


def detach_nic_from_bridge(host_obj, bridge, nic):
    """
    Detach NIC from bridge
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param bridge: Bridge name
    :type bridge: str
    :param nic: NIC name
    :type nic: str
    :return: True/False
    :rtype: bool
    """
    cmd = ["brctl", "delif", bridge, nic]
    host_exec = host_obj.executor()
    rc, out, err = host_exec.run_cmd(cmd)
    if rc:
        logger.error(
            "Failed to detach %s from %s. err: %s. out: %s", nic,  bridge,
            err, out
        )
        return False
    return True


def check_if_nic_in_hostnics(nic, host):
    """
    Check if NIC is among the host NICs collection
    :param nic: NIC name
    :type nic: str
    :param host: Host name (in engine)
    :type host: str
    :return: raise NetworkException on error
    """
    logger.info("Check that %s exists on %s via engine", nic, host)
    host_nics = getHostNicsList(host=host)
    if nic not in [i.name for i in host_nics]:
        raise NetworkException("%s not found in %s nics" % (nic, host))


def add_bridge_on_host_and_virsh(host_obj, bridge, network):
    """
    Create bridge on host and create the bridge on virsh as well
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param bridge: Bridge name
    :type bridge: str
    :param network: Network name
    :type network: str
    :return: raise NetworkException on error
    """
    host_name = get_host_name_from_engine(host_obj.ip)
    logger.info("Attaching %s to %s on %s", network, bridge, host_name)
    if not host_obj.network.add_bridge(bridge=bridge, network=network):
        raise NetworkException("Failed to add %s with %s" % (bridge, network))

    logger.info("Adding %s to %s via virsh", bridge, host_name)
    if not virsh_add_bridge(host_obj=host_obj, bridge=bridge):
        raise NetworkException("Failed to add %s to virsh" % bridge)

    refresh_capabilities(host=host_name)


def delete_bridge_on_host_and_virsh(host_obj, bridge):
    """
    Delete bridge on host and delete the bridge on virsh as well
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param bridge: Bridge name
    :type bridge: str
    :return: raise NetworkException on error
    """
    host_name = get_host_name_from_engine(host_obj.ip)
    logger.info("Delete %s on %s", bridge, host_name)
    if not virsh_delete_bridge(host_obj=host_obj, bridge=bridge):
        raise NetworkException(
            "Failed to delete %s on %s" % (bridge, host_name)
        )
    logger.info("Delete %s on %s", bridge, host_name)
    if not host_obj.network.delete_bridge(bridge=bridge):
        raise NetworkException(
            "Failed to delete %s on %s" % (bridge, host_name)
        )


def add_vlan_and_refresh_capabilities(host_obj, vlan_id, vlan_name, nic):
    """
    Add VLAN to host and refresh host capabilities
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param nic: Interface index (from host_obj.nics) or str (for bond nic)
    :type nic: int or str
    :param vlan_id: VLAN id
    :type vlan_id: str
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: raise NetworkException on error
    """
    host_name = get_host_name_from_engine(host_obj.ip)
    logger.info(
        "Adding VLAN ID: %s. Name: %s. to %s", vlan_id, vlan_name, host_name
    )
    if not host_add_vlan(
        host_obj=host_obj, vlan_id=vlan_id, nic=nic, vlan_name=vlan_name
    ):
        raise NetworkException(
            "Failed to create %s on %s" % (vlan_name, host_name)
        )

    refresh_capabilities(host=host_name)


def remove_vlan_and_refresh_capabilities(host_obj, vlan_name):
    """
    Add vlan to host and refresh host capabilities
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param vlan_name: VLAN name
    :type vlan_name: str
    :return: raise NetworkException on error
    """
    host_name = get_host_name_from_engine(host_obj.ip)
    logger.info("Removing %s from %s", vlan_name, host_name)
    if not host_delete_vlan(host_obj=host_obj, vlan_name=vlan_name):
        raise NetworkException(
            "Failed to remove %s from %s" % (vlan_name, host_name)
        )

    refresh_capabilities(host=host_name)


def refresh_capabilities(host):
    """
    Refresh host capabilities
    :param host: Host name (engine name)
    :type host: str
    :return: raise NetworkException on error
    """
    last_event = get_max_event_id(query="")
    logger.info("Refresh capabilities for %s", host)
    if not refresh_host_capabilities(host=host, start_event_id=last_event):
        logger.error("Failed to refresh capabilities for: %s" % host)


def check_if_nic_in_vdscaps(host_obj, nic):
    """
    Check if NIC in vdsClient getVdsCaps
    :param host_obj: resources.VDS object
    :type host_obj: object
    :param nic: NIC name
    :type nic: str
    :return: raise NetworkException on error
    """
    host_exec = host_obj.executor()
    cmd = [
        "vdsClient", "-s", "0", "getVdsCaps", "|", "grep", nic, "|", "wc",
        "-l"
    ]
    rc, out, err = host_exec.run_cmd(cmd)
    if rc or not out:
        raise NetworkException(
            "%s not found in getVdsCaps. err: %s" % (nic, err)
        )
