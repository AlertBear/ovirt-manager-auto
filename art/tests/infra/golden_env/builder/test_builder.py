import logging

from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.utils import test_utils, cpumodel
from art.core_api.apis_utils import TimeoutingSampler


from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.rhevm_api.tests_lib.low_level import external_providers
from art.rhevm_api.tests_lib.high_level import mac_pool as hl_mac_pool
from art.rhevm_api.tests_lib.high_level import storagedomains

from art.rhevm_api.resources import VDS

import art.test_handler.exceptions as errors

import infra.golden_env.config as config
LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS
GB = 1024 * 1024 * 1024
GLANCE = 'OpenStackImageProvider'
ADD_GROUP_CMD = ('ovirt-aaa-jdbc-tool', 'group', 'add')
ADD_USER_CMD = ('ovirt-aaa-jdbc-tool', 'user', 'add')
PASSWORD_RESET_CMD = ('ovirt-aaa-jdbc-tool', 'user', 'password-reset')
GROUP_MANAGE_ADD_USER_CMD = ('ovirt-aaa-jdbc-tool', 'group-manage', 'useradd')


class HostConfiguration(object):
    def __init__(self, hosts, passwords):
        self.hosts = zip(hosts, passwords)
        self.unused = list(self.hosts)

    def get_unused_host(self):
        return self.unused.pop(0)


class StorageConfiguration(object):
    def __init__(self, configuration):
        if 'data_domain_address' in configuration:
            self.nfs_addresses = configuration.as_list('data_domain_address')
            self.nfs_paths = configuration.as_list('data_domain_path')
        else:
            self.nfs_addresses, self.nfs_paths = [], []
        if 'lun' in configuration:
            self.iscsi_luns = configuration.as_list('lun')
            self.iscsi_lun_addresses = configuration.as_list('lun_address')
            self.iscsi_lun_targets = configuration.as_list('lun_target')
        else:
            self.iscsi_luns, self.iscsi_lun_addresses = [], []
            self.iscsi_lun_targets = []
        if 'gluster_data_domain_address' in configuration:
            self.gluster_addresses = configuration.as_list(
                'gluster_data_domain_address')
            self.gluster_paths = configuration.as_list(
                'gluster_data_domain_path'
            )
            self.gluster_vfs_types = (
                [configuration['vfs_type']] * len(self.gluster_paths))
        else:
            self.gluster_addresses, self.gluster_paths = [], []
            self.gluster_vfs_types = []
        if 'local_domain_path' in configuration:
            self.local_paths = configuration.as_list('local_domain_path')
        else:
            self.local_paths = []
        if 'export_domain_address' in configuration:
            self.export_addresses = configuration.as_list(
                'export_domain_address')
            self.export_paths = configuration.as_list('export_domain_path')
        else:
            self.export_addresses, self.export_paths = [], []
        if 'tests_iso_domain_address' in configuration:
            self.shared_iso_address = configuration.get(
                'tests_iso_domain_address')
            self.shared_iso_path = configuration.get('tests_iso_domain_path')

        self.nfs_shares = zip(self.nfs_addresses, self.nfs_paths)
        self.iscsi_shares = zip(
            self.iscsi_luns, self.iscsi_lun_addresses, self.iscsi_lun_targets)
        self.gluster_shares = zip(
            self.gluster_addresses, self.gluster_paths, self.gluster_vfs_types)
        self.unused_local_paths = list(self.local_paths)
        self.export_shares = zip(
            self.export_addresses, self.export_paths)

    def get_shared_iso(self):
        return self.shared_iso_address, self.shared_iso_path

    def get_nfs_share(self):
        return self.nfs_shares.pop(0)

    def get_iscsi_share(self):
        return self.iscsi_shares.pop(0)

    def get_gluster_share(self):
        return self.gluster_shares.pop(0)

    def get_unused_local_share(self):
        return self.unused_local_paths.pop(0)

    def get_export_share(self):
        return self.export_shares.pop(0)


class GlanceConfiguration(object):
    def __init__(self, configuration):
        self._name = configuration.get('name')
        self._url = configuration.get('url')
        self._username = configuration.get('username')
        self._password = configuration.get('password')
        self._tenant = configuration.get('tenant')
        self._authentication_url = configuration.get('authentication_url')

    def get_name(self):
        return self._name

    def get_url(self):
        return self._url

    def get_username(self):
        return self._username

    def get_password(self):
        return self._password

    def get_tenant(self):
        return self._tenant

    def get_authentication_url(self):
        return self._authentication_url


class EPConfiguration(object):
    def __init__(self, configuration):
        self.eps_to_add = configuration.as_list('ep_to_add')
        self._glance_providers = []

        for ep in self.eps_to_add:
            if configuration[ep]['type'] == GLANCE:
                ep_conf = GlanceConfiguration(configuration[ep])
                self._glance_providers.append(ep_conf)

    def glance_providers(self):
        return self._glance_providers[:]


class CreateDC(TestCase):
    __test__ = True

    def __init__(self, *args, **kwargs):
        super(CreateDC, self).__init__(*args, **kwargs)
        self.vds_objs = list()

    def build_cluster(self, cl_def, dc_name, comp_version, host_conf):
        cluster_name = cl_def['name']
        cpu_name = config.CPU_NAME

        if not clusters.addCluster(
                True, name=cluster_name, cpu=cpu_name, data_center=dc_name,
                version=comp_version):
            raise errors.ClusterException(
                "addCluster %s with cpu_type %s and version %s to datacenter"
                " %s failed" %
                (cluster_name, cpu_name, comp_version, dc_name))
        LOGGER.info("Cluster %s was created successfully", cluster_name)

        hosts_def = cl_def['hosts']
        if not hosts_def:
            LOGGER.info("No hosts in cluster")
            return
        for host_def in hosts_def:
            host_ip, host_pwd = host_conf.get_unused_host()
            vds_obj = VDS(host_ip, host_pwd)
            vds_fqdn = vds_obj.fqdn
            self.vds_objs.append(vds_obj)
            if not hosts.addHost(
                    True, host_def['name'], address=host_ip,
                    root_password=host_pwd, wait=False, cluster=cluster_name,
                    **{"comment": vds_fqdn}
                    ):
                raise errors.HostException("Cannot add host")

        if not hosts.waitForHostsStates(
                True,
                ",".join([x['name'] for x in hosts_def])):
            raise errors.HostException("Hosts are not up")

        # Set the best cpu_model for hosts
        cpu_den = cpumodel.CpuModelDenominator()
        try:
            cpu_info = cpu_den.get_common_cpu_model(
                self.vds_objs,
                version=comp_version,
            )
        except cpumodel.CpuModelError as ex:
            LOGGER.error("Can not determine the best cpu_model: %s", ex)
        else:
            LOGGER.info("Cpu info %s for cluster: %s", cpu_info, cluster_name)
            if not clusters.updateCluster(
                True,
                cluster_name,
                cpu=cpu_info['cpu']
            ):
                LOGGER.error(
                    "Can not update cluster cpu_model to: %s", cpu_info['cpu'],
                )

    def add_sds(self, storages, host, datacenter_name, storage_conf):
        for sd in storages:
            sd_name = sd['name']
            storage_type = sd['storage_type']
            if storage_type == ENUMS['storage_type_nfs']:
                address, path = storage_conf.get_nfs_share()
                self.delete_data_from_storage_domain(address, path)
                assert storagedomains.addNFSDomain(
                    host, sd_name, datacenter_name, address, path, format=True)
            elif storage_type == ENUMS['storage_type_iscsi']:
                lun, address, target = storage_conf.get_iscsi_share()
                assert storagedomains.addISCSIDataDomain(
                    host,
                    sd_name,
                    datacenter_name,
                    lun,
                    address,
                    target,
                    override_luns=True,
                    login_all=True
                )
            elif storage_type == ENUMS['storage_type_gluster']:
                address, path, vfs = storage_conf.get_gluster_share()
                self.delete_data_from_storage_domain(
                    address, path, fs_type='-tglusterfs'
                )
                assert storagedomains.addGlusterDomain(
                    host, sd_name, datacenter_name, address, path,
                    vfs_type=vfs)
            elif storage_type == ENUMS['storage_type_local']:
                path = storage_conf.get_unused_local_share()
                assert storagedomains.addLocalDataDomain(
                    host, sd_name, datacenter_name, path)
            else:
                LOGGER.warning("unknown type: %s", storage_type)

    def _create_vm(self, vm, dc_name, cl_name):
        vm_name = vm['name']
        vm_description = vm_name
        storage_domain_name = ll_sd.getDCStorages(dc_name, False)[0].name
        LOGGER.info("storage domain: %s" % storage_domain_name)
        sparse = vm['disk_sparse']
        volume_format = vm['disk_format']
        vm_type = vm['type']
        disk_interface = vm['disk_interface']
        assert ll_vms.createVm(
            True, vm_name, vm_description, cluster=cl_name,
            nic='nic1', storageDomainName=storage_domain_name,
            size=vm['disk_size'], diskType=vm['disk_type'],
            volumeType=sparse, volumeFormat=volume_format,
            diskInterface=disk_interface, memory=vm['memory'],
            cpu_socket=vm['cpu_socket'], cpu_cores=vm['cpu_cores'],
            nicType=vm['nic_type'], display_type=vm['display_type'],
            os_type=config.OS_TYPE, slim=True, user=vm['user'],
            password=vm['password'], type=vm_type, installation=True,
            network=config.MGMT_BRIDGE, useAgent=config.USE_AGENT,
            image=config.COBBLER_PROFILE)
        assert ll_vms.waitForVMState(vm_name, state=ENUMS['vm_state_up'])
        assert ll_vms.stopVm(True, vm_name)

    def _seal_vm(self, vm_name, vm_password):
        vm_state = ll_vms.get_vm_state(vm_name)
        if vm_state == ENUMS['vm_state_down']:
            ll_vms.startVm(True, vm_name, wait_for_status=ENUMS['vm_state_up'])

        LOGGER.info("Waiting for IP of %s", vm_name)
        status, result = ll_vms.waitForIP(vm_name)
        assert status

        LOGGER.info("Sealing: set persistent network for %s", vm_name)

        assert test_utils.setPersistentNetwork(
            result['ip'], vm_password)
        LOGGER.info("Stopping %s to create template", vm_name)
        assert ll_vms.stopVm(True, vm_name)

    def _create_and_seal_vm(self, vm, dc_name, cl_name):
        self._create_vm(vm, dc_name, cl_name)
        self._seal_vm(vm['name'], vm['password'])

    def _is_vms_state_down(self, cloned_vms):
        for cloned_vm in cloned_vms:
            LOGGER.info("Waiting until %s state is down...", cloned_vm)
            assert ll_vms.waitForVMState(
                cloned_vm,
                state=ENUMS['vm_state_down']
            )

    def _clone_vm(self, vm_description, cloned_vms, cl_name, destination_sd):
        suffix_num = 0
        vm_prefix = vm_description['name']
        if 'number_of_vms' in vm_description:
            number_of_vms = vm_description['number_of_vms']
            vm_description['name'] += repr(suffix_num)
        else:
            number_of_vms = 1

        while suffix_num < number_of_vms:
            LOGGER.info(
                "Creating VM: %s from Template: %s",
                vm_description['name'],
                vm_description['clone_from']
            )

            ll_vms.cloneVmFromTemplate(
                True,
                vm_description['name'],
                vm_description['clone_from'],
                cl_name,
                wait=True,
                storagedomain=destination_sd
            )
            ll_vms.updateVmDisk(
                positive=True, vm=vm_description['name'],
                disk=vm_description['clone_from'], bootable=True
            )
            cloned_vms.append(vm_description['name'])
            suffix_num += 1
            vm_description['name'] = vm_prefix
            vm_description['name'] += repr(suffix_num)

    def _add_multiple_vms_from_template(
            self, vm_description, cloned_vms, dc_name, cl_name
    ):
        LOGGER.info(
            "Creating a template and clone %s vms out of it",
            vm_description['number_of_vms']
        )
        prefix_vm_name = vm_description['name']
        suffix_num = 0
        vm_description['name'] += repr(suffix_num)
        suffix_num += 1
        self._create_and_seal_vm(
            vm_description,
            dc_name,
            cl_name
        )
        tmp_template = "tmp_template"
        template_creation_status = templates.createTemplate(
            True,
            vm=vm_description['name'],
            name=tmp_template, cluster=cl_name
        )
        assert template_creation_status

        while suffix_num < vm_description['number_of_vms']:
            vm_description['name'] = prefix_vm_name
            vm_description['name'] += repr(suffix_num)
            suffix_num += 1
            LOGGER.info(
                "Cloning vm %s from template %s",
                vm_description['name'], tmp_template
            )

            ll_vms.cloneVmFromTemplate(
                True,
                vm_description['name'], tmp_template,
                cl_name,
                vol_sparse=vm_description['disk_sparse'],
                vol_format=vm_description['disk_format'],
                wait=False,
                storagedomain=vm_description['storage_domain']
            )

            cloned_vms.append(vm_description['name'])

        self._is_vms_state_down(cloned_vms)

        assert templates.removeTemplate(True, tmp_template)

    def add_vms(self, vms_def, dc_name, cl_name):
        """ add description
        """
        if not vms_def:
            return

        for vm_description in vms_def:
            LOGGER.info(vm_description)
            cloned_vms = []

            if 'clone_from' in vm_description:
                self._clone_vm(
                    vm_description,
                    cloned_vms,
                    cl_name,
                    vm_description['storage_domain']
                )
            elif 'number_of_vms' in vm_description:
                self._add_multiple_vms_from_template(
                    vm_description,
                    cloned_vms,
                    dc_name,
                    cl_name
                )
            else:
                LOGGER.info("Creating a new vm")
                self._create_and_seal_vm(
                    vm_description,
                    dc_name,
                    cl_name
                )
            if cloned_vms:
                self._is_vms_state_down(cloned_vms)

    def copy_template_disks(self, template, all_sds):
        template_disks = [
            x.get_name() for x in templates.getTemplateDisks(template)]
        template_disk = template_disks[0]
        disk_sd = disks.get_disk_storage_domain_name(
            template_disk, template_name=template)
        for sd in all_sds:
            if disk_sd != sd:
                for disk in template_disks:
                    templates.copyTemplateDisk(template, disk, sd)

    def _get_data_storage_domains(self, data_center):
        sds = ll_sd.getDCStorages(data_center, False)
        data_type = ENUMS['storage_dom_type_data']
        data_sds = [x.get_name() for x in sds if x.get_type() == data_type]

        return data_sds

    def add_templates(self, templ_def, cluster, datacenter):

        data_sds = self._get_data_storage_domains(datacenter)

        for template in templ_def:
            template_name = template['name']
            assert templates.createTemplate(
                True, vm=template['base_vm'],
                name=template_name,
                cluster=cluster
            )

            self.copy_template_disks(template_name, data_sds)

    def add_glance_templates(self, glance_templates, data_center, cluster):
        for glance_template in glance_templates:
            glance, image = glance_template['source'].split(':')
            gi = ll_sd.GlanceImage(image, glance)

            data_sds = self._get_data_storage_domains(data_center)
            assert gi.import_image(
                destination_storage_domain=data_sds[0],
                cluster_name=cluster,
                new_disk_alias=glance_template['name'],
                new_template_name=glance_template['name'],
                import_as_template=True,
                async=False
            )
            self.add_nic_to_glance_template(glance_template['name'])

    def add_nic_to_glance_template(self, template_name):
        sampler = TimeoutingSampler(
            300,
            10,
            templates.check_template_existence,
            template_name
        )

        for status in sampler:
            if status:
                break
            else:
                LOGGER.info(
                    "Wait for import template: %s from glance has completed",
                    template_name
                )

        assert templates.addTemplateNic(
            positive=True,
            template=template_name,
            name=config.NIC_NAME,
            network=config.MGMT_BRIDGE
        )

    def add_export_templates(self, export_templates, data_center, cluster):
        data_sds = self._get_data_storage_domains(data_center)
        for export_template in export_templates:
            export_domain, template = export_template['source'].split(':')

            assert templates.import_template(
                positive=True,
                template=template,
                source_storage_domain=export_domain,
                destination_storage_domain=data_sds[0],
                cluster=cluster,
                name=export_template['name']
            )

    def build_dc(self, dc_def, host_conf, storage_conf):
        datacenter_name = dc_def['name']
        local = bool(dc_def['local'])
        comp_version = dc_def['compatibility_version']
        if not datacenters.addDataCenter(
                True, name=datacenter_name, local=local, version=comp_version):
            raise errors.DataCenterException(
                "addDataCenter %s with local %s and version %s failed."
                % (datacenter_name, local, comp_version))

        clusters = dc_def['clusters']
        for cluster in clusters:
            self.build_cluster(
                cluster, datacenter_name, comp_version, host_conf)
            LOGGER.info("Cluster %s added", cluster['name'])
        LOGGER.info("Added all clusters")

        if clusters[0]['hosts']:
            LOGGER.info("Adding storage domains")
            storages = dc_def['storage_domains']
            host = clusters[0]['hosts'][0]['name']
            if storages is not None:
                self.add_sds(storages, host, datacenter_name, storage_conf)
            else:
                LOGGER.info("No storage_domains on yaml description file")

            export_domains = dc_def['export_domains']
            if export_domains is None:
                LOGGER.info("No export_domains to add")
            else:
                for export_domain in export_domains:
                    self.add_export_domain(
                        export_domain, storage_conf, datacenter_name, host
                    )
        else:
            LOGGER.info("No hosts, so no adding storages")

        for cluster in clusters:
            if cluster['external_templates']:
                for external_template in cluster['external_templates']:
                    if external_template['glance']:
                        LOGGER.info("Adding glance templates")
                        self.add_glance_templates(
                            external_template['glance'],
                            datacenter_name,
                            cluster['name']
                        )
                    if external_template['export_domain']:
                        LOGGER.info("Adding export templates")
                        self.add_export_templates(
                            external_template['export_domain'],
                            datacenter_name,
                            cluster['name']
                        )
                else:
                    LOGGER.info("No templates to add")

            vms_def = cluster['vms']
            if vms_def:
                LOGGER.info("Adding vms")
                self.add_vms(
                    vms_def, datacenter_name, cluster['name']
                )
            else:
                LOGGER.info("No vms to add")

            templ_def = cluster['templates']
            if templ_def:
                LOGGER.info("Adding templates")
                self.add_templates(templ_def, cluster['name'], datacenter_name)
            else:
                LOGGER.info("No templates to add")

    def _get_executor(self):
        return self.vds_objs[0].executor()

    def _execute_cmd(self, cmd, ss=None):
        if ss is None:
            ss = self._get_executor()
        rc, out, err = ss.run_cmd(cmd)
        assert rc == 0, "Return code %s != 0" % rc

    def delete_data_from_storage_domain(self, address, path, fs_type='-tnfs'):
        mount_dir = "/tmp/mount_dir"
        nfs_path = "%s:%s" % (address, path)
        create_dir_cmd = ['mkdir', '-p', mount_dir]
        mount_cmd = ['mount', fs_type, nfs_path, mount_dir]
        rm_cmd = ['rm', '-rf', mount_dir + '/*']
        umount_cmd = ['umount', mount_dir]
        with self._get_executor().session() as ss:
            self._execute_cmd(create_dir_cmd, ss)
            self._execute_cmd(mount_cmd, ss)
            self._execute_cmd(rm_cmd, ss)
            self._execute_cmd(umount_cmd, ss)

    def add_export_domain(self, export_domain, storage_conf, dc, host):
        if export_domain['name']:
            name = export_domain['name']
            address, path = storage_conf.get_export_share()
            # Delete existed export domain
            if config.CLEAN_EXPORT_DOMAIN:
                self.delete_data_from_storage_domain(address, path)
            # Add export storage domain
            assert ll_sd.addStorageDomain(
                True,
                name=name,
                type=ENUMS['storage_dom_type_export'],
                storage_type=ENUMS['storage_type_nfs'],
                address=address,
                host=host,
                path=path,
            )
            assert ll_sd.attachStorageDomain(
                True, datacenter=dc, storagedomain=name
            )
            # Attach storage domain
            LOGGER.info("Export SD %s has been successfully attached", name)
        else:
            LOGGER.info("Please provide name to your export domain")

    def import_shared_iso_domain(self, storage_conf, host):
        address, path = storage_conf.get_shared_iso()
        LOGGER.info("Importing iso domain %s:%s", address, path)
        assert ll_sd.importStorageDomain(
            True, ENUMS['storage_dom_type_iso'], ENUMS['storage_type_nfs'],
            address[0], path[0], host)

    def connect_glance(self, external_provider_def):
        LOGGER.info(
            "Connecting %s to environment", external_provider_def.get_name()
        )
        LOGGER.info(
            "OpenStackImageProvider %s %s %s %s %s %s",
            external_provider_def.get_name(),
            external_provider_def.get_url(),
            external_provider_def.get_username(),
            external_provider_def.get_password(),
            external_provider_def.get_tenant(),
            external_provider_def.get_authentication_url()
        )

        glance = external_providers.OpenStackImageProvider(
            name=external_provider_def.get_name(),
            url=external_provider_def.get_url(),
            requires_authentication=True,
            username=external_provider_def.get_username(),
            password=external_provider_def.get_password(),
            authentication_url=external_provider_def.get_authentication_url(),
            tenant_name=external_provider_def.get_tenant()
        )

        assert glance.add()

    def _create_users_groups(self, golden_env):
        LOGGER.info("Creating users and groups")
        with config.ENGINE_HOST.executor().session() as ss:
            for group in golden_env['groups']:
                cmd = list(ADD_GROUP_CMD)
                cmd.append(group['name'])
                assert not ss.run_cmd(cmd)[0], 'Failed to add group'

            for user in golden_env['users']:
                cmd = list(ADD_USER_CMD)
                cmd.append(user['name'])
                cmd.append('--attribute=firstName=%s' % user['name'])
                assert not ss.run_cmd(cmd)[0], 'Failed to add user'

                cmd = list(PASSWORD_RESET_CMD)
                cmd.append(user['name'])
                cmd.append('--password=pass:%s' % user['passwd'])
                cmd.append('--password-valid-to=2050-01-01 00:00:00Z')
                assert not ss.run_cmd(cmd)[0], 'Failed to reset password'

                if user.get('group', None):
                    cmd = list(GROUP_MANAGE_ADD_USER_CMD)
                    cmd.append(user['group'])
                    cmd.append('--user=%s' % user['name'])
                    assert not ss.run_cmd(cmd)[0], 'Failed to assign group'

    def test_build_env(self):
        hl_mac_pool.update_default_mac_pool()

        GOLDEN_ENV = config.ART_CONFIG['prepared_env']

        if GOLDEN_ENV['external_providers']:
            eps = EPConfiguration(config.EPS)
            for glance in eps.glance_providers():
                self.connect_glance(glance)

        dcs = GOLDEN_ENV['dcs']

        storage_conf = StorageConfiguration(config.STORAGE)
        host_conf = HostConfiguration(config.HOSTS, config.PASSWORDS)
        for dc in dcs:
            self.build_dc(dc, host_conf, storage_conf)

        iso_domains = GOLDEN_ENV['iso_domains']
        host = (hosts.get_host_list()[0]).get_name()
        if not host or iso_domains is None:
            LOGGER.info(
                "There are no hosts or no iso domain described in yaml,"
                "can't add shared_iso_domain!"
            )
        else:
            self.import_shared_iso_domain(storage_conf, host)

        self._create_users_groups(GOLDEN_ENV)
