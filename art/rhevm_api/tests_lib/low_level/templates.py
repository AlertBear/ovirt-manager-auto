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
import time

from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, data_st, TimeoutingSampler
import art.rhevm_api.tests_lib.low_level.jobs as ll_jobs
from art.rhevm_api.utils.test_utils import get_api, split, waitUntilGone
from art.rhevm_api.tests_lib.low_level.disks import getObjDisks
import art.rhevm_api.tests_lib.low_level.general as ll_general
from art.rhevm_api.tests_lib.low_level.networks import (
    get_vnic_profile_obj, VNIC_PROFILE_API,
)
from art.rhevm_api.tests_lib.low_level.vms import (
    DiskNotFound,
    _prepareWatchdogObj,
    getWatchdogModels,
    createCustomPropertiesFromArg,
)
from art.test_handler.settings import opts
from utilities.jobs import Job, JobsSet
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
WATCHDOG_API = get_api('watchdog', 'watchdogs')
CLUSTER_API = get_api('cluster', 'clusters')

Template = getDS('Template')
Cluster = getDS('Cluster')
CPU = getDS('CPU')
CpuTopology = getDS('CpuTopology')
StorageDomain = getDS('StorageDomain')
VM = getDS('VM')
SAMPLER_TIMEOUT = 120
SAMPLER_SLEEP = 5

ENUMS = opts['elements_conf']['RHEVM Enums']

logger = logging.getLogger("art.ll_lib.templates")


def _prepareTemplateObject(**kwargs):

    templ = Template()

    name = kwargs.pop('name', None)
    if name:
        templ.set_name(name)

    description = kwargs.pop('description', None)
    if description:
        templ.set_description(description)

    memory = kwargs.pop('name', None)
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
        templ.set_os(data_st.Boot(dev=boot))

    storagedomain = kwargs.pop('storagedomain', None)
    if storagedomain:
        sd = SD_API.find(storagedomain)
        templ.set_storage_domain(StorageDomain(id=sd.get_id()))

    protected = kwargs.pop('protected', None)
    if protected is not None:
        templ.set_delete_protected(protected)

    copy_permissions = kwargs.pop('copy_permissions', None)
    if copy_permissions:
        perms = data_st.Permissions()
        perms.set_clone(True)
        templ.set_permissions(perms)

    custom_prop = kwargs.pop("custom_properties", None)
    if custom_prop:
        templ.set_custom_properties(createCustomPropertiesFromArg(custom_prop))

    virtio_scsi = kwargs.pop('virtio_scsi', None)
    if virtio_scsi is not None:
        virtio_scsi_obj = data_st.VirtIO_SCSI(enabled=virtio_scsi)
        templ.set_virtio_scsi(virtio_scsi_obj)

    return templ


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

    Keyword arguments:
        vm (str): Name of vm for template generation
        name (str): Template name
        description (str):Template description
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

    Returns:
        bool: True if template was added properly, False otherwise
    """
    name = kwargs.get("name")
    log_info, log_error = ll_general.get_log_msg(
        action="Create", obj_type="template", obj_name=name, positive=positive,
        **kwargs
    )
    template = _prepareTemplateObject(**kwargs)
    logger.info(log_info)
    template, status = TEMPLATE_API.create(template, positive)
    if wait and status and positive:
        status = TEMPLATE_API.waitForElemStatus(template, 'OK', timeout)

    if not status:
        logger.error(log_error)
    return status


def updateTemplate(positive, template, **kwargs):
    '''
    Description: update existed template
    Author: edolinin
    Parameters:
       * template - name of template that should be updated
       * name - new template name
       * description - new template description
       * cluster - new template cluster
       * memory - new template memory size
       * cpu_socket - new number of cpu sockets
       * cpu_cores - new number of cpu cores
       * boot - new template boot device
       * type - new template type
       * protected - if template is delete protected
       * watchdog_model - model of watchdog card
       * watchdog_action - action to perform when watchdog is triggered
       * custom_properties - custom properties set to the template
       * virtio_scsi - Enables attaching disks using VirtIO-SCSI interface
    Return: status (True if template was updated properly, False otherwise)
    '''

    templObj = TEMPLATE_API.find(template)
    templNew = _prepareTemplateObject(**kwargs)
    templObj, status = TEMPLATE_API.update(templObj, templNew, positive)

    # FIXME: check if polling instead of sleep
    time.sleep(40)

    watchdog_model = kwargs.pop('watchdog_model', None)
    watchdog_action = kwargs.pop('watchdog_action', None)

    if status and watchdog_model is not None:
        status = updateTemplateWatchdog(template,
                                        watchdog_model,
                                        watchdog_action)

    return status


def removeTemplate(
    positive, template, wait=True, sleepTime=SAMPLER_SLEEP,
    timeout=SAMPLER_TIMEOUT
):
    """
    Remove template

    __author__: edolinin

    Args:
        positive (bool): Expected status
        template (str): Name of template that should be removed
        wait (str): Wait until end of action if true, else return without wait
        sleepTime (int): Sleep between sampler iterations
        timeout (int): Timeout to wait for template removal

    Returns:
        bool: True if template was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type="template", obj_name=template,
        positive=positive
    )
    template_obj = TEMPLATE_API.find(template)
    logger.info(log_info)
    status = TEMPLATE_API.delete(template_obj, positive)
    if status and positive and wait:
        sample = TimeoutingSampler(
            timeout=timeout, sleep=sleepTime, func=validateTemplate,
            positive=False, template=template
        )
        res = sample.waitForFuncStatus(result=True)
        if not res:
            logger.error(log_error)
            return False
        return True

    elif status and positive and not wait:
        return True

    elif status and not positive:
        return True

    logger.error(log_error)
    return False


def removeTemplates(positive, templates):
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
        templates_list = split(templates)
    else:
        templates_list = templates
    jobs = [Job(
        target=removeTemplate, args=(True, tmpl)) for tmpl in templates_list]
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

    nic_obj = data_st.NIC()
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

    if 'active' in kwargs:
        nic_obj.set_active(kwargs.get('active'))

    return nic_obj


def getTemplatesNics(template):

    templ_obj = TEMPLATE_API.find(template)
    return TEMPLATE_API.getElemFromLink(templ_obj, link_name='nics',
                                        attr='nic', get_href=True)


def getTemplatesNic(template, nic):

    templ_obj = TEMPLATE_API.find(template)
    return TEMPLATE_API.getElemFromElemColl(templ_obj, nic, 'nics', 'nic')


def addTemplateNic(positive, template, **kwargs):
    """
    Add nic to template

    :param positive: Expected status
    :type positive: bool
    :param template: Name of template to add the NIC to
    :type template: str
    :param kwargs: NIC kwargs
        name (str): Name of NIC
        network (str): Network that should reside in NIC
        interface (str): NIC type. (virtio, rtl8139, e1000 and passthrough)
    :type kwargs: dict
    :return: Status (True if nic was added properly, False otherwise)
    :rtype: bool
    """
    nic_name = kwargs.get("name")
    log_info_txt, log_error_txt = ll_general.get_log_msg(
        action="add", obj_type="nic", obj_name=nic_name, positive=positive,
        **kwargs
    )
    templ_obj = TEMPLATE_API.find(template)
    kwargs.update([("cluster", templ_obj.cluster.id)])

    nic_obj = _prepareNicObj(**kwargs)
    nics_coll = getTemplatesNics(template)

    logger.info("%s to %s", log_info_txt, template)
    status = NIC_API.create(nic_obj, positive, collection=nics_coll)[1]
    if not status:
        logger.error(log_error_txt)
        return False
    return True


def updateTemplateWatchdog(template, watchdog_model, watchdog_action):
    """
    Description: Add watchdog card to Template
    Parameters:
        * template - Name of the watchdog's template
        * watchdog_model - model of watchdog card-ib6300esb or empty string
        * watchdog_action - action of watchdog card
    Return: status (True if watchdog card added successfully. False otherwise)
    """
    templateObj = TEMPLATE_API.find(template)
    templateWatchdog = VM_API.getElemFromLink(templateObj,
                                              link_name='watchdogs',
                                              attr='watchdog',
                                              get_href=False)
    status, models = getWatchdogModels(template, False)
    if not status:
        return False

    if watchdog_model in models['watchdog_models']:
        watchdogObj = _prepareWatchdogObj(watchdog_model, watchdog_action)
        if not templateWatchdog:
            if not (watchdog_action and watchdog_model):
                return False
            vmWatchdog = TEMPLATE_API.getElemFromLink(
                templateObj,
                link_name='watchdogs',
                get_href=True)

            return WATCHDOG_API.create(watchdogObj, True,
                                       collection=vmWatchdog)[1]

        return WATCHDOG_API.update(templateWatchdog[0],
                                   watchdogObj,
                                   True)[1]
    if templateWatchdog:
        return TEMPLATE_API.delete(templateWatchdog[0], True)
    return True


def updateTemplateNic(positive, template, nic, **kwargs):
    '''
    Description: update an existing nic
    Author: atal
    Parameters:
       * template - name of template that we update the nic
       * nic - nic name that should be updated
       * name - new nic name
       * network - network that nic depends on
       * interface - nic type. available types: virtio, rtl8139 and e1000
                    (for 2.2 also rtl8139_virtio)
       * active - Boolean attribute which present nic hostplug state
    Return: status (True if nic was updated properly, False otherwise)
    '''
    templ_obj = TEMPLATE_API.find(template)
    kwargs.update([('cluster', templ_obj.cluster.id)])

    nic_obj = getTemplatesNic(template, nic)
    nic_new = _prepareNicObj(**kwargs)

    res, status = NIC_API.update(nic_obj, nic_new, positive)

    return status


def removeTemplateNic(positive, template, nic):
    """
    Remove nic from template

    :param positive: Expected status
    :type positive: bool
    :param template: Template where nic should be removed
    :type template: str
    :param nic: NIC name that should be removed
    :type nic: str
    :return: status (True if nic was removed properly, False otherwise)
    :rtype: bool
    """
    log_info_txt, log_error_txt = ll_general.get_log_msg(
        action="Remove", obj_type="NIC", obj_name=nic, positive=positive,
        extra_txt="from template %s" % template
    )
    nic_obj = getTemplatesNic(template, nic)
    logger.info(log_info_txt)
    res = NIC_API.delete(nic_obj, positive)
    if not res:
        logger.error(log_error_txt)
        return False
    return True


def removeTemplateFromExportDomain(
    positive, template, datacenter, export_storagedomain,
    timeout=SAMPLER_TIMEOUT, sleep=SAMPLER_SLEEP
):
    """
    Removes a template from export domain

    __author__: istein

    Args:
        positive (bool): Expected status
        template (str): Template name
        datacenter (str): Name of data center
        export_storagedomain (str): Storage domain where to remove vm from
        timeout (int): Timeout to wait for template removal
        sleep (int): Sleep between sampler iterations

    Returns:
        bool: True if template was removed properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Remove", obj_type="template", obj_name=template,
        positive=positive,
        extra_txt="from export domain %s" % export_storagedomain
    )
    export_storage_domain_obj = SD_API.find(export_storagedomain)
    template_obj = TEMPLATE_API.getElemFromElemColl(
        export_storage_domain_obj, template
    )
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


def export_domain_template_exist(template, export_domain, positive=True):
    """
    Checks if a template exists in an export domain

    Args:
        template (str): Template name
        export_domain (str): Export domain name
        positive (bool): Expected status

    Returns:
        bool: True if template exists in export domain False otherwise
    """
    export_domain_object = SD_API.find(export_domain)
    try:
        TEMPLATE_API.getElemFromElemColl(export_domain_object, template)
    except EntityNotFound:
        if positive:
            TEMPLATE_API.logger.error(
                "template %s cannot be found in export domain: %s",
                template, export_domain
            )
            return False
        return True
    return True


def validateTemplate(positive, template):
    '''
    Description: Validate template if exist
    Author: egerman
    Parameters:
       * template - template name
    Return: status (True if template exist, False otherwise)
    '''
    templates = TEMPLATE_API.get(absLink=False)
    templates = filter(lambda x: x.name.lower() == template.lower(), templates)
    return bool(templates) == positive


def getTemplateId(positive, template):
    '''
    Description: Get template id
    Author: egerman
    Parameters:
       * template - template name
    Return: True and template id or False and None
    '''
    try:
        templObj = TEMPLATE_API.find(template)
    except EntityNotFound:
        return False, {'templateId': None}
    return True, {'templateId': templObj.get_id()}


def exportTemplate(
    positive, template, storagedomain, exclusive='false', wait=False
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
        wait (bool): Waits until template is exported

    Returns:
        bool: True if template was exported properly, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Create", obj_type="template", obj_name=template,
        positive=positive, extra_txt="to export domain %s" % storagedomain
    )
    template_obj = TEMPLATE_API.find(template)
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
    cluster, name=None, async=False
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
        name (str): new name for the imported template
        async (bool): True wait for response, False otherwise

    Returns:
        bool: True if function should wait for response, False otherwise
    """
    log_info, log_error = ll_general.get_log_msg(
        action="Import", obj_type="template", obj_name=template,
        positive=positive,
        extra_txt="from export domain %s" % source_storage_domain
    )
    export_storage_domain_obj = SD_API.find(source_storage_domain)
    template_obj = TEMPLATE_API.getElemFromElemColl(
        export_storage_domain_obj,
        template
    )

    sd = StorageDomain(name=destination_storage_domain)
    cl = Cluster(name=cluster)

    action_params = dict(
        storage_domain=sd,
        cluster=cl,
        async=async
    )

    action_name = 'import'
    if opts['engine'] in ('cli', 'sdk'):
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
    tmpObj = TEMPLATE_API.find(template)
    disks = TEMPLATE_API.getElemFromLink(
        tmpObj, link_name='disks', attr='disk', get_href=False)
    return disks


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
    Description: Copy disk of template to another storage domain
    Parameters:
        * template - Name of the disk's template
        * disk_name - Name of the disk
        * target_sd - Name of storage domain disk should be copyied to
    Throws: DiskException if syncAction returns False (syncAction should raise
            exception itself instead of returning False)
    """
    # comment from cmestreg: XXX AVOID THIS
    # TBD call for "/api/templates/{template:id}/disks/{disk:id}/copy"
    # for a /api/disks/{disk:id}/copy better go to disks.py
    disk = _getTemplateFirstDiskByName(template, disk_name)
    sd = SD_API.find(target_sd)
    if not DISKS_API.syncAction(
            disk, 'copy', storage_domain=sd, positive=True
    ):
        raise errors.DiskException("Failed to move disk %s of template %s to "
                                   " storage domain %s"
                                   % (disk_name, template, target_sd))


def get_template_state(template_name):
    """
    Return the template state

    :param template_name: Get the state of the template name
    :type template_name: str
    :return: Template state (illegal, locked, ok)
    :rtype: str
    """
    template = TEMPLATE_API.find(template_name)
    return template.get_status().get_state()


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
                (templ.get_status().get_state() != state)]

    names = split(names)
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
    disks = getObjDisks(template, get_href=False, is_template=True)
    for disk in disks:
        if not DISKS_API.waitForElemStatus(disk, state, timeout):
            raise exceptions.DiskException(
                "Timeout, disk %s is still in status %s insted of desired %s"
                % (disk.alias, disk.get_status().get_state(), state))


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


def check_vnic_on_template_nic(template, nic='nic1', vnic='rhevm'):
    """
    Check for vnic parameter value if this profile resides on the nic
    parameter
    **Author**: gcheresh

    **Parameters**:
        * *template* - template name to check for VNIC profile name on
        * *nic* - NIC on template to check the VNIC profile on
        * *vnic* - vnic name to check on the NIC of Template
    **Returns**: True if VNIC profile with 'vnic' name is located on the nic
    of the Template
    """
    try:
        nic = getTemplatesNic(template=template, nic=nic)
    except EntityNotFound:
        VM_API.logger.error("Template %s doesn't have nic '%s'", template,
                            nic)
        return False
    if nic.get_vnic_profile():
        vnic_obj = VNIC_PROFILE_API.find(val=nic.get_vnic_profile().get_id(),
                                         attribute='id')
        return vnic_obj.get_name() == vnic
    # for NIC that doesn't have VNIC profile on it
    else:
        return vnic is None


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
        logger.error('Entity %s not found!' % template_name)
        return False
    if not template_obj:
        return False
    return True


def copy_template_disks(positive, template, disks, storagedomain, async=True):
    """
    Description: Copies disks of given template to target storage domain
    Author: ratamir
    Parameters:
    * template - name of the template
    * disks - list of disks separated by comma
    * storagedomain - target storage domain name
    * async -
    """
    disks_names = split(disks)
    storage_domain = SD_API.find(storagedomain)
    all_disks = getObjDisks(template, is_template=True, get_href=False)
    relevant_disks = [disk for disk in all_disks if
                      (disk.get_name() in disks_names)]
    for disk in relevant_disks:
        if not TEMPLATE_API.syncAction(
                disk, action='copy', positive=positive, async=async,
                storage_domain=storage_domain
        ):
            raise exceptions.TemplateException(
                "Copying of disk %s of template %s to storage domain %s "
                "failed." % (disk.name, template, storagedomain))


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
    templates = TEMPLATE_API.get(absLink=False)
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
    return TEMPLATE_API.get(absLink=False)


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


def get_template_obj(template_name, all_content=False):
    """
    Get Template object by using the Template name

    __author__ = "glazarov"
    :param template_name: The Template name from which the Template object
    should be retrieved
    :type template_name: str
    :param all_content: Specifies whether the entire content for the Template
    should be retrieved, False is the default
    :type all_content: bool
    :returns: The Template object for the input template_name
    :rtype: Template object
    """
    template_name_query = "name=%s" % template_name
    # Retrieve the entire object content only in the case where this is
    # requested
    if all_content:
        return TEMPLATE_API.query(template_name_query,
                                  all_content=all_content)[0]
    return TEMPLATE_API.query(template_name_query)[0]
