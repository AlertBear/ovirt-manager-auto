#! /usr/bin/python
# -*- coding: utf-8 -*-

import copy
import logging
import itertools
import config
from art.rhevm_api.tests_lib.low_level import (
    mac_pool as ll_mac_pool,
    vms as ll_vms,
    disks as ll_disks,
    general as ll_general,
    external_import as ll_external_import,
    hosts as ll_hosts
)
from art.unittest_lib import testflow
from rhevmtests.compute.virt import helper

logger = logging.getLogger()


@ll_general.generate_logs()
def check_imported_vm(
    vm_name,
    parameters_to_check=config.V2V_VALUES_TO_COMPARE,
    number_of_disks=1
):
    """
    Check imported vm from external provider.

    Args:
        vm_name(str): Name of the parameter to check
        parameters_to_check (list): list of parameters to check
            disk size, memory, sockets, cores, threads,
            windows_drivers, number_of_disks
        number_of_disks(int): Number of disks on VM

    Raise:
        AssertionError: if one of the tested parameter is in correct
    """
    actual_values = {}
    expected_config = get_expected_config(vm_name)
    testflow.step(
        "Check imported vm {vm} with parameters{p}".format(
            vm=vm_name, p=parameters_to_check)
    )
    for parameter in parameters_to_check:
        if parameter == 'disk_size':
            if number_of_disks > 1:
                logger.info("VM with more then 1 disk")
                found = False
                vm_disks = ll_disks.getObjDisks(vm_name, get_href=False)
                for disk in vm_disks:
                    size = disk.get_provisioned_size()
                    logger.info("Disk {disk_name} size: {size}".format(
                        disk_name=disk.get_alias(),
                        size=size
                    ))
                    if size == expected_config['disk_size']:
                        found = True
                assert found, "Disk size did not match expect size"
            else:
                logger.info("VM with disk")
                disk_size = ll_disks.getObjDisks(
                    vm_name, get_href=False
                )[0].get_provisioned_size()
                assert disk_size == expected_config['disk_size']
        elif parameter == 'windows_drivers':
            continue  # Todo: get drivers list from VM
        else:
            actual_values[parameter] = getattr(
                ll_vms, 'get_vm_{p}'.format(p=parameter)
            )(vm_name)
    logging.info(
        "Checking vm parameters: \n Expected: {e} \n Actual: {v}".format(
            e=expected_config, v=actual_values
        )
    )
    for parameter in parameters_to_check:
        assert helper.compare_vm_parameters(
            param_name=parameter,
            param_value=actual_values[parameter],
            expected_config=expected_config
        ), "VM parameter {p}={v} is different from expected: {e}".format(
            p=parameter,
            v=actual_values[parameter],
            e=expected_config[parameter]
        )
    if number_of_disks > 1:
        actual_number_of_disks = len(ll_vms.get_vm_disks_ids(vm=vm_name))
        testflow.step(
            "Check that VM has {num_of_disks} disks, "
            "actual: {a_size}".format(
                num_of_disks=number_of_disks,
                a_size=actual_number_of_disks
            )
        )
        assert actual_number_of_disks == number_of_disks


def get_expected_config(vm_name):
    """
    Returns vm expected configuration

    Args:
        vm_name (str): VM name

    Return:
        dict: Dictionary with VM configuration
    """
    expected_config = copy.copy(
        config.EXTERNAL_VM_CONFIGURATIONS[vm_name]
    )
    testflow.step("Get mac range for the environment")
    default_mac_range = ll_mac_pool.get_mac_range_values(
        ll_mac_pool.get_default_mac_pool()
    )[0]
    expected_config['nic_mac_address']['start'] = default_mac_range[0]
    expected_config['nic_mac_address']['end'] = default_mac_range[1]
    return expected_config


@ll_general.generate_logs()
def import_vm_from_external_provider(
    provider_vm_name=None,
    new_vm_name=None,
    provider=None,
    timeout=config.IMPORT_V2V_TIMEOUT,
    win_drivers=None,
    cluster=config.CLUSTER_NAME[0],
    host=None,
    wait=True,
    **kwargs
):
    """
    Imports vm from the external provider like VMWare, KVM and waits for its
    conversion

    Args:
        provider_vm_name (str): VM name to import from the external provider
        new_vm_name (str): New VM name on system (RHV)
        provider (str): External provider name: vmware, kvm
        timeout (int): Time out to was till import done
        win_drivers (str): Name of the driver iso file in iso domain
        cluster (str): Cluster name
        wait (bool): wait till import finished
        host(str): Host name
    Keyboard arguments:
        provider_vm_name (str): Name of vm in the provider
        cluster (str): Name of cluster
        storage_domain (str): Name of destination storage domain
        new_vm_name (str): Name for the vm in the system
        user_name (str): User name for the provider
        password (str): Password for the provider
        provider (str): Name of the provider
        url (str): Url of provider (for OVA)
        driver_iso (str): Name of the driver iso file in iso domain
        sparse (bool): True if import the image as sparse, False otherwise
        engine_url (str): Engine Url for the destination engine
        host (str): Name of the host to use for importing the image

    Returns:
        bool: If wait == False returns the import command status
              If wait == True returns the import status, True if VM is
                imported and in status down, Else False
    """
    import_status = list()
    testflow.step(
        "Importing {vm_name_ext} VM from "
        "{provider_name} as {vm_name} with host {host}".format(
            vm_name_ext=provider_vm_name,
            provider_name=provider,
            vm_name=new_vm_name,
            host=host
        )
    )
    if kwargs:
        import_status.append(
            ll_external_import.import_vm_from_external_provider(
                provider_vm_name=provider_vm_name,
                cluster=cluster,
                storage_domain=kwargs.get("storage_domain"),
                new_vm_name=new_vm_name,
                password=kwargs.get("password"),
                provider=provider,
                url=kwargs.get("url"),
                driver_iso=kwargs.get("driver_iso"),
                sparse=kwargs.get("sparse"),
                engine_url=kwargs.get("engine_url"),
                host=host,
                user_name=kwargs.get("user_name")
            )
        )
    else:
        import_info = set_import_data(
            new_vm_name, provider, provider_vm_name, win_drivers, host
        )
        import_status.append(
            ll_external_import.import_vm_from_external_provider(
                **import_info
            )
        )
    if import_status[0]:
        testflow.step(
            "For vm {vm_name}: waiting for event of successful import, "
            "vm status is {vm_status}".format(
                vm_name=provider_vm_name,
                vm_status=ll_vms.get_vm(new_vm_name).get_status()
            )
        )
        import_status.append(helper.wait_for_v2v_import_event(
            vm_name=provider_vm_name, cluster=cluster, timeout=timeout
        )
        )
        if wait and import_status[1]:
            testflow.step(
                "Check that VM: {vm} status is down".format(vm=new_vm_name)
            )
            import_status.append(
                ll_vms.get_vm(new_vm_name).get_status() ==
                config.VM_DOWN_STATE
            )
        else:
            return import_status[0]
    return all(import_status)


def set_import_data(
    new_vm_name, provider, vm_name_on_provider, windows_drivers=None,
    host=None
):
    """
    Set import data

    Args:
        new_vm_name (str): VM name on system (RHV)
        provider (str):  Provider name
        vm_name_on_provider (str): Name of the VM on provider
        windows_drivers (str): Name of the driver iso file in iso domain
        host(str): Host name

    Returns:
        dict: Dict with all the data in order to import from external
        provider
    """
    if not new_vm_name:
        new_vm_name = vm_name_on_provider
    import_info = {}
    import_info.update(**config.EXTERNAL_PROVIDER_INFO[provider])
    import_info.update(**config.IMPORT_DATA)
    import_info['provider_vm_name'] = vm_name_on_provider
    import_info['new_vm_name'] = new_vm_name
    import_info['driver_iso'] = windows_drivers
    import_info['host'] = host
    return import_info


def get_all_vms_import_info(provider, vms_to_import):
    """
    Returns list of dictionaries with all the info to import vm.
    And set the host from which the VM will be imported (round robin between
    hosts)
    Args:
        provider (str): Provider name
        vms_to_import (list): List of vms to import with there configuration
        in tuple

    Returns:
        List: List of dictionaries
    """
    vms_import_info = []
    hosts_up = filter(
        lambda host: ll_hosts.is_host_up(positive=True, host=host),
        config.HOSTS
    )
    schedule_hosts = itertools.cycle(hosts_up)
    for vms in vms_to_import:
        vms_import_info.append(
            set_import_data(
                vm_name_on_provider=vms[0],
                new_vm_name=vms[1],
                windows_drivers=vms[2],
                host=schedule_hosts.next(),
                provider=provider
            )
        )
    logger.info("VMs import data: %s", vms_import_info)
    return vms_import_info
