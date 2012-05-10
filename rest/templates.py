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

from utils.data_structures import StorageDomain
from utils.restutils import get_api

ELEMENT = 'template'
COLLECTION = 'templates'
util = get_api(ELEMENT, COLLECTION)


def exportTemplate(positive, template, storagedomain, exclusive='false'):
    '''
    Description: export template
    Author: edolinin
    Parameters:
       * template - name of template that should be exported
       * storagedomain - name of export storage domain where to export to
       * exclusive - 'true' if overwrite already existed templates with the same
                       name, 'false' otherwise ('false' by default)
    Return: status (True if template was exported properly, False otherwise)
    '''

    templObj = util.find(template)
 
    sd = StorageDomain(name=storagedomain)

    actionParams = dict(storage_domain=sd, exclusive=exclusive)
    
    return util.syncAction(templObj, "export", positive, **actionParams)
      