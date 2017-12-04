#!/usr/bin/env python

# Copyright (C) 2016 Red Hat, Inc.
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

"""
High-level functions for templates.
"""

import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.templates as ll_template
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.rhevm_api.utils.test_utils import get_api

VM_API = get_api('vm', 'vms')


@ll_general.generate_logs(step=True)
def check_vnic_on_template_nic(template, nic, vnic):
    """
    Check if vnic is resides on template nic.

    Args:
        template (str): Template name to check for VNIC profile name on.
        nic (str): NIC on template to check the VNIC profile on.
        vnic (str): VNIC name to check on the NIC of Template.

    Returns:
        bool: True if VNIC profile with 'vnic' name is located on the nic
            of the Template.
    """
    template_nic_obj = ll_template.get_template_nic(template=template, nic=nic)
    if not template_nic_obj:
        VM_API.logger.error("Template %s doesn't have nic '%s'", template, nic)
        return False

    vnic_obj = ll_vms.get_vm_vnic_profile_obj(nic=template_nic_obj)
    return vnic_obj.get_name() == vnic if vnic_obj else vnic is None
