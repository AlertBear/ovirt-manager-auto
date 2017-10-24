import re

import pytest

import config as vcons_conf
import fixtures
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier2,
    VirtTest,
    testflow,
)


class TestVirtConsoleSanityClass(VirtTest):

    vm_name = vcons_conf.VIRT_CONSOLE_VM_SANITY
    start_vms_dict = {
        vm_name: {
            "host": None
        }
    }

    @tier2
    @polarion('RHEVM3-14575')
    def test_1_network_port_range(self):
        """
        Verify host network port range.
        """
        for host in vcons_conf.VDS_HOSTS:
            out = host.fs.read_file(vcons_conf.VIRSH_CONF_FILE)
            for query in vcons_conf.VIRSH_CONF_SEARCH_PARAMS:
                testflow.step(
                    "Verify {field} value in {conf_file} on {host} "
                    "host.".format(
                        field=query.split('=')[0],
                        conf_file=vcons_conf.VIRSH_CONF_FILE,
                        host=host.fqdn
                    )
                )
                assert re.search(query, out), (
                    "{query} parameter was not found in the {conf_file}, "
                    "actual output is:\n\n{out}".format(
                        query=query,
                        conf_file=vcons_conf.VIRSH_CONF_FILE,
                        out=out
                    )
                )

    @tier2
    @polarion('RHEVM3-9896')
    @pytest.mark.skipif(
        vcons_conf.PPC_ARCH,
        reason=vcons_conf.PPC_SKIP_MESSAGE
    )
    @pytest.mark.usefixtures(fixtures.setup_2_vms_env.__name__)
    def test_2_multiple_monitors_mem_size(self):
        """
        Multiple monitors verification test case.
        """
        for vm in vcons_conf.VIRT_CONSOLE_VM_DICT_SANITY.keys():
            vm_obj = ll_vms.get_vm(vm)
            for host in vcons_conf.VDS_HOSTS:
                if host.fqdn == ll_hosts.get_host_vm_run_on(vm):
                    testflow.step(
                        "Executing test command on the {host} for {vm} "
                        "test VM".format(
                            host=host,
                            vm=vm
                        )
                    )
                    rc, out, err = host.run_command(
                        vcons_conf.VIRSH_DUMP_CMD_RAM.format(
                            vm_id=vm_obj.get_id()
                        ).split(' ')
                    )
                    testflow.step(
                        "Verifying command was executed successfully."
                    )
                    assert not rc, (
                        "Failed to execute command on the host with following "
                        "error message:\n{message}".format(message=err)
                    )
                    expected_len = vcons_conf.VIRT_CONSOLE_VM_DICT_SANITY[vm]
                    testflow.step(
                        "Verifying output of the executed command returned "
                        "proper amount of monitors."
                    )
                    assert len(
                        out.strip().split('\n')) == expected_len, (
                        "Incorrect amount of monitors is represented via Virsh"
                        " dump command.\nExpected: {exp}\nActual: {act}\nFull "
                        "output: {full_out}".format(
                            exp=expected_len,
                            act=len(out.strip().split('\n')),
                            full_out=out
                        )
                    )
                    testflow.step(
                        "Verifying that primary video device is present in "
                        "the output."
                    )
                    assert re.search("primary='yes'", out), (
                        "No primary video device was found in Virsh output."
                    )
