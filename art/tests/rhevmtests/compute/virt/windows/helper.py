#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt windows helper
"""
import copy
import logging

from concurrent.futures import ThreadPoolExecutor

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config
import rhevmtests.compute.virt.config as virt_config
import rhevmtests.compute.virt.helper as virt_helper
import rhevmtests.compute.virt.windows_helper as win_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    templates as ll_templates,
    disks as ll_disks
)
from art.unittest_lib.common import testflow

logger = logging.getLogger(__name__)


def migrate_job_info():
    """
    builds kwargs dict for job_runner with
    vms name

    Returns:
        dict: dict with job info
    """
    kwargs_info = {}

    for vm_name in config.WINDOWS_VM_NAMES:
        kwargs_info['{0}'.format(vm_name)] = {
            'positive': True,
            'vm': vm_name
        }
    return kwargs_info


def test_vm_snapshots(vm_name, export_domain, with_memory=False):
    """
    Create, restore, export and remove snapshots

    Args:
        vm_name (str): vm_name
        with_memory (bool): create/restore snapshot with memory
        export_domain (str): export domain name

    Returns:
        bool: True if all actions success, else False
    """

    testflow.step("Create two new snapshots of vm %s", vm_name)
    for description in virt_config.SNAPSHOT_DESCRIPTION:
        job_description = "Creating VM Snapshot %s for VM %s" % (
            description, vm_name
        )
        logger.info("add snapshot job description: %s", job_description)
        if not ll_vms.addSnapshot(
            positive=True,
            vm=vm_name,
            description=description,
            persist_memory=with_memory
        ):
            logger.error("Failed to add snapshot to VM.")
            return False
    testflow.step(
        "Restore vm %s from snapshot %s",
        vm_name,
        virt_config.SNAPSHOT_DESCRIPTION[1]
    )
    if not ll_vms.restore_snapshot(
        True,
        vm=vm_name,
        description=virt_config.SNAPSHOT_DESCRIPTION[1],
        restore_memory=True,
        ensure_vm_down=True
    ):
        logger.error("Failed to restore snapshot.")
        return False
    testflow.step("Export vm %s with discarded snapshots", vm_name)
    if not ll_vms.exportVm(
        positive=True,
        vm=vm_name,
        storagedomain=export_domain,
        discard_snapshots='true',
        timeout=virt_config.VM_ACTION_TIMEOUT
    ):
        logger.error("Failed to export VM.")
        return False
    testflow.step(
        "Remove snapshots %s and %s of vm %s",
        virt_config.SNAPSHOT_DESCRIPTION[0],
        virt_config.SNAPSHOT_DESCRIPTION[1],
        vm_name
    )
    for snapshot in virt_config.SNAPSHOT_DESCRIPTION:
        if not ll_vms.removeSnapshot(
            positive=True,
            vm=vm_name,
            description=snapshot,
            timeout=config.VM_REMOVE_SNAPSHOT_TIMEOUT,
            wait=True
        ):
            logger.error("Failed to remove vm snapshot.")
            return False
    return True


def suspend_resume_vm(vm_name):
    """
    Suspend / Resume VM

    Args:
        vm_name (str): VM name
    """
    assert ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    )
    testflow.step("Suspend vm %s", vm_name)
    assert ll_vms.suspendVm(True, vm_name)
    testflow.step("Resume vm %s", vm_name)
    return ll_vms.startVm(
        positive=True,
        vm=vm_name,
        wait_for_status=config.VM_UP,
        wait_for_ip=False
    )


def wait_for_snapshot_jobs(vms_list, export_domain, with_memory=False):
    """
    Wait until all snapshot jobs finish and returns status

    Args:
        vms_list (list): vm names
        with_memory (bool): create/restore snapshot with memory
        export_domain (str): export domain name

    Returns:
        bool: True, if all snapshot jobs finish succeeded, otherwise False
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(vms_list)) as executor:
        for vm in vms_list:
            results.append(
                executor.submit(
                    test_vm_snapshots, vm, export_domain, with_memory
                )
            )
    for result in results:
        if not result.result():
            return False
    return True


def get_sysprep_configuration(
    os_type=config.WIN_OS_TYPE_DESKTOP,
    base_params=config.INIT_PARAMS,
    update_params=None
):
    """
    Update (replace/add) initialization params

    Args:
        os_type (str): Windows OS type (Desktop/Server)
        base_params (dict): Dict with initialization parameters
        update_params (dict): Dict with update parameters

    Returns:
        Dist: Dict with updated initialization parameters
    """
    if update_params is None:
        update_params = {}
    params = copy.deepcopy(base_params)
    if os_type is config.WIN_OS_TYPE_SERVER:
        params['root_password'] = config.WIN_PASSWORD
    params.update(update_params)
    return params


def check_syspreped_vm(
    vm_name,
    expected_values,
    os_type=config.WIN_OS_TYPE_DESKTOP
):
    """
    Checks the following:
     - users list as expect by os type
     - Initialization parameters set on VM (custom locale, host name,
     time zone)
     - Query DB if VM initialized flag set to True

    Args:
        vm_name (str): VM name
        expected_values (dict): Expected value set in test
        os_type (str): OS type (Desktop/Server)
    """

    failures = []
    vm_ip = hl_vms.get_vm_ip(vm_name=vm_name, start_vm=False)
    users_list = config.USER_LIST_BY_OS_TYPE[os_type]
    windows_vm = win_helper.WindowsGuest(
        ip=vm_ip, connectivity_check=True, user=users_list[0]
    )
    sys_info = windows_vm.get_system_info()
    actual_users_list = windows_vm.get_users_list()
    if not set(users_list).issubset(set(actual_users_list)):
        logger.error(
            "Not all users found, user list: %s OS type: %s",
            actual_users_list, os_type
        )
        failures.append(False)
    for key, expected_value in expected_values.iteritems():
        actual_value = sys_info[key]
        if expected_value not in actual_value:
            logger.error("%s is not set. found: %s ", key, actual_value)
            failures.append(False)
    initialized = is_vm_initialized(vm_name=vm_name)
    if not initialized:
        logger.error("VM is not set on DB with initialized flag")
        failures.append(False)
    logger.info("Windows vm check is done, status: %s", failures)
    return not any(failures)


def get_sysprep_template_file(windows_version):
    """
    Return sysprep file template from the engine configuration

    Args:
        windows_version (str): OS Type
    Returns:
         str: sysprep file content
    """
    file_path = '%s/%s' % (
        config.SYSPREP_FILE_ENG_PATH,
        config.WIN_OS_TO_SYSPREP_FILE[windows_version]
    )
    return config.ENGINE_HOST.run_command(command=['cat', file_path])[1]


def get_query_results(sql_query):
    """
    Query Engine DB and return output

    Args:
        sql_query (str): SQL query

    Returns:
        str: sql query results
    """
    return config.ENGINE.db.psql(sql=sql_query)


def init_sysprep_file(
    windows_version,
    os_type=config.WIN_OS_TYPE_DESKTOP,
    system_data=config.SYSPREP_FILE_VALUES
):
    """
    Replace all $parameters_name$ at sysprep file with  configuration values

    Args:
        windows_version (str): Windows version like windows 10 64B
        os_type (str): OS type (Desktop/Server)
        system_data (dict): dict with parameter name to value
        (parameter name must be as configure in sysprep template file)

    Returns:
        str: Updated sysperp file
    """
    file_content = get_sysprep_template_file(windows_version=windows_version)
    if os_type is config.WIN_OS_TYPE_SERVER:
        system_data['AdminPassword'] = config.WIN_PASSWORD
    for k, v in system_data.items():
        file_content = file_content.replace('${0}$'.format(k), v)
    return file_content


def is_vm_initialized(vm_name):
    """
    Query DB is vm initialized, to check if VM run for one time

    Args:
        vm_name (str): vm name

    Return:
        bool: True if vm initialized (meaning run onr time),Else False
    """
    query = "%s%s';" % (config.IS_VM_INITIALIZED_QUREY, vm_name)
    results = get_query_results(sql_query=query)
    logger.info("Qurey result:%s", results)
    return results[0][0] == 't'


def make_template_from_sealed_vm(vm_name):
    """
    Create template from sealed vm

    Args:
        vm_name (str): vm name
    """
    template_name = config.WINDOWS_SEAL_VM_TO_TEMPLATES[vm_name]
    return ll_templates.createTemplate(
        True, vm=vm_name, name=template_name,
        cluster=config.CLUSTER_NAME[0]
    )


def get_windows_templates(vms=config.WINDOWS_VM_NAMES):
    """
    Returns windows template names according to vm name.

    Args:
        vms (list): Windows vm name

    Return:
        list: List of  templates name
    """
    template_names = []
    vm_to_templates_names = {
        config.WINDOWS_10: config.WINDOWS_10_TEMPLATE,
        config.WINDOWS_7: config.WINDOWS_7_TEMPLATE,
        config.WINDOWS_2012: config.WINDOWS_2012_TEMPLATE
    }
    for vm_name in vms:
        template_names.append(vm_to_templates_names[vm_name])
    return template_names


def create_and_start_windows_vm(template_names, vms_names, start_vm=True):
    """
    Create windows vms from templates and start them on demand

    Args:
        template_names (list): templates names
        vms_names (list): vms names list
        start_vm (bool): start VM
    """
    testflow.setup("Create Windows VMS %s", vms_names)
    for vm_name, template_name in zip(
        vms_names, template_names
    ):
        assert virt_helper.create_vm_from_template(
            vm_name=vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=template_name,
            vm_parameters=config.VM_PARAMETERS[vm_name]
        )
        testflow.setup("update disk interface to IDE and bootable")
        first_disk_id = ll_disks.getObjDisks(
            name=vm_name, get_href=False
        )[0].id
        assert ll_disks.updateDisk(
            positive=True,
            vmName=vm_name,
            id=first_disk_id,
            bootable=True,
            interface=config.INTERFACE_IDE
        )
        if not ll_vms.get_vm_nics_obj(vm_name):
            testflow.setup("Add nic to VM %s", vm_name)
            assert ll_vms.addNic(
                positive=True,
                vm=vm_name,
                name=config.NIC_NAME[0],
                network=config.MGMT_BRIDGE
            )
        if start_vm:
            testflow.setup("Start VM: %s", vm_name)
            assert ll_vms.startVm(positive=True, vm=vm_name)
