import art.test_handler.exceptions as exceptions

import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

import art.rhevm_api.tests_lib.high_level.hosts as hosts
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sd
import art.test_handler.exceptions as errors
import logging
import config

logger = logging.getLogger(__name__)


def add_storage_domain(datacenter_name, **domain):
    """
    Add and attach an storege domain to datacenter_name
    """
    if domain['storage_type'] == config.ISCSI_SD_TYPE:
        if not hl_sd._ISCSIdiscoverAndLogin(config.HOST,
                                            domain['lun_address'],
                                            domain['lun_target']):
            return False

    if not ll_sd.addStorageDomain(True, host=config.HOST, **domain):
        return False

    status = ll_sd.attachStorageDomain(
        True, datacenter_name, domain['name'], True)

    return status and ll_sd.activateStorageDomain(
        True, datacenter_name, domain['name'])


def build_environment(compatibility_version, storage_domains):
    """
    Build an environment
        * compatibility version: str with version
        * domains: list of dictionary with the storage domains parameters
    """
    datacenter_name = config.DATA_CENTER_NAME
    cluster_name = config.CLUSTER_NAME

    if not ll_dc.addDataCenter(True, name=datacenter_name,
                               local=False,
                               version=compatibility_version):
        raise errors.DataCenterException(
            "addDataCenter %s with version %s failed." %
            (datacenter_name, compatibility_version))

    if not ll_clusters.addCluster(True, name=cluster_name,
                                  cpu=config.PARAMETERS['cpu_name'],
                                  data_center=datacenter_name,
                                  version=compatibility_version):
        raise errors.ClusterException(
            "addCluster %s with version %s to datacenter %s failed" %
            (cluster_name, compatibility_version, datacenter_name))

    hosts.add_hosts(
        config.PARAMETERS.as_list('vds'),
        config.PARAMETERS.as_list('vds_password'),
        cluster_name)

    for domain in storage_domains:
        assert add_storage_domain(datacenter_name, **domain)


def add_disk_to_sd(disk_name, storagedomain, attach_to_vm=None):
    """
    Creates a disk in storage domain
        * disk_name: name of the disk
        * storagedomain : name of the storage domain
        * attach_to_vm: name to vm to attach if need it
    """
    logger.info('Creating disk %s on storage domain %s',
                disk_name, storagedomain)

    disk_args = {
        'alias': disk_name,
        'size': config.DISK_SIZE,
        'interface': config.INTERFACE_IDE,
        'format': config.DISK_FORMAT_COW,
        'sparse': True,
        'storagedomain': storagedomain,
    }

    if not ll_disks.addDisk(True, **disk_args):
        raise exceptions.DiskException('Unable to create disk %s' %
                                       disk_args['alias'])
    assert ll_disks.waitForDisksState([disk_name])

    start = False
    if attach_to_vm:
        # This is use to be able to know if the machine was up
        if ll_vms.get_vm_state(attach_to_vm) == config.ENUMS['vm_state_up']:
            ll_vms.stop_vms_safely([attach_to_vm])
            start = True

        assert ll_disks.attachDisk(True, disk_name, attach_to_vm)

        if start:
            assert ll_vms.startVm(
                True, attach_to_vm, config.VM_UP)


def create_and_start_vm(vm_name, sd_name, installation=True):
    """
    Creates a vm in a specific storage domain
        * vm_name: name of the vm
        * sd_name: name of the storage domain
        * installation: if an OS should be installted
    """
    logger.info("Creating vm %s on storage domain %s", vm_name, sd_name)

    vmArgs = {'positive': True,
              'vmName': vm_name,
              'vmDescription': vm_name,
              'diskInterface': config.VIRTIO,
              'volumeFormat': config.DISK_FORMAT_RAW,
              'cluster': config.CLUSTER_NAME,
              'storageDomainName': sd_name,
              'installation': installation,
              'size': config.DISK_SIZE,
              'nic': 'nic1',
              'cobblerAddress': config.COBBLER_ADDRESS,
              'cobblerUser': config.COBBLER_USER,
              'cobblerPasswd': config.COBBLER_PASSWD,
              'image': config.COBBLER_PROFILE,
              'useAgent': True,
              'os_type': config.ENUMS['rhel6'],
              'user': config.VM_USER,
              'password': config.VM_PASSWORD,
              'network': config.MGMT_BRIDGE,
              'volumeType': False,  # pre-allocated
              }

    if not ll_vms.createVm(**vmArgs):
        raise exceptions.VMException('Unable to create vm %s for test'
                                     % vm_name)
