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

import logging

from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api
from art.rhevm_api.tests_lib.low_level import general as ll_general

ELEMENT = 'bookmark'
COLLECTION = 'bookmarks'
BOOKMARK_API = get_api(ELEMENT, COLLECTION)

Bookmark = getDS('Bookmark')

logger = logging.getLogger(__name__)


@ll_general.generate_logs()
def create_bookmark(name, value):
    """
    Create bookmark object

    Args:
        name (str): name for the bookmark
        value (str): value to search for with this bookmark

    Returns:
        bool: True if operation is successful, otherwise - False
    """
    bookmark_obj = Bookmark(name=name, value=value)
    return BOOKMARK_API.create(entity=bookmark_obj, positive=True)[1]


@ll_general.generate_logs()
def get_bookmark_object(bookmark_name, attribute="name"):
    """
    Get bookmark object by bookmark_name

    Args:
        bookmark_name (str): name of the bookmark
        attribute (str): key to search for, 'name' or 'id'

    Returns:
        bookmark: bookmark object
    """
    return BOOKMARK_API.find(bookmark_name, attribute=attribute)


@ll_general.generate_logs()
def update_bookmark(bookmark, name=None, value=None):
    """
    Update properties of a bookmark

    Args:
        bookmark (str): name of a target bookmark
        name (str): new name for the bookmark
        value (str): new value for the bookmark

    Returns:
        bool: True if operation is successful, otherwise - False
    """
    bookmark_obj = get_bookmark_object(bookmark_name=bookmark)
    bookmark_update = Bookmark()

    if name:
        bookmark_update.set_name(name)
    if value:
        bookmark_update.set_value(value)

    return BOOKMARK_API.update(bookmark_obj, bookmark_update, positive=True)[1]


@ll_general.generate_logs()
def remove_bookmark(bookmark):
    """
    Remove bookmark

    Args:
        bookmark (str): name of a bookmark

    Returns:
        bool: True if operation is successful, otherwise - False
    """
    bookmark_obj = get_bookmark_object(bookmark_name=bookmark)
    return BOOKMARK_API.delete(bookmark_obj, positive=True)


@ll_general.generate_logs()
def get_bookmark_list():
    """
    Get list of all bookmarks

    Returns:
        list: bookmarks
    """
    return BOOKMARK_API.get(abs_link=False)


@ll_general.generate_logs()
def get_bookmark_names_list():
    """
    Get list of all bookmarks names

    Returns:
        list: bookmarks names
    """
    return [bookmark.get_name() for bookmark in get_bookmark_list()]
