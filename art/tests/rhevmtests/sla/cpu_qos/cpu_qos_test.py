"""
CPU QoS TEST
"""
import pytest

import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.test_handler.exceptions as errors
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    hosts as ll_hosts,
    sla as ll_sla,
    clusters as ll_cluster,
    datacenters as ll_datacenter,
    templates as ll_templates
)
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import SlaTest as TestCase, attr
from rhevmtests import helpers
from rhevmtests.sla.cpu_qos import config

logger = config.logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown(request):
    """
    Setup:
    1. Create 3 VMS for QOS test
    2. Set the default CPU profile ID for each cluster

    Teardown:
    1. Remove all CPU profile except the Default
    2. Remove all CPU QoS
    3. Remove all VMS created in the test
    4. Remove QOS template
    """
    def fin():
        config.QOS_VMS.append(config.QOS_VM_FROM_TEMPLATE)
        assert ll_vms.safely_remove_vms(config.QOS_VMS)
        if ll_templates.get_template_obj(config.QOS_template):
            if not ll_templates.removeTemplate(True, config.QOS_template):
                logger.error(
                    "Failed to remove template %s", config.QOS_template
                )
        for cluster_name in config.CLUSTER_NAME[:2]:
            for profile in ll_cluster.get_all_cpu_profile_names(cluster_name):
                if profile != cluster_name:
                    if not ll_cluster.remove_cpu_profile(
                        cluster_name, profile
                    ):
                        logger.error(
                            "Failed to remove CPU profile %s" % profile
                        )
        for qos in ll_datacenter.get_cpu_qoss_from_data_center(
            config.DC_NAME[0]
        ):
            assert ll_datacenter.delete_qos_from_datacenter(
                config.DC_NAME[0], qos
            )

    request.addfinalizer(fin)

    config.DEFAULT_CPU_PROFILE_ID_CLUSTER_0 = (
        ll_cluster.get_cpu_profile_id_by_name(
            config.CLUSTER_NAME[0], config.CLUSTER_NAME[0]
        )
    )
    config.DEFAULT_CPU_PROFILE_ID_CLUSTER_1 = (
        ll_cluster.get_cpu_profile_id_by_name(
            config.CLUSTER_NAME[1], config.CLUSTER_NAME[1]
        )
    )
    for vm_name in config.QOS_VMS:
        if not ll_vms.createVm(
            positive=True,
            vmName=vm_name,
            vmDescription="QOS VM",
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0]
        ):
            raise errors.VMException("Failed to Create VM %s" % vm_name)


@pytest.fixture()
def clean(request):
    """
    stop Vms
    """
    def fin():
        for vm in config.QOS_VMS:
            if not ll_vms.stopVm(True, vm):
                logger.error("Failed to stop VM %s", vm)

    request.addfinalizer(fin)


@attr(tier=1)
class QOS(TestCase):
    """
    1. test_a_add_qos
    2. test_b_negative_add_qos
    3. test_c_add_cpu_profile
    4. test_d_attach_cpu_profile_to_vm
    5. test_e_negative_remove_cpu_profile_and_qos
    6. test_f_remove_cpu_profile_and_qos
    7. test_g_create_qos_vm_from_template
    8. test_h_sanity
    9. test_i_migration
    10. test_j_cpu_qos_while_hot_plug
    11. test_k_different_QoS_values
    12. test_l_no_guest_agent
    """

    __test__ = True

    @classmethod
    def load_vm_and_check_the_load(cls, load_dict, expected_dict=None):
        """
        1. load vms
        2. check if the vms have expected cpu load percentage

        :param load_dict: keys - vm names , values - load percentage
        :type load_dict: dict
        :param expected_dict: keys - vm names ,values - vm expected cpu percent
        :type: dict
        :return:True if VM gets the expected CPU load, False otherwise
        :rtype: bool
        """
        if expected_dict is None:
            expected_dict = load_dict
        for vm_name, load_value in load_dict.iteritems():
            vm_res = helpers.get_host_resource(
                hl_vms.get_vm_ip(vm_name), config.VMS_LINUX_PW
            )
            if not ll_sla.load_resource_cpu(vm_res, 100):
                logger.error("Failed to load the %s", vm_name)
                return False
        if not helpers.wait_for_vms_gets_to_full_consumption(expected_dict):
            logger.error("VM is not loading the VM %s as expected", vm_name)
            return False
        return True

    @polarion("RHEVM3-14700")
    def test_a_add_qos(self):
        """
        Add 4 QoS with: 10%, 25%, 50% and 75%
        """
        for qos_name, qos_value in config.QOSS.iteritems():
            self.assertTrue(
                ll_datacenter.add_qos_to_datacenter(
                    config.DC_NAME[0], qos_name, "cpu", cpu_limit=qos_value
                )
            )

    @polarion("RHEVM3-14700")
    def test_b_negative_add_qos(self):
        """
        1. Try to set a string in Qos
        2. Try to set a value in QoS that is bigger then 100
        3. Try to set a value in QoS that is smaller then 0
        """
        qoss = {"qos_120": 120, "qos_-5": -5}
        for qos_name, qos_value in qoss.iteritems():
            self.assertFalse(
                ll_datacenter.add_qos_to_datacenter(
                    config.DC_NAME[0], qos_name, "cpu", cpu_limit=qos_value
                )
            )

    @polarion("RHEVM3-14711")
    def test_c_add_cpu_profile(self):
        """
        Add 4 cpu profile that match the QOSS that were already created
        """
        for qos_name in config.QOSS.keys():
            cpu_qos_obj = ll_datacenter.get_qos_from_datacenter(
                config.DC_NAME[0], str(qos_name)
            )
            logger.info(
                "Create cpu profile %s on cluster %s",
                qos_name, config.CLUSTER_NAME[0]
                )
            self.assertTrue(
                ll_cluster.add_cpu_profile(
                    cluster_name=config.CLUSTER_NAME[0],
                    name=qos_name,
                    qos=cpu_qos_obj
                ), "Failed to create cpu profile with qos %s" % qos_name
            )

    @polarion("RHEVM-14932")
    def test_d_attach_cpu_profile_to_vm(self):
        """
        Attach all cpu profiles to VMs
        """
        for vm_name, qos in zip(
            config.QOS_VMS, sorted(config.QOSS.keys())[:3]
        ):
            cpu_profile_id = ll_cluster.get_cpu_profile_id_by_name(
                config.CLUSTER_NAME[0], str(qos)
            )
            self.assertTrue(
                ll_vms.updateVm(
                    positive=True, vm=vm_name,
                    cpu_profile_id=cpu_profile_id
                ), "Failed to update VM cpu profile %s" % qos
            )

    @polarion("RHEVM-14708")
    def test_e_negative_remove_cpu_profile_and_qos(self):
        """
        1. Try to delete a CPU profile that is attached to a VM
        2. Try to delete a Qos that is attached to a VM
        """
        cpu_profile = sorted(config.QOSS.keys())[0]
        self.assertFalse(
            ll_cluster.remove_cpu_profile(
                config.CLUSTER_NAME[0], cpu_profile
            )
        )

    @polarion("RHEVM-14710")
    def test_f_remove_cpu_profile_and_qos(self):
        """
        1. Delete a CPU profile that is not attached to a VM
        2. Delete a Qos that is not attached to a VM
        """
        cpu_qos = sorted(config.QOSS.keys())[3]
        self.assertTrue(
            ll_cluster.remove_cpu_profile(
                config.CLUSTER_NAME[0], cpu_qos
            )
        )
        self.assertTrue(
            ll_datacenter.delete_qos_from_datacenter(
                config.DC_NAME[0], cpu_qos
            )
        )

    @polarion("RHEVM3-14939")
    def test_g_create_qos_vm_from_template(self):
        """
        1. Create a template on first cluster with a CPU profile
        2. Create a VM from the template on second cluster
        3. Check that created and gets the default CPU profile
        """
        cpu_profile_id = ll_cluster.get_cpu_profile_id_by_name(
            config.CLUSTER_NAME[0], str(config.QOSS.keys()[0])
        )
        if not ll_templates.createTemplate(
            True, name=config.QOS_template,
            vm=config.VM_NAME[0],
            vmDescription="QOS VM",
            cluster=config.CLUSTER_NAME[0],
            template=config.TEMPLATE_NAME[0],
            cpu_profile_id=cpu_profile_id

        ):
            raise errors.TemplateException(
                "Failed to create template for pool"
            )
        if not ll_vms.createVm(
            positive=True,
            vmName=config.QOS_VM_FROM_TEMPLATE,
            cluster=config.CLUSTER_NAME[1],
            template=config.QOS_template
        ):
            raise errors.VMException(
                "Failed to Create VM %s" % config.QOS_template
            )
        vm_cpu_profile_id = ll_vms.get_cpu_profile_id(
            config.QOS_VM_FROM_TEMPLATE
        )
        self.assertEqual(
            vm_cpu_profile_id, config.DEFAULT_CPU_PROFILE_ID_CLUSTER_1
        )

    @bz({'1337145': {}})
    @polarion("RHEVM3-14688")
    def test_h_sanity(self):
        """
        1. Start VM
        2. Load VM CPU to 100%
        3. Check that the VM CPU is the right amount CPU,
           that is taken from the host.
        """
        assert ll_vms.startVm(True, config.QOS_VMS[0])
        load_dict = {config.QOS_VMS[0]: sorted(config.QOSS.values())[0]}
        host = ll_vms.get_vm_host(config.QOS_VMS[0])
        host_cpu = ll_hosts.get_host_processing_units_number(host)
        expected_value = host_cpu * 100 / load_dict.values()[0]
        expected_dict = {config.QOS_VMS[0]: expected_value}
        self.assertTrue(
            self.load_vm_and_check_the_load(load_dict, expected_dict)
        )

    @bz({'1337145': {}})
    @polarion("RHEVM3-14697")
    def test_i_migration(self):
        """
        1. Migrate VM to a different host
        2. Load vm CPU to 100%
        3. Check that the VM CPU is the right amount CPU,
           that is taken from the host.
        """
        load_dict = {config.QOS_VMS[0]: sorted(config.QOSS.values())[0]}
        host = ll_vms.get_vm_host(config.QOS_VMS[0])
        if not ll_vms.migrateVm(True, config.QOS_VMS[0]):
            raise errors.VMException("Failed to migrate VM")
        host_cpu = ll_hosts.get_host_processing_units_number(host)
        expected_value = host_cpu * 100 / load_dict.values()[0]
        expected_dict = {config.QOS_VMS[0]: expected_value}
        self.assertTrue(
            self.load_vm_and_check_the_load(load_dict, expected_dict)
        )

    @bz({'1337145': {}})
    @polarion("RHEVM3-14696")
    @pytest.mark.usefixtures("clean")
    def test_j_cpu_qos_while_hot_plug(self):
        """
        1. Load the vms CPU to 100%
        2. See that every VM take CPU resources exactly as set in cpu profile
        3. Preform hot-plug to maximum host processing units
        4. Check if now CPU load increased, as additional CPUs were added
        """
        load_dict = {config.QOS_VMS[0]: sorted(config.QOSS.values())[0]}
        host = ll_vms.get_vm_host(config.QOS_VMS[0])
        host_cpu = ll_hosts.get_host_processing_units_number(host)
        for vm_name in config.QOS_VMS:
            if not ll_vms.updateVm(
                True, vm_name,
                cpu_socket=host_cpu
            ):
                raise errors.VMException(
                    "Failed to update vm %s cpu sockets", vm_name
                )
        self.assertTrue(self.load_vm_and_check_the_load(load_dict))
        return True

    @bz({'1337145': {}})
    @polarion("RHEVM3-14727")
    @pytest.mark.usefixtures("clean")
    def test_k_different_QoS_values(self):
        """
        1. Load the 3 vms with different cpu profiles values CPU to 100%
        2. See that every VM take CPU resources exactly as set in cpu profile
        """
        load_dict = dict(zip(config.QOS_VMS, sorted(config.QOSS.values())))
        vm_cpu = ll_hosts.get_host_processing_units_number(config.HOSTS[0])
        for vm_name in config.QOS_VMS:
            if not ll_vms.updateVm(
                True, vm_name,
                cpu_socket=vm_cpu,
                placement_host=config.HOSTS[0],
                placement_affinity=config.VM_PINNED
            ):
                raise errors.VMException(
                    "Failed to update vm %s", vm_name
                )
        self.assertTrue(self.load_vm_and_check_the_load(load_dict))

    @bz({'1337145': {}})
    @polarion("RHEVM3-14729")
    def test_l_no_guest_agent(self):
        """
        1. Remove guest agent and puppet if exits
        2. Load VM CPU to 100%
        3. Check that VM take CPU resources exactly as set in cpu profile
        """
        load_dict = {config.QOS_VMS[0]: sorted(config.QOSS.values())[0]}
        vm_resource = helpers.get_host_resource(
            hl_vms.get_vm_ip(config.QOS_VMS[0]), config.VMS_LINUX_PW
        )
        if vm_resource.package_manager.exist(config.SERVICE_PUPPET):
            logger.info("remove %s", config.SERVICE_PUPPET)
            if not vm_resource.package_manager.remove(config.SERVICE_PUPPET):
                raise errors.VMException(
                    "Failed to remove %s" % config.SERVICE_PUPPET
                )

        logger.info("Stop %s service", config.SERVICE_GUEST_AGENT)
        if not vm_resource.service(config.SERVICE_GUEST_AGENT).stop():
            raise errors.VMException(
                "Failed to stop service %s on VM %s" %
                (config.SERVICE_GUEST_AGENT, config.QOS_VMS[0])
            )
        self.assertTrue(self.load_vm_and_check_the_load(load_dict))
