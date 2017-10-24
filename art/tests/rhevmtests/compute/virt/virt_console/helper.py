import re
import copy

from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level import graphics_console as ll_gc
from art.rhevm_api.tests_lib.high_level import graphics_console as hl_gc
from art.rhevm_api.tests_lib.low_level import templates as ll_templates
from art.rhevm_api.tests_lib.low_level import instance_types as ll_inst_types

import config as vcons_conf


def del_consoles(object_name, obj_type):
    """
    Delete console devices from a object (VM/Template/Instance-type)

    Args:
        object_name (str): Name of the test object.
        obj_type (str): type of the object. Available types are:
                        - vm
                        - template
                        - instance_type

    Raises:
        AssertionError: error is reproduced in case of console deletion
                        failure.
    """
    if obj_type == 'vm':
        obj = ll_vms.get_vm_obj(object_name)
    elif obj_type == 'template':
        obj = ll_templates.get_template_obj(object_name)
    elif obj_type == 'instance_type':
        obj = ll_inst_types.get_instance_type_object(object_name)
    consoles = ll_gc.get_graphics_consoles_values(obj)
    if consoles:
        for console in consoles:
            assert ll_gc.delete_virt_console(console), (
                "Was not able to delete {console} console.".format(
                    console=console.protocol
                )
            )


def verify_object_headless(object_name, object_type):
    """
    Verify if object is in headless state by verifying if there are no displays
     present.

    Args:
        object_name (str): name of object which has to be verified.
        object_type (str): type of object, can be:
                               - vm
                               - template
                               - instance_type

    Returns:
        bool: True if vm is headless (has no displays), False - otherwise.
    """
    if object_type == 'vm':
        obj = ll_vms.get_vm_obj(vm_name=object_name)
    elif object_type == 'template':
        obj = ll_templates.get_template_obj(object_name)
    elif object_type == 'instance_type':
        obj = ll_inst_types.get_instance_type_object(object_name)
    consoles = ll_gc.get_graphics_consoles_values(obj)
    if obj.display or consoles:
        return False
    return True


def set_console_type(console_type, object_name, obj):
    """
    Set console type for instance.

    Args:
        console_type (str): type of console to be set. Available types are:
                            - spice
                            - vnc
                            - spice+vnc
        object_name (str): name of the object.

        obj (str): type of the object to set console for. Available types are:
                   - vm
                   - template
                   - instance_type

    Raises:
        AssertionError: error is being raised if console type was not set for
                        an object.
    """
    fail_message = "Failed to set {cons_type} console for {obj}.".format(
        cons_type=console_type,
        obj=obj.upper()
    )
    if re.search("spice_plus_vnc", console_type.lower()):
        if obj == 'vm':
            assert hl_gc.set_console_spice_plus_vnc(obj, object_name), (
                fail_message
            )
        elif obj == 'template':
            assert hl_gc.set_console_spice_plus_vnc(
                obj, object_name
            ), fail_message
        elif obj == 'instance_type':
            assert hl_gc.set_console_spice_plus_vnc(
                obj, object_name
            ), fail_message

    else:
        if obj == 'vm':
            assert ll_vms.updateVm(
                positive=True, vm=object_name, display_type=console_type
            ), fail_message
        elif obj == 'template':
            assert ll_templates.updateTemplate(
                positive=True, template=object_name, display_type=console_type
            ), fail_message
        elif obj == 'instance_type':
            assert ll_inst_types.update_instance_type(
                instance_type_name=object_name, display_type=console_type
            )


def get_vv_files_info(consoles):
    """
    Download info stored in console VV file.

    Args:
        consoles (list): list of console objects.

    Returns:
        list: list of strings with VV file info for each console available.
    """
    vv_files = []
    for console in consoles:
        vv_files.append(ll_gc.get_console_vv_file(console))
    return vv_files


def compute_data_from_vv(data):
    """
    Organize data received as REST responce with VV file content into form of
    dict.

    Args:
        data (str): vv file information in the form of string.

    Returns:
        data_dict (dict): VV file data formatted in the form of dictionary.
    """
    new_val = None
    data_dict = {}
    data_list = data.strip().split('\n')
    for elem in data_list:
        if re.search('\[*\]', elem):
            data_dict[elem] = {}
            new_val = copy.deepcopy(elem)
        if re.search('=', elem):
            data_dict[new_val][elem.split('=')[0]] = '='.join(
                elem.split('=')[1:]
            )
    return data_dict


def get_vv_data_list(consoles):
    """
    Form a list of data in form of dicts for each console available:

    Args:
        consoles (list): list of console objects.

    Returns:
        data_list (list): list of dicts containing formatted information about
                          each console.
    """
    data_list = []
    raw_data = get_vv_files_info(consoles)
    for data in raw_data:
        data_dict = compute_data_from_vv(data)
        data_list.append(data_dict)
    return data_list


def verify_vv_fields(data_list):
    """
    Verify if proper fields are present in VV file.

    Args:
        data_list (list): list of dicts containing formatted information about
                          each console.

    Returns:
        exceptions_list (list): list of fields that were not found in VV file.
    """
    exceptions_list = []
    for data in data_list:
        protocol = data[data.keys()[1]]['type']
        for key in vcons_conf.VV_FILE_FIELDS[protocol].keys():
            for element in vcons_conf.VV_FILE_FIELDS[protocol][key]:
                if element not in data[key].keys():
                    exceptions_list.append(element)
    return exceptions_list


def import_object(obj_name, obj_type):
    """
    Import object.

    Args:
        obj_name (str): name of the object.
        obj_type (str): type of the object, can be "vm" or "template" only.

    Returns:
        bool: True if import was successful, otherwise - False
    """

    if obj_type == "vm":
        return ll_vms.importVm(
            positive=True,
            vm=obj_name,
            export_storagedomain=vcons_conf.EXPORT_DOMAIN_NAME,
            import_storagedomain=vcons_conf.STORAGE_NAME[0],
            cluster=vcons_conf.CLUSTER_NAME[0],
            name=vcons_conf.VIRT_CONSOLE_VM_IMPORT_NEW
        )
    elif obj_type == "template":
        return ll_templates.import_template(
            positive=True,
            template=obj_name,
            source_storage_domain=vcons_conf.EXPORT_DOMAIN_NAME,
            destination_storage_domain=vcons_conf.STORAGE_NAME[0],
            cluster=vcons_conf.CLUSTER_NAME[0],
            name=vcons_conf.VIRT_CONSOLE_TEMPLATE_IMPORT_NEW
        )


def export_object(obj_name, obj_type):
    """
    Export object.

    Args:
        obj_name (str): name of the object.
        obj_type (str): type of the object, can be "vm" or "template" only.

    Returns:
        bool: True if import was successful, otherwise - False
    """

    if obj_type == "vm":
        return ll_vms.exportVm(
            True,
            obj_name,
            vcons_conf.EXPORT_DOMAIN_NAME
        )
    elif obj_type == "template":
        return ll_templates.exportTemplate(
            positive=True,
            template=obj_name,
            storagedomain=vcons_conf.EXPORT_DOMAIN_NAME,
            wait=True
        )
