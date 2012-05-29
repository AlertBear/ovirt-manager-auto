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

from rhevm_api.test_utils import get_api
from framework_utils.apis_utils import getDS

ELEMENT = 'tag'
COLLECTION = 'tags'
util = get_api(ELEMENT, COLLECTION)

Tag = getDS('Tag')
TagParent = getDS('TagParent')


def _prepareTagObject(**kwargs):

    tag = Tag()

    if 'name' in kwargs:
        tag.set_name(kwargs.get('name'))

    if 'description' in kwargs:
        tag.set_description(kwargs.get('description'))

    if 'parent' in kwargs:
        parent = util.find(kwargs.pop('parent'))
        tag.set_parent(TagParent(tag=parent))

    return tag


def addTag(positive, **kwargs):
    '''
    Description: create new tag
    Author: edolinin
    Parameters:
       * name - name of a new tag
       * description - tag description
       * parent - name of the tag to be used as a parent.
    Return: status (True if tag was created properly, False otherwise)
    '''

    tag = _prepareTagObject(**kwargs)
    tag, status = util.create(tag, positive)

    return status


def updateTag(positive, tag, **kwargs):
    '''
    Description: update existed tag
    Author: edolinin
    Parameters:
       * tag - name of a tag that should be updated
       * name - new tag name
       * description - new tag description
       * parent - name of the new parent tag
    Return: status (True if tag was updated properly, False otherwise)
    '''

    tagObj = util.find(tag)
    tagUpd = _prepareTagObject(**kwargs)
    tagUpd, status = util.update(tagObj, tagUpd, positive)
    return status


def removeTag(positive, tag):
    '''
    Description: remove existed tag
    Author: edolinin
    Parameters:
       * tag - name of a tag that should be removed
    Return: status (True if tag was removed properly, False otherwise)
    '''

    tagObj = util.find(tag)
    return util.delete(tagObj, positive)

