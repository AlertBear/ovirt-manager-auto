"""
Help to create storage for HE tests
"""
import logging
import config as conf
import art.test_handler.exceptions as errors
import storageapi.storageErrors as strg_errors
from storageapi.storageManagerWrapper import StorageManagerWrapper

logger = logging.getLogger(__name__)


class StorageForHostedEngine(object):
    """
    Base class to create storage for HE deployment
    """
    storage_type = None

    def __init__(self, storage_config, **kwargs):
        """
        Initiate new StorageForHostedEngine class

        :param storage_config: storage configuration
        :type storage_config: dict
        """
        self.storage_config = storage_config
        logger.debug("Create storage manager with parameters: %s", kwargs)
        self.manager = self._get_manager(**kwargs)
        self.name = "hosted_engine_automation"

    def _get_manager(self, **kwargs):
        """
        Get storage manager of specific type

        :returns: correct manager for storage
        """
        storage_server = "%s_server" % self.storage_type
        return StorageManagerWrapper(
            self.storage_config.get(storage_server),
            self.storage_type,
            self.storage_config["storage_conf"],
            **kwargs
        ).manager

    def create_storage(self):
        raise NotImplementedError("Please implement this method")

    def clean_storage(self):
        raise NotImplementedError("Please implement this method")


class FileStorageForHostedEngine(StorageForHostedEngine):
    """
    Base class for all file storages
    """

    def __init__(self, storage_config, **kwargs):
        """
        Initiate new FileStorageForHostedEngine class

        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(FileStorageForHostedEngine, self).__init__(
            storage_config=storage_config, **kwargs
        )
        self.volume_dir = None
        self.volume_path = None

    def create_storage(self):
        """
        Create file storage

        :raise: HostedEngineException
        """

        fs_server = self.storage_config.get(
            "%s_server" % self.storage_type
        )
        logger.info(
            "Create %s storage %s on server %s",
            self.storage_type, self.name, fs_server
        )
        try:
            self.volume_dir = self.manager.createDevice(self.name)
        except strg_errors.StorageAPIGeneralException as err:
            raise errors.HostedEngineException(str(err))
        self.volume_path = "%s:%s" % (fs_server,  self.volume_dir)
        logger.info(
            "%s Storage path is: %s", self.storage_type, self.volume_path
        )

    def clean_storage(self):
        """
        Remove file storage

        :raise: HostedEngineException
        """
        if self.volume_dir:
            try:
                fs_server = self.storage_config.get(
                    "%s_server" % self.storage_type
                )
                logger.info(
                    "Remove %s storage %s from server %s",
                    self.storage_type, self.name, fs_server
                )
                self.manager.removeDevice(self.volume_dir)
            except strg_errors.StorageAPIGeneralException as err:
                raise errors.HostedEngineException(str(err))


class NFSStorage(FileStorageForHostedEngine):
    """
    NFS storage class for hosted engine deployment
    """
    storage_type = "nfs"

    def __init__(self, storage_config):
        """
        Initiate new NFSStorage class

        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(NFSStorage, self).__init__(
            storage_config,
            vol_nfs=storage_config.get("vol_nfs", conf.DEFAULT_VOL_NFS)
        )


class GlusterStorage(FileStorageForHostedEngine):
    """
    Gluster storage class for hosted engine deployment
    """
    storage_type = "gluster"

    def __init__(self, storage_config):
        """
        Initiate new GlusterStorage class

        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(GlusterStorage, self).__init__(
            storage_config,
            replica=storage_config["gluster_replica"],
            hosts_list=storage_config["gluster_hosts_list"]
        )


class ISCSIStorage(StorageForHostedEngine):
    """
    Create ISCSI storage for hosted engine deployment
    """
    storage_type = "iscsi"

    def __init__(self, storage_config):
        """
        Initiate new ISCSIStorage class

        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(ISCSIStorage, self).__init__(storage_config)
        self.hosts_initiators = []
        self.lun_id = None
        self.target_name = None

    @classmethod
    def _get_host_initiator(cls, vds_resource):
        """
        Get iscsi initiator from host

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :returns: host iscsi initiator
        :rtype: str
        :raise: HostedEngineException
        """
        rc, out, _ = vds_resource.run_command(
            command=["cat", conf.ISCSI_INITIATOR_FILE]
        )
        if rc:
            raise errors.HostedEngineException(
                "Failed to get initiator from host %s" % vds_resource.fqdn
            )
        return out.split("=")[1].strip("\n\r")

    def _re_add_initiator(self, host_initiator):
        """
        Remove initiator from old host group and add to new one

        :param host_initiator: host initiator
        :type host_initiator: str
        """
        try:
            old_hg = self.manager.getInitiatorHostGroups(host_initiator)
            if old_hg:
                if old_hg != self.name:
                    logger.info(
                        "Initiator is %s already exist in hostgroup %s",
                        host_initiator, old_hg
                    )
                    logger.info(
                        "Remove initiator %s from old hostgroup %s",
                        host_initiator, old_hg
                    )
                else:
                    return
            logger.info(
                "Add initiator %s to new host group %s",
                host_initiator, self.name
            )
            self.manager.mapInitiators(self.name, host_initiator)
        except strg_errors.StorageAPIGeneralException as err:
            raise errors.HostedEngineException(str(err))

    def create_storage(self):
        """
        Create LUN on iscsi storage

        :raise: HostedEngineException
        """
        try:
            logger.info(
                "Create iscsi lun %s on server %s",
                self.name, self.storage_config.get("iscsi_server")
            )
            self.lun_id, self.target_name = self.manager.createLun(
                name=self.name, size=conf.HOSTED_ENGINE_DISK_SIZE
            )
            logger.info(
                "Lun and Target Name of ISCSI storage: %s, %s",
                self.lun_id, self.target_name
            )
            logger.info("Map host group %s to lun %s", self.name, self.lun_id)
            self.manager.mapLunToHostGroup(
                name=self.name, lunGuid=self.lun_id
            )
        except strg_errors.StorageAPIGeneralException as err:
            raise errors.HostedEngineException(str(err))

    def add_host_to_hostgroup(self, vds_resource):
        """
        Add host initiator to hostgroup

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :raise: HostedEngineException
        """
        host_initiator = self._get_host_initiator(vds_resource)
        self.hosts_initiators.append(host_initiator)
        self._re_add_initiator(host_initiator)

    def clean_storage(self):
        """
        1) Unmap host from hostgroup
        2) Unmap hostgroup from lun
        3) Remove lun

        :raise: HostedEngineException
        """
        if self.lun_id:
            try:
                for initiator in self.hosts_initiators:
                    logger.info(
                        "Remove initiator %s from host group %s",
                        initiator, self.name
                    )
                    self.manager.unmapInitiator(
                        self.name, initiator
                    )
                self.manager.unmapLun(
                    self.lun_id, self.name
                )
                lun_serial = self.manager.getLun(self.lun_id)["serial"]
                self.manager.removeLun(lun_serial)
            except strg_errors.StorageAPIGeneralException as err:
                raise errors.HostedEngineException(str(err))
