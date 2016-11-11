"""
Affinity labels test - check VM start and
migration under affinity labels conditions
"""
import art.rhevm_api.tests_lib.low_level.affinitylabels as ll_afflabels
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import pytest
import rhevmtests.sla.config as sla_conf
from art.test_handler.tools import polarion
from rhevmtests.sla.fixtures import (
    activate_hosts,
    choose_specific_host_as_spm,
    run_once_vms,
    start_vms
)
from rhevmtests.sla.scheduler_tests.fixtures import (
    create_affinity_labels,
    assign_affinity_label_to_element,
    create_affinity_groups
)

host_as_spm = 2


@u_libs.attr(tier=1)
class TestCRUD1(u_libs.SlaTest):
    """
    Basic CRUD tests for affinity labels
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestCRUD1", i
        ) for i in xrange(2)
    ]

    @polarion("RHEVM-15869")
    def test_check_affinity_labels_crud(self):
        """
        1) Create affinity label
        2) Update affinity label
        3) Delete affinity label
        """
        u_libs.testflow.step(
            "Create the affinity label %s", self.affinity_labels[0]
        )
        assert ll_afflabels.AffinityLabels.create(
            name=self.affinity_labels[0]
        )
        u_libs.testflow.step(
            "Update the affinity label %s to have new name %s",
            self.affinity_labels[0], self.affinity_labels[1]
        )
        assert ll_afflabels.AffinityLabels.update(
            old_name=self.affinity_labels[0], name=self.affinity_labels[1]
        )
        u_libs.testflow.step(
            "Delete the affinity label %s", self.affinity_labels[1]
        )
        assert ll_afflabels.AffinityLabels.delete(name=self.affinity_labels[1])


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(create_affinity_labels.__name__)
class TestCRUD2(u_libs.SlaTest):
    """
    Basic CRUD tests to assign and remove affinity label from VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestCRUD2", i
        ) for i in xrange(1)
    ]

    @polarion("RHEVM3-15870")
    def test_check_affinity_labels_crud(self):
        """
        1) Assign affinity label to VM via affinity labels collection
        2) Remove affinity label from VM via affinity labels collection
        3) Assign affinity label to VM via VMS collection
        3) Remove affinity label from VM via VMS collection
        """
        u_libs.testflow.step(
            "Assign the affinity label %s to the VM %s "
            "via affinity label collection",
            self.affinity_labels[0], sla_conf.VM_NAME[0]
        )
        assert ll_afflabels.AffinityLabels.add_label_to_vm(
            label_name=self.affinity_labels[0], vm_name=sla_conf.VM_NAME[0]
        )
        u_libs.testflow.step(
            "Unassign the affinity label %s from the VM %s "
            "via affinity label collection",
            self.affinity_labels[0], sla_conf.VM_NAME[0]
        )
        assert ll_afflabels.AffinityLabels.remove_label_from_vm(
            label_name=self.affinity_labels[0], vm_name=sla_conf.VM_NAME[0]
        )
        u_libs.testflow.step(
            "Assign the affinity label %s to the VM %s via VM's collection",
            self.affinity_labels[0], sla_conf.VM_NAME[0]
        )
        assert ll_vms.add_affinity_label(
            vm_name=sla_conf.VM_NAME[0],
            affinity_label_name=self.affinity_labels[0]
        )
        u_libs.testflow.step(
            "Unassign the affinity label %s from the VM %s "
            "via VM's collection",
            self.affinity_labels[0], sla_conf.VM_NAME[0]
        )
        assert ll_vms.remove_affinity_label(
            vm_name=sla_conf.VM_NAME[0],
            affinity_label_name=self.affinity_labels[0]
        )


@u_libs.attr(tier=1)
@pytest.mark.usefixtures(create_affinity_labels.__name__)
class TestCRUD3(u_libs.SlaTest):
    """
    Basic CRUD tests to assign and remove affinity label from host
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestCRUD3", i
        ) for i in xrange(1)
    ]

    @polarion("RHEVM3-16262")
    def test_check_affinity_labels_crud(self):
        """
        1) Assign affinity label to host via affinity labels collection
        2) Remove affinity label from host via affinity labels collection
        3) Assign affinity label to host via hosts collection
        3) Remove affinity label from host via hosts collection
        """
        u_libs.testflow.step(
            "Assign the affinity label %s to the host %s "
            "via affinity label collection",
            self.affinity_labels[0], sla_conf.HOSTS[0]
        )
        assert ll_afflabels.AffinityLabels.add_label_to_host(
            label_name=self.affinity_labels[0], host_name=sla_conf.HOSTS[0]
        )
        u_libs.testflow.step(
            "Unassign the affinity label %s from the host %s "
            "via affinity label collection",
            self.affinity_labels[0], sla_conf.HOSTS[0]
        )
        assert ll_afflabels.AffinityLabels.remove_label_from_host(
            label_name=self.affinity_labels[0], host_name=sla_conf.HOSTS[0]
        )
        u_libs.testflow.step(
            "Assign the affinity label %s to the host %s via hosts collection",
            self.affinity_labels[0], sla_conf.HOSTS[0]
        )
        assert ll_hosts.add_affinity_label(
            host_name=sla_conf.HOSTS[0],
            affinity_label_name=self.affinity_labels[0]
        )
        u_libs.testflow.step(
            "Unassign the affinity label %s from the host %s "
            "via hosts collection",
            self.affinity_labels[0], sla_conf.HOSTS[0]
        )
        assert ll_hosts.remove_affinity_label(
            host_name=sla_conf.HOSTS[0],
            affinity_label_name=self.affinity_labels[0]
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    start_vms.__name__
)
class TestAffinityLabels1(u_libs.SlaTest):
    """
    Check the positive behavior of affinity labels, when start VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels1", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False

    @polarion("RHEVM-15871")
    def test_check_where_vm_started(self):
        """
        Check if VM with the affinity label,
        started on the host with the same affinity label
        """
        u_libs.testflow.step(
            "Check that VM %s starts on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(sla_conf.VM_NAME[0]) == sla_conf.HOSTS[0]


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
)
class TestAffinityLabels2(u_libs.SlaTest):
    """
    Check the negative behavior of affinity labels, when start VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels2", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "vms": [sla_conf.VM_NAME[0]]
        }
    }

    @polarion("RHEVM-15871")
    def test_check_if_vm_started(self):
        """
        Check that VM with the affinity label, failed to start
        in the cluster that does not have hosts with the same affinity label
        """
        u_libs.testflow.step("Start the VM %s", sla_conf.VM_NAME[0])
        assert not ll_vms.startVm(positive=True, vm=sla_conf.VM_NAME[0])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    run_once_vms.__name__
)
class TestAffinityLabels3(u_libs.SlaTest):
    """
    Check positive behavior of affinity labels, when user migrate VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels3", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0, 1],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_run = {sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0}}

    @polarion("RHEVM-15873")
    def test_check_if_vm_migrated(self):
        """
        Check if VM with the affinity label, migrate on hosts with
        the same affinity label
        """
        u_libs.testflow.step("Migrate the VM %s", sla_conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=sla_conf.VM_NAME[0])
        u_libs.testflow.step(
            "Check that VM %s migrates on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[1]
        )
        assert sla_conf.HOSTS[1] == ll_vms.get_vm_host(sla_conf.VM_NAME[0])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    start_vms.__name__
)
class TestAffinityLabels4(u_libs.SlaTest):
    """
    Check negative behavior of affinity labels, when user migrate VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels4", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False

    @polarion("RHEVM-15874")
    def test_check_if_vm_migrated(self):
        """
        Check if VM with the affinity label, failed to migrate in cluster
        that has only one host with the same affinity label
        """
        u_libs.testflow.step(
            "Check that VM %s starts on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert sla_conf.HOSTS[0] == ll_vms.get_vm_host(sla_conf.VM_NAME[0])
        u_libs.testflow.step("Migrate the VM %s", sla_conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=sla_conf.VM_NAME[0])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    run_once_vms.__name__,
    activate_hosts.__name__
)
class TestAffinityLabels5(u_libs.SlaTest):
    """
    Check positive behavior of labels, when system migrate VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels5", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0, 1],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_run = {sla_conf.VM_NAME[0]: {sla_conf.VM_RUN_ONCE_HOST: 0}}
    hosts_to_activate_indexes = [0]

    @polarion("RHEVM-15875")
    def test_check_if_vm_migrated(self):
        """
        Check if VM with the affinity label, migrate on hosts with
        the same affinity label, when user put source host to maintenance
        """
        u_libs.testflow.step("Deactivate host %s", sla_conf.HOSTS[0])
        assert ll_hosts.deactivate_host(positive=True, host=sla_conf.HOSTS[0])
        u_libs.testflow.step(
            "Check that VM %s runs on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[1]
        )
        assert sla_conf.HOSTS[1] == ll_vms.get_vm_host(sla_conf.VM_NAME[0])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    start_vms.__name__,
    activate_hosts.__name__
)
class TestAffinityLabels6(u_libs.SlaTest):
    """
    Check negative behavior of labels, when system migrate VM
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels6", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False
    hosts_to_activate_indexes = [0]

    @polarion("RHEVM-15876")
    def test_check_if_vm_migrated(self):
        """
        Check if VM with the affinity label, failed to migrate in cluster
        that has only one host with the same affinity label,
        when user put source host to maintenance
        """
        u_libs.testflow.step(
            "Check that VM %s runs on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert sla_conf.HOSTS[0] == ll_vms.get_vm_host(sla_conf.VM_NAME[0])
        u_libs.testflow.step("Deactivate host %s", sla_conf.HOSTS[0])
        assert not ll_hosts.deactivate_host(
            positive=True, host=sla_conf.HOSTS[0], timeout=120
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestAffinityLabels7(u_libs.SlaTest):
    """
    Add two VM's to the hard positive affinity group,
    attach different labels to VM's and start VM's
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels7", i
        ) for i in xrange(2)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        },
        affinity_labels[1]: {
            "hosts": [1],
            "vms": [sla_conf.VM_NAME[1]]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False
    affinity_groups = {
        "TestAffinityLabels7": {
            sla_conf.AFFINITY_GROUP_POSITIVE: True,
            sla_conf.AFFINITY_GROUP_ENFORCING: True,
            sla_conf.AFFINITY_GROUP_VMS: sla_conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM-15975")
    def test_check_if_vm_started(self):
        """
        Check that second VM in the hard positive affinity group failed
        to start because collision between affinity group and affinity labels
        """
        u_libs.testflow.step("Start the VM %s", sla_conf.VM_NAME[1])
        assert not ll_vms.startVm(positive=True, vm=sla_conf.VM_NAME[1])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestAffinityLabels8(u_libs.SlaTest):
    """
    Add two VM's to the hard negative affinity group,
    attach the same label to VM's and start VM's
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels8", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": sla_conf.VM_NAME[:2]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False
    affinity_groups = {
        "TestAffinityLabels8": {
            sla_conf.AFFINITY_GROUP_POSITIVE: False,
            sla_conf.AFFINITY_GROUP_ENFORCING: True,
            sla_conf.AFFINITY_GROUP_VMS: sla_conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM-16079")
    def test_check_if_vm_started(self):
        """
        Check that second VM in the hard negative affinity group failed
        to start because collision between affinity group and affinity labels
        """
        u_libs.testflow.step("Start the VM %s", sla_conf.VM_NAME[1])
        assert not ll_vms.startVm(positive=True, vm=sla_conf.VM_NAME[1])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestAffinityLabels9(u_libs.SlaTest):
    """
    Add two VM's to the soft positive affinity group,
    attach different labels to VM's and start VM's
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels9", i
        ) for i in xrange(2)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        },
        affinity_labels[1]: {
            "hosts": [1],
            "vms": [sla_conf.VM_NAME[1]]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False
    affinity_groups = {
        "TestAffinityLabels9": {
            sla_conf.AFFINITY_GROUP_POSITIVE: True,
            sla_conf.AFFINITY_GROUP_ENFORCING: False,
            sla_conf.AFFINITY_GROUP_VMS: sla_conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM-16080")
    def test_check_if_vm_started(self):
        """
        Check that second VM in the soft positive affinity
        group succeed to start
        """
        u_libs.testflow.step("Start the VM %s", sla_conf.VM_NAME[1])
        assert ll_vms.startVm(positive=True, vm=sla_conf.VM_NAME[1])
        u_libs.testflow.step("Stop the VM %s", sla_conf.VM_NAME[1])
        assert ll_vms.stopVm(positive=True, vm=sla_conf.VM_NAME[1])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    create_affinity_groups.__name__,
    start_vms.__name__
)
class TestAffinityLabels10(u_libs.SlaTest):
    """
    Add two VM's to the soft negative affinity group,
    attach different labels to VM's and start VM's
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels10", i
        ) for i in xrange(1)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": sla_conf.VM_NAME[0:2]
        }
    }
    vms_to_start = [sla_conf.VM_NAME[0]]
    wait_for_vms_ip = False
    affinity_groups = {
        "TestAffinityLabels10": {
            sla_conf.AFFINITY_GROUP_POSITIVE: False,
            sla_conf.AFFINITY_GROUP_ENFORCING: False,
            sla_conf.AFFINITY_GROUP_VMS: sla_conf.VM_NAME[:2]
        }
    }

    @polarion("RHEVM-16081")
    def test_check_if_vm_started(self):
        """
        Check that second VM in the soft negative affinity
        group succeed to start
        """
        u_libs.testflow.step("Start the VM %s", sla_conf.VM_NAME[1])
        assert ll_vms.startVm(positive=True, vm=sla_conf.VM_NAME[1])
        u_libs.testflow.step("Stop the VM %s", sla_conf.VM_NAME[1])
        assert ll_vms.stopVm(positive=True, vm=sla_conf.VM_NAME[1])


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    start_vms.__name__
)
class TestAffinityLabels11(u_libs.SlaTest):
    """
    Create two different affinity labels on the host and check if VM's
    succeed to start on it
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels11", i
        ) for i in xrange(2)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        },
        affinity_labels[1]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[1]]
        }
    }
    vms_to_start = sla_conf.VM_NAME[:2]
    wait_for_vms_ip = False

    @polarion("RHEVM-16082")
    def test_check_where_vm_started(self):
        """
        Check if VM's with the affinity label,
        started on the host with the same affinity label
        """
        u_libs.testflow.step(
            "Check that VM %s runs on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(sla_conf.VM_NAME[0]) == sla_conf.HOSTS[0]
        u_libs.testflow.step(
            "Check that VM %s runs on the host %s",
            sla_conf.VM_NAME[1], sla_conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(sla_conf.VM_NAME[1]) == sla_conf.HOSTS[0]


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    create_affinity_labels.__name__,
    assign_affinity_label_to_element.__name__,
    start_vms.__name__
)
class TestAffinityLabels12(u_libs.SlaTest):
    """
    Create two different affinity labels on the VM and check if it can start
    on the host with the same labels
    """
    __test__ = True
    affinity_labels = [
        "{0}_{1}_{2}".format(
            __name__.split(".")[-1], "TestAffinityLabels12", i
        ) for i in xrange(2)
    ]
    affinity_label_to_element = {
        affinity_labels[0]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        },
        affinity_labels[1]: {
            "hosts": [0],
            "vms": [sla_conf.VM_NAME[0]]
        }
    }
    vms_to_start = sla_conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @polarion("RHEVM-16083")
    def test_check_where_vm_started(self):
        """
        1) Check that VM runs on correct host
        """
        u_libs.testflow.step(
            "Check that VM %s runs on the host %s",
            sla_conf.VM_NAME[0], sla_conf.HOSTS[0]
        )
        assert ll_vms.get_vm_host(sla_conf.VM_NAME[0]) == sla_conf.HOSTS[0]


@u_libs.attr(tier=1)
class TestSanityAffinityLabelName(u_libs.SlaTest):
    """
    Sanity tests on affinity label name
    """
    __test__ = True

    @polarion("RHEVM-16297")
    def test_create_affinity_label(self):
        """
        1) Create affinity label with too long name
        2) Create affinity label with that includes special characters
        """
        u_libs.testflow.step("Create the affinity label %s", "a" * 51)
        assert not ll_afflabels.AffinityLabels.create(name=("a" * 51))
        special_name = "*@_@*"
        u_libs.testflow.step("Create the affinity label %s", special_name)
        assert not ll_afflabels.AffinityLabels.create(name=special_name)
