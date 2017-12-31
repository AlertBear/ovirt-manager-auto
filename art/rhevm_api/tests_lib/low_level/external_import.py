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

from art.rhevm_api.tests_lib.low_level import (
    general as ll_general,
    clusters as ll_clusters,
    storagedomains as ll_sd,
    hosts as ll_hosts
)

from art.core_api.apis_utils import data_st
from art.rhevm_api.utils.test_utils import get_api

EXTERNAL_VM_IMPORT_API = get_api("external_vm_import", "externalvmimports")
EXTERNAL_VM_IMPORT = data_st.ExternalVmImport
FILE = data_st.File


@ll_general.generate_logs(step=True)
def prepare_external_vm_import_object(cluster, storage_domain, vm, **kwargs):
    """
    Creates externalVmImport object
    Arguments:
        cluster (str): cluster name
        storage_domain (str): storage domain name
        vm (str): internal vm name
    Keyword arguments:
        name (str): Name of vm in the provider
        cluster (str): Name of cluster
        storage_domain (str): Name of destination storage domain
        vm_name (str): Name for the vm in the system
        user_name (str): User name for the provider
        password (str): Password for the provider
        provider (str): Name of the provider
        url (str): Url of provider
        driver_iso (str): Name of the driver iso file in iso domain
        sparse (str): True if import the image as sparse, False otherwise
        engine_url (str): Engine Url for the destination engine
        host (str): Name of the host to use for importing the image

    Returns:
         ExternalVmImport: External vm import object
    """
    cluster_object = ll_clusters.get_cluster_object(cluster)
    sd_object = ll_sd.get_storage_domain_obj(storage_domain)
    host = kwargs.get('host')
    host_object = ll_hosts.get_host_object(host) if host else None
    vm_object = data_st.Vm(name=vm)
    driver_iso = kwargs.get('driver_iso')
    driver_object = FILE(id=driver_iso) if driver_iso else None
    name = kwargs.get('name')
    password = kwargs.get('password')
    provider = kwargs.get('provider')
    url = kwargs.get('url')
    sparse = kwargs.get('sparse')
    user_name = kwargs.get('user_name')

    return EXTERNAL_VM_IMPORT(
        name=name, cluster=cluster_object, storage_domain=sd_object,
        host=host_object, vm=vm_object, sparse=sparse, username=user_name,
        password=password, provider=provider, url=url,
        drivers_iso=driver_object
    )


@ll_general.generate_logs(step=True)
def import_vm_from_external_provider(
    provider_vm_name, cluster, storage_domain, new_vm_name, user_name,
    password, provider, url, driver_iso=None, sparse=True,
    engine_url=None, host=None
):
    """
    Import a vm from an external provider e.g. VmWare or KVM

    Args:
        provider_vm_name (str): Name of vm in the provider
        cluster (str): Name of cluster
        storage_domain (str): Name of destination storage domain
        new_vm_name (str): Name for the vm in the system
        user_name (str): User name for the provider
        password (str): Password for the provider
        provider (str): Name of the provider
        url (str): Url of provider
        driver_iso (str): Name of the driver iso file in iso domain
        sparse (bool): True if import the image as sparse, False otherwise
        engine_url (str): Engine Url for the destination engine
        host (str): Name of the host to use for importing the image

    Returns:
        bool: True if vm was created successfully, False otherwise
    """
    external_vm_import_object = prepare_external_vm_import_object(
        name=provider_vm_name, cluster=cluster, storage_domain=storage_domain,
        host=host, vm=new_vm_name, sparse=sparse, user_name=user_name,
        password=password, provider=provider, url=url,
        driver_iso=driver_iso
    )
    collection = '%s/%s' % (engine_url, EXTERNAL_VM_IMPORT_API._collection)
    return EXTERNAL_VM_IMPORT_API.create(
        entity=external_vm_import_object,
        positive=True,
        collection=collection,
        validate=False
    )[1]
    # Todo: Add wait argument for function when bz#1395154 is resolved
