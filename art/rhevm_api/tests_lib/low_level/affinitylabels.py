#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Module that handles affinity labels
"""

import logging

import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.rhevm_api.utils import test_utils

AFFINITY_LABEL_NAME = "affinity label"

AFFINITY_LABEL_DS_NAME = "AffinityLabel"
HOST_DS_NAME = "Host"
VM_DS_NAME = "Vm"

AFFINITY_LABEL_API = test_utils.get_api("affinity_label", "affinitylabels")

logger = logging.getLogger("art.ll_lib.affinitylabels")


def __get_affinity_label_collection_link_from_element(
    element_obj, element_api
):
    """
    Get affinity labels collection from the element

    Args:
        element_obj (BaseResource): Element object
        element_api (GetApi): Element API

    Returns:
        str: Link on affinity labels collection
    """
    return element_api.getElemFromLink(
        elm=element_obj, link_name="affinitylabels", get_href=True
    )


def add_affinity_label_to_element(
    element_obj, element_api, element_type, affinity_label_name
):
    """
    Add affinity label to the element

    Args:
        element_obj (BaseResource): Element object
        element_api (GetApi): Element API
        element_type (str): Element type
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if add action succeed, otherwise False
    """
    aff_label_col_link = __get_affinity_label_collection_link_from_element(
        element_obj=element_obj, element_api=element_api
    )
    if not aff_label_col_link:
        logger.error("No elements under affinitylabels collection")
        return False
    aff_label_id = AffinityLabels.get_label_object(
        label_name=affinity_label_name
    ).get_id()
    aff_label_obj = ll_general.prepare_ds_object(
        object_name=AFFINITY_LABEL_DS_NAME, id=aff_label_id
    )
    element_name = element_obj.get_name()
    log_info, log_err = ll_general.get_log_msg(
        log_action="Add",
        obj_type=AFFINITY_LABEL_NAME,
        obj_name=affinity_label_name,
        extra_txt="to the {0} {1}".format(element_type, element_name)
    )
    logger.info(log_info)
    status = AFFINITY_LABEL_API.create(
        entity=aff_label_obj, positive=True, collection=aff_label_col_link
    )[1]
    if not status:
        logger.error(log_err)
    return status


def remove_affinity_label_from_element(
    element_obj, element_api, element_type, affinity_label_name
):
    """
    Remove affinity label from the element

    Args:
        element_obj (BaseResource): Element object
        element_api (GetApi): Element API
        element_type (str): Element type
        affinity_label_name (str): Affinity label name

    Returns:
        bool: True, if remove action succeed, otherwise False
    """
    aff_label_col_link = __get_affinity_label_collection_link_from_element(
        element_obj=element_obj, element_api=element_api
    )
    aff_label_id = AffinityLabels.get_label_object(
        label_name=affinity_label_name
    ).get_id()
    aff_label_href = "{0}/{1}".format(aff_label_col_link, aff_label_id)
    aff_label_obj = ll_general.prepare_ds_object(
        object_name=AFFINITY_LABEL_DS_NAME, href=aff_label_href
    )
    element_name = element_obj.get_name()
    log_info, log_err = ll_general.get_log_msg(
        log_action="Remove",
        obj_type=AFFINITY_LABEL_NAME,
        obj_name=affinity_label_name,
        extra_txt="from the {0} {1}".format(element_type, element_name)
    )
    logger.info(log_info)
    status = AFFINITY_LABEL_API.delete(
        entity=aff_label_obj, positive=True
    )
    if not status:
        logger.error(log_err)
    return status


class AffinityLabels(object):
    """
    1) Add affinity label
    2) Remove affinity label
    3) Update affinity label
    4) Add affinity label to the VM
    5) Remove affinity label from the VM
    6) Add affinity label to the host
    7) Remove affinity label from the host
    """
    hosts_collection = "hosts"
    vms_collection = "vms"

    @classmethod
    def get_label_object(cls, label_name):
        """
        Get affinity label object

        Args:
            label_name (str): Affinity label name

        Returns:
            AffinityLabel: Affinity label instance
        """
        logger.info("Get affinity label %s object", label_name)
        return AFFINITY_LABEL_API.find(val=label_name)

    @classmethod
    def create(cls, name, **kwargs):
        """
        Create new affinity label object

        Args:
            name (str): Affinity label name

        Keyword Args:
            read_only (bool): Is affinity label read only

        Returns:
            bool: True, if create action succeed, otherwise False
        """
        affinity_label_obj = ll_general.prepare_ds_object(
            object_name=AFFINITY_LABEL_DS_NAME, name=name, **kwargs
        )
        log_info, log_error = ll_general.get_log_msg(
            log_action="Create",
            obj_type=AFFINITY_LABEL_DS_NAME,
            obj_name=name,
            positive=True,
            **kwargs
        )
        logger.info(log_info)
        status = AFFINITY_LABEL_API.create(
            entity=affinity_label_obj, positive=True
        )[1]
        if not status:
            logger.error(log_error)
        return status

    @classmethod
    def update(cls, old_name, **kwargs):
        """
        Update affinity label object

        Args:
            old_name (str): Affinity label name

        Keyword Args:
            name (str): New affinity label name
            read_only (bool): Is affinity label read only

        Returns:
            bool: True, if update action succeed, otherwise False
        """
        old_affinity_label_obj = cls.get_label_object(
            label_name=old_name
        )
        new_affinity_label_obj = ll_general.prepare_ds_object(
            object_name=AFFINITY_LABEL_DS_NAME, **kwargs
        )
        log_info, log_error = ll_general.get_log_msg(
            log_action="Update",
            obj_type=AFFINITY_LABEL_DS_NAME,
            obj_name=old_name,
            positive=True,
            **kwargs
        )
        logger.info(log_info)
        status = AFFINITY_LABEL_API.update(
            origEntity=old_affinity_label_obj,
            newEntity=new_affinity_label_obj,
            positive=True
        )[1]
        if not status:
            logger.error(log_error)
        return status

    @classmethod
    def delete(cls, name):
        """
        Delete affinity label

        Args:
            name (str): Affinity label name

        Returns:
            bool: True, if delete action succeed, otherwise False
        """
        affinity_label_obj = cls.get_label_object(label_name=name)
        log_info, log_error = ll_general.get_log_msg(
            log_action="Delete",
            obj_type=AFFINITY_LABEL_DS_NAME,
            obj_name=name
        )
        logger.info(log_info)
        status = AFFINITY_LABEL_API.delete(
            entity=affinity_label_obj, positive=True
        )
        if not status:
            logger.error(log_error)
        return status

    @classmethod
    def __get_collection_link(cls, label_name, collection_name):
        """
        Get collection link or object from affinity label

        Args:
            label_name (str): Affinity label name
            collection_name (str): Collection name

        Returns:
            str: Specific collection link
        """
        affinity_label_obj = cls.get_label_object(
            label_name=label_name
        )
        return AFFINITY_LABEL_API.getElemFromLink(
            elm=affinity_label_obj, link_name=collection_name, get_href=True
        )

    @classmethod
    def __add_label_to_element(
        cls,
        label_name,
        element_name,
        element_api,
        element_type,
        collection_name
    ):
        """
        Add affinity label to the element

        Args:
            label_name (str): Affinity label
            element_name (str): Element name
            element_api (GetApi): Element API
            element_type (str): Element type, how it looks under data_structure
            collection_name (str): Element collection name

        Returns:
            bool: True, if add affinity label succeed, otherwise False
        """
        element_collection_link = cls.__get_collection_link(
            label_name=label_name, collection_name=collection_name
        )
        element_id = element_api.find(val=element_name).get_id()
        element_obj = ll_general.prepare_ds_object(
            object_name=element_type, id=element_id
        )
        log_info, log_err = ll_general.get_log_msg(
            log_action="Add",
            obj_type=AFFINITY_LABEL_NAME,
            obj_name=label_name,
            extra_txt="to the {0} {1}".format(element_type, element_name)
        )
        logger.info(log_info)
        status = element_api.create(
            entity=element_obj,
            positive=True,
            collection=element_collection_link
        )[1]
        if not status:
            logger.error(log_err)
        return status

    @classmethod
    def __remove_label_from_element(
        cls,
        label_name,
        element_name,
        element_api,
        element_type,
        collection_name,
    ):
        """
        Remove affinity label from the element

        Args:
            label_name (str): Affinity label
            element_name (str): Element name
            element_api (GetApi): Element API
            element_type (str): Element type, how it looks under data_structure
            collection_name (str): Element collection name

        Returns:
            bool: True, if remove affinity label action succeed,
                otherwise False
        """
        elm_col_link = cls.__get_collection_link(
            label_name=label_name, collection_name=collection_name
        )
        element_id = element_api.find(element_name).get_id()
        label_elm_link = "{0}/{1}".format(elm_col_link, element_id)
        element_obj = ll_general.prepare_ds_object(
            object_name=element_type, href=label_elm_link
        )
        log_info, log_err = ll_general.get_log_msg(
            log_action="Remove",
            obj_type=AFFINITY_LABEL_NAME,
            obj_name=label_name,
            extra_txt="from the {0} {1}".format(element_type, element_name)
        )
        logger.info(log_info)
        status = element_api.delete(entity=element_obj, positive=True)
        if not status:
            logger.error(log_err)
        return status

    @classmethod
    def add_label_to_host(cls, label_name, host_name):
        """
        Add affinity label to the host

        Args:
            label_name (str): Affinity label name
            host_name (str): Host name

        Returns:
            bool: True, if succeed to add affinity label to the host,
                otherwise False
        """
        return cls.__add_label_to_element(
            label_name=label_name,
            element_name=host_name,
            element_api=ll_hosts.HOST_API,
            element_type=HOST_DS_NAME,
            collection_name=cls.hosts_collection
        )

    @classmethod
    def remove_label_from_host(cls, label_name, host_name):
        """
        Remove affinity label from the host

        Args:
            label_name (str): Affinity label name
            host_name (str): Host name

        Returns:
            bool: True, if succeed to remove affinity label from the host,
                otherwise False
        """
        return cls.__remove_label_from_element(
            label_name=label_name,
            element_name=host_name,
            element_api=ll_hosts.HOST_API,
            element_type=HOST_DS_NAME,
            collection_name=cls.hosts_collection
        )

    @classmethod
    def add_label_to_vm(cls, label_name, vm_name):
        """
        Add affinity label to the VM

        Args:
            label_name (str): Affinity label name
            vm_name (str): VM name

        Returns:
            bool: True, if succeed to add affinity label to the VM,
                otherwise False
        """
        return cls.__add_label_to_element(
            label_name=label_name,
            element_name=vm_name,
            element_api=ll_vms.VM_API,
            element_type=VM_DS_NAME,
            collection_name=cls.vms_collection
        )

    @classmethod
    def remove_label_from_vm(cls, label_name, vm_name):
        """
        Remove affinity label from the VM

        Args:
            label_name (str): Affinity label name
            vm_name (str): VM name

        Returns:
            bool: True, if succeed to remove affinity label from the VM,
                otherwise False
        """
        return cls.__remove_label_from_element(
            label_name=label_name,
            element_name=vm_name,
            element_api=ll_vms.VM_API,
            element_type=VM_DS_NAME,
            collection_name=cls.vms_collection
        )
