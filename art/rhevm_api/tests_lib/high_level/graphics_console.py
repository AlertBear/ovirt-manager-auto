#!/usr/bin/env python
# Copyright (C) 2017 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    general as ll_general,
    instance_types as ll_inst_types,
    templates as ll_template,
    graphics_console as ll_gc
)

GRAPHIC_CONSOLE_API = get_api("graphics_console", "graphicsconsoles")


@ll_general.generate_logs()
def set_console_spice_plus_vnc(
        obj_type, obj_name, expected_vm_state='down', reboot=True
):
    """
    Set SPICE+VNC flag for object. VM should be in down state.

    Args:
        obj_type (str): type of object to set console for, alowed values:
                            - vm
                            - template
                            - instance_type
        obj_name (str): name of the object on which spice+vnc console type will
                        be set.
        expected_vm_state (str): Expected VM state to perform action,
                                 default="DOWN"
        reboot (bool): If True reboot VM after update if it is in UP state,
                       otherwise - False.

    Returns:
        bool: operation status - True for success, False in case of failure.

    Raises:
        Exception: if unexpected obj_type specified.
    """

    if obj_type == 'instance_type':
        ll_inst_types.update_instance_type(
            instance_type_name=obj_name, display_type='spice'
        )
        obj = ll_inst_types.get_instance_type_object(obj_name)
    elif obj_type == 'template':
        ll_template.updateTemplate(
            positive=True, template=obj_name, display_type='spice'
        )
        obj = ll_template.get_template_obj(obj_name)
    else:
        obj = ll_vms.get_vm_obj(obj_name)
        # This action is required because updateVm method is using update
        # rest_api call, which during compare action is comparing expected
        # values vs actual VM values, which will only take place after VM
        # reboot. As it is leading to failure during compare procedure - will
        # use compare=False if VM is not in Down state.
        compare = obj.status == expected_vm_state
        ll_vms.updateVm(
            positive=True, vm=obj_name, display_type='spice', compare=compare
        )
        if not compare and reboot:
            ll_vms.reboot_vm(positive=True, vm=obj_name)

    return ll_gc.create_graphics_console(obj=obj, protocol="vnc")
