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

from art.core_api import apis_exceptions
from art.core_api.apis_utils import getDS, data_st, TimeoutingSampler
from art.rhevm_api.tests_lib.low_level import (
    jobs as ll_jobs,
    general as ll_general,
    disks as ll_disks,
)
from art.rhevm_api.utils.test_utils import get_api, waitUntilGone
from art.rhevm_api.tests_lib.low_level.networks import get_vnic_profile_obj
from art.rhevm_api.tests_lib.low_level.vms import (
    DiskNotFound,
    prepare_watchdog_obj,
    createCustomPropertiesFromArg,
    getVmDisks,
)
from art.test_handler.settings import ART_CONFIG
from art.rhevm_api.utils.jobs import Job, JobsSet
from art.rhevm_api.utils.test_utils import searchForObj
import art.test_handler.exceptions as errors
from art.test_handler import exceptions

CREATE_TEMPLATE_TIMEOUT = 900
ELEMENT = 'template'
COLLECTION = 'templates'
TEMPLATE_API = get_api(ELEMENT, COLLECTION)
SD_API = get_api('storage_domain', 'storagedomains')
CL_API = get_api('cluster', 'clusters')
VM_API = get_api('vm', 'vms')
NIC_API = get_api('nic', 'nics')
DISKS_API = get_api('disk', 'disks')
DISK_ATTACHMENTS_API = get_api('disk_attachment', 'diskattachments')
WATCHDOG_API = get_api('watchdog', 'watchdogs')
CLUSTER_API = get_api('cluster', 'clusters')

Template = getDS('Template')
Cluster = getDS('Cluster')
CPU = getDS('Cpu')
CpuTopology = getDS('CpuTopology')
StorageDomain = getDS('StorageDomain')
VM = getDS('Vm')
SAMPLER_TIMEOUT = 120
SAMPLER_SLEEP = 5
BASE_TEMPLATE_VERSION = 1

ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']

logger = logging.getLogger("art.ll_lib.templates")


def _prepareTemplateObject(**kwargs):

    templ = Template()

    name = kwargs.pop('name', None)
    if name:
        templ.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        templ.set_description(description)

    memory = kwargs.pop('memory', None)
    if memory:
        templ.set_memory(memory)

    type = kwargs.pop('type', None)
    if type:
        templ.set_type(type)

    cluster = kwargs.pop('cluster', None)
    if cluster:
        cl = CL_API.find(cluster)
        templ.set_cluster(Cluster(id=cl.id))

    cpu_socket = kwargs.pop('cpu_socket', None)
    cpu_cores = kwargs.pop('cpu_cores', None)

    if cpu_socket or cpu_cores:
        templ.set_cpu(CPU(topology=CpuTopology(sockets=cpu_socket,
                                               cores=cpu_cores)))

    vm = kwargs.pop('vm', None)
    if vm:
        vmObj = VM_API.find(vm)
        templ.set_vm(VM(id=vmObj.get_id()))

    boot = kwargs.pop('boot', None)
    if boot:
        templ.set_os(
            data_st.Boot(devices=data_st.devicesType(device=boot))
        )

    storagedomain = kwargs.pop('storagedomain', None)
    if storagedomain:
        sd = SD_API.find(storagedomain)
        templ.set_storage_domain(StorageDomain(id=sd.get_id()))

    protected = kwargs.pop('protected', None)
    if protected is not None:
        templ.set_delete_protected(protected)

    custom_prop = kwargs.pop("custom_properties", None)
    if custom_prop:
        templ.set_custom_properties(createCustomPropertiesFromArg(custom_prop))

    virtio_scsi = kwargs.pop('virtio_scsi', None)
    if virtio_scsi is not None:
        virtio_scsi_obj = data_st.VirtioScsi(enabled=virtio_scsi)
        templ.set_virtio_scsi(virtio_scsi_obj)

    # template version
    version = kwargs.pop('version', None)
    if version is not None:
        templ.set_version(version)

    # stateless
    templ.set_stateless(kwargs.pop("stateless", None))

    # start_paused
    start_paused = kwargs.pop("start_paused", None)
    if start_paused:
        templ.set_start_paused(start_paused)

    # display monitors and type
    display_type = kwargs.pop("display_type", None)
    monitors = kwargs.pop("monitors", None)
    disconnect_action = kwargs.pop("disconnect_action", None)
    file_transfer_enabled = kwargs.pop("file_transfer_enabled", None)
    if monitors or display_type or disconnect_action:
        templ.set_display(
            data_st.Display(
                type_=display_type, monitors=monitors,
                disconnect_action=disconnect_action,
                file_transfer_enabled=file_transfer_enabled
            )
        )

    os_type = kwargs.pop("os_type", None)
    boot_seq = kwargs.pop("boot", None)
    if os_type is not None:
        os_type = data_st.OperatingSystem(type_=os_type)
        if boot_seq:
            if isinstance(boot_seq, basestring):
                boot_seq = boot_seq.split()
            os_type.set_boot(
                [data_st.Boot(dev=boot_dev) for boot_dev in boot_seq]
                )
        templ.set_os(os_type)

    # serial number
    serial_number = kwargs.pop("serial_number", None)
    if serial_number is not None:
        sr = data_st.SerialNumber()
        sr.set_policy('custom')
        sr.set_value(serial_number)
        templ.set_serial_number(sr)

    # usb_type
    usb_type = kwargs.pop("usb_type", None)
    if usb_type:
        usb = data_st.Usb()
        usb.set_enabled(True)
        usb.set_type(usb_type)
        templ.set_usb(usb)

    # custom emulated machine
    custom_emulated_machine = kwargs.pop("custom_emulated_machine", None)
    if custom_emulated_machine:
        templ.set_custom_emulated_machine(custom_emulated_machine)

    # custom cpu model
    custom_cpu_model = kwargs.pop("custom_cpu_model", None)
    if custom_cpu_model:
        templ.set_custom_cpu_model(custom_cpu_model)

    # soundcard enabled
    soundcard_enabled = kwargs.pop("soundcard_enabled", None)
    if soundcard_enabled:
        templ.set_soundcard_enabled(soundcard_enabled)

    # migration_downtime
    migration_downtime = kwargs.pop("migration_downtime", None)
    if migration_downtime:
        templ.set_migration_downtime(migration_downtime)

    # io_threads
    io_threads = kwargs.pop("io_threads", None)
    if io_threads:
        io = data_st.Io()
        io.set_threads(io_threads)
        templ.set_io(io)

    # boot_menu
    boot_menu = kwargs.pop("boot_menu", None)
    if boot_menu:
        bios = data_st.Bios()
        boot = data_st.BootMenu(enabled=boot_menu)
        bios.set_boot_menu(boot)
        templ.set_bios(bios)

    # cpu shares
    cpu_shares = kwargs.pop("cpu_shares", None)
    if cpu_shares is not None:
        templ.set_cpu_shares(cpu_shares)

    # cpu topology & cpu pinning
    cpu_socket = kwargs.pop("cpu_socket", None)
    cpu_cores = kwargs.pop("cpu_cores", None)
    cpu_threads = kwargs.pop("cpu_threads", None)
    if cpu_socket or cpu_cores or cpu_threads:
        cpu = data_st.Cpu()
        cpu.set_topology(
            topology=data_st.CpuTopology(
                sockets=cpu_socket, cores=cpu_cores, threads=cpu_threads
            )
        )
        templ.set_cpu(cpu)

    # timezone
    time_zone = kwargs.pop("time_zone", None)
    time_zone_offset = kwargs.pop("time_zone_offset", None)
    if time_zone is not None or time_zone_offset is not None:
        templ.set_time_zone(data_st.TimeZone(
            name=time_zone, utc_offset=time_zone_offset)
        )

    # memory policy memory_guaranteed, ballooning and max_memory
    guaranteed = kwargs.pop("memory_guaranteed", None)
    ballooning = kwargs.pop('ballooning', None)
    max_memory = kwargs.pop('max_memory', None)
    if ballooning or guaranteed or max_memory:
        templ.set_memory_policy(
            data_st.MemoryPolicy(
                guaranteed=guaranteed,
                ballooning=ballooning,
                max=max_memory,
            )
        )

    # high availablity
    ha = kwargs.pop("highly_available", None)
    ha_priority = kwargs.pop("availablity_priority", None)
    if ha is not None or ha_priority:
        templ.set_high_availability(
            data_st.HighAvailability(
                enabled=ha, priority=ha_priority
            )
        )

    return templ


@ll_general.generate_logs(step=True)
def createTemplate(
    positive, wait=True, timeout=CREATE_TEMPLATE_TIMEOUT, **kwargs
):
    """
    create new template

    __author__: edolinin

    Args:
        positive (bool): Expected status
        wait (bool): wait till creation of template is done or timeout exceeds
        timeout (int): Timeout for wait

    Keyword Args:
        vm (str): Name of vm for template generation
        name (str): Template name
        description (str):Template description
        disks (dict): Dictionary disk id as key and as value another
        dictionary with each property (format, alias, storagedomain) and its
        value
        cluster (str): Template cluster
        memory (str): Template memory size
        cpu_socket (str): Number of cpu sockets
        cpu_cores (str): Number of cpu cores
        boot (str): Template boot device
        type (str): Template type
        storagedomain (str): Name of storage domain
        protected (str): If template is delete protected
        copy_permissions (bool): True if permissions from vm to template
        should be copied
        new_version (bool): If True create as a new template version of an
        existing template, otherwise create a new template normally.
        version_name (str): A specific name for the template version

    Returns:
        bool: True if template was added properly, False otherwise
    """
    name = kwargs.get("name")
    storage_domain = kwargs.get("storagedomain")
    vm_name = kwargs.get("vm")
    copy_permissions = kwargs.get("copy_permissions")
    new_version = kwargs.get("new_version", False)
    version_name = kwargs.get("version_name", None)
    if new_version and validateTemplate(True, name):
        template_version_params = {
            'base_template': get_template_obj(name),
            'version_name': version_name,
        }
        kwargs['version'] = data_st.TemplateVersion(**template_version_params)
    template = _prepareTemplateObject(**kwargs)
    disks = kwargs.pop('disks', None)
    if disks is None:
        vm_disks = getVmDisks(vm_name)
        disks = dict()
        for disk in vm_disks:
            disk_id = disk.get_id()
            disk_properties = {
                'alias': disk.get_alias(),
                'format': disk.get_format(),
                'sparse': disk.get_sparse(),
                'storagedomain': storage_domain,
            }
            disks[disk_id] = disk_properties
    if disks:
        disk_array = data_st.Disks()
        for key, properties in disks.items():
            disk = data_st.Disk(id=key)
            disk.set_format(properties.get('format', None))
            disk.set_sparse(properties.get('sparse', None))
            disk.set_alias(properties.get('alias', None))
            storagedomain = properties.get('storagedomain', None)
            if storagedomain:
                sd = SD_API.find(storagedomain)
                disk.set_storage_domains(StorageDomain(id=sd.get_id()))
            disk_array.add_disk(disk)

        disk_attachments = data_st.DiskAttachments()
        for disk_ in disk_array.get_disk():
            disk_attachments.add_disk_attachment(
                ll_disks.prepare_disk_attachment_object(
                    disk.get_id(), disk=disk_,
                )
            )
        template.vm.set_disk_attachments(disk_attachments)
    operations = []
    if copy_permissions:
        operations.append("clone_permissions")
    template, status = TEMPLATE_API.create(
        template, positive, operations=operations
    )
    if wait and status and positive:
        status = TEMPLATE_API.waitForElemStatus(template, 'OK', timeout)

    return status


def updateTemplate(positive, template, version_number=1, **kwargs):
    """
    Update existed template

    Author: edolinin

    Args:
        positive (bool): True if update is expected to succeed, False otherwise
        template (str): Name of template that should be updated
        version_number (int): Template version number

    Keyword arguments:
        name (str): New template name
        description (str): New template description
        cluster (str): New template cluster
        memory (int): New template memory size
        max_memory (int): New template maximum memory size
        cpu_socket (int): New number of cpu sockets
        cpu_cores (int): New number of cpu cores
        boot (str): New template boot device
        type (str): New template type
        protected (bool): If template is delete protected
        watchdog_model (str): Model of watchdog card
        watchdog_action (str): Action to perform when watchdog is triggered
        custom_properties (str): Custom properties set to the template
        virtio_scsi (bool): Enables attaching disks using VirtIO-SCSI interface

    Returns
        bool: True if template was updated properly, False otherwise
    """
    template_obj = get_template_obj(template, version=version_number)
    if not template_obj:
        return False
    template_new = _prepareTemplateObject(**kwargs)
    template_object, status = TEMPLATE_API.update(
        template_obj, template_new, positive
    )

    return status


@ll_general.generate_logs()
def safely_remove_templates(templates):
    """
    Safely remove templates.

    Args:
        templates (list): List of template names (str) which to be deleted.

    Returns:
        bool: False if any of stated templates still exists, otherwise - True.
    """
    if templates:
        existing_templates = filter(check_template_existence, templates)
        if existing_templates:
            remove_templates(positive=True, templates=templates)
            return waitForTemplatesGone(True, existing_templates)
    logger.info("There are no templates to remove")
    return True


@ll_general.generate_logs()
def remove_template(
    positive, template, version_number=1, wait=True, sleep_time=SAMPLER_SLEEP,
    timeout=SAMPLER_TIMEOUT
):
    """
    Remove template

    __author__: edolinin

    Args:
        positive (bool): Expected status
        template (str): Name of template that should be removed
        version_number (int): Template version number
        wait (str): Wait until end of action if true, else return without wait
        sleep_time (int): Sleep between sampler iterations
        timeout (int): Timeout to wait for template removal

    Returns:
        bool: True if template was removed properly, False otherwise
    """
    template_obj = get_template_obj(template, version=version_number)
    if not template_obj:
        return False

    status = TEMPLATE_API.delete(template_obj, positive)
    if status and positive and wait:
        sample = TimeoutingSampler(
            timeout=timeout, sleep=sleep_time, func=validateTemplate,
            positive=False, template=template, version=version_number
        )
        return sample.waitForFuncStatus(result=True)

    return status


def remove_templates(positive, templates):
    """
    Remove multiple templates

    :param positive: True if test is positive, False if negative
    :type positive: bool
    :param templates: The templates to be removed
    :type templates: list or str
    :return: True if all the templates are removed properly, False otherwise
    :rtype: bool
    """
    if isinstance(templates, basestring):
        templates_list = templates.replace(',', ' ').split()
    else:
        templates_list = templates
    jobs = [Job(
        target=remove_template, args=(True, tmpl)) for tmpl in templates_list]
    js = JobsSet()
    js.addJobs(jobs)
    js.start()
    js.join()

    status = True
    for job in jobs:
        status = status and job.result
        if not job.result:
            TEMPLATE_API.logger.error(
                'Removing template %s failed', job.args[1])
    return status


def searchForTemplate(positive, query_key, query_val, key_name, **kwargs):
    """
    Description: search for a template by desired property
    Parameters:
       * query_key - name of property to search for
       * query_val - value of the property to search for
       * key_name - property in template object equivalent to query_key
    Return: status (True if expected number of templates equal to
                    found by search, False otherwise)
    """

    return searchForObj(TEMPLATE_API, query_key, query_val, key_name, **kwargs)


def _prepareNicObj(**kwargs):

    nic_obj = data_st.Nic()
    vnic_profile_obj = data_st.VnicProfile()

    if 'name' in kwargs:
        nic_obj.set_name(kwargs.get('name'))

    if 'interface' in kwargs:
        nic_obj.set_interface(kwargs.get('interface'))

    if 'network' in kwargs:
        if kwargs.get('network'):
            cluster = kwargs.get('cluster')
            cl_obj = CL_API.find(cluster, 'id')

        if kwargs.get('network') is None:
            nic_obj.set_vnic_profile(vnic_profile_obj)
        else:
            vnic_profile_obj = get_vnic_profile_obj(
                kwargs.get('vnic_profile') if 'vnic_profile' in kwargs else
                kwargs.get('network'), kwargs.get('network'),
                cl_obj.get_name()
            )
            nic_obj.set_vnic_profile(vnic_profile_obj)

    return nic_obj


def getTemplatesNics(template, version=BASE_TEMPLATE_VERSION):
    """
    Gets all the nics for a specific template

    Args:
        template (str): Name of the template.
        version (int): Template version number.

    Returns:
        list: Nics collection of the given template .
    """
    template_obj = get_template_obj(template, version=version)
    if not template_obj:
        return None
    return TEMPLATE_API.getElemFromLink(template_obj, link_name='nics',
                                        attr='nic', get_href=True)


@ll_general.generate_logs()
def get_template_nic(template, nic, version=BASE_TEMPLATE_VERSION):
    """
    Get NIC from template

    Args:
        template (str): Name of the template.
        nic (str): Name of the nic.
        version (int): Template version number.

    Returns:
        Nic: If found returns the specific nic element, otherwise None.
    """
    template_obj = get_template_obj(template, version=version)
    if not template_obj:
        return None

    return TEMPLATE_API.getElemFromElemColl(template_obj, nic, 'nics', 'nic')


@ll_general.generate_logs()
def addTemplateNic(
    positive, template, version=BASE_TEMPLATE_VERSION, **kwargs
):
    """
    Add nic to template

    Args:
        positive (bool): Expected status
        template (str): Name of template to add the NIC to
        version (int): Template version number

    keyword arguments:
        name (str): Name of NIC
        network (str): Network that should reside in NIC
        interface (str): NIC type. (virtio, rtl8139, e1000 and passthrough)

    Returns:
        bool: True if nic was added properly, False otherwise
    """
    template_obj = get_template_obj(template_name=template, version=version)
    if not template_obj:
        return False

    kwargs.update([("cluster", template_obj.cluster.id)])

    nic_obj = _prepareNicObj(**kwargs)
    nics_coll = getTemplatesNics(template=template, version=version)

    return NIC_API.create(nic_obj, positive, collection=nics_coll)[1]


def get_watchdog_collection(template_name, version=BASE_TEMPLATE_VERSION):
    """
    Get template watchdog collection

    Args:
        template_name (str): Template name
        version (int): template version

    Returns:
        list: List of watchdog objects
    """
    template_obj = get_template_obj(
        template_name=template_name, version=version
    )
    if not template_obj:
        return None
    logger.info("Get template %s watchdog collection", template_name)
    watchdog_collection = VM_API.getElemFromLink(
        template_obj, link_name="watchdogs", attr="watchdog", get_href=False
    )
    if not watchdog_collection:
        logging.error(
            "Template %s watchdog collection is empty", template_name
        )
    return watchdog_collection


def add_watchdog(template_name, model, action, version=BASE_TEMPLATE_VERSION):
    """
    Add watchdog card to template

    Args:
        template_name (str): Template name
        model (str): Watchdog card model
        action (str): Watchdog action
        version (int): Template version

    Returns:
        bool: True, if add watchdog card action succeed, otherwise False
    """
    template_obj = get_template_obj(
        template_name=template_name, version=version
    )
    if not template_obj:
        return False
    log_info, log_error = ll_general.get_log_msg(
        log_action="Add",
        obj_type="watchdog",
        obj_name=model,
        extra_txt="to template %s with action %s" % (template_name, action),
    )
    vm_watchdog_link = VM_API.getElemFromLink(
        elm=template_obj, link_name="watchdogs", get_href=True
    )
    watchdog_obj = prepare_watchdog_obj(model=model, action=action)

    logger.info(log_info)
    status = WATCHDOG_API.create(
        watchdog_obj, True, collection=vm_watchdog_link
    )[1]
    if not status:
        logger.error(log_error)
    return status


def delete_watchdog(template_name):
    """
    Delete watchdog card from template

    Args:
        template_name (str): Template name

    Returns:
        bool: True, if delete watchdog card action succeed, otherwise False
    """
    watchdog_collection = get_watchdog_collection(template_name=template_name)
    if not watchdog_collection:
        return False
    watchdog_obj = watchdog_collection[0]
    log_info, log_error = ll_general.get_log_msg(
        log_action="Delete",
        obj_type="watchdog",
        obj_name=watchdog_obj.get_model(),
        extra_txt="from template %s" % template_name
    )
    logger.info(log_info)
    status = WATCHDOG_API.delete(watchdog_obj, True)
    if not status:
        logger.error(log_error)
    return status


def updateTemplateNic(
    positive, template, nic, version=BASE_TEMPLATE_VERSION, **kwargs
):
    """
    Update an existing template nic

    Args:
        positive (bool): True if update is expected to succeed, False otherwise
        template (str): Name of template that we update the nic
        nic (str): Nic name that should be updated
        version (int): Template version number

    Keyword arguments:
        name (str): New nic name
        network (str): Network that nic depends on
        interface (str): Nic type. Available types: virtio, rtl8139 and e1000
            (for 2.2 also rtl8139_virtio)
        active (bool): Attribute which present nic hostplug state

    Returns:
        bool: True if nic was updated properly, False otherwise
    """
    template_obj = get_template_obj(template, version=version)
    if not template_obj:
        return False
    kwargs.update([('cluster', template_obj.cluster.id)])

    nic_obj = get_template_nic(template, nic, version)
    nic_new = _prepareNicObj(**kwargs)

    res, status = NIC_API.update(nic_obj, nic_new, positive)

    return status


def removeTemplateNic(positive, template, nic, version=BASE_TEMPLATE_VERSION):
    """
    Remove an existing template nic

    Args:
        positive (bool): True if update is expected to succeed, False otherwise
        template (str): Name of template that we update the nic
        nic (str): Nic name that should be updated
        version (int): Template version number

    Returns:
        bool: True if nic was removed properly, False otherwise
    """
    log_info_txt, log_error_txt = ll_general.get_log_msg(
        log_action="Remove", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="from template %s, version: %s" % (template, version)
    )
    nic_obj = get_template_nic(template, nic, version)
    logger.info(log_info_txt)
    res = NIC_API.delete(nic_obj, positive)
    if not res:
        logger.error(log_error_txt)
        return False
    return True


def removeTemplateFromExportDomain(
    positive, template, export_storagedomain, version=BASE_TEMPLATE_VERSION,
    timeout=SAMPLER_TIMEOUT, sleep=SAMPLER_SLEEP
):
    """
    Removes a template from export domain

    __author__: istein

    Args:
        positive (bool): Expected status
        template (str): Template name
        export_storagedomain (str): Storage domain where to remove vm from
        version (int): Template version number
        timeout (int): Timeout to wait for template removal
        sleep (int): Sleep between sampler iterations

    Returns:
        bool: True if template was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Remove", obj_type="template", obj_name=template,
        positive=positive,
        extra_txt="from export domain %s" % export_storagedomain,
        template_version=version
    )
    export_storage_domain_obj = SD_API.find(export_storagedomain)
    template_obj = get_template_obj_from_export_domain(
        export_storage_domain_obj, template, version
    )
    if not template_obj:
        return False
    logger.info(log_info)
    status = TEMPLATE_API.delete(template_obj, positive)
    if not status:
        logger.error(log_error)
        return False

    if positive:
        sample = TimeoutingSampler(
            timeout=timeout, sleep=sleep,
            func=export_domain_template_exist, template=template,
            export_domain=export_storagedomain, positive=False
        )
        return sample.waitForFuncStatus(result=True)
    return True


def export_domain_template_exist(
    template, export_domain, version=BASE_TEMPLATE_VERSION, positive=True
):
    """
    Checks if a template exists in an export domain

    Args:
        template (str): Template name
        export_domain (str): Export domain name
        version (int): Template version number
        positive (bool): Expected status

    Returns:
        bool: True if got expected result, False otherwise
    """
    export_domain_object = SD_API.find(export_domain)
    template_obj = get_template_obj_from_export_domain(
        export_domain_object, template, version
    )
    if bool(template_obj) != positive:
        logger.error(
            "Try to find template %s, version: %s in export domain: %s. "
            "Expected: %s, got: %s",
            template, version, export_domain, positive, bool(template_obj)
        )
        return False
    return True


def validateTemplate(positive, template, version=BASE_TEMPLATE_VERSION):
    """
    Validate template if exist

    Args:
        positive (bool): True if template is expected to exist, False otherwise
        template (str): Template name
        version (int): Template version number
    Returns:
        bool: True if template existence is as expected (positive),
            False otherwise
    """
    return bool(
        get_template_obj(template_name=template, version=version)
    ) is positive


def exportTemplate(
    positive, template, storagedomain, version=BASE_TEMPLATE_VERSION,
    exclusive='false', wait=False
):
    """
    Export template

    __author__: edolinin

    Args:
        positive (bool): Expected status
        template (str): Name of template that should be exported
        storagedomain (str): Name of export storage domain where to export to
        exclusive (str): 'true' if overwrite already existed templates with the
            same name, 'false' otherwise ('false' by default)
        version (int): Template version number
        wait (bool): Waits until template is exported

    Returns:
        bool: True if template was exported properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Export", obj_type="template", obj_name=template,
        positive=positive,
        extra_txt="to export domain %s. override: %s" % (
            storagedomain, exclusive
        )
    )
    template_obj = get_template_obj(template, version=version)
    if not template_obj:
        return False

    sd = StorageDomain(name=storagedomain)
    action_params = dict(storage_domain=sd, exclusive=exclusive)
    logger.info(log_info)
    result = bool(
        TEMPLATE_API.syncAction(
            template_obj, "export", positive, **action_params
        )
    )
    if wait and result:
        return wait_for_export_domain_template_state(storagedomain, template)

    if not result:
        logger.error(log_error)
    return result


def import_template(
    positive, template, source_storage_domain, destination_storage_domain,
    cluster, version=BASE_TEMPLATE_VERSION, name=None, async=False
):
    """
    Import template from export_domain

    __author__: edolinin

    Args:
        positive (bool): True if success, False otherwise
        template (str): name of template to be imported
        source_storage_domain (str): from which to export the template
        destination_storage_domain (str): which to import the template
        cluster (str): cluster into which template will be imported
        version (int): Template version number
        name (str): new name for the imported template
        async (bool): True wait for response, False otherwise

    Returns:
        bool: True if function should wait for response, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        log_action="Import", obj_type="template", obj_name=template,
        positive=positive,
        extra_txt="from export domain %s" % source_storage_domain
    )
    export_storage_domain_obj = SD_API.find(source_storage_domain)
    template_obj = get_template_obj_from_export_domain(
        export_storage_domain_obj, template, version
    )
    if not template_obj:
        return False
    sd = StorageDomain(name=destination_storage_domain)
    cl = Cluster(name=cluster)

    action_params = dict(
        storage_domain=sd,
        cluster=cl,
        async=async
    )

    action_name = 'import'
    if ART_CONFIG['RUN']['engine'] in ('cli', 'sdk'):
        action_name = 'import_template'

    if name is not None:
        action_params['clone'] = True
        new_template = Template(name=name)
        action_params['template'] = new_template

    logger.info(log_info)
    status = bool(
        TEMPLATE_API.syncAction(
            template_obj, action_name, positive, **action_params
        )
    )
    if not async:
        ll_jobs.wait_for_jobs([ENUMS['job_add_vm_template']])

    if not status:
        logger.error(log_error)
    return status


def getTemplateDisks(template):
    """
    Return template's disks

    :param template: Template name
    :type template: str
    :returns: List of disks
    :rtype: list
    """
    return ll_disks.get_disk_list_from_disk_attachments(
        ll_disks.get_disk_attachments(name=template, object_type='template')
    )


def _getTemplateFirstDiskByName(template, diskName, idx=0):
    """
    Description: Searches for template's disk by name
                 Name is not unique!
    Parameters
        * template - Name of template we want disk from
        * diskId - disk's id
        * idx - index of found disk to return
    Return: Disk object
    """
    disk_not_found_msg = "Disk %s was not found in tmp's %s disk collection"
    disks = getTemplateDisks(template)
    found = [disk for disk in disks if disk.get_name() == diskName]
    if not found:
        raise DiskNotFound(disk_not_found_msg % (diskName, template))
    return found[idx]


def copyTemplateDisk(template, disk_name, target_sd):
    """
    Copy disk of template to another storage domain
    Args:
        template (str): Name of the disk's template
        disk_name (str): Name of the disk
        target_sd (str): Name of storage domain disk should be copied to

    Returns: DiskException if syncAction returns False (syncAction should
        raise exception itself instead of returning False)

    """
    # comment from cmestreg: XXX AVOID THIS
    # TBD call for "/api/templates/{template:id}/disks/{disk:id}/copy"
    # for a /api/disks/{disk:id}/copy better go to disks.py
    disk = _getTemplateFirstDiskByName(template, disk_name)
    sd = SD_API.find(target_sd)
    if not DISKS_API.syncAction(
            disk, 'copy', storage_domain=sd, positive=True
    ):
        raise errors.DiskException("Failed to copy disk %s of template %s to "
                                   " storage domain %s"
                                   % (disk_name, template, target_sd))


def get_template_state(template_name):
    """
    Return the template state

    :param template_name: Get the state of the template name
    :type template_name: str
    :return: Template status (illegal, locked, ok)
    :rtype: str
    """
    template = TEMPLATE_API.find(template_name)
    return template.get_status()


def waitForTemplatesStates(names, state=ENUMS['template_state_ok'],
                           timeout=CREATE_TEMPLATE_TIMEOUT, sleep=10):
    """
    Wait until all templates are in state given by 'states' argument
    Parameters:
        * names - Comma separated list of templates' names
        * states - Desired state for all given templates
    Author: jlibosva
    """
    def get_pending_templates(template_names, state):
        """
        Gets templates that doesn't fit the desired state
        Parameters:
        * template_names - list of templates' names
        * state - desired state
        """
        templates = [TEMPLATE_API.find(name) for name in template_names]
        return [templ for templ in templates if
                (templ.get_status() != state)]

    if not isinstance(names, list):
        names = names.replace(',', ' ').split()
    else:
        names = names
    sampler = TimeoutingSampler(
        timeout, sleep, get_pending_templates, names, state)
    for bad_templates in sampler:
        if not bad_templates:
            return True
    raise exceptions.TemplateException(
        "Timeout: Templates %s haven't reached state %s after %s seconds" %
        (bad_templates, state, timeout))


def wait_for_template_disks_state(template, state=ENUMS['disk_state_ok'],
                                  timeout=CREATE_TEMPLATE_TIMEOUT):
    """
    Description: Waits until all template's disks are in given state
    Author: ratamir
    Parameters:
    * template - name of the template
    * state - desired state of disks
    * timeout - how long should it wait
    """
    disks = getTemplateDisks(template)
    for disk in disks:
        if not DISKS_API.waitForElemStatus(disk, state, timeout):
            raise exceptions.DiskException(
                "Timeout, disk %s is still in status %s instead of desired %s"
                % (disk.alias, disk.get_status(), state))


def waitForTemplatesGone(positive, templates, timeout=600, samplingPeriod=10):
    '''
    Wait for templates to disappear from the setup. This function will block up
    to `timeout` seconds, sampling the templates list every `samplingPeriod`
    seconds, until no template specified by names in `templates` exists.

    Parameters:
        * templates - comma (and no space) separated string of template names
        * timeout - Time in seconds for the templates to disappear
        * samplingPeriod - Time in seconds for sampling the templates list
    '''
    return waitUntilGone(
        positive, templates, TEMPLATE_API, timeout, samplingPeriod)


def check_template_existence(template_name):
    """
    Check if template exist
    **Author**: alukiano

    **Parameters**:
        * *template_name* - template name
    **Returns**: True if template exist, otherwise False
    """
    name_query = "name=%s" % template_name
    try:
        template_obj = TEMPLATE_API.query(name_query, all_content=True)[0]
    except IndexError:
        logger.warning('Entity %s not found!' % template_name)
        return False
    if not template_obj:
        return False
    return True


def copy_template_disks(template_name, storage_domains, wait=True):
    """
    Copies a template disks to target storage domains

    Arguments:
        template_name (str): Template name
        storage_domains (list): List of target storage domains
        wait (bool): True in case we should wait for the copy to complete,
            False otherwise
    """
    template_disks = [
        x.get_name() for x in getTemplateDisks(template_name)
    ]
    disk_sd = ll_disks.get_disk_storage_domain_name(
        template_disks[0], template_name=template_name
    )
    for sd in storage_domains:
        if sd not in disk_sd:
            for disk in template_disks:
                wait_for_template_disks_state(template_name)
                logging.info(
                    "Copy disk: %s of template %s to storage domain: %s",
                    disk, template_name, sd
                )
                copyTemplateDisk(template_name, disk, sd)

            if wait:
                wait_for_template_disks_state(template_name)


def get_template_from_cluster(cluster):
    """
    Gets all templates in given cluster
    :param cluster: cluster name
    :type cluster: str
    :return: return templates names in list
    :rtype: list
    """
    logging.info("Getting all templates in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    templates = TEMPLATE_API.get(abs_link=False)
    templates_in_cluster = [
        template.name for template in templates
        if template.cluster and template.cluster.id == cluster_id
        ]
    logging.info("Templates in cluster: %s", templates_in_cluster)
    return templates_in_cluster


def get_all_template_objects():
    """
    Get all templates objects from engine
    :return: List of template objects
    :rtype: list
    """
    return TEMPLATE_API.get(abs_link=False)


def get_all_template_objects_names():
    """
    Get all templates objects names from engine
    :return: List of template objects names
    :rtype: list
    """
    return [template.get_name() for template in get_all_template_objects()]


def get_template_nics_objects(template):
    """
    Get all NICs objects from template
    :param template: Template name
    :type template: str
    :return: List off template NICs
    :rtype: list
    """
    template_obj = TEMPLATE_API.find(template)
    return TEMPLATE_API.getElemFromLink(
        template_obj, link_name="nics", attr="nic")


def wait_for_export_domain_template_state(
        export_domain, template, state=ENUMS['disk_state_ok'],
        timeout=CREATE_TEMPLATE_TIMEOUT
):
    """
    Wait for status of the specified template under the specified export_domain
    :param export_domain: Export domain name
    :type export_domain: str
    :param template: Template name
    :type template: str
    :param state: Expected state of the template
    :type state: str
    :param timeout: Time to wait for the expected status
    :type timeout: int
    :return: True if template's state is as expected in the timeout frame.
     False otherwise
    """
    export_domain_object = SD_API.find(export_domain)
    template_object = TEMPLATE_API.getElemFromElemColl(
        export_domain_object, template
    )
    if not TEMPLATE_API.waitForElemStatus(template_object, state, timeout):
        TEMPLATE_API.logger.error(
            "Template: %s from export domain: %s failed to enter state: %s",
            template, export_domain, state
        )
        return False
    return True


@ll_general.generate_logs(warn=True)
def get_templates_obj(template_name, all_content=False):
    """
    Get template objects by using the template_name

    Args:
        template_name (str): The template name from which the template object
            should be retrieved
        all_content (bool): Specifies whether the entire content for the
            template should be retrieved, False is the default

    Returns:
        list: A list of Template objects for the input template_name
    """
    template_name_query = "name=%s" % template_name
    return TEMPLATE_API.query(template_name_query, all_content=all_content)


@ll_general.generate_logs(warn=True)
def get_template_obj(
    template_name, all_content=False, version=BASE_TEMPLATE_VERSION
):
    """
    Gets template object by template_name and specific template version

    Args:
        template_name (str): Name of the template.
        all_content (bool): True if we want to apply all_content header, False
            otherwise.
        version (int): Template version number.

    Returns:
         Template: If found returns the template object, otherwise None
    """
    templates_list = get_templates_obj(template_name, all_content)
    if not templates_list:
        return None

    if template_name == "Blank":
        return templates_list[0]

    for template in templates_list:
        if template.get_version().get_version_number() == version:
            return template
    return None


@ll_general.generate_logs(warn=True)
def get_template_obj_from_export_domain(
    export_domain_object, template_name, version=BASE_TEMPLATE_VERSION
):
    """
    Gets template object by name and specific template version from export
    domain

    Args:
        export_domain_object (ExportDomain): Export domain object
        template_name (str): Name of the template
        version (int): Template version number

    Returns:
         object: If found returns the template object, otherwise None
    """
    try:
        templates_list = TEMPLATE_API.getElemFromLink(export_domain_object)
    except apis_exceptions.EntityNotFound:
        return None

    for template_object in templates_list:
        if template_object.get_version().get_version_number() == version:
            return template_object
    return None


def get_template_disk_by_id(template_name, disk_id):
    """
    Get Disk object from template by disk ID

    Arguments:
        template_name (str): Name of template we want disk from
        disk_id (str): Disk ID
    Returns:
        Disk object: Disk object with given ID, or None
    """
    disks = getTemplateDisks(template_name)
    found = [disk for disk in disks if disk.get_id() == disk_id]
    return found[0] if found else None


def remove_template_disk_from_storagedomain(
        positive, template_name, storage_domain, disk_id, force=False
):
    """
    Remove a copy of template disk from storage domain

    Arguments:
        positive (bool): Expected result
        template_name (str): Name of the template which it's disk needs
        to be removed
        storage_domain (str): Name of the storage domain
        disk_id (str): Disk ID
        force (bool): True in case we should remove the disk forcibly

    Returns:
        bool: True if disk removed successfully, False otherwise
    """
    disk_obj = get_template_disk_by_id(template_name, disk_id)
    operations = ['storage_domain=%s' % storage_domain]
    if force:
        operations.append('force=true')
    return DISK_ATTACHMENTS_API.delete(
        disk_obj, positive, operations=operations
    )


def get_template_boot_sequence(template_name):
    """
    Get template boot sequence

    Args:
        template_name (str): template name

    Returns:
        list: list of vm boot devices
    """
    template_obj = get_template_obj(template_name)
    boots = template_obj.get_os().get_boot()
    return boots.get_devices().get_device()
