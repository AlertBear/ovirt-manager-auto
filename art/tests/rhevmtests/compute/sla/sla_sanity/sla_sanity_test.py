"""
General test of some SLA features: CPU pinning, CPU host, delete protection,
count threads as cores and placement policy
"""
import random

import pytest
from rhevmtests.compute.sla.fixtures import (  # noqa: F401
    create_vms,
    start_vms,
    stop_vms,
    update_cluster,
    update_vms,
    update_vms_to_default_parameters,
    update_vms_cpus_to_hosts_cpus,
    update_cluster_to_default_parameters
)

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler.tools import polarion
from art.unittest_lib import testflow, tier1, tier2, SlaTest


class BasicSlaSanity(SlaTest):
    """
    Base class for all sla sanity tests
    """

    @staticmethod
    def _update_vm_vcpu_pinning(vcpu_pinning, positive=True, compare=True):
        """
        Update the VM VCPU pinning

        Args:
            vcpu_pinning (list): VCPU pinning
            positive (bool): Positive test behaviour
            compare (bool): Enable validator
        """
        testflow.step(
            "Set VM %s VCPU pinning to %s", conf.VM_NAME[0], vcpu_pinning
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            vcpu_pinning=vcpu_pinning,
            compare=compare
        ) == positive


@pytest.mark.usefixtures(
    create_vms.__name__,
    update_vms_to_default_parameters.__name__
)
class TestProtectedVm(BasicSlaSanity):
    """
    1) Remove the protected VM
    2) Force remove the protected VM
    """
    vms_create_params = {
        conf.PROTECTED_VM_NAME: {
            conf.VM_CLUSTER: conf.CLUSTER_NAME[0],
            conf.VM_STORAGE_DOMAIN: conf.STORAGE_NAME[0],
            conf.VM_DISK_SIZE: conf.GB,
            conf.VM_NIC: conf.NIC_NAME[0],
            conf.VM_NETWORK: conf.MGMT_BRIDGE,
            conf.VM_PROTECTED: True
        }
    }
    update_to_default_params = [conf.PROTECTED_VM_NAME]

    @tier2
    @polarion("RHEVM3-9512")
    def test_remove_protected_vm(self):
        """
        Remove the protected VM
        """
        testflow.step(
            "Remove the protected VM %s", conf.PROTECTED_VM_NAME
        )
        assert not ll_vms.removeVm(positive=True, vm=conf.PROTECTED_VM_NAME)

    @tier2
    @polarion("RHEVM3-9519")
    def test_force_remove_protected_vm(self):
        """
        Attempt to force remove the protected VM
        """
        testflow.step(
            "Force remove the protected VM %s", conf.PROTECTED_VM_NAME
        )
        assert not ll_vms.removeVm(
            positive=True, vm=conf.PROTECTED_VM_NAME, force=True
        )


@pytest.mark.usefixtures(update_vms_to_default_parameters.__name__)
class TestCPUHostCase1(BasicSlaSanity):
    """
    Update the migratable VM to use CPU host
    """
    update_to_default_params = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9527")
    def test_update_migratable_vm_to_use_cpu_host(self):
        """
        Update the migratable VM to use CPU host
        """
        testflow.step(
            "Update the migratable VM %s CPU passthrough to 'host'",
            conf.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            cpu_mode=conf.VM_HOST_PASS_THROUGH
        )


@pytest.mark.usefixtures(update_vms_to_default_parameters.__name__)
class TestCPUHostCase2(BasicSlaSanity):
    """
    Update the user migratable VM to use CPU host
    """
    update_to_default_params = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9531")
    def test_update_user_migratable_vm_to_use_cpu_host(self):
        """
        Update the user migratable VM to use CPU host
        """
        testflow.step(
            "Update the user migratable VM %s CPU passthrough to 'host'",
            conf.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_USER_MIGRATABLE,
            cpu_mode=conf.VM_HOST_PASS_THROUGH
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUHostCase3(BasicSlaSanity):
    """
    Update the VM with host_passthrough to migratable
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }

    @tier2
    @polarion("RHEVM3-9523")
    def test_update_vm_with_host_passthrough_to_migratable(self):
        """
        Update the VM with host_passthrough to migratable
        """
        testflow.step(
            "Update the VM %s with host_passthrough to migratable",
            conf.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_MIGRATABLE
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUHostCase4(BasicSlaSanity):
    """
    Unpin the VM with host_passthrough
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }

    @tier1
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9533")
    def test_unpin_vm_with_host_passthrough(self):
        """
        Unpin the VM with host_passthrough
        """
        testflow.step(
            "Unpin the VM %s with host_passthrough", conf.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            positive=True, vm=conf.VM_NAME[0], placement_host=conf.VM_ANY_HOST
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUHostCase5(BasicSlaSanity):
    """
    Update the VM with host_passthrough to user migratable
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }

    @tier1
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9535")
    def test_update_vm_with_host_passthrough_to_user_migratable(self):
        """
        Update the VM with host_passthrough to user migratable
        """
        testflow.step(
            "Update the VM %s with host_passthrough to user migratable",
            conf.VM_NAME[0]
        )
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_USER_MIGRATABLE
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestCPUHostCase6(BasicSlaSanity):
    """
    Check that VM with CPU host is running with correct QEMU values
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_MODE: conf.VM_HOST_PASS_THROUGH
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier1
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9536")
    def test_check_qemu_params(self):
        """
        Check that VM runs with the correct "-cpu" value on QEMU
        """
        expected_value = "host"
        testflow.step(
            "Check that the VM %s QEMU process has arg '-cpu' equal to '%s'",
            conf.VM_NAME[0], expected_value
        )
        value = helpers.get_vm_qemu_argument_from_host(
            host_resource=conf.VDS_HOSTS[0],
            vm_name=conf.VM_NAME[0],
            qemu_arg_name="cpu"
        )
        assert value == expected_value


@pytest.mark.usefixtures(
    update_cluster.__name__,
    update_vms_cpus_to_hosts_cpus.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class BasicThreadSla(BasicSlaSanity):
    """
    Basic class for all tests connect to thread_as_core option
    """
    cluster_to_update_params = None
    vms_to_hosts_cpus = {conf.VM_NAME[0]: 0}
    double_vms_cpus = None
    threads_on = None
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_stop = conf.VM_NAME[:1]


class TestThreadsOff(BasicThreadSla):
    """
    Check that VM with the number of CPU's equals to
    the host number of CPU's(without threads) succeeds to start,
    in the cluster with the threads_as_core option disabled
    """
    cluster_to_update_params = {
        conf.CLUSTER_THREADS_AS_CORE: False
    }
    double_vms_cpus = False
    threads_on = False

    @tier1
    @polarion("RHEVM3-9518")
    def test_cores_as_threads_off(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


class TestNegativeThreadsOff(BasicThreadSla):
    """
    Check that VM with the number of CPU's greater than
    the host number of CPU's(without threads) failed to start,
    in the cluster with the threads_as_core option disabled
    """
    cluster_to_update_params = {
        conf.CLUSTER_THREADS_AS_CORE: False
    }
    double_vms_cpus = True
    threads_on = False

    @tier2
    @polarion("RHEVM3-9517")
    def test_cores_as_threads_off(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


class TestThreadsOn(BasicThreadSla):
    """
    Check that VM with the number of CPU's equals to
    the host number of CPU's(include threads) succeeds to start,
    in the cluster with the threads_as_core option disabled
    """
    cluster_to_update_params = {
        conf.CLUSTER_THREADS_AS_CORE: True
    }
    double_vms_cpus = False
    threads_on = True

    @tier1
    @polarion("RHEVM3-9515")
    def test_cores_as_threads_on(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


class TestThreadsOnNegative(BasicThreadSla):
    """
    Check that VM with the number of CPU's greater than
    the host number of CPU's(include threads) failed to start,
    in the cluster with the threads_as_core option disabled
    """
    cluster_to_update_params = {
        conf.CLUSTER_THREADS_AS_CORE: True
    }
    double_vms_cpus = True
    threads_on = True

    @tier2
    @polarion("RHEVM3-9516")
    def test_cores_as_threads_on(self):
        """
        Start the VM
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert not ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUPinCase1(BasicSlaSanity):
    """
    Check CPU pinning format
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }

    @tier1
    @polarion("RHEVM3-9541")
    def test_cpupin_format1(self):
        """
        Set pinning to 0#0
        """
        self._update_vm_vcpu_pinning(vcpu_pinning=conf.DEFAULT_VCPU_PINNING)

    @tier1
    @polarion("RHEVM3-12221")
    def test_cpupin_format2(self):
        """
        Set pinning to 0#0-16
        """
        self._update_vm_vcpu_pinning(vcpu_pinning=[{"0": "0-16"}])

    @tier2
    @polarion("RHEVM3-12222")
    def test_cpupin_format3(self):
        """
        Negative: Set pinning to 0#^1
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=[{"0": "^1"}], positive=False
        )

    @tier2
    @polarion("RHEVM3-12223")
    def test_cpupin_format4(self):
        """
        Negative: Set pinning to 0#^1,^2
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "^1,^2"}]
        )
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, positive=False
        )

    @tier1
    @polarion("RHEVM3-12224")
    def test_cpupin_format5(self):
        """
        Set pinning to 0#0-3,^1
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "0-3,^1"}]
        )
        compare = conf.ART_CONFIG['RUN']["engine"] != "cli"
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, compare=compare
        )

    @tier1
    @polarion("RHEVM3-12225")
    def test_cpupin_format6(self):
        """
        Set pinning to 0#0-3,^1,^2
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "0-3,^1,^2"}]
        )
        compare = conf.ART_CONFIG['RUN']["engine"] != "cli"
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, compare=compare
        )

    @tier1
    @polarion("RHEVM3-12226")
    def test_cpupin_format7(self):
        """
        Set pinning to 0#1,2,3
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "1,2,3"}]
        )
        compare = conf.ART_CONFIG['RUN']["engine"] != "cli"
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, compare=compare
        )

    @tier2
    @polarion("RHEVM3-12227")
    def test_cpupin_format8(self):
        """
        Negative: Set pinning to 0#0_0#1
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "0"}, {"0": "1"}]
        )
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, positive=False
        )

    @tier2
    @polarion("RHEVM3-12228")
    def test_cpupin_format9(self):
        """
        Negative: Letter instead of pCPU
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=[{"0": "A"}], positive=False
        )

    @tier2
    @polarion("RHEVM3-12229")
    def test_cpupin_format10(self):
        """
        Negative: Letter instead of pCPU
        """
        try:
            self._update_vm_vcpu_pinning(
                vcpu_pinning=[{"A": "0"}], positive=False
            )
        except (TypeError, ValueError):
            pass

    @tier2
    @polarion("RHEVM3-12230")
    def test_cpupin_format15(self):
        """
        Negative: Pinning to empty range
        """
        vcpu_pinning = helpers.adapt_vcpu_pinning_to_cli(
            vcpu_pinning=[{"0": "0-1,^0,^1"}]
        )
        self._update_vm_vcpu_pinning(
            vcpu_pinning=vcpu_pinning, positive=False
        )

    @tier2
    @polarion("RHEVM3-12231")
    def test_cpupin_format16(self):
        """
        Negative: Pinning to non-existing pCPU
        """
        self._update_vm_vcpu_pinning(vcpu_pinning=[{"0": "4096"}])
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert not ll_vms.startVm(
            positive=True, vm=conf.VM_NAME[0], timeout=conf.CONNECT_TIMEOUT
        )

    @tier2
    @polarion("RHEVM3-12232")
    def test_cpupin_format17(self):
        """
        Negative: Pinning to an empty string
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=[{"0": ""}], positive=False
        )

    @tier2
    @polarion("RHEVM3-12233")
    def test_cpupin_format18(self):
        """
        Negative: Pinning non-existing vCPU
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=[{"4096": "0"}], positive=False
        )


@pytest.mark.usefixtures(update_vms_to_default_parameters.__name__)
class TestCPUPinCase2(BasicSlaSanity):
    """
    Set VCPU pinning on the migratable VM
    """
    update_to_default_params = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9532")
    def test_update_vcpu_pinning(self):
        """
        Update the VM VCPU pinning
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=conf.DEFAULT_VCPU_PINNING, positive=False
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUPinCase3(BasicSlaSanity):
    """
    Change the VM with VCPU pinning to migratable
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_PINNING: conf.DEFAULT_VCPU_PINNING
        }
    }

    @tier2
    @polarion("RHEVM3-9534")
    def test_update_vm_to_migratable(self):
        """
        Update the VM to migratable
        """
        testflow.step("Update the VM %s", conf.VM_NAME[0])
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_MIGRATABLE,
            placement_host=conf.VM_ANY_HOST
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUPinCase4(BasicSlaSanity):
    """
    Set VCPU pinning on the user migratable VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_USER_MIGRATABLE
        }
    }

    @tier2
    @polarion("RHEVM3-9543")
    def test_update_vcpu_pinning(self):
        """
        Update the VM VCPU pinning
        """
        self._update_vm_vcpu_pinning(
            vcpu_pinning=conf.DEFAULT_VCPU_PINNING, positive=False
        )


@pytest.mark.usefixtures(update_vms.__name__)
class TestCPUPinCase5(BasicSlaSanity):
    """
    Change the VM with VCPU pinning to user migratable
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_PINNING: conf.DEFAULT_VCPU_PINNING
        }
    }

    @tier2
    @polarion("RHEVM3-9542")
    def test_update_vm_to_user_migratable(self):
        """
        Update the VM to user migratable
        """
        testflow.step("Update the VM %s", conf.VM_NAME[0])
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_MIGRATABLE,
            placement_host=conf.VM_ANY_HOST
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestCPUPinCase6(BasicSlaSanity):
    """
    Check VCPU pinning to the random host CPU
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_CPU_PINNING: conf.DEFAULT_VCPU_PINNING
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9529")
    def test_random_vcpu_pinning(self):
        """
        Update the VM with the random VCPU pinning
        """
        online_cpus = ll_sla.get_list_of_online_cpus_on_resource(
            resource=conf.VDS_HOSTS[0]
        )
        host_cpus = online_cpus[-1] + online_cpus[1]
        for n in range(5):
            expected_pin = str(random.choice(online_cpus))
            hyp_exp = "-" * int(expected_pin)
            hyp_cores = "-" * (host_cpus - int(expected_pin) - 1)
            expected_affinity = "%sy%s" % (hyp_exp, hyp_cores)

            self._update_vm_vcpu_pinning(vcpu_pinning=[{"0": expected_pin}])

            testflow.step("Start the VM %s", conf.VM_NAME[0])
            assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])

            res = helpers.get_vcpu_pinning_info_from_host(
                host_resource=conf.VDS_HOSTS[0],
                vm_name=conf.VM_NAME[0],
                vcpu=0
            )
            testflow.step(
                "Check that VCPU 0 is pinned to the CPU %s", expected_pin
            )
            assert expected_pin == res[0]

            testflow.step(
                "Check that VCPU 0 has pinning affinity %s",
                expected_affinity
            )
            assert expected_affinity == res[1][:host_cpus]

            testflow.step("Stop the VM %s", conf.VM_NAME[0])
            assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms_cpus_to_hosts_cpus.__name__,
    update_vms.__name__,
    stop_vms.__name__
)
class TestCPUPinCase7(BasicSlaSanity):
    """
    Test VCPU pinning of all VM CPU's to the one host CPU
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_hosts_cpus = {conf.VM_NAME[0]: 0}
    vms_to_stop = conf.VM_NAME[:1]

    @tier1
    @polarion("RHEVM3-9539")
    def test_pinning_load(self):
        """
        Check VCPU pinning
        """
        host_online_cpu = str(
            ll_sla.get_list_of_online_cpus_on_resource(
                resource=conf.VDS_HOSTS[0]
            )[0]
        )
        host_topology = ll_hosts.get_host_topology(host_name=conf.HOSTS[0])
        host_cpus = host_topology.cores * host_topology.sockets
        vcpu_pinning = [
            {i: host_online_cpu} for i in xrange(host_cpus)
        ]

        testflow.step(
            "Update the VM %s VCPU pinning", conf.VM_NAME[0]
        )
        assert ll_vms.updateVm(
            positive=True, vm=conf.VM_NAME[0], vcpu_pinning=vcpu_pinning
        )

        testflow.step("Update the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[0])

        for i in range(host_cpus):
            vcpu_pinning_info = helpers.get_vcpu_pinning_info_from_host(
                host_resource=conf.VDS_HOSTS[0],
                vm_name=conf.VM_NAME[0],
                vcpu=i
            )
            testflow.step(
                "Check that VM %s VCPU %s pinned to the host %s CPU %s",
                conf.VM_NAME[0], i, conf.HOSTS[0], host_online_cpu
            )
            assert vcpu_pinning_info[0] == host_online_cpu


@pytest.mark.usefixtures(update_vms_to_default_parameters.__name__)
class TestCPUPinCase8(BasicSlaSanity):
    """
    Set VCPU pinning to the non migratable VM with no specified host to run on
    """
    update_to_default_params = conf.VM_NAME[:1]

    @tier2
    @polarion("RHEVM3-9544")
    def test_set_pinned_cpupin_vm_a(self):
        """
        Update the VM with VCPU pinning without specific host to run on
        """
        testflow.step("Update the VM %s", conf.VM_NAME[0])
        assert not ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME[0],
            placement_affinity=conf.VM_PINNED,
            placement_host=conf.VM_ANY_HOST,
            vcpu_pinning=conf.DEFAULT_VCPU_PINNING
        )


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestPlacementPolicyCase1(BasicSlaSanity):
    """
    Migrate a migratable VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0]
        }
    }
    vms_to_start = conf.VM_NAME[:1]

    @tier1
    @polarion("RHEVM3-9522")
    def test_migrate_migratable_vm(self):
        """
        Migrate a migratable VM
        """
        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestPlacementPolicyCase2(BasicSlaSanity):
    """
    Migrate a user-migratable VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_USER_MIGRATABLE
        }
    }
    vms_to_start = conf.VM_NAME[:1]

    @tier1
    @polarion("RHEVM3-9525")
    def test_migrate_user_migratable_vm(self):
        """
        Migrate a user-migratable VM
        """
        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0], force=True)


@pytest.mark.usefixtures(
    update_vms.__name__,
    start_vms.__name__
)
class TestPlacementPolicyCase3(BasicSlaSanity):
    """
    Migrate a non-migratable VM
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_start = conf.VM_NAME[:1]
    wait_for_vms_ip = False

    @tier1
    @polarion("RHEVM3-9526")
    def test_migrate_non_migratable_vm(self):
        """
        Migrate a non-migratable VM
        """
        testflow.step("Migrate the VM %s", conf.VM_NAME[0])
        assert not ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    update_vms.__name__,
    stop_vms.__name__
)
class TestPlacementPolicyCase4(BasicSlaSanity):
    """
    Run non migratable VM with no specific host
    """
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @tier1
    @polarion("RHEVM3-9530")
    def test_run_non_migratable_no_specific(self):
        """
        Start a non-migratable VM with no specific host to run on
        """
        testflow.step("Start the VM %s", conf.VM_NAME[0])
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME[0], wait_for_status=conf.VM_UP
        )
