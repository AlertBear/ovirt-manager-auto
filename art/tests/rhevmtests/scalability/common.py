import logging
import Queue
import threading
from copy import deepcopy
import time

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.utils.test_utils import toggleServiceOnHost
import config

LOGGER = logging.getLogger(__name__)
GB = 1024 * 1024 * 1024
ENUMS = config.ENUMS


def create_vm(vm_name, sd_name, template_name=config.TEMPLATE_NAME,
              is_install=False, res_queue=None):
    """
        Create VM with option to perform it asynchronously
        Parameters:
            * sd_name - storage doamin name
            * template_name - vm template name
            * is_install - to install vm or not
            * res_queue - queue to save result in
    """
    LOGGER.info("Creating VM %s from template %s", vm_name, template_name)
    try:
        res = vms.createVm(
            True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
            nic=config.HOST_NICS[0], storageDomainName=sd_name,
            size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
            volumeType=True, volumeFormat=ENUMS['format_cow'],
            diskInterface=config.INTERFACE_VIRTIO, template=template_name,
            memory=GB, cpu_socket=config.CPU_SOCKET,
            cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
            user=config.VM_LINUX_USER, password=config.VM_LINUX_PASSWORD,
            type=config.VM_TYPE_DESKTOP, installation=is_install, slim=True,
            cobblerAddress=config.COBBLER_ADDRESS,
            cobblerUser=config.COBBLER_USER,
            cobblerPasswd=config.COBBLER_PASSWORD,
            image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
            useAgent=config.USE_AGENT, start='true', attempt=10)
    except Exception as ex:
        LOGGER.error("Caught exception creating VM %s: %s", vm_name, ex)
        res = False
    if res_queue:
        res_queue.put((vm_name, res))


def create_fake_host(vm_name, res_queue=None):
    """
        Create fake host with option to perform it asynchronously
        Parameters:
            * vm_name - vm name
            * res_queue - queue to save result in
    """
    fake_host_name = 'host_%s' % vm_name
    try:
        ip = vms.waitForIP(vm_name)[-1]['ip']
        LOGGER.info("Creating fake host %s, ip = %s", fake_host_name, ip)
        res = hosts.addHost(
            True,
            fake_host_name,
            root_password=config.VM_LINUX_PASSWORD,
            address=ip,
            cluster=config.FAKE_CLUSTER_NAME
        )
    except Exception as ex:
        LOGGER.error("Caught exception adding fake host %s: %s",
                     fake_host_name, ex)
        res = False
    if res_queue:
        res_queue.put((vm_name, res))


def remove_fake_host(fake_host_name, res_queue=None):
    """
        Remove fake host with option to perform it asynchronously
        Parameters:
            * fake_host_name - fake host name
            * res_queue - queue to save result in
    """
    try:
        hosts.HOST_API.find(fake_host_name)
    except hosts.EntityNotFound:
        LOGGER.warning("fake host %s is not found", fake_host_name)
        res = False
    else:
        res = hosts.deactivateHost(True, fake_host_name)
        res = hosts.removeHost(True, fake_host_name) and res
    if res_queue:
        res_queue.put((fake_host_name, res))


def run_concurrent(target, param_list):
    """
        Run target function concurrently for each set of parameters
        Parameters:
            * target - target function
            * param_list - function parameters
    """
    threads = set()
    i = 0
    for param_set in param_list:
        thr = threading.Thread(target=target, name='%s%s' % (target, i),
                               args=param_set)
        threads.add(thr)
        thr.start()
        i += 1

    for thr in threads:
        thr.join()


def create_vms(vm_names, template_name=config.TEMPLATE_NAME,
               is_install=False):
    """
        Create number of VMs concurrently
        Parameters:
            * vm_names - list of vm names
            * template_name - vm template name
            * is_install - to install vm or not
    """
    sd_name = None
    for sd in storagedomains.getDCStorages(config.DATA_CENTER_NAME, False):
        if sd.get_master():
            sd_name = sd.name
            break

    vm_names_ = deepcopy(vm_names)
    vm_cnt = len(vm_names_)
    LOGGER.info("Creating %s VMs on storage domain %s", vm_cnt, sd_name)
    status = True
    while vm_names_:
        thr_cnt = config.MAX_WORKERS
        if thr_cnt < config.MAX_WORKERS:
            thr_cnt = vm_cnt
        res_queue = Queue.Queue()
        param_list = [(vm_name, sd_name, template_name, is_install, res_queue)
                      for vm_name in vm_names_[:thr_cnt]]
        run_concurrent(create_vm, param_list)

        while not res_queue.empty():
            vm_name, res = res_queue.get()
            if not res:
                LOGGER.error("Failed to create VM %s" % vm_name)
                status = status and False
            vm_names_.remove(vm_name)

        vm_cnt = len(vm_names_)

    return status


def create_fake_hosts(vm_names):
    """
        Create number of fake hosts concurrently
        Parameters:
            * vm_names - list of vm names
    """
    LOGGER.info("Creating fake hosts")
    status = True
    vm_names_ = deepcopy(vm_names)

    while(vm_names_):
        thr_cnt = config.MAX_WORKERS if \
            len(vm_names_) >= config.MAX_WORKERS else len(vm_names_)
        res_queue = Queue.Queue()
        param_list = [(vm_name, res_queue)
                      for vm_name in vm_names_[:thr_cnt]]
        run_concurrent(create_fake_host, param_list)

        while not res_queue.empty():
            name, res = res_queue.get()
            if not res:
                LOGGER.error("Failed to create fake host %s" % name)
                status = status and False
            vm_names_.remove(name)

    return status


def remove_fake_hosts(fake_host_names):
    """
        Remove number of fake hosts concurrently
        Parameters:
            * fake_host_names - list of fake host names
    """
    LOGGER.info("Removing fake hosts")
    status = True

    while(fake_host_names):
        thr_cnt = config.MAX_WORKERS if \
            len(fake_host_names) >= config.MAX_WORKERS else \
            len(fake_host_names)
        res_queue = Queue.Queue()
        param_list = [(h_name, res_queue)
                      for h_name in fake_host_names[:thr_cnt]]
        run_concurrent(remove_fake_host, param_list)

        while not res_queue.empty():
            name, res = res_queue.get()
            if not res:
                LOGGER.error("Failed to remove fake host %s" % name)
                status = status and False
            fake_host_names.remove(name)

    return status


def toggle_dwh_service(action='start'):
    """
        Start/stop rhevm reporting process
        Parameters:
            * action - service action to perform
    """
    status = toggleServiceOnHost(
        True, host=config.VDC, user='root',
        password=config.VDC_PASSWORD, service=config.DWH_SERVICE,
        action=action)
    if action == 'start':
        time.sleep(int(config.DWH_WAIT))
    assert(status)
