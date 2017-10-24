"""
AREM test - check automatic migration of VM's under different affinity rules
"""
import pytest
import rhevmtests.compute.sla.config as conf
import rhevmtests.compute.sla.scheduler_tests.helpers as sch_helpers
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    choose_specific_host_as_spm,
    run_once_vms,
    start_vms,
    update_vms,
    update_vms_memory_to_hosts_memory,
    update_vms_to_default_parameters,
    update_cluster,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
from art.test_handler.tools import polarion
from art.unittest_lib import tier2, SlaTest
from rhevmtests.compute.sla.scheduler_tests.fixtures import (
    create_affinity_groups,
    load_hosts_cpu,
    wait_for_scheduling_memory_update,
)

host_as_spm = 0


@pytest.fixture(scope="module")
def deactivate_third_host(request):
    """
    1) Deactivate third host in the cluster
    """
    def fin():
        """
        1) Activate third host in the cluster
        """
        ll_hosts.activate_host(
            positive=True, host=conf.HOSTS[2], host_resource=conf.VDS_HOSTS[2]
        )
    request.addfinalizer(fin)

    assert ll_hosts.deactivate_host(
        positive=True, host=conf.HOSTS[2], host_resource=conf.VDS_HOSTS[2]
    )


@pytest.mark.usefixtures(
    choose_specific_host_as_spm.__name__,
    deactivate_third_host.__name__
)
class BaseAREM(SlaTest):
    """
    Base class for all AREM tests
    """
    pass


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM1(BaseAREM):
    """
    Check AREM for positive hard affinity group

    1) Run two VM's on different hosts
    2) Add VM's to the hard positive affinity group
    3) Check if one of VM's migrated by system on the host with the second VM
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    affinity_groups = {
        "test_arem_1": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_stop = conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM3-10923")
    def test_check_balancing(self):
        """
        Check if some of VM's migrate on or from the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM2(BaseAREM):
    """
    Check AREM for negative hard affinity group

    1) Run two VM's on the same host
    2) Add VM's to the hard negative affinity group
    3) Check if one of VM's migrated by system on the other host
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 0}
    }
    affinity_groups = {
        "test_arem_2": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_stop = conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM3-10924")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from the host
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM3(BaseAREM):
    """
    Check AREM for positive soft affinity group

    1) Run two VM's on the different hosts
    2) Add VM's to the soft positive affinity group
    3) Check that VM's stay on the old hosts
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    affinity_groups = {
        "test_arem_3": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_stop = conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM3-12536")
    def test_check_balancing(self):
        """
        Check if some of VM's migrate on or from the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM4(BaseAREM):
    """
    Check AREM for negative soft affinity group

    1) Run two VM's on the same host
    2) Add VM's to the soft negative affinity group
    3) Check that VM's stay on the old host
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 0}
    }
    affinity_groups = {
        "test_arem_4": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: False,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    vms_to_stop = conf.VM_NAME[:2]

    @tier2
    @polarion("RHEVM3-12537")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    update_cluster.__name__,
    wait_for_scheduling_memory_update.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    update_vms_to_default_parameters.__name__,
    start_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM5(BaseAREM):
    """
    Check AREM for positive hard affinity group under
    additional memory restriction

    1) Update each VM's memory to the free host memory
    2) Start VM's, they must start on different hosts because memory constraint
    3) Add VM's to the positive hard affinity group
    4) Check that VM's stay on the old hosts because memory constraint
    """
    cluster_to_update_params = {
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    vms_to_start = conf.VM_NAME[:2]
    update_vms_memory = conf.VM_NAME[:2]
    update_to_default_params = conf.VM_NAME[:2]
    vms_to_stop = conf.VM_NAME[:2]
    affinity_groups = {
        "test_arem_5": {
            conf.AFFINITY_GROUP_POSITIVE: True,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }

    @tier2
    @polarion("RHEVM3-10927")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from or on the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    update_cluster.__name__,
    wait_for_scheduling_memory_update.__name__,
    update_vms.__name__,
    update_vms_memory_to_hosts_memory.__name__,
    update_vms_to_default_parameters.__name__,
    run_once_vms.__name__,
    create_affinity_groups.__name__
)
class TestAREM6(BaseAREM):
    """
    Check AREM for negative hard affinity group

    1) Update additional VM memory to the free host memory
    2) Start two VM's on the same host, and additional VM on the other host
    3) Add VM's to the negative hard affinity group
    4) Check that VM's stay on the old hosts because memory constraint
    """
    cluster_to_update_params = {
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.VM_NAME[2]: {conf.VM_RUN_ONCE_HOST: 1}
    }
    vms_to_params = dict(
        (
            vm_name, {conf.VM_MEMORY: 3 * conf.GB}
        ) for vm_name in conf.VM_NAME[1:3]
    )
    update_vms_memory = conf.VM_NAME[:1]
    update_to_default_params = conf.VM_NAME[:1]
    vms_to_stop = conf.VM_NAME[:3]
    affinity_groups = {
        "test_arem_6": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[1:3]
        }
    }

    @tier2
    @polarion("RHEVM3-10928")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from or on the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    wait_for_scheduling_memory_update.__name__,
    run_once_vms.__name__,
    create_affinity_groups.__name__,
    update_cluster.__name__,
    load_hosts_cpu.__name__,
)
class TestAREM7(BaseAREM):
    """
    Check AREM for negative hard affinity group under the PowerSaving
    scheduling policy constraint

    1) Run two VM's on the different hosts
    2) Add VM's to the negative hard affinity group
    3) Update cluster policy to PowerSaving with default values
    4) Load one of the hosts CPU to 50%
    5) Check that PowerSaving balance module does not
     migrate VM from overutilized host
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_POWER_SAVING,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_PARAMS
    }
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
    }
    vms_to_stop = conf.VM_NAME[:2]
    affinity_groups = {
        "test_arem_7": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    hosts_cpu_load = {conf.CPU_LOAD_50: [0]}

    @tier2
    @polarion("RHEVM3-10931")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from or on the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    create_affinity_groups.__name__,
    load_hosts_cpu.__name__,
    update_cluster.__name__,
)
class TestAREM8(BaseAREM):
    """
    Check AREM for negative hard affinity group under the EvenlyDistributed
    scheduling policy constraint

    1) Run two VM's on the different hosts
    2) Add VM's to the negative hard affinity group
    3) Update cluster policy to EvenlyDistributed with default values
    4) Load one of the hosts CPU to 100%
    5) Check that EvenlyDistributed balance module does not
     migrate VM from overutilized host
    """
    vms_to_run = {
        conf.VM_NAME[0]: {
            conf.VM_RUN_ONCE_HOST: 0,
            conf.VM_RUN_ONCE_WAIT_FOR_STATE: conf.VM_UP
        },
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
    }
    vms_to_stop = conf.VM_NAME[:2]
    affinity_groups = {
        "test_arem_8": {
            conf.AFFINITY_GROUP_POSITIVE: False,
            conf.AFFINITY_GROUP_ENFORCING: True,
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:2]
        }
    }
    hosts_cpu_load = {conf.CPU_LOAD_100: [0]}
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS
    }

    @tier2
    @polarion("RHEVM3-10932")
    def test_check_balancing(self):
        """
        Check if one of VM's migrated from or on the host
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            sampler_timeout=conf.AREM_BALANCE_TIMEOUT
        )
