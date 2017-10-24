import re

import pytest

import config as vcons_conf
import fixtures
import helper
from art.rhevm_api.tests_lib.low_level import graphics_console as ll_gc
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    tier2,
)
from art.unittest_lib import testflow


class TestVirtConsoleClass(VirtTest):

    @tier2
    @polarion('RHEVM3-12357')
    @pytest.mark.skipif(
        vcons_conf.PPC_ARCH,
        reason=vcons_conf.PPC_SKIP_MESSAGE
    )
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    def test_1_spice_plus_vnc(self):
        """
        Verify if console can be set to 'Spice+VNC'
        """

        testflow.step('Set console type to Spice+VNC.')
        helper.set_console_type(
            console_type='spice_plus_vnc',
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
            obj='vm'
        )
        testflow.step('Activate test VM.')
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        testflow.step("Verify VM was configured with SPICE+VNC console.")
        vm_obj = ll_vms.get_vm(vcons_conf.VIRT_CONSOLE_VM_SYSTEM)
        consoles = ll_gc.get_graphics_consoles_values(vm_obj)
        protocols_used = []
        for console in consoles:
            protocols_used.append(console.protocol)

        consoles_state = '+'.join(sorted(protocols_used))
        assert re.search('spice\+vnc', consoles_state), (
            "Console was not set to 'SPICE+VNC' during setup."
        )

        for host in vcons_conf.VDS_HOSTS:
            if host.fqdn == ll_hosts.get_host_vm_run_on(
                    vcons_conf.VIRT_CONSOLE_VM_SYSTEM
            ):
                testflow.step(
                    "Verify KVM process is running with Spice and VNC consoles"
                    " enabled."
                )
                rc, out, err = host.run_command(
                    vcons_conf.KVM_PROCESS_INFO_CMD.split(' ')
                )

                assert not rc, (
                    "Failed to execute command on the host with following "
                    "error message:\n{message}".format(message=err)
                )
                assert re.search("-spice", out), (
                    "SPICE console is not represented as running in QEMU-KVM "
                    "process."
                )
                assert re.search("-vnc", out), (
                    "VNC console is not represented as running in QEMU-KVM "
                    "process."
                )
                testflow.step(
                    "Verify Graphics type displayed by virsh dumpxml command."
                )
                rc, out, err = host.run_command(
                    vcons_conf.VIRSH_DUMP_CMD_GC.format(
                        vm_id=vm_obj.get_id()
                    ).split(' ')
                )
                assert not rc, (
                    "Failed to execute command on the host with following "
                    "error message:\n{message}".format(message=err)
                )
                assert re.search("graphics type='vnc'", out), (
                    "Graphics type VNC was not found in the virsh dumpxml"
                    " command output."
                )
                assert re.search("graphics type='spice'", out), (
                    "Graphics type SPICE was not found in the virsh dumpxml"
                    " command output."
                )

    @tier2
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    @pytest.mark.parametrize(
        vcons_conf.VV_FILE_ARGS,
        vcons_conf.VV_FILE_FIELDS_PARAMS
    )
    def test_2_verify_vv_file_fields(self, console_protocol):
        """
        Verify proper fields are present in VV file downloaded to open a
        console.
        """
        testflow.step(
            'Set {proto} console protocol for test VM.'.format(
                proto=console_protocol
            )
        )
        helper.set_console_type(
            console_type=console_protocol,
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
            obj='vm'
        )
        testflow.step('Activate test VM.')
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        vm_obj = ll_vms.get_vm(vcons_conf.VIRT_CONSOLE_VM_SYSTEM)
        consoles = ll_gc.get_graphics_consoles_values(vm_obj)
        testflow.step("Get VV file content.")
        data_list = helper.get_vv_data_list(consoles)
        missing_fields = helper.verify_vv_fields(data_list)
        testflow.step("Verify all fields are present.")
        assert not missing_fields, (
            "Following fields are missing in the VV file:\n "
            "-> {fields}".format(
                fields=missing_fields
            )
        )

    @tier2
    @pytest.mark.usefixtures(
        fixtures.setup_vm.__name__,
        fixtures.shutdown_vm.__name__
    )
    @pytest.mark.parametrize(
        vcons_conf.VV_FILE_ARGS,
        vcons_conf.VV_FILE_VALUES_PARAMS
    )
    def test_3_verify_proper_data_in_vv_file(self, console_protocol):
        """
        Verify that VV file is different for consoles on different monitors.
        """
        testflow.step(
            'Set {proto} console protocol for test VM.'.format(
                proto=console_protocol
            )
        )
        helper.set_console_type(
            console_type=console_protocol,
            object_name=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
            obj='vm'
        )
        testflow.step('Activate test VM.')
        assert ll_vms.startVms(
            vms=[vcons_conf.VIRT_CONSOLE_VM_SYSTEM],
            wait_for_status=vcons_conf.VM_UP
        ), "Failed to start test VMs."

        vm_obj = ll_vms.get_vm(vcons_conf.VIRT_CONSOLE_VM_SYSTEM)
        consoles = ll_gc.get_graphics_consoles_values(vm_obj)

        data_list = helper.get_vv_data_list(consoles)
        testflow.step("Verify VV file was downloaded for proper VM.")
        vm_obj = ll_vms.get_vm(vcons_conf.VIRT_CONSOLE_VM_SYSTEM)

        error_list = []

        for data in data_list:
            testflow.step("Verify VM ID represented in VV file.")
            if vm_obj.get_id() != data['[ovirt]']['vm-guid']:
                error_list.append(
                    "VV file has incorrect VM id value.\nexpected: {exp}\n"
                    "actual: {act}\n".format(
                        exp=vm_obj.get_id(),
                        act=data['[ovirt]']['vm-guid']
                    )
                )
            testflow.step("Verify engine fqdn represented in VV file.")
            if not re.search(
                    vcons_conf.ENGINE.host.fqdn, data['[ovirt]']['host']
            ):
                error_list.append(
                    "VV file has incorrect engine info.\nexpected: {exp}\n"
                    "actual: {act}\n".format(
                        exp=vcons_conf.ENGINE.host.fqdn,
                        act=data['[ovirt]']['host']
                    )
                )
            for host in vcons_conf.VDS_HOSTS:
                if host.fqdn == ll_hosts.get_host_vm_run_on(
                        vcons_conf.VIRT_CONSOLE_VM_SYSTEM
                ):
                    testflow.step("Verify host IP represented in VV file.")
                    if host.ip != data['[virt-viewer]']['host']:
                        error_list.append(
                            "Host IP VM is situated on is not displayed in VV "
                            "file.\nexpected - {exp}\actual - "
                            "{act}\n ".format(
                                exp=host.ip,
                                act=data['[virt-viewer]']['host']
                            )
                        )
            if console_protocol == 'spice':
                testflow.step("Verify host fqdn represented in VV file.")
                if not re.search(
                        ll_hosts.get_host_vm_run_on(
                            vcons_conf.VIRT_CONSOLE_VM_SYSTEM
                        ), data['[virt-viewer]']['host-subject']
                ):
                    error_list.append(
                        "Incorrect host fqdn is represented in the VV file.\n"
                        "expected for {exp} to be present in {act} "
                        "field".format(
                            exp=ll_hosts.get_host_vm_run_on(
                                vcons_conf.VIRT_CONSOLE_VM_SYSTEM
                            ),
                            act=data['[virt-viewer]']['host-subject']
                        )
                    )

        assert not error_list, (
            "Following fields were represented with incorrect information in "
            "VV file:\n{err}".format(err="\n".join(error_list))
        )
