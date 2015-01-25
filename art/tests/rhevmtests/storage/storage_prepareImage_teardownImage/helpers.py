"""
3.5 Feature: Helper module for prepareImage and teardownImage
"""
from art.rhevm_api.tests_lib.low_level import hosts
from utilities.machine import Machine
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost
import config


def host_to_use():
    """
    Extract the SPM host for use with prepareImage and teardownImage.
    The commands executed by these commands only take affect on the host from
    which they are run

    __author__ = "glazarov"
    :returns: Machine object on which commands can be executed
    :rtype: Machine
    """
    host = getSPMHost(config.HOSTS)
    host = hosts.getHostIP(host)
    return Machine(host=host, user=config.HOSTS_USER,
                   password=config.HOSTS_PW).util('linux')


def get_spuuid(dc_obj):
    """
    Returns the Storage Pool UUID of the provided Data center object

    __author__ = "glazarov"
    :param: Data center object
    :type: object
    :returns: Storage Pool UUID
    :rtype: str
    """
    return dc_obj.get_id()


def get_sduuid(disk_object):
    """
    Returns the Storage Domain UUID using the provided disk object.  Note
    that this assumes the disk only has one storage domain (i.e. in the case of
    a template with a disk copy or a vm created from such as template,
    the first instance will be returned which may either be the original
    disk or its copy)

    __author__ = "glazarov"
    :param: disk object from which the Storage Domain ID will be
    :type: Disk from disks collection
    :returns: Storage Domain UUID
    :rtype: str
    """
    return disk_object.get_storage_domains().get_storage_domain()[0].get_id()


def get_imguuid(disk_object):
    """
    Returns the imgUUID using the provided disk object

    __author__ = "glazarov"
    :param: disk object from which the Image ID will be retrieved
    :type: Disk from disks collection
    :returns: Image UUID
    :rtype: str
    """
    return disk_object.get_id()


def get_voluuid(disk_object):
    """
    Returns the volUUID using the provided disk object

    __author__ = "glazarov"
    :param: disk_object from which to retrieve the Volume ID
    :type: Disk from disks collection
    :returns: Volume UUID
    :rtype: str
    """
    return disk_object.get_image_id()
