#! /usr/bin/python
# -*- coding: utf-8 -*-

import logging
import shlex
from art.rhevm_api.data_struct import data_structures as data_struct
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import rhevmtests.helpers as helpers
import config

NIC_CONFIGURATION = data_struct.NicConfiguration(
    name=config.CLOUD_INIT_NIC_NAME, ip=None, boot_protocol='dhcp',
    on_boot=True
)
SCRIPT_CONTENT = "test_cloud_init"
CUSTOM_SCRIPT = (
    "write_files:\n"
    "-  content: %s\n"
    "   path: /tmp/test.txt\n"
    "   permissions: '0644'"
) % SCRIPT_CONTENT

# base initialization parameters
initialization_params = {
    'host_name': config.CLOUD_INIT_HOST_NAME,
    'root_password': config.VDC_ROOT_PASSWORD,
    'user_name': config.VM_USER_CLOUD_INIT,
    'timezone': config.NEW_ZEALAND_TZ,
    'dns_servers': config.DNS_SERVER,
    'dns_search': config.DNS_SEARCH,
    'nic_configurations': data_struct.NicConfigurations(
        nic_configuration=[NIC_CONFIGURATION]
    ),
    'custom_script': CUSTOM_SCRIPT
}

# use in update test
updated_initialization_params = {
    'host_name': config.CLOUD_INIT_HOST_NAME,
    'root_password': config.VDC_ROOT_PASSWORD,
    'user_name': config.VM_USER_CLOUD_INIT,
    'timezone': config.MEXICO_TZ,
    'dns_servers': config.DNS_SERVER,
    'dns_search': config.DNS_SEARCH,
    'nic_configurations': data_struct.NicConfigurations(
        nic_configuration=[NIC_CONFIGURATION]
    ),
    'custom_script': CUSTOM_SCRIPT
}

logger = logging.getLogger("cloud_init_helper")


def check_data_on_vm(command_to_run, expected_output):
    """
    Check configure data on VM. Runs command on VM and compare it with
    expected output

    :param command_to_run: command to run on vm
    :type command_to_run: str
    :param expected_output: the expected value
    :type expected_output: str
    :return: True if output as expected else False
    :rtype bool
    """
    if config.VM_USER_CLOUD_INIT is config.VDC_ROOT_USER:
        logger.info("connect with root user")
        executor = helpers.get_host_executor(
            ip=config.VM_IP, password=config.VDC_ROOT_PASSWORD
        )
    elif config.USER_PKEY:
        logger.info(
            "connect without password, user: %s", config.VM_USER_CLOUD_INIT
        )
        host = helpers.Host(ip=config.VM_IP)
        host.users.append(config.VM_USER_CLOUD_INIT)
        user_root = helpers.User(
            name=config.VDC_ROOT_USER,
            password=config.VDC_ROOT_PASSWORD
        )
        executor = host.executor(
            user=user_root, pkey=True
        )
    else:
        logger.info("connect with user %s", config.VM_USER_CLOUD_INIT)
        executor = helpers.get_host_executor(
            ip=config.VM_IP,
            username=config.VM_USER_CLOUD_INIT,
            password=config.VDC_ROOT_PASSWORD
        )
    logger.info("Run command: %s", command_to_run)
    rc, out, err = executor.run_cmd(shlex.split(command_to_run))
    logger.info("output: %s", out)
    return expected_output in out


def check_cloud_init_parameters(
    dns_search=None, dns_servers=None, time_zone=None, script_content=None,
    hostname=None, check_nic=True
):
    """
    Checks cloud init parameters on VM

    :param dns_search: DNS search configured
    :type dns_search: str
    :param dns_servers:  DNS server/s configured
    :type dns_servers: str
    :param time_zone: list of possible time zones configured
    :type time_zone: list
    :param script_content: file content configured by script
    :type script_content: str
    :param hostname: configured hostname
    :type hostname: str
    :param check_nic: check nic configuration
    :type check_nic: bool
    :return: True if all checks pass Else
    :rtype: bool
    """
    logger.info('Get ip for VM: %s', config.CLOUD_INIT_VM_NAME)
    config.VM_IP = hl_vms.get_vm_ip(
        vm_name=config.CLOUD_INIT_VM_NAME, start_vm=False
    )
    logger.info('VM: %s , IP:%s', config.CLOUD_INIT_VM_NAME, config.VM_IP)
    network_status = check_networks_configuration(
        check_nic, dns_search, dns_servers
    )
    authentication_status = check_authentication_configuration()
    script_status = check_custom_script(script_content)
    general_status = check_general(time_zone, hostname)
    if (
        network_status and
        authentication_status and
        script_status and
        general_status
    ):
        return True
    else:
        logger.error("The guest check failed")
        return False


def check_general(time_zone=None, hostname=None):
    """
    Check general data on VM

    :param time_zone: list of possible Time zone on guest
    (Daylight vs Standard) e.g. NZST and NZDT
    :type time_zone: list
    :param hostname: configured hostname
    :type hostname: str
    :return: True if general parameters are as expected else False
    :rtype bool
    """
    status = True
    if time_zone:
        for tz in time_zone:
            logger.info("Check time zone, expected: %s", tz)
            if check_data_on_vm(config.CHECK_TIME_ZONE_IN_GUEST, tz):
                logger.info("time zone check pass")
                status = True
                break
            else:
                logger.error("time zone check failed")
                status = False
    if hostname:
        logger.info("Check hostname, expected: %s", hostname)
        if check_data_on_vm(config.CHECK_HOST_NAME, hostname):
            logger.info("hostname check pass")
        else:
            logger.error("hostname check failed")
            status = False
    return status


def check_custom_script(script_content):
    """
    Check custom script content

    :param script_content: expected script content
    :type script_content: str
    :return: True if content on guest equals to expected content
    :rtype bool
    """

    if script_content:
        logger.info("Check script content, expected: %s", script_content)
        if check_data_on_vm(config.CHECK_FILE_CONTENT, script_content):
            logger.info("script content check pass")
            return True
        else:
            logger.error("script content check failed")
            return False
    else:
        return True


def check_authentication_configuration():
    """
    Check user authentication

    :return: True if user name matches the user name on guest else False
    :rtype: bool
    """
    logger.info("Check user name, expected: %s", config.VM_USER_CLOUD_INIT)
    cmd = config.CHECK_USER_IN_GUEST % config.VM_USER_CLOUD_INIT
    if check_data_on_vm(cmd, config.VM_USER_CLOUD_INIT):
        logger.info("user name check pass")
        return True
    else:
        logger.error("user name check failed")
        return False


def check_networks_configuration(
    check_nic=False, dns_search=None, dns_servers=None
):
    """
    Check networks configuration, first check that NIC exists

    :param check_nic: check nic configuration
    :type check_nic: bool
    :param dns_search: DNS search configured
    :type dns_search: str
    :param dns_servers: DNS server/s configured
    :type dns_servers: str
    :return: True if networks check pass else False
    :rtype: bool
    """
    status = True
    if check_nic:
        logger.info("Check the NIC file name exists")
        cmd = config.CHECK_NIC_EXIST
        if check_data_on_vm(cmd, config.CLOUD_INIT_NIC_NAME):
            logger.info("NIC file name exist")
        else:
            logger.error("NIC file name doesn't exist")
            status = False
    if dns_search:
        logger.info("Check DNS search, expected: %s", dns_search)
        cmd = config.CHECK_DNS_IN_GUEST % dns_search
        if check_data_on_vm(cmd, dns_search):
            logger.info("DNS search check pass")
        else:
            logger.error("DNS search check failed")
            status = False
    if dns_servers:
        logger.info("Check DNS servers, expected: %s", dns_servers)
        cmd = config.CHECK_DNS_IN_GUEST % dns_servers
        if check_data_on_vm(cmd, dns_servers):
            logger.info("DNS servers check pass")
        else:
            logger.error("DNS servers check failed")
            status = False
    return status
