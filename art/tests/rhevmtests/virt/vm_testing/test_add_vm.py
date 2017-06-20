import pytest
import helper
import fixtures
import add_vm_scenarios

from art.unittest_lib import (
    VirtTest,
    tier1,
)


@tier1
class TestAddVm(VirtTest):
    """
    Add VM test suite.
    """

    helper.update_domains()
    reload(add_vm_scenarios)

    @pytest.mark.usefixtures(
        fixtures.remove_vms_func_scope.__name__,
        fixtures.setup_vm.__name__,
    )
    @pytest.mark.parametrize(
        ("test_descr", "setup_data", "scenarios_data"),
        add_vm_scenarios.add_vm_scenario,
        ids=helper.get_ids(add_vm_scenarios.add_vm_scenario)
    )
    def test_add_vm(self, test_descr, setup_data, scenarios_data):
        helper.executor(scenarios_data)
