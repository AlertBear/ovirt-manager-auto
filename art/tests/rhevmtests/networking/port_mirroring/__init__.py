"""
Port Mirroring test
"""

import logging
from rhevmtests.networking import config, network_cleanup
from art.rhevm_api.tests_lib.low_level.storagedomains import cleanDataCenter
from art.rhevm_api.tests_lib.low_level.vms import (
    createVm, waitForIP, updateNic, stopVms, removeNic, get_vm_nics_obj,
    waitForVMState,
)
from art.rhevm_api.tests_lib.high_level.networks import (
    prepareSetup, createAndAttachNetworkSN, remove_net_from_setup
)
from art.rhevm_api.tests_lib.low_level.networks import addVnicProfile
from art.test_handler.exceptions import NetworkException

from art.rhevm_api.tests_lib.low_level.vms import addNic
from rhevmtests.networking.port_mirroring.utils import(
    ge_seal_vm, set_port_mirroring
)
from utilities import machine

logger = logging.getLogger("PortMirroring")

# ################################################


def setup_package():
    """
    Prepare environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on GE. Calling network_cleanup()")
        network_cleanup()

    if not config.GOLDEN_ENV:
        logger.info(
            "Create DC, Cluster, attach hosts and create VM and template"
        )
        if not prepareSetup(hosts=config.VDS_HOSTS,
                            cpuName=config.CPU_NAME,
                            username=config.HOSTS_USER,
                            password=config.HOSTS_PW,
                            datacenter=config.DC_NAME[0],
                            storageDomainName=config.STORAGE_NAME[0],
                            storage_type=config.STORAGE_TYPE,
                            cluster=config.CLUSTER_NAME[0],
                            auto_nics=[0],
                            lun_address=config.LUN_ADDRESS[0],
                            lun_target=config.LUN_TARGET[0],
                            luns=config.LUN[0], version=config.COMP_VERSION,
                            vm_password=config.VMS_LINUX_PW,
                            placement_host=config.HOSTS[0],
                            vmName=config.VM_NAME[0],
                            mgmt_network=config.MGMT_BRIDGE,
                            template_name=config.TEMPLATE_NAME[0]):
            raise NetworkException("Cannot create setup")

        logger.info(
            "Create 4 more VMs from the template created by prepareSetup()"
        )
        for vmName in config.VM_NAME[1:config.NUM_VMS]:
            if not createVm(
                True, vmName=vmName, vmDescription='linux vm',
                cluster=config.CLUSTER_NAME[0], start='True',
                template=config.TEMPLATE_NAME[0],
                placement_host=config.HOSTS[0],
                network=config.MGMT_BRIDGE
            ):
                raise NetworkException(
                    "Failed to create %s from template" % vmName
                )

            if not waitForVMState(vm=vmName):
                raise NetworkException("VM is not UP")

    logger.info(
        "Create %s, %s on %s/%s and attach them to %s",
        config.VLAN_NETWORKS[0], ".".join(
            [config.BOND[0], config.VLAN_NETWORKS[1]]),
        config.DC_NAME[0], config.CLUSTER_NAME[0], config.HOSTS[:2]
    )
    network_params = {None: {'nic': config.BOND[0], 'mode': 1,
                             'slaves': [2, 3]},
                      config.VLAN_NETWORKS[0]: {
                          'vlan_id': config.VLAN_ID[0],
                          'nic': 1,
                          'required': 'false'},
                      config.VLAN_NETWORKS[1]: {
                          'vlan_id': config.VLAN_ID[1],
                          'nic': config.BOND[0],
                          'required': 'false'}}

    if not createAndAttachNetworkSN(
        data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
        host=config.VDS_HOSTS[:2], network_dict=network_params,
        auto_nics=[0, 1]
    ):
        raise NetworkException("Cannot create and attach networks")

    logger.info(
        "Create VNIC profiles with port mirroring for %s network and %s" % (
            config.MGMT_BRIDGE, config.VLAN_NETWORKS[0])
    )
    for i, network in enumerate(
            (config.MGMT_BRIDGE, config.VLAN_NETWORKS[0])
    ):
        if not addVnicProfile(
            positive=True, name=config.PM_VNIC_PROFILE[i],
            cluster=config.CLUSTER_NAME[0],
            network=network, port_mirroring=True
        ):
            raise NetworkException(
                "Failed to create VNIC profile with port mirroring."
            )

    for vmName in config.VM_NAME[:config.NUM_VMS]:
        if config.GOLDEN_ENV:
            logger.info("Running on GE: sealing %s", vmName)
            ge_seal_vm(vm=vmName)

        add_profile = True
        for i in (0, 1):
            if vmName == config.VM_NAME[0] and add_profile:
                logger.info(
                    "Setting %s with profile %s on %s", config.NIC_NAME[0],
                    config.MGMT_BRIDGE + "_PM", vmName
                )
                set_port_mirroring(
                    config.VM_NAME[0], config.NIC_NAME[0], config.MGMT_BRIDGE
                )
                vnic_profile = config.PM_VNIC_PROFILE[1]
                add_profile = False
            else:
                vnic_profile = config.VLAN_NETWORKS[i]

            logger.info("Adding %s to %s", config.NIC_NAME[i + 1], vmName)
            if not addNic(
                True, vm=vmName, name=config.NIC_NAME[i + 1],
                interface=config.NIC_TYPE_VIRTIO,
                network=config.VLAN_NETWORKS[i],
                vnic_profile=vnic_profile
            ):
                raise NetworkException('Failed to add nic to %s' % vmName)

    logger.info("Configure IPs for each VM")
    for i, vm in enumerate(config.VM_NAME[:config.NUM_VMS]):
        logger.info("Getting mgmt network IP for %s.", vm)
        rc, out = waitForIP(vm=vm, timeout=180, sleep=10)

        if not rc:
            raise NetworkException("Failed to get VM IP on mgmt network")

        local_mgmt_ip = out['ip']
        logger.info(
            "Update the list of mgmt network IPs with %s from %s",
            local_mgmt_ip, vm
        )
        config.MGMT_IPS.append(local_mgmt_ip)

        vm_obj = machine.Machine(
            local_mgmt_ip, config.VMS_LINUX_USER,
            config.VMS_LINUX_PW).util(machine.LINUX)

        logger.info("Configure IPs on %s for nic1 and nic2", vm)
        for nicIndex, ip in enumerate(
                (config.NET1_IPS[i], config.NET2_IPS[i]), start=1
        ):

            logger.info(
                "Creating eth%s file with %s in %s", nicIndex, ip, vm
            )
            if not vm_obj.addNicConfFile(
                    nic="eth%s" % nicIndex, ip=ip, bootproto="static",
                    netmask="255.255.0.0"
            ):
                raise NetworkException(
                    "Failed to create ifcfg file eth%s" % nicIndex
                )

        logger.info("Restarting network service on %s", vm)
        vm_obj.restartService("network")

    logger.info("Stop iptables service on hosts")
    for host in config.VDS_HOSTS[:2]:
        if not host.service(config.FIREWALL_SRV).stop():
            raise NetworkException("Cannot stop Firewall service")


def teardown_package():
    """
    Clean the environment
    """
    if config.GOLDEN_ENV:
        logger.info("Running on GE")
        for vm in config.VM_NAME[:config.NUM_VMS]:
            logger.info("Getting mgmt network IP for %s.", vm)
            rc, out = waitForIP(vm=vm, timeout=180, sleep=10)

            if not rc:
                raise NetworkException('Failed to get VM IP on mgmt network')

            local_mgmt_ip = out['ip']
            vm_obj = machine.Machine(
                local_mgmt_ip, config.VMS_LINUX_USER,
                config.VMS_LINUX_PW).util(machine.LINUX)

            for idx in (1, 2):
                logger.info("Removing ifcfg-eth%s file from %s", idx, vm)
                vm_obj.removeNicConfFile("eth%s" % idx)

        logger.info("Stopping %s", config.VM_NAME[:config.NUM_VMS])
        if not stopVms(config.VM_NAME):
            logger.error("Failed to stop VMs")

        for vm in config.VM_NAME:
            vm_nics = get_vm_nics_obj(vm)
            for nic in vm_nics:
                if nic.name == "nic1":
                    logger.info(
                        "Setting %s profile on %s in %s",
                        config.MGMT_BRIDGE, nic.name, vm
                    )
                    if not updateNic(
                            True, vm, config.NIC_NAME[0],
                            network=config.MGMT_BRIDGE,
                            vnic_profile=config.MGMT_BRIDGE
                    ):
                        logger.error(
                            "Failed to update %s in %s  to profile "
                            "without port mirroring", config.NIC_NAME[0], vm
                        )
                logger.info("Removing %s from %s", nic.name, vm)
                if not removeNic(True, vm, nic):
                    logger.error(
                        "Failed to remove %s from %s", nic, vm
                    )

        logger.info("Removing all networks from DC/Cluster and hosts")
        if not remove_net_from_setup(
            host=config.VDS_HOSTS[0], auto_nics=[0],
            data_center=config.DC_NAME[0], all_net=True,
            mgmt_network=config.MGMT_BRIDGE
        ):
            logger.error("Cannot remove network from setup")

        logger.info("Running on GE. Calling network_cleanup()")
        network_cleanup()

    else:
        logger.info("Clean the environment")
        if not cleanDataCenter(positive=True, datacenter=config.DC_NAME[0],
                               vdc=config.VDC_HOST,
                               vdc_password=config.VDC_ROOT_PASSWORD):
            raise NetworkException("Cannot remove setup")
