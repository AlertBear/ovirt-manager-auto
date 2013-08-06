#!/usr/bin/env python
""" Enums of roles in RHEVM """


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

## Could be changed in future
role = Enum([
    "UserRole",
    "UserVmManager",
    "TemplateAdmin",
    "UserTemplateBasedVm",
    "SuperUser",
    "ClusterAdmin",
    "DataCenterAdmin",
    "StorageAdmin",
    "HostAdmin",
    "NetworkAdmin",
    "VmPoolAdmin",
    "QuotaConsumer",
    "DiskOperator",
    "DiskCreator",
    "VmCreator",
    "TemplateCreator",
    "TemplateOwner",
    "GlusterAdmin",
    "PowerUserRole",
    "VnicProfileUser",
    "ExternalEventsCreator"
    ])
