"""
Watchdog test fixtures
"""
import pytest

import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers


@pytest.fixture(scope="class")
def add_watchdog_device_to_vm(request):
    """
    Add watchdog device to VM
    """
    watchdog_vm = getattr(request.node.cls, "watchdog_vm", None)
    watchdog_action = getattr(
        request.node.cls, "watchdog_action", conf.WATCHDOG_ACTION_NONE
    )

    def fin():
        """
        Remove watchdog device from VM
        """
        u_libs.testflow.teardown(
            "Remove watchdog device from VM %s", watchdog_vm
        )
        assert ll_vms.delete_watchdog(vm_name=watchdog_vm)
    request.addfinalizer(fin)

    u_libs.testflow.teardown(
        "Add watchdog device with action %s to VM %s",
        watchdog_action, watchdog_vm
    )
    assert ll_vms.add_watchdog(
        vm_name=watchdog_vm,
        model=conf.WATCHDOG_MODEL,
        action=watchdog_action
    )


@pytest.fixture(scope="class")
def add_watchdog_device_to_template(request):
    """
    Add watchdog device to template
    """
    watchdog_template = getattr(request.node.cls, "watchdog_template", None)
    watchdog_action = getattr(
        request.node.cls, "watchdog_action", conf.WATCHDOG_ACTION_NONE
    )

    def fin():
        """
        Remove watchdog device from template
        """
        u_libs.testflow.teardown(
            "Remove watchdog device from template %s", watchdog_template
        )
        assert ll_templates.delete_watchdog(template_name=watchdog_template)
    request.addfinalizer(fin)

    u_libs.testflow.teardown(
        "Add watchdog device with action %s to template %s",
        watchdog_action, watchdog_template
    )
    assert ll_templates.add_watchdog(
        template_name=watchdog_template,
        model=conf.WATCHDOG_MODEL,
        action=watchdog_action
    )


@pytest.fixture(scope="class")
def backup_engine_log(request):
    """
    1) Backup engine log
    """
    def fin():
        """
        1) Remove backup
        """
        conf.ENGINE_HOST.fs.remove(path=conf.ENGINE_TEMP_LOG)
    request.addfinalizer(fin)

    cmd = ["cp", conf.ENGINE_LOG, conf.ENGINE_TEMP_LOG]
    assert not conf.ENGINE_HOST.run_command(command=cmd)[0]


@pytest.fixture(scope="module")
def install_watchdog_on_vm():
    """
    1) Install watchdog package on the VM
    2) Enable watchdog service on the VM
    3) Start watchdog service
    """
    u_libs.testflow.setup(
        "Install and enable watchdog on VM %s", conf.VM_NAME[0]
    )
    assert helpers.install_watchdog_on_vm(vm_name=conf.VM_NAME[0])
