from art.core_api.apis_exceptions import EntityNotFound
from art.unittest_lib import BaseTestCase, testflow

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    clusters as ll_clusters,
    external_providers as ll_ep,
    storagedomains as ll_sd,
    vms as ll_vms,
    templates as ll_templates,
)
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    clusters as hl_clusters,
    storagedomains as hl_sd,
)

from art.rhevm_api.utils.test_utils import wait_for_tasks
import golden_env.config as config
from art.rhevm_api import resources

import logging
import shlex

logger = logging.getLogger(__name__)

GLOBAL_MAINTENANCE_CMD = "hosted-engine --set-maintenance --mode=global"
SHUTDOWN_VM = "hosted-engine --vm-poweroff"
SANLOCK_SHUTDOWN_CMD = "sanlock client shutdown -f 1"
OVIRT_HA_AGENT_SRV = "ovirt-ha-agent"
OVIRT_HA_BROKER_SRV = "ovirt-ha-broker"
SANLOCK_SRV = "sanlock"
WDMD_SRV = "wdmd"
SRV_TIMEOUT = 300
HOSTED_ENGINE_HA_PACKAGE = "rhevm-appliance"
DEL_STORAGE_ISCSI = "dd if=/dev/zero of=/dev/mapper/%s bs=1024k count=10"
MOUNT_PATH = "/rhev/data-center/mnt/*"
UMOUNT_CMD = "umount {0}"
RM_MOUNT_CMD = "rm -rf {0}"


def clean_he_env():
    """
    Clean the Golden Environment(GE) in case of hosted engine deployed
    """

    hosted_host = resources.Host(config.HE_HOST_IP)
    hosted_host.users.append(resources.RootUser(config.PASSWORDS[0]))
    hosts_with_he_cap = [hosted_host]

    for host_ip in config.HE_ADDITIONAL_HOSTS:
        host_resource = resources.Host(host_ip)
        host_resource.users.append(resources.RootUser(config.PASSWORDS[0]))
        hosts_with_he_cap.append(host_resource)

    testflow.step("Set the Hosted Engine Cluster, to Global Maintenance mode")
    hosted_host.run_command(shlex.split(GLOBAL_MAINTENANCE_CMD))
    testflow.step("Power-off the Hosted Engine VM")
    hosted_host.run_command(shlex.split(SHUTDOWN_VM))

    for host in hosts_with_he_cap:
        testflow.step("Stop the %s on %s", OVIRT_HA_AGENT_SRV, host.ip)
        if not host.service(OVIRT_HA_AGENT_SRV, timeout=SRV_TIMEOUT).stop():
            logger.error(
                "Failed to stop the service %s", OVIRT_HA_AGENT_SRV
            )
        testflow.step("Stop the %s on %s", OVIRT_HA_BROKER_SRV, host.ip)
        if not host.service(OVIRT_HA_BROKER_SRV, timeout=SRV_TIMEOUT).stop():
            logger.error(
                "Failed to stop the service %s", OVIRT_HA_BROKER_SRV
            )
        testflow.step("Sanlock force shutdown")
        host.run_command(shlex.split(SANLOCK_SHUTDOWN_CMD))

    if config.HE_SD_LUN:
        testflow.step("Delete the content of lun: %s", config.HE_SD_LUN)
        del_lun_cmd = DEL_STORAGE_ISCSI % config.HE_SD_LUN
        hosted_host.run_command(shlex.split(del_lun_cmd))

    for host in hosts_with_he_cap:
        testflow.step("Remove & clean the mount %s on %s", MOUNT_PATH, host.ip)
        if not host.run_command(shlex.split(UMOUNT_CMD.format(MOUNT_PATH))):
            logger.error("Failed to umount %s", MOUNT_PATH)
        if not host.run_command(shlex.split(RM_MOUNT_CMD.format(MOUNT_PATH))):
            logger.error("Failed to clean mount point %s", MOUNT_PATH)
        testflow.step("Restart the %s on %s", SANLOCK_SRV, host.ip)
        if not host.service(SANLOCK_SRV, timeout=SRV_TIMEOUT).restart():
            logger.error("Failed to stop the service %s", SANLOCK_SRV)

    testflow.step("Remove the %s from %s", HOSTED_ENGINE_HA_PACKAGE, host.ip)
    if not hosted_host.package_manager.remove(HOSTED_ENGINE_HA_PACKAGE):
        logger.error("Failed to remove HE packages from host %s", host.ip)


def remove_vms_and_templates():
    vm_names = ll_vms.get_all_vms_names()
    if config.HE_VM_NAME in vm_names:
        vm_names.remove(config.HE_VM_NAME)

    if vm_names:
        testflow.step("Remove VMs: %s", vm_names)
        ll_vms.removeVms(True, vm_names, stop='true', timeout=300)
    template_names = ll_templates.get_all_template_objects_names()
    if 'Blank' in template_names:
        template_names.remove('Blank')
    if template_names:
        testflow.step("Remove templates: %s", template_names)
        ll_templates.removeTemplates(True, template_names)


def remove_disks_and_sds():
    sds = ll_sd.get_storage_domains()
    hosts = ll_hosts.get_host_names_list()
    dcs_list = ll_dc.get_datacenters_list()
    if config.HE_SD_NAME:
        sds = [
            sd for sd in sds
            if sd.get_name() != config.HE_SD_NAME and not sd.get_master()
        ]

    if hosts and sds:
        for sd in sds:
            testflow.step("Clean disks from storage: %s", sd.get_name())
            ll_sd.remove_floating_disks(sd)
        for dc in dcs_list:
            wait_for_tasks(
                vdc=config.VDC,
                vdc_password=config.VDC_PASSWORD,
                datacenter=dc.get_name(),
                db_name=config.DB_NAME,
                db_user=config.DB_USER
            )
        for sd in sds:
            if sd.get_master():
                continue
            sd_name = sd.get_name()
            sd_dcs = sd.get_data_centers()
            sd_dcs = sd_dcs.get_data_center() if sd_dcs else []
            for sd_dc in sd_dcs:
                dc_name = ll_dc.get_data_center(
                    sd_dc.get_id(), key="id"
                ).get_name()
                hl_sd.detach_and_deactivate_domain(dc_name, sd_name)
            if sd.get_type() != 'image':
                testflow.step("Remove SD: %s", sd_name)
                ll_sd.removeStorageDomain(True, sd_name, hosts[0])


def remove_users_groups():
    engine = resources.Engine(
        config.ENGINE_HOST,
        resources.ADUser(
            'admin', config.VDC_PASSWORD, resources.Domain('internal')
        )
    )
    what_remove_list = ['user', 'group']
    for what_remove in what_remove_list:
        rc, out, err = engine.ovirt_aaa_jdbc_tool('list', what_remove)
        if not rc and out:
            assert not rc, "Failed to get list of %s" % what_remove
            list_for_remove = out.splitlines()
            for remove_name in list_for_remove:
                if what_remove == 'user' and remove_name == 'admin':
                    continue
                testflow.step("Removing %s: %s", what_remove, remove_name)
                delete_results = engine.ovirt_aaa_jdbc_tool(
                    'delete', what_remove, remove_name
                )
                assert not delete_results[0], (
                    "Failed to delete %s: %s with err: " % (
                        what_remove, remove_name, delete_results[2]
                    )
                )


class CleanGoldenEnv(BaseTestCase):

    __test__ = True

    def test_clean_dc(self):
        """
        Clean the GE. For each DC (including default) list the attached
        clusters and hosts, remove SDs connected to DC and DC itself.
        Remove all hosts and clusters listed. In case there were clusters
        unattached to DC, they and the hosts attached to them
        will also be removed.
        """

        remove_users_groups()
        remove_vms_and_templates()
        remove_disks_and_sds()

        for glance_ep in ll_ep.get_glance_ep_objs():
            testflow.step(
                "Remove glance image external provider: %s",
                glance_ep.get_name()
            )
            ll_ep.remove_glance_ep(glance_ep.get_name())

        for cinder_ep in ll_ep.get_cinder_ep_objs():
            testflow.step(
                "Remove cinder volume external provider: %s",
                cinder_ep.get_name()
            )
            ll_ep.remove_cinder_ep(cinder_ep.get_name())

        for dc in ll_dc.get_datacenters_list():
            testflow.step("Clean datacenter: %s", dc.get_name())
            hl_dc.clean_datacenter(
                True,
                dc.name,
                vdc=config.VDC,
                vdc_password=config.VDC_PASSWORD,
                hosted_engine_vm=config.HE_VM_NAME,
                hosted_engine_sd=config.HE_SD_NAME,
            )
        for cluster in ll_clusters.get_cluster_list():
            cl_name = cluster.get_name()
            hosts_to_remove = (
                hl_clusters.get_hosts_connected_to_cluster(cluster.get_id())
            )
            if config.HE_VM_NAME:
                hosted_host = ll_vms.get_vm_host(config.HE_VM_NAME)
                hosts_to_remove = [
                    h for h in hosts_to_remove if h.get_name() != hosted_host
                ]
                ll_hosts.select_host_as_spm(
                    positive=True, host=hosted_host, data_center=dc.name
                )

            for host in hosts_to_remove:
                testflow.step(
                    "Remove host: %s from cluster: %s", host.get_name(),
                    cl_name
                )
                ll_hosts.removeHost(
                    positive=True, host=host.get_name(), deactivate=True
                )
            if cl_name != config.HE_CL_NAME:
                testflow.step("Remove cluster: %s", cl_name)
                ll_clusters.removeCluster(True, cl_name)
        for glance_ep in ll_ep.get_glance_ep_objs():
            testflow.step(
                "Remove glance image external provider: %s",
                glance_ep.get_name()
            )
            ll_ep.remove_glance_ep(glance_ep.get_name())
        for cinder_ep in ll_ep.get_cinder_ep_objs():
            testflow.step(
                "Remove cinder volume external provider: %s",
                cinder_ep.get_name()
            )
            ll_ep.remove_cinder_ep(cinder_ep.get_name())

        try:
            if config.HE_VM_NAME and ll_vms.get_vm(config.HE_VM_NAME):
                clean_he_env()
        except EntityNotFound:
            logger.error(
                "Failed to get the Hosted Engine VM, Please make sure you"
                " need HE details in the conf file of this GE"
            )
