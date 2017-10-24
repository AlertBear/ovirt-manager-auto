import logging

import pytest

import config as sc_conf
import helper
import rhevmtests.helpers as rhevm_helpers
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import users as usr
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.unittest_lib import testflow
from rhevmtests.fixtures import start_vm  # noqa


logger = logging.getLogger("serial_console_fixture")


@pytest.fixture(scope='module')
def generate_and_upload_key(request):
    """
    Setup/teardown of private keys for SC module. Being executed after
    'verify_services_on_nodes' fixture.
    Setup:
        1. Verify if there are private keys generated on the engine.
        2. If step #1 is False - generate private keys on the engine, else -
           get existing keys.
        3. Verify if there is a leftover key in user options key-field (on the
           web page) for specific user.
        4. If step #3 is True - remove the leftover key.
        5. Set public key obtained in step #2 in a specific user options
           key-field.
    """
    def fin():
        """
        Teardown procedure to:
            1. Delete private key-pair from the engine.
            2. Remove key from specific user options key-field.
        """
        testflow.teardown('Remove SC keypair from execution host.')
        assert sc_conf.SLAVE_HOST.fs.remove(
            path='{key_name}*'.format(
                key_name=sc_conf.SERIAL_CONSOLE_PRIVATE_KEY_NAME
            )
        ), 'Failed to remove SC key-pair from execution host.'
        testflow.teardown('Remove key from specific user options key-field.')
        ssh_obj_cleanup = helper.get_ssh_key_object(user_name=sc_conf.SC_ADMIN)
        if ssh_obj_cleanup:
            assert usr.del_ssh_private_key(ssh_obj_cleanup[0]), (
                'Failed to remove key from specific user options key-field.'
            )

    request.addfinalizer(fin)

    if not sc_conf.SLAVE_HOST.fs.exists(
        path=sc_conf.SERIAL_CONSOLE_PRIVATE_KEY_NAME
    ):
        testflow.setup('Generate SC keypair on execution host.')
        rc, _, err = sc_conf.SLAVE_HOST.run_command(
            sc_conf.GENERATE_PRIVATE_KEY_CMD
        )
        assert not rc, (
            'Failed to generate SC keypair on execution host with following '
            'error:\n{err}'.format(err=err)
        )

    generated_key = sc_conf.SLAVE_HOST.fs.read_file(
        path='{key_name}.pub'.format(
            key_name=sc_conf.SERIAL_CONSOLE_PRIVATE_KEY_NAME
        )
    )

    existing_keys = usr.get_ssh_private_keys(sc_conf.SC_ADMIN)
    if existing_keys:
        testflow.setup(
            (
                'Remove leftover key from specific user options key-field '
                'from previous run.'
            )
        )
        ssh_obj = helper.get_ssh_key_object(user_name=sc_conf.SC_ADMIN)
        usr.del_ssh_private_key(ssh_obj[0])

    testflow.setup('Set public key in a specific user options key-field.')
    _, status = usr.set_ssh_private_key(sc_conf.SC_ADMIN, generated_key)
    assert status, sc_conf.KEY_UPLOAD_FAILURE_MSG


@pytest.fixture(scope='class')
def setup_vm(request, generate_and_upload_key):
    """
    Setup/teardown of VM for SC module. Being executed after
    'generate_and_upload_key' fixture.
    Setup:
        1. Create VM.
        2. Update VM with 'Console' -> 'Enable VirtIO serial console' flag.
        3. Start VM and wait for status 'UP' and for VM to obtain IP.
    """

    def fin():
        """
        Teardown:
            1. Safely remove VM.
        """
        testflow.teardown('Safely remove test VM.')
        assert ll_vms.safely_remove_vms(vms=[sc_conf.SERIAL_CONSOLE_VM]), (
            'Failed to safelly remove {vm} as part of teardown.'.format(
                vm=sc_conf.SERIAL_CONSOLE_VM
            )
        )

    request.addfinalizer(fin)

    testflow.setup("Create a VM for SC test cases execution.")
    assert ll_vms.createVm(
        positive=True, vmName=sc_conf.SERIAL_CONSOLE_VM,
        vmDescription=sc_conf.SERIAL_CONSOLE_VM,
        cluster=sc_conf.CLUSTER_NAME[0],
        template=sc_conf.TEMPLATE_NAME[0], os_type=sc_conf.VM_OS_TYPE,
        display_type=sc_conf.VM_DISPLAY_TYPE,
        nic=sc_conf.SERIAL_CONSOLE_VM_NIC,
        network=sc_conf.MGMT_BRIDGE
    )

    testflow.setup("Enable serial console for test VM.")
    assert ll_vms.updateVm(
        positive=True,
        vm=sc_conf.SERIAL_CONSOLE_VM,
        serial_console=True
    )

    sc_conf.SC_VM_ID = ll_vms.get_vm(sc_conf.SERIAL_CONSOLE_VM).get_id()


@pytest.fixture(scope='class')  # noqa
def setup_env(setup_vm, start_vm):
    """
    Setup of services for SC on VM and Enable SC VM. Being executed after
    'setup_vm' fixture. Service is being enabled for it to be started on each
    VM restart/reboot cycle, as it is required to be sure that SC tunnels are
    closed and they will not interfere with other cases.
    Setup:
        1. Start VM.
        2. Enable serial-getty service on the VM.
        3. Start the serial-getty service on the VM.
    """

    host_ip = hl_vms.get_vm_ip(sc_conf.SERIAL_CONSOLE_VM)
    vm_resource = rhevm_helpers.get_host_resource(
        ip=host_ip,
        password=sc_conf.SERIAL_CONSOLE_VM_PASSWORD
    )
    testflow.setup('Run serial-getty service on the SC test VM.')
    vm_resource.executor().wait_for_connectivity_state(positive=True)
    assert vm_resource.service(sc_conf.GETTY_SERVICE).enable(), (
        sc_conf.GETTY_SERVICE_FAILED.format(action='enable')
    )
    assert vm_resource.service(sc_conf.GETTY_SERVICE).start(), (
        sc_conf.GETTY_SERVICE_FAILED.format(action='start')
    )


@pytest.fixture(scope='function')
def restart_vm(request):
    """
    Teardown procedure for SC test cases. Restarts a VM (Power off/on) in order
    to be sure that SC tunnels are closed and they will not interfere with
    other cases.
    """
    def fin():
        """
        Teardown:
            1. Restart VM.
        """
        testflow.teardown('Restart VM as part of each test case teardown.')
        assert ll_vms.restartVm(
            vm=sc_conf.SERIAL_CONSOLE_VM,
            wait_for_ip=True
        ), 'Failed to restart VM.'
    request.addfinalizer(fin)
