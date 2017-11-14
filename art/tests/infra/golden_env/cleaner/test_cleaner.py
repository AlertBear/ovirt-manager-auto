from art.unittest_lib import BaseTestCase, testflow

from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    clusters as ll_clusters,
    external_providers as ll_ep,
    storagedomains as ll_sd,
    vms as ll_vms,
    templates as ll_templates,
    vmpools as ll_vmpools,
)
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    clusters as hl_clusters,
    storagedomains as hl_sd,
)

from art.rhevm_api.utils.test_utils import wait_for_tasks
import config
from art.rhevm_api import resources

import logging

logger = logging.getLogger(__name__)


def remove_vm_pools():
    for vmpool in ll_vmpools.get_all_vm_pools_names():
        testflow.step("Remove VMPool: %s", vmpool)
        ll_vmpools.removeVmPool(positive=True, vmpool=vmpool)


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
        ll_templates.remove_templates(True, template_names)


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
            wait_for_tasks(engine=config.ENGINE, datacenter=dc.get_name())
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
                hl_sd.detach_and_deactivate_domain(
                    dc_name, sd_name, engine=config.ENGINE
                )
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
                    "Failed to delete %s: %s with err: %s" % (
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
        remove_vm_pools()
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
                engine=config.ENGINE,
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
                ll_hosts.remove_host(
                    positive=True, host=host.get_name(), deactivate=True
                )
            if cl_name != config.HE_CL_NAME:
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
