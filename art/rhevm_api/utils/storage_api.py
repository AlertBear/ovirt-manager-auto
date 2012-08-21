"""
A collection of wrappers which allow the usage of general utils functions and storage API in the REST framework.
"""
import logging

import storageManagement.storageManagerWrapper as sm
import utilities.utils as utils
import utilities.VDS4 as vds4
import utilities.machine as hostUtil
import utilities.storage_utils as st_util
from utilities.host_utils import VdsLinuxMachine
from art.core_api import is_action

log = logging.getLogger("storage_api")


def setupIptables(source, userName, password, dest, command, chain, \
                  target, protocol='all', persistently=False, *ports):
    """Wrapper for utilities.machine.setupIptables() method."""
    hostObj = hostUtil.Machine(source, userName, password).util('linux')
    return hostObj.setupIptables(dest, command, chain, target, \
                                 protocol, persistently, *ports)

@is_action('blockConnection')
def blockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Blocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to prevent traffic
      * port - outgoing port we wanna block
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
         return setupIptables(source, userName, password, dest, '--append',
                       'OUTPUT', 'DROP')
    else:
         return setupIptables(source, userName, password, dest, '--append',
                              'OUTPUT', 'DROP', 'all', False, port)


@is_action('unblockConnection')
def unblockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Unblocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to remove traffic block
      * port - outgoing port we wanna unblock
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
        return setupIptables(source, userName, password, dest, '--delete',
                             'OUTPUT', 'DROP')
    else:
        return setupIptables(source, userName, password, dest,'--delete',
                             'OUTPUT', 'DROP', 'all', False, port)

def blockIncomingConnection(source, userName, password, dest):
    """Warpper for blocking incoming connection from any server to host."""
    return setupIptables(source, userName, password, dest, \
                         '--append', 'INPUT', 'DROP')


def unblockIncomingConnection(source, userName, password, dest):
    """Warpper for unblocking incoming connection from any server to host."""
    return setupIptables(source, userName, password, dest, \
                         '--delete', 'INPUT', 'DROP')


def flushIptables(host, userName, password, chain='', persistently=False):
    """Warpper for utilities.machine.flushIptables() method."""
    hostObj = hostUtil.Machine(host, userName, password).util('linux')
    return hostObj.flushIptables(chain, persistently)

@is_action()
def getStorageManager(ip, storageType):
    """
        Wrapper for retrieving an instance of any sub-class
        of utilities.storageManagement.StorageManager base class.
        Author: mbenenso
        Parameters:
         * ip - IP address of storage server
         * storageType - storage protocol type
        Return: True and dictionary with instance of StorageManager class on success,
                (False, {'mgr': None}) otherwise
    """
    retDict = {'mgr': None}
    retDict['mgr'] = sm.StorageManagerWrapper(ip, storageType).manager

    return (retDict['mgr'] is not None), retDict


@is_action()
def createLuns(mgr, name, size, sparse=True, cnt=1, \
               addToExisting=False, targetName=None):
    """
        Create LUN storage.
        Author: mbenenso
        Parameters:
         * mgr - concrete storage manager instance
         * name - logical name (setup name)
         * size - LUN size in GB
         * sparse - thin provision by default (preallocated if False)
         * cnt - amount of LUNs to create (1 by default)
         * addToExisting - create LUN and attach to existing target (False by default)
         * targetName - optional name for the target (None by default)
        Return: True and LUN details dictionary on successful LUN creation,
                (False, an empty dictionary) otherwise
    """
    keys = ('lunId', 'targetName')
    if mgr is not None:
        lunId, tName = mgr.createLuns(name, size, sparse, cnt, \
                                      addToExisting, targetName)
        return True, dict(zip(keys, [lunId, tName]))

    return False, dict()


@is_action()
def mapLuns(mgr, lunGuids, name, *initiators):
    """
        Map LUN storages.
        Author: mbenenso
        Parameters:
         * mgr - concrete storage manager instance
         * lunGuids - list of LUN uuids
         * name - logical name (setup name)
         * *initiators - variable-length argument list of initiator iqns
                         in case of NetApp and OpenSolaris,
                         or list of IP addresses in case of Linux TGT
        Return: None
    """
    mgr.mapLuns(lunGuids, name, *initiators)


@is_action()
def unmapLuns(mgr, lunGuids, name, *initiators):
    """
        Unmap LUN storages.
        Author: mbenenso
        Parameters:
         * mgr - concrete storage manager instance
         * lunGuids - list of LUN uuids
         * name - logical name (setup name)
         * *initiators - variable-length argument list of initiator iqns
                         in case of NetApp and OpenSolaris,
                         or list of IP addresses in case of Linux TGT
        Return: None
    """
    mgr.unmapLuns(lunGuids, name, *initiators)


@is_action()
def removeLuns(mgr, lunGuids, force=True):
    """
        Remove LUN storages.
        Author: mbenenso
        Parameters:
         * mgr - concrete storage manager instance
         * lunGuids - list of LUN uuids
         * force - force removal (True by default)
        Return: None
    """
    mgr.removeLuns(lunGuids, force)


@is_action()
def sendTargets(initiator, user, password, portal, targetName, login=True):
    """
        SCSI send targets discovery. Login is optional.
        Author: egerman
        Parameters:
         * initiator - IP address or name of SCSI initiator host
         * user - user name
         * password - user password
         * portal - portal number
         * targetName - SCSI target name
         * login - login to target (True by default)
        Return: True if send targets discovery successful,
                False otherwise
    """
    hostObj = hostUtil.Machine(initiator, user, password).util('linux')
    rc, targets = hostObj.sendTargetsDiscovery(portal)
    if rc and login:
        return hostObj.loginTarget(portal, targetName)

    return False


@is_action()
def logoutTargets(initiator, user, password):
    """
        Logout SCSI targets.
        Author: egerman
        Parameters:
         * initiator - IP address or name of SCSI initiator host
         * user - user name
         * password - user password
        Return: True if logout targets successful,
                False otherwise
    """
    hostObj = hostUtil.Machine(initiator, user, password).util('linux')
    return hostObj.logoutTargets()


def sleep(seconds):
    """
        Suspend execution for the given number of seconds.
        Author: egerman
        Parameters:
         * seconds - time to sleep in seconds
        Return: True
    """
    utils.sleep(seconds)
    return True


@is_action()
def getDeviceList(vds_name, user, passwd):
    """
        Retrieve list of storage devices.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
        Return: status and a list of storage devices within a dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    devices_list = vds_obj.getDeviceList()

    return bool(devices_list), {'devices_list': devices_list}


@is_action()
def getStorageDomainsList(vds_name, user, passwd):
    """
        Retrieve list of storage domains.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
        Return: status and a list of storage domain uuids within a dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    sd_uuids_list = vds_obj.getPoolDomains()

    return bool(sd_uuids_list), {'sd_uuids_list': sd_uuids_list}


@is_action()
def getStorageDomainInfo(vds_name, user, passwd, sp_uuid, option='none'):
    """
        Retrieve storage domain info.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
        Return: status and storage domain related info within a dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    sd_info = vds_obj.getStorageDomainInfo(sp_uuid, option)

    return bool(sd_info), {'sd_info': sd_info}


@is_action()
def generateSDMetadataCorruption(vds_name, username, passwd, sd_name, \
                                 md_backup_path=None, md_tag="MDT_TYPE", \
                                 md_tag_bad_value=st_util.CORRUPTION_STRING, \
                                 bs=st_util.BS, count=st_util.COUNT):
    """
        Generate metadata corruption on storage domain.
        Author: mbenenso
        Parameters:
         * vds_name - VDS name
         * username - user name
         * passwd - user password
         * sd_name - storage domain name
         * md_backup_path - full metadata backup path
         * md_tag - metadata tag ("TYPE" by default)
         * md_tag_bad_value - new value for md_tag (corruption_string by default)
         * bs - block size (1024 by default)
         * count - number of blocks (1 by default)
        Return: True and dictionary with storage domain object with all \
                relevant info on success, raise exception otherwise
        Throws: ValueError, st_util.SDMetadataError
    """
    sd_obj = None
    sd_info = {}
    obj = st_util.SD(vds_name, username, passwd)
    uuid = obj.getSDUuidByName(sd_name)
    if uuid is None:
        msg = "domain {0} doesn't exist or has corrupted metadata"
        raise st_util.SDMetadataError(msg.format(sd_name))

    sd_info = obj.vdsObj.getStorageDomainInfo(uuid)
    if sd_info['type'] == st_util.ST_TYPE['ISCSI']:
        sd_obj = st_util.BlockSD(vds_name, username, passwd, sd_info)
    elif sd_info['type'] == st_util.ST_TYPE['NFS']:
        sd_obj = st_util.FileSD(vds_name, username, passwd, sd_info)
    else:
        msg = "unsupported storage domain type: {0}."
        raise ValueError(msg.format(sd_info['type']))

    sd_info = sd_obj.generateMDCorruption(md_backup_path, md_tag, \
                                          md_tag_bad_value, bs, count)
    if not sd_info:
        msg = "failed to corrupt metadata of storage domain {0} with uuid {1}"
        raise st_util.SDMetadataError(msg.format(sd_name, uuid))

    return True, {'sd_obj': sd_obj}


@is_action()
def restoreSDOriginalMetadata(sd_obj):
    """
        Restore the original metadata of storage domain.
        Author: mbenenso
        Parameters:
         * sd_obj - an instance of a sub-class of st_util.SD class
        Return: True if the metadata successfully restored,
                False otherwise
    """
    return sd_obj.restoreMetadata()


@is_action()
def getVolumeInfo(vds_name, user, passwd, dc_uuid, sd_uuid, image_uuid, volume_uuid):
    """
        Retrieve volume info.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
         * dc_uuid - data center uuid
         * sd_uuid - storage domain uuid
         * image_uuid - image uuid
         * volume_uuid - volume uuid
        Return: volume related info dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    args = [sd_uuid, dc_uuid, image_uuid, volume_uuid]
    status, vol_info = vds_obj.getVolumeInfo(args)   # status 0 implies True

    if not status:
        return vol_info

    return {}


@is_action()
def getImagesList(vds_name, user, passwd, sd_uuid):
    """
        Retrieve images list.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
         * sd_uuid - storage domain uuid
        Return: images list dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    return vds_obj.getImagesList(sd_uuid)


@is_action()
def getVmsInfo(vds_name, user, passwd, dc_uuid, sd_uuid):
    """
        Retrieve VMs info.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
         * dc_uuid - data center uuid
         * sd_uuid - storage domain uuid
        Return: VMs related info dictionary
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    return vds_obj.getVmsInfo(dc_uuid, sd_uuid)


@is_action()
def spmStart(positive, vds_name, user, passwd, sp_uuid, prev_id=-1, prev_lver=-1, \
             recovery_mode=0, scsi_fencing='False', max_host_id=0, version=2):
    """
        Start SPM on VDS host.
        Author: egerman
        Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
         * sp_uuid - storage pool uuid
         * prev_id - previous ID of the host (-1 by default)
         * prev_lver - previous lver of the host (-1 by default)
         * recovery_mode - recovery mode (0 by default)
         * scsi_fencing - scsi fencing (False by default)
         * max_host_id - max host id (0 by default)
         * version - version (2 by default)
        Return: True if SPM started successfully on host,
                False otherwise
    """
    vds_obj = VdsLinuxMachine(vds_name, user, passwd).vdsObj
    res = vds_obj.startSpm(sp_uuid, prev_id, prev_lver, \
                          recovery_mode, scsi_fencing, max_host_id, version)
    return not positive ^ res


def getVolumesList(vds_name, user, passwd, dc_uuid, sd_uuid, images):
    """
    Description: gets list of volumes on given domain
    Author: jlibosva
    Parameters:
         * vds_name - IP address or name of VDS host
         * user - user name
         * password - user password
         * dc_uuid - data center uuid
         * sd_uuid - storage domain uuid
         * images - list of images' uuid
    Return: List of volumes id
    """
    vds = vds4.VDS(vds_name, account=(user, passwd))
    return vds.getVolumesList(sd_uuid, dc_uuid, images)


