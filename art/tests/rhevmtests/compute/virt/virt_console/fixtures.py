import re

import pytest

import config as vcons_conf
import helper
import rhevmtests.helpers as global_helper
from art.rhevm_api.tests_lib.low_level import instance_types as ll_inst_type
from art.rhevm_api.tests_lib.low_level import templates as ll_templates
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.unittest_lib import testflow


@pytest.fixture(scope="class")
def setup_vm(request):
    """
    Setup/teardown of VM for SVNC module.

    Setup:
        1. Create instance_type for test case execution.
        2. Create Template for test case execution.
        3. Create VM.
    """

    result = list()

    def fin_verify_results():
        """
        Check if none of finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)

    def fin_vm():
        """
        Teardown:
            Safely remove VM.
        """
        testflow.teardown("Safely remove test VM.")
        result.append(
            (
                ll_vms.safely_remove_vms(
                    vms=[
                        vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
                        vcons_conf.VIRT_CONSOLE_CLONE_VM_NAME,
                        vcons_conf.VIRT_CONSOLE_VM_IMPORT_NEW
                    ]
                ), "Failed to safelly remove {vm} as part of teardown.".format(
                    vm=vcons_conf.VIRT_CONSOLE_VM_SYSTEM
                )
            )
        )

    def fin_vm_from_export_domain():
        """
        Teardown:
            Remove VM from export domain
        """

        testflow.teardown("Remove exported VM from export domain.")
        if ll_vms.is_vm_exists_in_export_domain(
                vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
                vcons_conf.EXPORT_DOMAIN_NAME
        ):
            result.append(
                (
                    ll_vms.remove_vm_from_export_domain(
                        True,
                        vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
                        vcons_conf.DC_NAME[0],
                        vcons_conf.EXPORT_DOMAIN_NAME
                    ), "Failed to remove VM from export domain."
                )
            )

    def fin_instance_type():
        """
        Teardown:
            Remove instance type.
        """
        testflow.teardown("Remove custom instance_type.")
        result.append(
            (
                ll_inst_type.remove_instance_type(
                    instance_type_name=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE
                ), "Was not able to remove test instance_type."
            )
        )

    def fin_templates():
        """
        Teardown:
            Remove test template.
        """
        testflow.teardown("Remove test template.")
        result.append(
            (
                ll_templates.safely_remove_templates(
                    templates=[
                        vcons_conf.VIRT_CONSOLE_TEMPLATE,
                        vcons_conf.VIRT_CONSOLE_TEMPLATE_IMPORT_NEW
                    ]
                ), "Was not able to remove test Template."
            )
        )

    def fin_template_from_export_domain():
        """
        Teardown:
            Remove template from export domain
        """

        testflow.teardown("Remove exported template from export domain.")
        if ll_templates.export_domain_template_exist(
                vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
                vcons_conf.EXPORT_DOMAIN_NAME
        ):
            result.append(
                (
                    ll_templates.removeTemplateFromExportDomain(
                        True,
                        vcons_conf.VIRT_CONSOLE_TEMPLATE,
                        vcons_conf.EXPORT_DOMAIN_NAME
                    ), "Failed to remove Template from export domain."
                )
            )

    request.addfinalizer(fin_instance_type)
    request.addfinalizer(fin_template_from_export_domain)
    request.addfinalizer(fin_templates)
    request.addfinalizer(fin_vm_from_export_domain)
    request.addfinalizer(fin_vm)
    request.addfinalizer(fin_verify_results)

    testflow.setup(
        "Create a instance_type for Virt console test cases execution."
    )

    assert ll_inst_type.create_instance_type(
        instance_type_name=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE,
        **vcons_conf.INSTANCE_TYPE_PARAMS
    ), "Failed to create instance_type."

    testflow.setup("Create a Template for Virt console test cases execution.")
    assert ll_templates.createTemplate(
        positive=True,
        vm=vcons_conf.VM_NAME[0],
        name=vcons_conf.VIRT_CONSOLE_TEMPLATE,
        cluster=vcons_conf.CLUSTER_NAME[0]
    ), "Was not able to create template."

    testflow.setup("Create a VM for Virt console test cases execution.")
    assert ll_vms.createVm(
        positive=True,
        vmName=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
        vmDescription=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
        cluster=vcons_conf.CLUSTER_NAME[0],
        template=vcons_conf.VIRT_CONSOLE_TEMPLATE,
        os_type=vcons_conf.VM_OS_TYPE,
        display_type=vcons_conf.VM_DISPLAY_TYPE,
        nic=vcons_conf.VIRT_CONSOLE_VM_NIC,
        network=vcons_conf.MGMT_BRIDGE
    ), "Was not able to create VM."

    testflow.setup("Update VM to use test instance type and 2 monitors.")
    assert ll_vms.updateVm(
        positive=True,
        vm=vcons_conf.VIRT_CONSOLE_VM_SYSTEM,
        instance_type=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE
    ), "Failed to set instance_type for VM."


@pytest.fixture(scope="function")
def setup_2_vms_env(request):
    """
    Setup of VMs for Virt console module.

    Setup:
        1. Create 2 VMs.
        2. Update VM #1 with console -> monitors = 4, VM #2 with console ->
           monitors = 1, console -> Single PCI enabled.
        3. Start VMs and wait for status "UP" and for VM to obtain IP.
    """
    def fin():
        """
        Teardown of Virt console module.

        Teardown:
            Safely remove test VMs.
        """
        testflow.teardown("Safely remove test VM.")
        assert ll_vms.safely_remove_vms(
            vms=vcons_conf.VIRT_CONSOLE_VM_DICT_SANITY.keys()
        ), "Failed to safely remove vms as part of teardown."

    request.addfinalizer(fin)

    kwargs = {"positive": True,
              "monitors": [4, 1],
              "os_type": [vcons_conf.VM_OS_TYPE, "other_linux"],
              "single_qxl_pci": [None, True]
              }
    for ind in range(2):
        testflow.setup(
            "Create a VM #{num} for Multiple Monitor verification test cases "
            "execution.".format(num=ind+1)
        )
        vm_name = "{name}_{index}".format(
            name=vcons_conf.VIRT_CONSOLE_VM_SANITY,
            index=ind
        )
        assert ll_vms.createVm(
            positive=True,
            vmName=vm_name,
            vmDescription=vm_name,
            cluster=vcons_conf.CLUSTER_NAME[0],
            template=vcons_conf.TEMPLATE_NAME[0],
            os_type=kwargs.get("os_type")[ind],
            display_type=vcons_conf.VM_DISPLAY_TYPE,
            nic=vcons_conf.VIRT_CONSOLE_VM_NIC,
            network=vcons_conf.MGMT_BRIDGE
        ), "Was not able to create VM."

        vcons_conf.VIRT_CONSOLE_VM_DICT_SANITY[vm_name] = kwargs.get(
            "monitors"
        )[ind]

        testflow.setup(
            "Configure virt console VM #{num} for test execution.".format(
                num=ind+1
            )
        )
        assert ll_vms.updateVm(
            positive=kwargs.get("positive"),
            vm=vm_name,
            monitors=kwargs.get("monitors")[ind],
            single_qxl_pci=kwargs.get("single_qxl_pci")[ind]
        ), "Was not able to update VM with new values."

        testflow.setup(
            "Start VM #{num}".format(num=ind+1)
        )
        assert ll_vms.startVm(
            positive=True,
            vm=vm_name,
            wait_for_status=vcons_conf.VM_UP,
            wait_for_ip=True
        ), "Was not able to start VM: {vm_name}".format(vm_name=vm_name)


@pytest.fixture(scope="function")
def shutdown_vm(request):
    """
    Teardown procedure to shutdown VM for SVNC module.
    """

    def fin():
        """
        Teardown:
            Shutdown VM.
        """
        testflow.teardown("Shutdown VM.")
        assert ll_vms.shutdownVm(
            positive=True, vm=vcons_conf.VIRT_CONSOLE_VM_SYSTEM, async="False"
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def setup_vm_adv(request):
    """
    Setup/teardown of VM for SVNC module.

    Setup:
        1. Create instance_type for test case execution.
        2. Delete consoles from instance type.
        3. Create Template for test case execution.
        4. delete consoles from template.
        5. Create 2 VMs, one from template, other with instance type without
           consoles.
    """

    result = list()

    def fin_verify_results():
        """
        Check if none of finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)

    def fin_vm():
        """
        Teardown:
            Remove test VMs.
        """
        testflow.teardown("Remove test VMs.")
        result.append(
            (
                ll_vms.safely_remove_vms(
                    vms=vcons_conf.VIRT_CONSOLE_VM_DICT_ADV.keys()
                ), "Failed to safely remove vms as part of teardown."
            )
        )

    def fin_instance_type():
        """
        Teardown:
            Remove instance type.
        """
        testflow.teardown("Remove custom instance_type.")
        result.append(
            (
                ll_inst_type.remove_instance_type(
                    instance_type_name=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE
                ), "Failed to remove instance_type."
            )
        )

    def fin_templates():
        """
        Teardown:
            Remove test template.
        """
        testflow.teardown("Remove test template.")
        result.append(
            (
                ll_templates.safely_remove_templates(
                    templates=[vcons_conf.VIRT_CONSOLE_TEMPLATE]
                ), "Was not able to remove test Template."
            )
        )

    request.addfinalizer(fin_instance_type)
    request.addfinalizer(fin_templates)
    request.addfinalizer(fin_vm)
    request.addfinalizer(fin_verify_results)

    testflow.setup(
        "Create a instance_type for Virt console test cases execution."
    )

    assert ll_inst_type.create_instance_type(
        instance_type_name=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE,
        **vcons_conf.INSTANCE_TYPE_PARAMS
    ), "Failed to create instance_type."

    testflow.setup("Set created instance type as headless")
    helper.del_consoles(
        object_name=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE,
        obj_type="instance_type"
    )

    testflow.setup("Create a Template for Virt console test cases execution.")
    assert ll_templates.createTemplate(
        positive=True,
        vm=vcons_conf.VM_NAME[0],
        name=vcons_conf.VIRT_CONSOLE_TEMPLATE,
        cluster=vcons_conf.CLUSTER_NAME[0]
    ), "Was not able to create template."

    testflow.setup("Set created template as headless")
    helper.del_consoles(
        object_name=vcons_conf.VIRT_CONSOLE_TEMPLATE,
        obj_type="template"
    )

    obj_types = ["instance_type", "template", "template_and_instance_type"]

    for ind in enumerate(obj_types):
        testflow.setup(
            "Create a VM #{num} to verify if VM is headless when booted from "
            "headless {obj}".format(
                num=ind[0]+1,
                obj=obj_types[ind[0]]
            )
        )

        vm_name = "{name}_{index}".format(
            name=vcons_conf.VIRT_CONSOLE_VM_ADV,
            index=ind[0]
        )

        vcons_conf.VIRT_CONSOLE_VM_DICT_ADV[vm_name] = obj_types[ind[0]]

        if re.search("template", obj_types[ind[0]]):
            template = vcons_conf.VIRT_CONSOLE_TEMPLATE
        else:
            template = vcons_conf.TEMPLATE_NAME[0]

        assert ll_vms.createVm(
            positive=True,
            vmName=vm_name,
            vmDescription=vm_name,
            cluster=vcons_conf.CLUSTER_NAME[0],
            template=template,
            os_type=vcons_conf.VM_OS_TYPE,
            nic=vcons_conf.VIRT_CONSOLE_VM_NIC,
            network=vcons_conf.MGMT_BRIDGE
        ), "Was not able to create VM."

        if re.search("instance_type", obj_types[ind[0]]):
            testflow.setup("Update VM to use test instance type.")
            assert ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                instance_type=vcons_conf.VIRT_CONSOLE_VM_INSTANCE_TYPE
            ), "Failed to set instance_type for VM."

        testflow.setup(
            "Start a VM #{num} to verify if VM is headless when booted from "
            "headless {obj}".format(
                num=ind[0]+1,
                obj=obj_types[ind[0]]
            )
        )
        assert ll_vms.startVm(
            positive=True,
            vm=vm_name,
            wait_for_status=vcons_conf.VM_UP,
            wait_for_ip=True
        ), "Was not able to start VM: {vm_name}".format(vm_name=vm_name)
