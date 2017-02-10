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

import copy

from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.tests_lib.low_level import general as ll_general
from art.core_api.apis_utils import getDS

GRAPHIC_CONSOLE_API = get_api("graphics_console", "graphicsconsoles")


@ll_general.generate_logs()
def create_graphics_console(obj, protocol):
    """
    Create graphics console for object with console protocol.

    Args:
        obj (object): object to add graphic console to (VM, Template or
                      instance_type).
        protocol (str): protocol type spice or VNC.

    Returns:
        Bool: True if operation successful, otherwise - False.
    """
    graphic_console = getDS('GraphicsConsole')
    graphic_console_obj = graphic_console(protocol=protocol)
    collection = GRAPHIC_CONSOLE_API.getElemFromLink(
        obj,
        get_href=True
    )
    return GRAPHIC_CONSOLE_API.create(
        graphic_console_obj,
        positive=True,
        collection=collection
    )[1]


@ll_general.generate_logs()
def delete_virt_console(console):
    """
    Remove console devices from the resource.

    Args:
        console (obj): data_structures.GraphicsConsole class instance for
                       console sub-collection objects.

    Returns:
        bool: True for successful action, False - otherwise.
    """
    return GRAPHIC_CONSOLE_API.delete(console, positive=True)


@ll_general.generate_logs()
def get_console_vv_file(console):
    """
    Obtain information from console VV file.

    Args:
        console (obj): data_structures.GraphicsConsole class instance for
                       console sub-collection objects.

    Returns:
        str: data stored in VV file for specific console.
    """

    headers_set = copy.deepcopy(GRAPHIC_CONSOLE_API.get_headers())
    try:
        data = GRAPHIC_CONSOLE_API.get(
            console.href,
            custom_headers={'Accept': 'application/x-virt-viewer'},
            no_parse=True
        )
    finally:
        if 'Accept' in headers_set.keys():
            GRAPHIC_CONSOLE_API.set_header(
                header='Accept', value=headers_set['Accept']
            )
        else:
            GRAPHIC_CONSOLE_API.set_header(header='Accept', value=None)
    return data


@ll_general.generate_logs()
def get_graphics_consoles_values(obj):
    """
    Get graphics consoles values.

    Args:
        obj (object): Object of an instance to get graphics consoles for.

    Returns:
        list: contains of data_structures.GraphicsConsole class instances for
              console sub-collection objects.
    """
    return GRAPHIC_CONSOLE_API.getElemFromLink(obj)
