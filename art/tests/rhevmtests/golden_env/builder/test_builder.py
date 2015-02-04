import logging

import os

from art.unittest_lib import BaseTestCase as TestCase

from art.rhevm_api.utils import test_utils

from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import templates
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd

from art.rhevm_api.tests_lib.high_level import storagedomains

import art.test_handler.exceptions as errors

import config
LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS
GB = 1024 * 1024 * 1024
HOME = os.environ.get('HOME', '.')
INVENTORY_FILE = 'golden_env_hosts.txt'


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
        if 'gluster_domain_address' in configuration:
            self.gluster_addresses = configuration.as_list(
                'gluster_domain_address')
            self.gluster_paths = configuration.as_list('gluster_domain_path')
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
        self.unused_gluster_shares = zip(
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

    def get_unused_gluster_share(self):
        return self.unused_gluster_shares.pop(0)

    def get_unused_local_share(self):
        return self.unused_local_paths.pop(0)

    def get_export_share(self):
        return self.export_shares.pop(0)


class CreateDC(TestCase):
    __test__ = True

    def build_cluster(self, cl_def, dc_name, comp_version, host_conf):
        cluster_name = cl_def['name']
        cpu_name = cl_def['cpu_name']

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
            if not hosts.addHost(
                    True, host_def['host']['name'], address=host_ip,
                    root_password=host_pwd, wait=False, cluster=cluster_name):
                raise errors.HostException("Cannot add host")

        if not hosts.waitForHostsStates(
                True,
                ",".join([x['host']['name'] for x in hosts_def])):
            raise errors.HostException("Hosts are not up")

    def add_sds(self, storages, host, datacenter_name, storage_conf):
        for sd in storages:
            sd_name = sd['storage_domain']['name']
            storage_type = sd['storage_domain']['storage_type']
            if storage_type == ENUMS['storage_type_nfs']:
                address, path = storage_conf.get_nfs_share()
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
                    override_luns=True
                )
            elif storage_type == ENUMS['storage_type_gluster']:
                address, path, vfs = storage_conf.get_unused_gluster_share()
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
        assert vms.createVm(
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
        assert vms.waitForVMState(vm_name, state=ENUMS['vm_state_up'])
        assert vms.stopVm(True, vm_name)

    def _seal_vm(self, vm_name, vm_password):
        vm_state = vms.get_vm_state(vm_name)
        if vm_state == ENUMS['vm_state_down']:
            vms.startVm(True, vm_name, wait_for_status=ENUMS['vm_state_up'])

        LOGGER.info("Waiting for IP of %s", vm_name)
        status, result = vms.waitForIP(vm_name)
        assert status

        LOGGER.info("Sealing: set persistent network for %s", vm_name)

        assert test_utils.setPersistentNetwork(
            result['ip'], vm_password)
        LOGGER.info("Stopping %s to create template", vm_name)
        assert vms.stopVm(True, vm_name)

    def _create_and_seal_vm(self, vm, dc_name, cl_name):
        self._create_vm(vm, dc_name, cl_name)
        self._seal_vm(vm['name'], vm['password'])

    def add_vms(self, vms_def, dc_name, cl_name):
        """ add description
        """
        if not vms_def:
            return

        for vm_description in vms_def:
            LOGGER.info(vm_description)
            prefix_vm_name = vm_description['vm']['name']
            if 'number_of_vms' in vm_description['vm']:
                LOGGER.info(
                    "Creating a template and clone %s vms out of it",
                    vm_description['vm']['number_of_vms']
                )
                suffix_num = 0
                vm_description['vm']['name'] += repr(suffix_num)
                suffix_num += 1
                self._create_and_seal_vm(
                    vm_description['vm'],
                    dc_name,
                    cl_name
                )
                tmp_template = "tmp_template"
                template_creation_status = templates.createTemplate(
                    True,
                    vm=vm_description['vm']['name'],
                    name=tmp_template, cluster=cl_name
                )
                assert template_creation_status

                cloned_vms = []
                while suffix_num < vm_description['vm']['number_of_vms']:
                    vm_description['vm']['name'] = prefix_vm_name
                    vm_description['vm']['name'] += repr(suffix_num)
                    suffix_num += 1
                    LOGGER.info(
                        "Cloning vm %s from template %s",
                        vm_description['vm']['name'], tmp_template
                    )

                    vms.cloneVmFromTemplate(
                        True,
                        vm_description['vm']['name'], tmp_template,
                        cl_name,
                        vol_sparse=vm_description['vm']['disk_sparse'],
                        vol_format=vm_description['vm']['disk_format'],
                        wait=False)

                    cloned_vms.append(vm_description['vm']['name'])

                for cloned_vm in cloned_vms:
                    LOGGER.info("Waiting until %s state is down...", cloned_vm)
                    assert vms.waitForVMState(
                        cloned_vm,
                        state=ENUMS['vm_state_down']
                    )

                assert templates.removeTemplate(True, tmp_template)
            else:
                LOGGER.info("Creating a new vm")
                self._create_and_seal_vm(
                    vm_description['vm'],
                    dc_name,
                    cl_name
                )

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

    def add_templates(self, templ_def, cluster, datacenter):
        sds = ll_sd.getDCStorages(datacenter, False)
        data_type = ENUMS['storage_dom_type_data']
        data_sds = [x.get_name() for x in sds if x.get_type() == data_type]
        for template in templ_def:
            template_name = template['template']['name']
            assert templates.createTemplate(
                True, vm=template['template']['base_vm'], name=template_name,
                cluster=cluster)
            self.copy_template_disks(template_name, data_sds)

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
                cluster['cluster'], datacenter_name, comp_version, host_conf)
            LOGGER.info("Cluster %s added", cluster['cluster']['name'])
        LOGGER.info("Added all clusters")

        if clusters[0]['cluster']['hosts']:
            LOGGER.info("Adding storage domains")
            storages = dc_def['storage_domains']
            host = clusters[0]['cluster']['hosts'][0]['host']['name']
            if storages is not None:
                self.add_sds(storages, host, datacenter_name, storage_conf)
            else:
                LOGGER.info("No storage_domains on yaml description file")
        else:
            LOGGER.info("No hosts, so no adding storages")

        for cluster in clusters:
            cl_def = cluster['cluster']
            vms_def = cl_def['vms']
            if vms_def:
                LOGGER.info("Adding vms")
                self.add_vms(
                    vms_def, datacenter_name, cl_def['name'])
            else:
                LOGGER.info("No vms to add")

            templ_def = cl_def['templates']
            if templ_def:
                LOGGER.info("Adding templates")
                self.add_templates(templ_def, cl_def['name'], datacenter_name)
            else:
                LOGGER.info("No templates to add")

    def add_export_domain(self, export_domain, storage_conf, host):
        if export_domain['name']:
            name = export_domain['name']
            address, path = storage_conf.get_export_share()
            assert ll_sd.addStorageDomain(
                True, name=name, type=ENUMS['storage_dom_type_export'],
                storage_type=ENUMS['storage_type_nfs'],
                path=path,
                address=address,
                host=host
            )
        else:
            LOGGER.info("Please provide name to your export domain")

    def import_shared_iso_domain(self, storage_conf, host):
        address, path = storage_conf.get_shared_iso()
        LOGGER.info("Importing iso domain %s:%s", address, path)
        assert ll_sd.importStorageDomain(
            True, ENUMS['storage_dom_type_iso'], ENUMS['storage_type_nfs'],
            address[0], path[0], host)

    def test_build_env(self):
        GOLDEN_ENV = config.ART_CONFIG['prepared_env']
        dcs = GOLDEN_ENV[0]['dcs']
        storage_conf = StorageConfiguration(config.STORAGE)
        host_conf = HostConfiguration(config.HOSTS, config.PASSWORDS)
        for dc in dcs:
            self.build_dc(dc['dc'], host_conf, storage_conf)

        export_domains = GOLDEN_ENV[1]['export_domains']
        host = ''
        if export_domains is None:
            LOGGER.info("No export_domains to add!")
        else:
            host = (hosts.get_host_list()[0]).get_name()
            for export_domain in export_domains:
                self.add_export_domain(
                    export_domain['export_domain'], storage_conf, host)

        iso_domains = GOLDEN_ENV[2]['iso_domains']
        if not host or iso_domains is None:
            LOGGER.info(
                "There are no hosts or no iso domain described in yaml,"
                "can't add shared_iso_domain!"
            )
        else:
            host = (hosts.get_host_list()[0]).get_name()
            self.import_shared_iso_domain(storage_conf, host)

        GoldenEnvironmentInventory.write_host_list_to_file()


class GoldenEnvironmentInventory(object):
    """ This class collects information about entities on engine.
    At the moment it collects the host list.
    We need to keep the list on file to allow the log collection to work
    on the end of the golden_env_runner job.
    """
    @staticmethod
    def write_host_list_to_file():
        LOGGER.info(
            "Write list of hosts available in engine to %s/%s",
            HOME, INVENTORY_FILE
        )
        host_objects = hosts.get_host_list()

        with open(os.path.join(HOME, INVENTORY_FILE), 'w') as fd:
            fd.write(','.join([x.get_address() for x in host_objects]))
