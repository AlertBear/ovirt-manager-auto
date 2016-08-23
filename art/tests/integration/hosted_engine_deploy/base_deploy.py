"""
Base classes for HE deployment
"""
import copy
import logging

import art.core_api.apis_exceptions as core_errors
import art.core_api.apis_utils as utils
import art.test_handler.exceptions as errors
import art.unittest_lib as test_libs
import config as conf
import otopi_parser_helper
import storageapi.he_storage_api as storage_helper
from concurrent.futures import ThreadPoolExecutor
from storageapi.storageErrors import StorageAPIGeneralException

logger = logging.getLogger(__name__)


@test_libs.attr(tier=4)
class BaseDeploy(test_libs.IntegrationTest):
    """
    Base HE deployment class
    """
    storage_api = None
    storage_type = None
    otopi_parser = None
    answer_file_d = None

    @classmethod
    def setup_class(cls):
        """
        1) Reprovision host
        2) Install hosted engine packages
        3) Create storage for test
        """
        storage_class = getattr(
            storage_helper, conf.STORAGE_CLASS_D[cls.storage_type]
        )
        cls.storage_api = storage_class(conf.STORAGE_PARAMETERS)
        cls.otopi_parser = otopi_parser_helper.OtopiParser()
        results = []
        with ThreadPoolExecutor(max_workers=len(conf.VDS_HOSTS)) as executor:
            for vds_resource in conf.VDS_HOSTS:
                logger.info(
                    "Prepare host %s for HE deployment", vds_resource.fqdn
                )
                results.append(
                    executor.submit(
                        cls.__prepare_resource_for_he_deployment, vds_resource
                    )
                )
        for result in results:
            if result.exception():
                raise result.exception()
        cls.answer_file_d = copy.deepcopy(conf.DEFAULT_ANSWER_FILE_D)
        host_cpu_model = cls.get_minimal_cpu_type(conf.VDS_HOSTS[0])
        cls.answer_file_d[
            conf.ANSWER_SECTION_OVEHOSTED_VDSM
        ]["cpu"] = host_cpu_model
        if conf.APPLIANCE_PATH:
            cls.answer_file_d[
                conf.ANSWER_SECTION_OVEHOSTED_VM
            ]["ovfArchive"] = conf.APPLIANCE_PATH

    @classmethod
    def teardown_class(cls):
        """
        1) Clean hosts from HE deployment
        2) Clean storage after test
        """
        logger.info("%s: Enable global maintenance", conf.VDS_HOSTS[0])
        conf.VDS_HOSTS[0].run_command(
            command=[
                conf.HOSTED_ENGINE_CMD, "--set-maintenance", "--mode=global"
            ]
        )
        results = []
        with ThreadPoolExecutor(max_workers=len(conf.VDS_HOSTS)) as executor:
            for vds_resource in conf.VDS_HOSTS:
                logger.info(
                    "Clean host %s after HE deployment", vds_resource.fqdn
                )
                results.append(
                    executor.submit(
                        cls.__clean_host_from_he_deployment, vds_resource
                    )
                )
        for result in results:
            if result.exception():
                logger.error(result.exception())
        try:
            if cls.storage_api:
                cls.storage_api.clean_storage()
        except StorageAPIGeneralException as e:
            logger.error(
                "Failed to clean storage: %s", e
            )

    @staticmethod
    def get_minimal_cpu_type(vds_resource):
        """
        Get minimal CPU model for HE deployment

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :returns: CPU model type
        :rtype: str
        """
        logger.info("Get CPU model from host %s", vds_resource.fqdn)
        rc, out, _ = vds_resource.run_command(
            command=["cat", "/proc/cpuinfo", "|", "grep", "-i", "amd"]
        )
        return conf.AMD_MODEL if out else conf.INTEL_MODEL

    @classmethod
    def __prepare_resource_for_he_deployment(cls, vds_resource):
        """
        1) Reprovision host
        2) Install HE packages on host
        3) Stop NetworkManager

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :raise: HostedEngineException
        """
        host_package_manager = vds_resource.package_manager
        logger.info(
            "Make sure, that %s package exist on host %s",
            conf.HOSTED_ENGINE_SETUP_PACKAGE, vds_resource.fqdn
        )
        packages_to_install = [conf.HOSTED_ENGINE_SETUP_PACKAGE]
        if vds_resource.fqdn == conf.VDS_HOSTS[0].fqdn:
            if not conf.APPLIANCE_OVA_URL:
                if conf.RHEVH_FLAG:
                    raise errors.HostedEngineException(
                        "Can not install rpm package on RHEV-H"
                    )
                packages_to_install.append(conf.RHEVM_APPLIANCE_PACKAGE)
        for package in packages_to_install:
            if not host_package_manager.install(package):
                raise errors.HostedEngineException(
                    "Failed to install %s package on host %s" %
                    (package, vds_resource.fqdn)
                )
        cls.otopi_parser.enable_machine_dialog(vds_resource)
        logger.info(
            "Stop %s service on %s", conf.NETWORK_MANAGER, vds_resource
        )
        vds_resource.service(conf.NETWORK_MANAGER).stop()

    @staticmethod
    def __clean_host_from_he_deployment(vds_resource):
        """
        1) Remove HE packages
        2) Remove HE configuration directories
        3) Reboot host

        :param vds_resource: vds resource
        :type vds_resource: VDS
        """
        logger.info("%s: Poweroff HE VM", vds_resource)
        vds_resource.run_command(
            command=[conf.HOSTED_ENGINE_CMD, "--vm-poweroff"]
        )
        logger.info(
            "%s: Stop %s service", vds_resource, conf.OVIRT_HA_AGENT_SERVICE
        )
        if not vds_resource.service(
            name=conf.OVIRT_HA_AGENT_SERVICE, timeout=120
        ).stop():
            logger.error(
                "%s: Failed to stop %s service",
                vds_resource, conf.OVIRT_HA_AGENT_SERVICE
            )
        logger.info(
            "%s: Unmount all storages from %s",
            vds_resource, conf.RHEV_MOUNT_POINT
        )
        vds_resource.nfs.umount(mount_point="%s*" % conf.RHEV_MOUNT_POINT)

    @classmethod
    def __create_answer_file_on_resource(
        cls, vds_resource, **kwargs
    ):
        """
        Create answer file on resource for future HE deployment

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :param kwargs: override or create new parameter under answer file
                       example:
                       OVEHOSTED_VM = {"automateVMShutdown": True}
                       OVEHOSTED_NOTIF = {"smtpServer": "testhost@testdomain"}
        """
        answer_file_d = copy.deepcopy(cls.answer_file_d)
        logger.debug("Update answer file with new parameters %s", kwargs)
        for section, params in kwargs.iteritems():
            if section in answer_file_d:
                answer_file_d[section].update(params)
            else:
                answer_file_d[section] = params
        logger.info("Create answer file on resource %s", vds_resource.fqdn)
        with vds_resource.executor().session() as resource_session:
            with resource_session.open_file(
                conf.ANSWER_FILE_PATH, 'wb'
            ) as answer_file:
                answer_file.write("%s\n" % conf.ANSWER_FILE_HEADER)
                for section, params in answer_file_d.iteritems():
                    for k, v in params.iteritems():
                        v_type = type(v).__name__
                        if v_type == 'NoneType':
                            v_type = 'none'
                        answer_file.write(
                            "%s/%s=%s:%s\n" % (section, k, v_type, v)
                        )

    @classmethod
    def create_answer_file_on_resources(cls):
        """
        Create answer file on all resources
        """
        logger.debug(cls.answer_file_d)
        cls.__create_answer_file_on_resource(vds_resource=conf.VDS_HOSTS[0])
        for vds_resource in conf.VDS_HOSTS[1:]:
            cls.__create_answer_file_on_resource(
                vds_resource=vds_resource,
                OVEHOSTED_ENGINE={"appHostName": vds_resource.fqdn},
                **conf.ADDITIONAL_HOST_SPECIFIC_PARAMETERS
            )

    def deploy_and_check_he_status_on_hosts(self):
        """
        1) Deploy HE on resources
        2) Check that ovirt-ha-agent and ovirt-ha-broker up after deployment
        """
        for vds_resource in conf.VDS_HOSTS:
            vds_fqdn = vds_resource.fqdn
            logger.info("Deploy hosted-engine on host %s", vds_fqdn)
            try:
                self.otopi_parser.start_parsing(vds_resource)
            except errors.HostedEngineException as ex:
                logger.error(ex)
                return False
            for service in (
                conf.OVIRT_HA_AGENT_SERVICE, conf.OVIRT_HA_BROKER_SERVICE
            ):
                logger.info(
                    "Check if service %s on host %s is up", service, vds_fqdn
                )
                if not vds_resource.service(service).status():
                    logger.error(
                        "Service %s is down on host %s", service, vds_fqdn
                    )
                    return False
            if vds_fqdn == conf.VDS_HOSTS[0].fqdn:
                try:
                    for sample in utils.TimeoutingSampler(
                        timeout=conf.SAMPLER_ENGINE_START_TIMEOUT,
                        sleep=conf.SAMPLER_ENGINE_START_SLEEP,
                        func=lambda: conf.ENGINE.health_page_status
                    ):
                        if sample:
                            break
                except core_errors.APITimeout:
                    logger.error("Engine is still down")
                    return False
        return True


class BaseDeployOverFileStorage(BaseDeploy):
    """
    Base class for deployment over file storage
    """
    storage_params_d = None

    @classmethod
    def setup_class(cls):
        """
        1) Create file storage
        2) Update answer file with correct values
        """
        super(BaseDeployOverFileStorage, cls).setup_class()
        cls.storage_api.create_storage()
        storage_params_d = copy.deepcopy(cls.storage_params_d)
        storage_params_d[
            "storageDomainConnection"
        ] = cls.storage_api.volume_path
        cls.answer_file_d[conf.ANSWER_SECTION_OVEHOSTED_STORAGE].update(
            storage_params_d
        )


class BaseDeployOverNFS(BaseDeployOverFileStorage):
    """
    Base HE deployment over NFS storage class
    """
    storage_type = conf.NFS_TYPE
    storage_params_d = conf.NFS_SPECIFIC_PARAMETERS


class BaseDeployOverGluster(BaseDeployOverFileStorage):
    """
    Base HE deployment over Gluster storage class
    """
    storage_type = conf.GLUSTER_TYPE
    storage_params_d = conf.GLUSTER_SPECIFIC_PARAMETERS


class BaseDeployOverISCSI(BaseDeploy):
    """
    Base HE deployment over ISCSI storage class
    """
    storage_type = conf.ISCSI_TYPE

    @classmethod
    def setup_class(cls):
        """
        1) Create ISCSI storage
        2) Map vds resources to ISCSI lun
        3) Update answer file with correct values
        """
        super(BaseDeployOverISCSI, cls).setup_class()
        for vds_resource in conf.VDS_HOSTS:
            cls.storage_api.add_host_to_hostgroup(vds_resource)
        cls.storage_api.create_storage()
        iscsi_params_d = copy.deepcopy(conf.ISCSI_SPECIFIC_PARAMETERS)
        cls.answer_file_d[conf.ANSWER_SECTION_OVEHOSTED_STORAGE].update(
            iscsi_params_d
        )
