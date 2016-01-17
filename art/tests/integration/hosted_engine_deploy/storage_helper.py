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
    def __init__(self, storage_type, storage_config, **kwargs):
        """
        Initiate new StorageForHostedEngine class

        :param storage_type: storage type
        :type storage_type: str
        :param storage_config: storage configuration
        :type storage_config: dict
        """
        self.he_storage_type = storage_type
        self.storage_config = storage_config
        logger.debug("Create storage manager with parameters: %s", kwargs)
        self.manager = self._get_manager(**kwargs)
        self.name = "hosted_engine_automation"

    def _get_manager(self, **kwargs):
        """
        Get storage manager of specific type

        :returns: correct manager for storage
        """
        storage_server = "%s_server" % self.he_storage_type
        return StorageManagerWrapper(
            self.storage_config.get(storage_server),
            self.he_storage_type,
            self.storage_config["storage_conf"],
            **kwargs
        ).manager

    def create_storage(self):
        raise NotImplementedError("Please implement this method")

    def clean_storage(self):
        raise NotImplementedError("Please implement this method")


class NFSStorage(StorageForHostedEngine):
    """
    NFS storage class for hosted engine deployment
    """

    def __init__(self, storage_type, storage_config):
        """
        Initiate new NFSStorage class

        :param storage_type: storage type
        :type storage_type: str
        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(NFSStorage, self).__init__(
            storage_type, storage_config,
            vol_nfs=storage_config.get("vol_nfs", conf.DEFAULT_VOL_NFS)
        )
        self.nfs_dir = None
        self.nfs_path = None

    def create_storage(self):
        """
        Create NFS storage

        :raise: HostedEngineException
        """

        nfs_server = self.storage_config.get("nfs_server")
        logger.info(
            "Create NFS directory %s on server %s", self.name, nfs_server
        )
        try:
            self.nfs_dir = self.manager.createDevice(self.name)
        except strg_errors.CreateLinuxNFSError as err:
            raise errors.HostedEngineException(str(err))
        self.nfs_path = "%s:%s" % (nfs_server,  self.nfs_dir)
        logger.info("NFS Storage path is: %s", self.nfs_path)

    def clean_storage(self):
        """
        Remove NFS storage

        :raise: HostedEngineException
        """
        if self.nfs_dir:
            try:
                self.manager.removeDevice(self.nfs_dir)
            except strg_errors.RemoveLinuxNFSError as err:
                raise errors.HostedEngineException(str(err))


class ISCSIStorage(StorageForHostedEngine):
    """
    Create ISCSI storage for hosted engine deployment
    """

    def __init__(self, storage_type, storage_config):
        """
        Initiate new ISCSIStorage class

        :param storage_type: storage type
        :type storage_type: str
        :param storage_config: storage configuration
        :type storage_config: dict
        """
        super(ISCSIStorage, self).__init__(storage_type, storage_config)
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
