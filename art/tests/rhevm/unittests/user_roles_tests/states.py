#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Red Hat, Inc.
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

""" Enums of possible states of RHEVM objects. """

class Enum(set):
    """ Implementation of Enum type.

    The name of the enum item is equal to its content.
    Source - http://stackoverflow.com/a/2182437/770335

    >>> Animals = Enum(["DOG", "CAT", "HORSE"])
    >>> print Animals.DOG
    DOG
    """
    def __getattr__(self, name):
        if name in self:
            return name
        else:
            raise AttributeError("Unknown Enum item")


#: States into which a host can get
#:
#: >>> print states.host.installing
#: installing
host = Enum([
    "down",
    "error",
    "initializing",
    "installing",
    "install_failed",
    "maintenance",
    "non_operational",
    "non_responsive",
    "pending_approval",
    "preparing_for_maintenance",
    "problematic",
    "unassigned",
    "reboot",
    "up"
    ])

#: States into which a storage domain can get
storage = Enum([
    "active",
    "inactive",
    "maintenance",
    "locked",
    "mixed",
    "unattached",
    "unknown",
    "unreachable"
    ])

#: States into which an oVirt network can get
network = Enum([
    "operational",
    "non_operational"
    ])

#: States into which a template can get
template = Enum([
    "illegal",
    "locked",
    "ok",
    ])

#: States into which a VM can get
vm = Enum([
    "unassigned",
    "down",
    "up",
    "powering_up",
    "powered_down",
    "paused",
    "migrating",
    "migrating_from",
    "migrating_to",
    "unknown",
    "not_responding",
    "wait_for_launch",
    "reboot_in_progress",
    "saving_state",
    "restoring_state",
    "suspended",
    "image_illegal",
    "image_locked",
    "powering_down",
    ])

#: States into which a disk can get
disk = Enum([
    "illegal",
    "invalid",
    "locked",
    "ok"
    ])
