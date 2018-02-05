import re
import pytest
from art.test_handler.tools import polarion
from art.unittest_lib import (
    VirtTest,
    testflow,
    tier1,
    tier3,
)
import config as sc_conf
import helper
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
import fixtures


class SerialConsoleClass(VirtTest):

    __test__ = True
    vm_name = sc_conf.SERIAL_CONSOLE_VM
    start_vms_dict = {
        vm_name: {
            "host": None
        }
    }

    @polarion('RHEVM-19068')
    @tier1
    def test_1_verify_services_on_nodes(self):
        """
        Verify necessary services running on engine and hosts.
        """
        testflow.step(
            'Get and verify engine service {engine_service} status.'.format(
                engine_service=sc_conf.SC_ENGINE_SERVICE
            )
        )
        if not sc_conf.ENGINE_HOST.service(sc_conf.SC_ENGINE_SERVICE).status():
            sc_conf.ENV_READY = False
        assert sc_conf.ENV_READY, (
            'Service {service} is not enabled on engine site.'.format(
                service=sc_conf.SC_ENGINE_SERVICE
            )
        )

        for host in sc_conf.VDS_HOSTS:
            testflow.step(
                'Get and verify host service: {host_service} status on {host} '
                'host.'.format(
                    host_service=sc_conf.SC_HOST_SERVICE,
                    host=host
                )
            )
            if not host.service(sc_conf.SC_HOST_SERVICE).status():
                sc_conf.ENV_READY = False
            assert sc_conf.ENV_READY, (
                'Service {service} is not enabled on {host}.'.format(
                    service=sc_conf.SC_HOST_SERVICE,
                    host=host
                )
            )

    @tier3
    @polarion('RHEVM-19069')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(fixtures.setup_env.__name__)
    def test_2_get_help_for_sc(self):
        """
        Verify that proper help message is being reproduced for SC.
        """
        testflow.step('Generate test command to obtain Help for SC.')
        cmd = helper.generate_command(
            add_flag=['--', '--help'],
            remove_flag=['-t']
        )
        testflow.step('Execute SC help command.')
        rc, out, _ = sc_conf.SLAVE_HOST.run_command(cmd)
        testflow.step('Verify SC help command output.')
        assert not rc, (
            'Unexpected return code: {code}'.format(code=rc)
        )
        assert out == sc_conf.HELP_RETURN, (
            'Help option returned incorrect output.'
            ' Actual output is:\n{out}'.format(out=out)
        )

    @tier3
    @polarion('RHEVM-19071')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(fixtures.setup_env.__name__)
    def test_3_get_info_for_sc(self):
        """
        Verify that proper SC-info message is being reproduced via SC command.
        """
        testflow.step('Generate test command to obtain SC info.')
        cmd = helper.generate_command(
            add_flag=['info'],
            remove_flag=['-t']
        )
        testflow.step('Execute SC info command.')
        rc, out, _ = sc_conf.SLAVE_HOST.run_command(cmd)
        testflow.step('Verify SC info command output.')
        assert not rc, (
            'Unexpected return code: {code}'.format(code=rc)
        )
        assert re.search(sc_conf.PACKAGE, out), (
            'Info command returned unexpected package name.\n{out} instead of'
            '{expected_out}'.format(out=out, expected_out=sc_conf.PACKAGE)
        )
        proxy_key = sc_conf.ENGINE.host.fs.read_file(
            path=sc_conf.PROXY_KEY_LOCATION
        )
        assert proxy_key in out, (
            'Proxy key was not displayed by info command. Proxy key:'
            '\n{proxy_key}\nOut:{out}'.format(proxy_key=proxy_key, out=out)
        )

    @tier1
    @polarion('RHEVM-19070')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(fixtures.setup_env.__name__)
    def test_4_get_list_of_vms_via_sc(self):
        """
        Verify that list of vms obtained via SC is reproduced properly.
        """
        testflow.step('Generate test command to obtain VM list via SC.')
        cmd = helper.generate_command(
            add_flag=['list'],
            remove_flag=['-t']
        )
        testflow.step('Execute SC list command.')
        rc, out, _ = sc_conf.SLAVE_HOST.run_command(cmd)
        testflow.step('Verify SC list VMs command output.')
        assert not rc, (
            'Unexpected return code: {code}'.format(code=rc)
        )
        assert re.search(sc_conf.SERIAL_CONSOLE_VM, out), (
            'VM name was not represented by list command. Actual output:'
            '\n{out}\nExpected {vm_name} in output.'.format(
                out=out, vm_name=sc_conf.SERIAL_CONSOLE_VM
            )
        )
        assert re.search(sc_conf.SC_VM_ID, out), (
            'VM ID was not represented by list command. Actual output:'
            '\n{out}\nExpected {vm_id} in output.'.format(
                out=out, vm_id=sc_conf.SC_VM_ID
            )
        )

    @tier1
    @polarion('RHEVM-19073')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(
        fixtures.setup_env.__name__,
        fixtures.restart_vm.__name__
    )
    def test_5_establish_ssh_connection_via_sc(self):
        """
        Establish connection to the VM via SC, and verify if it is possible to
        perform actions on the VM via SC connection.
        """
        testflow.step('Generate SC command used to connect to test VM.')
        cmd = helper.generate_command(
            add_flag=[
                'connect',
                '--vm-id={vm_id}'.format(vm_id=sc_conf.SC_VM_ID)
            ]
        )
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=True)
        child.logfile = open('/tmp/sc_basic_connect.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)

    @tier3
    @polarion('RHEVM-19072')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(
        fixtures.setup_env.__name__,
        fixtures.restart_vm.__name__
    )
    def test_6_ssh_connection_via_sc_drops_on_suspension(self):
        """
        Verify that connection to the VM via SC drops when VM is suspended.
        """
        testflow.step('Generate SC command used to connect to test VM.')
        cmd = helper.generate_command(
            add_flag=[
                'connect',
                '--vm-id={vm_id}'.format(vm_id=sc_conf.SC_VM_ID)
            ]
        )
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=True)
        child.logfile = open('/tmp/sc_before_suspension.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)
        testflow.step('Suspend test VM.')
        assert ll_vms.suspendVm(
            positive=True, vm=sc_conf.SERIAL_CONSOLE_VM
        ), 'Was not able to suspend the VM.'
        testflow.step('Verify SC tunnel dropped upon VM suspension.')
        helper.verify_child_dead(child, action='suspend', timeout=20)
        testflow.step('Start VM after suspension.')
        assert ll_vms.startVm(
            positive=True,
            vm=sc_conf.SERIAL_CONSOLE_VM,
            wait_for_status=sc_conf.VM_UP,
            timeout=1500
        ), 'Was not able to start VM after suspension.'
        assert ll_vms.wait_for_vm_ip(sc_conf.SERIAL_CONSOLE_VM), (
            "VM failed to obtain IP."
        )
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=False)
        child.logfile = open('/tmp/sc_after_suspension.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)

    @tier3
    @polarion('RHEVM-19074')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(
        fixtures.setup_env.__name__,
        fixtures.restart_vm.__name__
    )
    def test_7_ssh_connection_via_sc_remains_upon_reboot(self):
        """
        Verify that connection to VM via SC remains active upon VM reboot.
        """
        testflow.step('Generate SC command used to connect to test VM.')
        cmd = helper.generate_command(
            add_flag=[
                'connect',
                '--vm-id={vm_id}'.format(vm_id=sc_conf.SC_VM_ID)
            ]
        )
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=True)
        child.logfile = open('/tmp/sc_on_reboot.log', 'w')
        testflow.step('Reboot test VM and wait for it to become active again.')
        ll_vms.reboot_vm(positive=True, vm=sc_conf.SERIAL_CONSOLE_VM)
        testflow.step('Rebooting')
        assert ll_vms.waitForVMState(
            sc_conf.SERIAL_CONSOLE_VM,
            sc_conf.VM_REBOOT
        ), 'VM did not go for reboot.'
        testflow.step('Activating')
        assert ll_vms.waitForVMState(
            sc_conf.SERIAL_CONSOLE_VM,
            sc_conf.VM_UP
        ), 'VM did not recover successfully after reboot.'
        assert ll_vms.wait_for_vm_ip(sc_conf.SERIAL_CONSOLE_VM)
        testflow.step(
            'Verify SC is working after reboot of VM and SC session did not '
            'drop.'
        )
        assert helper.get_prompt(child, authorize=True), (
            "Failed to obtain expected prompt"
        )
        helper.credentials_provider(child)
        helper.verify_sc(child)

    @tier3
    @polarion('RHEVM19075')
    @pytest.mark.skipif(not sc_conf.ENV_READY, reason=sc_conf.SKIP_MESSAGE)
    @pytest.mark.usefixtures(
        fixtures.setup_env.__name__,
        fixtures.restart_vm.__name__
    )
    def test_8_reestablish_sc_connection_after_vm_migration(self):
        """
        Verify that connection to VM via SC drops upon migration and user is
        able to reconnect to the VM via SC after migration.
        """
        testflow.step('Generate SC command used to connect to test VM.')
        cmd = helper.generate_command(
            add_flag=[
                'connect',
                '--vm-id={vm_id}'.format(vm_id=sc_conf.SC_VM_ID)
            ]
        )
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=True)
        child.logfile = open('/tmp/sc_before_migration.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)
        testflow.step('Migrate VM.')
        ll_vms.migrateVm(
            positive=True,
            vm=sc_conf.SERIAL_CONSOLE_VM,
            wait=True
        )
        testflow.step('Verify SC session dropped upon migration of VM.')
        helper.verify_child_dead(child, action='migrate', timeout=300)
        testflow.step('Connect to VM via SC using proper command.')
        child = helper.sc_ssh_connector(cmd, authorize=False)
        child.logfile = open('/tmp/sc_after_migration_1.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)
        testflow.step('Migrate VM.')
        ll_vms.migrateVm(
            positive=True,
            vm=sc_conf.SERIAL_CONSOLE_VM,
            wait=True
        )
        testflow.step('Verify SC session dropped upon migration of VM.')
        helper.verify_child_dead(child, action='migrate', timeout=300)
        child = helper.sc_ssh_connector(cmd, authorize=False)
        child.logfile = open('/tmp/sc_after_migration_2.log', 'w')
        testflow.step('Verify SC is working properly.')
        helper.verify_sc(child)
