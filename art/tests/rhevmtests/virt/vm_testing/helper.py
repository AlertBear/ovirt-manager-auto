import re
import copy
import config as vm_conf
from art.unittest_lib import testflow
from art.rhevm_api.tests_lib.low_level import vms as ll_vms

import config
import rhevmtests.virt.helper as helper
from art.core_api.apis_exceptions import EntityNotFound


def executor(scenario):
    """
    Go through scenario dictionary and perform actions listed in that scenario
    on a specific VM.

    Args:
        scenario (dict): dictionary with the steps that will be performed on a
                         VM.

    Raises:
        AssertionError: in cases of action failure.

    Detailed explanation:
        scenarios are passed as a dict of dicts. Example:
            {
                (step_id(int), action(str), positive(bool), vm_name(str)):
                    args_required_for_action,
                (2, ...
            }
        Different actions have different inner dict model, below are shown
        formats for all the current actions available:
            - update:
                {
                   (1, "update", True, config.VM_NAME_T1): {
                       "max_memory": 8 * config.specific_values["standard"]
                },
                where:
                   key:
                      (step_id(int), action(str), positive(bool), vm_name(str))
                   val:
                      {param_name: value_to_be_set}
            - reboot:
                {
                   (4, "reboot", config.VM_NAME_T1): True
                },
                where:
                   key:
                      (step_id(int), action(str), vm_name(str))
                   val:
                      expected_result(bool)
            - start:
                {
                   (4, "start", config.VM_NAME_T1): True
                },
                where:
                   key:
                      (step_id(int), action(str), vm_name(str))
                   val:
                      expected_result(bool)
            - remove:
                {
                   (4, "remove", config.VM_NAME_T1): True
                },
                where:
                   key:
                      (step_id(int), action(str), vm_name(str))
                   val:
                      expected_result(bool)
            - create:
                {
                    (1, "create"): [
                        ADD_VM_DEFAULTS, {
                            'storagedomain': config.MASTER_DOM,
                            'disk_type': config.DISK_TYPE_DATA,
                            'provisioned_size': config.GB * 2,
                            'interface': config.INTERFACE_VIRTIO,
                        }
                    ]
                }
                where:
                   key:
                      (step_id(int), action(str))
                   val:
                      [vm_params(dict), vm_params_to_be_updated(dict)]
            - compare:
                {
                   (1, "compare"): {
                       (1, 'func'): [
                           ll_vms.get_vm_boot_sequence, [config.ADD_VM_NAME]
                       ],
                       (2, "val"): [
                           config.ENUMS['boot_sequence_network'],
                           config.ENUMS['boot_sequence_hd']
                       ]
                   }
                }
                where:
                   key:
                      (step_id(int), action(str))
                   val:
                      {
                           (step_id(int), arg_type('func' or 'val')): {
                               # if func:
                               [method_to_obtain_val, [args_used_in_method]]
                               # if val:
                               [values_to_compare]
                               #NOTE: can have multiple vals or funcs or mixed,
                               #      as long as they supposed to be the same.
                           }
                      }

    """
    for k in sorted(scenario.keys()):
        v = scenario[k]
        if vm_conf.UPDATE in k:
            msg = (
                "Was {status}able to update {field} with value "
                "equal {value}".format(
                    status=("not " if k[2] else ""),
                    field=v.keys(),
                    value=v.values()
                )
            )
            assert ll_vms.updateVm(
                positive=k[2],
                vm=k[3],
                **v
                ), msg
        if vm_conf.REBOOT in k:
            testflow.step(
                "Rebooting VM: {vm}".format(vm=k[2])
            )
            assert ll_vms.reboot_vms(vms=[k[2]]), (
                "Failed to reboot following vms:\n{vms}".format(
                    vms=k[2]
                )
            )
        if vm_conf.START in k:
            testflow.step(
                "Start VMs: {vm}".format(vm=k[2])
            )
            assert ll_vms.startVms(
                vms=[k[2]], wait_for_status=vm_conf.VM_UP
            ), (
                "Failed to start following vms:\n{vms}".format(
                    vms=k[2]
                )
            )
        if vm_conf.REMOVE in k:
            msg = "Was {status}able to remove VM: {vm}.".format(
                status=("not " if v else ""),
                vm=k[2]
            )
            if ll_vms.does_vm_exist(k[2]):
                if v:
                    assert ll_vms.stop_vms_safely([k[2]]), (
                        "Failed to stop VM before removing it."
                    )
                assert ll_vms.removeVm(positive=v, vm=k[2], wait=v), msg
                if v:
                    config.VMS_CREATED.remove(k[2])
        if vm_conf.CREATE in k:
            status, msg = add_vm_from_scenario(v)
            assert status, msg
        if vm_conf.COMPARE in k:
            testflow.step(
                "Performing verification that proper values set."
            )
            results = list()
            for key, val in v.iteritems():
                if re.search("func", key[1]):
                    gained_item = val[0](*val[1])
                    results.append(gained_item)
                if re.search("val", key[1]):
                    results.append(val)
            assert all(elm == results[0] for elm in results), (
                "Comparation failed as elements of list are not the "
                "same:\n".format(results)
            )


def get_ids(scenarios):
    """
    Get test cases ids from scenario dictionary.

    Args:
        scenarios (dict): test cases scenarios in dict form.

    Returns:
        list: list of test case ids.
    """

    ids = list()

    def iterator(collection):
        if isinstance(collection, list):
            ids.append(collection[0].keys()[0])
        else:
            iterator(collection.args[1])

    for scenario in scenarios:
        item = scenario.args[1]
        iterator(item)

    return ids


def update_domains():
    """
    Update storage domain values in the config module.
    """
    try:
        config.MASTER_DOM, config.EXPORT_DOM, config.NON_MASTER_DOM = \
            helper.get_storage_domains()
    except EntityNotFound:
        config.NO_STORAGE = True


def add_vm_from_scenario(vm_params):
    """
    Add VM procedure from scenarios dict.

    Args:
        vm_params (list): contains two dicts, with VM params, 1-st one with
                          default values, 2-nd one with values to be updated
                          and used in VM creation.
    Returns:
        status (bool): True if operation acted as expected, otherwise - False
        msg (str): error message to be used in case of failure.
    """
    new_values = copy.deepcopy(vm_params)
    new_values[0].update(new_values[1])
    vm_name = new_values[0]['vmName']
    positive = new_values[0]['positive']
    msg = (
        "Was {status}able to create a VM: {vm}.".format(
            status=("not " if positive else ""),
            vm=vm_name
        )
    )
    status = ll_vms.createVm(**new_values[0])
    if positive:
        config.VMS_CREATED.append(vm_name)
    return status, msg
