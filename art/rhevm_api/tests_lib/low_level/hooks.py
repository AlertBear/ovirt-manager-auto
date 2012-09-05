#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
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

import os
import tempfile
import logging
from art.rhevm_api.utils.test_utils import get_api
from utilities.machine import Machine
from art.core_api import is_action

logger = logging.getLogger(__package__ + __name__)


@is_action()
def checkForFileExistenceAndContent(ip, password, filename, content=None,
    user='root'):
    '''
    Checks for file existence and content on given address
    Author: jvorcak
    Parameters:
       * ip - address of the machine
       * password - password for accessing the machine
       * filename - file name
       * content - content of the remote file
       * user - username for accessing the machine
    '''

    vm = Machine(ip, user, password).util('linux')
    new_filename = tempfile.gettempdir()\
            + os.sep + os.path.basename(filename)

    if not vm.copyFrom(filename, new_filename):
        logger.error("Couldn't copy filename %s from address %s" %\
                (filename, ip))
        return False

    if content:
        content = content.strip()
        with open(new_filename, "r") as f:
            file_content = f.read().strip()

        if file_content != content:
            logger.error("Content of the file differs from expected content")
            logger.error("Expected content: %s" % content)
            logger.error("Actual content: %s" % file_content)
            return False

    return True

@is_action()
def checkForFileExistenceAndContentOnVm(vmName, password, filename,
    content=None, user='root'):
    '''
    Checks for file existence and content on given virtual Machine
    Author: jvorcak
    Parameters:
       * vmName - name of the virtual Machine
       * filename - file name
       * content - content of the remote file
       * user - username for accessing vm
       * password - password for accessing vm
    '''
    vm_api = get_api('vm', 'vms')
    vm = vm_api.find(vmName)

    if not vm.guest_info or not vm.guest_info.ips:
        logger.error("Can't find ip address of the vm, make sure that\
                rhev-agent is running")
        return False

    ip = vm.guest_info.ips[0].address

    return checkForFileExistenceAndContent(ip, password, filename, content, user)
