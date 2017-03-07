#!/usr/bin/python

"""
Tool for glance image update
"""
import os
import logging
import rrmngmnt
import config
from subprocess import list2cmdline
from art.unittest_lib import (
    BaseTestCase as TestCase,
    testflow
)
import art.rhevm_api.data_struct.data_structures as data_struct
from art.rhevm_api.utils.test_utils import setPersistentNetwork
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_sd,
    vms as ll_vms,
    disks as ll_disks,
    hosts as ll_hosts,
    templates as ll_templates
)


logger = logging.getLogger("Glance_image_updater")


def _run_cmd(session, cmd, error_msg, expected_rc=0, assert_rc=True):
    str_cmd = list2cmdline(cmd)
    rc, out, err = session.run_cmd(cmd)
    out = unicode(out, 'utf-8', errors='ignore')
    err = unicode(err, 'utf-8', errors='ignore')
    if rc != expected_rc:
        logger.error(
            'Error when running cmd: %s, err: %s, rc: %s', str_cmd, err, rc
        )
        if assert_rc:
            assert rc == expected_rc, "Cmd %s hasn't expected result" % str_cmd
    return rc, out, err


class GlanceImageBase(object):
    """
    Base class for glance Image
    """
    @classmethod
    def import_glance_image(cls, image_name):
        """
        Import image from glance as template

        :param image_name: name of glance image
        :type image_name: str
        """

        logger.info("Find NFS storage domain to import template")
        template_name = config.TEMPLATE_PREFIX.format(image_name)
        sd_name = ll_sd.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME,
            storage_type=config.STORAGE_TYPE
        )[0]
        logger.info("Storage domain name for store image: %s", sd_name)
        testflow.step(
            "Importing glance image %s and creating template %s", image_name,
            template_name
        )
        if not ll_sd.import_glance_image(
            glance_repository=config.GLANCE_DOMAIN,
            glance_image=image_name,
            target_storage_domain=sd_name,
            target_cluster=config.CLUSTER_NAME,
            new_disk_alias=config.DISK_PREFIX.format(image_name),
            new_template_name=template_name,
            import_as_template=True
        ):
            raise errors.TemplateException(
                "Failed to create template %s from glance" % template_name
            )

    @classmethod
    def create_vm_from_template(cls, template_name, vm_name, run_vm=True):
        """
        Creating vm from template

        :param template_name: name of template
        :type template_name: str
        :param vm_name: name of VM
        :type vm_name: str
        :param run_vm: True if it should runs VM after creation False otherwise
        :type run_vm: bool
        """

        initialization = data_struct.Initialization(
            **config.INITIALIZATION_PARAMS
        )
        testflow.step(
            "Creating VM %s from template %s", vm_name, template_name
        )
        if not ll_vms.createVm(
            positive=True, vmName=vm_name, vmDescription=vm_name,
            cluster=config.CLUSTER_NAME,
            template=template_name,
            os_type=config.ENUMS['rhel7x64'],
            initialization=initialization,
            nic=config.NIC_NAME,
            network=config.MGMT_BRIDGE
        ):
            raise errors.VMException(
                "Failed to create vm %s" % vm_name
            )
        if run_vm:
            logger.info("Starting VM %s", vm_name)
            if not ll_vms.startVm(
                positive=True, vm=vm_name, wait_for_ip=True
            ):
                raise errors.VMException(
                    "Failed to start vm: %s" % vm_name
                )
        return True


class GlanceImageUpdator(GlanceImageBase):
    """
    Wrap stuffs related with update image
    """

    def __init__(self, images=config.IMAGE_NAMES[:]):
        self.image_names = images
        self.vms_description = [
            dict(
                name=config.VM_PREFIX.format(image_name), image=image_name,
                template=config.TEMPLATE_PREFIX.format(image_name),
                disk_alias=config.DISK_PREFIX.format(image_name)
            ) for image_name in self.image_names
        ]
        self.host = self.get_host()
        self.host_session = self.host.executor().session()
        self.host_session.open()

    def close_session(self):
        self.host_session.close()

    def get_host(self):
        """
        Get non rhev-h host for process update image

        :return: instance of rrmngmnt.Host
        """

        hosts = ll_hosts.get_host_list()
        for host in hosts:
            if host.get_type() != 'rhev-h':
                host = rrmngmnt.Host(host.address)
                host.users.append(rrmngmnt.User('root', config.ROOT_PASSWORD))
                return host
        raise errors.HostException('No non rhev-h host has found')

    def get_disk_file_path(self, disk_id):
        """
        Finds disk file path on SD

        :param disk_id: id of disk
        :type disk_id: str
        :return: path of disk file
        :rtype: str
        """

        cmd_get_path = [
            'find', '/', '-ipath', '*/{0}/*'.format(disk_id), '-not', '-name',
            '*.meta', '-not', '-name', '*.lease'
        ]
        cmd_has_backing_file = [
            'qemu-img', 'info', 'replace_path', '|', 'grep', 'backing file',
            '|', 'wc', '-l'
        ]

        paths = []
        err_msg = (
            "Couldn't find path for disk_id %s, on host %s"
            % (disk_id, self.host.ip)
        )
        rc, out, err = _run_cmd(self.host_session, cmd_get_path, err_msg)
        for line in out.strip().split('\n'):
            paths.append(line.strip())
        if len(paths) == 1:
            return paths[0]
        for path in paths:
            cmd_has_backing_file[2] = path
            rc, out, err = self.host_session.run_cmd(cmd_has_backing_file)
            if not rc:
                if int(out):
                    return path
        raise errors.DiskException(
            "No disk file in paths %s on host %s" % (paths, self.host.ip)
        )

    def create_image_and_upload(
        self, disk_path, img_name, tmp_dir='/tmp/img_update',
        backup=config.BACKUP_IMAGE
    ):
        """
        Creating disk image and upload it to glance

        :param disk_path: path of VM disk for upload as glance image
        :type disk_path: str
        :param img_name: name of image
        :type img_name: str
        :param tmp_dir: tmp dir where create img
        :type tmp_dir: str
        :param backup: True if backup old glance image
        :type backup: bool
        """

        backup_name = img_name + '_backup'
        new_img_path = os.path.join(tmp_dir, img_name)
        create_image_cmd = [
            'qemu-img', 'convert', '-p', '-f', 'qcow2', disk_path, '-O',
            'qcow2', '-o', 'compat=0.10', new_img_path
        ]
        glance_base_cmd = [
            'glance', '--os-username', config.GLANCE_USER, '-T',
            config.GLANCE_TENANT, '--os-password', config.GLANCE_PASSWORD,
            '--os-auth-url', config.GLANCE_URL
        ]
        glance_img_info_cmd = glance_base_cmd + ['image-show']  # add img name
        glance_backup_cmd = glance_base_cmd + [
            'image-update', '--name', backup_name, img_name
        ]
        glance_delete_cmd = glance_base_cmd + ['image-delete']  # add img name
        glance_create_cmd = glance_base_cmd + [
            'image-create', '--name', img_name, '--is-public=true',
            '--disk-format=qcow2', '--container-format=bare', '--file',
            new_img_path
        ]
        mkdir_cmd = ['mkdir', '-p', tmp_dir]
        remove_img_file_cmd = ['rm', '-f', new_img_path]
        testflow.step("Creating image in path %s", new_img_path)
        _run_cmd(self.host_session, mkdir_cmd, "Failed create tmp dir")
        _run_cmd(self.host_session, create_image_cmd, "Failed create image")
        rc, out, err = self.host_session.run_cmd(
            glance_img_info_cmd + [img_name]
        )
        if backup:
            rc_backup_img, out_, err_ = self.host_session.run_cmd(
                glance_img_info_cmd + [backup_name]
            )
            # remove old backup image if exists
            if not rc_backup_img:
                logger.info(
                    "Deleting old backup file %s from glance", backup_name
                )
                _run_cmd(
                    self.host_session, glance_delete_cmd + [backup_name],
                    "Failed delete glance image %s" % backup_name
                )
            # rename old image if exists to backup name on glance
            if not rc:
                logger.info(
                    "Backup image %s to %s", img_name, backup_name
                )
                _run_cmd(
                    self.host_session, glance_backup_cmd,
                    "Failed when backup image %s" % img_name
                )
        else:
            if not rc:
                logger.info(
                    "Deleting old image %s from glance", img_name
                )
                _run_cmd(
                    self.host_session, glance_delete_cmd + [img_name],
                    "Failed delete glance image %s" % img_name
                )

        testflow.step("Uploading new image %s to glance", img_name)
        _run_cmd(
            self.host_session, glance_create_cmd,
            "Error when uploading image %s to glance" % img_name
        )
        logger.info("Removing image file: %s", new_img_path)
        _run_cmd(self.host_session, remove_img_file_cmd, "Failed remove image")
        logger.info("Succesfully updated image %s", img_name)

    def upload_images(self):
        """
        Upload images to glance from vms_description
        """

        for vm in self.vms_description:
            self.create_image_and_upload(vm['disk_path'], vm['image'])

    def create_vms(self):
        """
        Create VMs from vms_description
        """
        for vm in self.vms_description:
            self.create_vm_from_template(vm['template'], vm['name'])

    def seal_vms(self):
        """
        Seal VMs from vms_description
        """
        for vm in self.vms_description:
            self.seal_and_stop_vm(vm)

    def import_images(self):
        for image in self.image_names:
            self.import_glance_image(image)

    def update_images(self, repo_url):
        """
        Update VMs from vms_description

        :param repo_url: rhevm repository URL
        :type repo_url: str
        """
        for vm in self.vms_description:
            vm['ip'] = ll_vms.wait_for_vm_ip(vm['name'])[1]['ip']
            vm['disk_id'] = ll_disks.getVmDisk(
                vm['name'], vm['disk_alias']
            ).get_id()
            vm['disk_path'] = self.get_disk_file_path(vm['disk_id'])
            host = rrmngmnt.Host(vm['ip'])
            host.users.append(
                rrmngmnt.User('root', config.ROOT_PASSWORD)
            )
            self.update_repo(host, repo_url, config.PRODUCT)

    @classmethod
    def update_repo(cls, host, repo_url, product='rhevm'):
        """
        1) remove old repository on VM and
        2) remove old agent
        3) install new repository
        4) install new agent
        5) update all packages
        6) yum clean

        :param host: host where update repo and so on
        :type host: instance of rrmngmnt.Host
        :param repo_url: URL of repository
        :type repo_urp: str
        :param product: rhevm or ovirt
        :type product: str
        """

        remove_old_repo_cmd = [
            'rpm', '-qa', '\'(rhev|ovirt)-release-*\'', '|', 'xargs', 'rpm',
            '-e'
        ]
        remove_old_agent_cmd = [
            'rpm', '-qa', '\'(rhevm|ovirt)-guest-agent*\'', '|', 'xargs',
            'rpm', '-e'
        ]
        remove_old_repo_files_cmd = [
            "find", "/etc/yum.repos.d/", "-type", "f", "-name", "'ovirt*'",
            "-or", "-name", "'rhev*'", "|", "xargs", "rm", "-f"
        ]
        sync_disk_cmd = ['sync']
        if product == 'rhevm':
            install_agent = 'rhevm-guest-agent-common'
        else:
            install_agent = 'ovirt-guest-agent'

        yum_clean_cmd = ['yum', 'clean', 'all']
        with host.executor().session() as session:
            logger.info("Removing old repository")
            _run_cmd(
                session, remove_old_repo_cmd, "Failed remove old repo",
                assert_rc=False
            )
            # warkaround, because rpm doesn't remove repo files
            logger.info("Removing old repository files")
            _run_cmd(
                session, remove_old_repo_files_cmd,
                "Failed remove old repo files"
            )
            logger.info("Removing old agent")
            _run_cmd(
                session, remove_old_agent_cmd, "Failed remove old agent",
                assert_rc=False
            )
            logger.info("Running yum clean")
            _run_cmd(session, yum_clean_cmd, "Failed yum clean")
            host.logger.info("Installing new repository %s", config.REPOSITORY)
            assert host.package_manager.install(repo_url), (
                "Failed install new repo"
            )
            logger.info("Installing agent")
            assert host.package_manager.install(install_agent), (
                "Failed install agent"
            )
            logger.info("Running yum update")
            assert host.package_manager.update(), "Failed update all packages"
            logger.info("Running yum clean")
            _run_cmd(session, yum_clean_cmd, "Failed yum clean")
            logger.info("Syncing disk")
            _run_cmd(session, sync_disk_cmd, "Failed sync disk")
            logger.info('Installed new repo and agent updated')

    @classmethod
    def seal_and_stop_vm(cls, vm_description):
        """
        Sealing vm adn stop

        :param vm_description: vm description
        :type vm_description: dict
        """
        logger.info("seal VM: %s", vm_description['name'])
        if not setPersistentNetwork(
            vm_description['ip'], config.ROOT_PASSWORD
        ):
            raise errors.VMException(
                'Failed to seal VM: %s' % vm_description['ip']
            )
        if not ll_vms.stopVm(True, vm_description['name']):
            raise errors.VMException(
                'Failed to stop vm:' % vm_description['name']
            )

    def cleanup(self):
        """
        Cleanum method which stops and removes VMs and remvoes templates
        """
        vms = [vm['name'] for vm in self.vms_description]
        templates = [vm['template'] for vm in self.vms_description]
        ll_vms.stop_vms(vms)
        ll_vms.removeVms(True, vms)
        ll_templates.remove_templates(True, templates)
        self.close_session()


class TestGlanceImageUpdate(TestCase):
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.image_updator = GlanceImageUpdator(config.IMAGE_NAMES)
        cls.image_updator.import_images()
        cls.image_updator.create_vms()

    def test_update_glance_image(self):
        """
        Update glance image with new repo.
        """
        self.image_updator.update_images(config.REPOSITORY)
        self.image_updator.seal_vms()
        self.image_updator.upload_images()

    @classmethod
    def teardown_class(cls):
        cls.image_updator.cleanup()
