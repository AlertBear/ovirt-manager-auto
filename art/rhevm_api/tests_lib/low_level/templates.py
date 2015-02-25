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
from art.rhevm_api.tests_lib.low_level.disks import getObjDisks
import art.test_handler.exceptions as errors

from art.core_api.apis_exceptions import EntityNotFound
from art.core_api.apis_utils import getDS, data_st, TimeoutingSampler
from art.rhevm_api.utils.test_utils import get_api, split, waitUntilGone
from art.rhevm_api.utils.xpath_utils import XPathMatch
from art.rhevm_api.tests_lib.low_level.networks import getVnicProfileObj, \
    VNIC_PROFILE_API
from art.rhevm_api.tests_lib.low_level.vms import DiskNotFound, \
    _prepareWatchdogObj, getWatchdogModels
from art.test_handler.settings import opts
from utilities.jobs import Job, JobsSet
from art.rhevm_api.utils.test_utils import searchForObj
from art.core_api import is_action
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

ENUMS = opts['elements_conf']['RHEVM Enums']

xpathMatch = is_action('xpathTemplates',
                       id_name='xpathMatch')(XPathMatch(TEMPLATE_API))

logger = logging.getLogger(__name__)


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

    return templ


@is_action()
def createTemplate(positive, wait=True, timeout=CREATE_TEMPLATE_TIMEOUT,
                   **kwargs):
    '''
    Description: add new template
    Author: edolinin
    Parameters:
       * vm - name of vm for template generation
       * name - template name
       * description - template description
       * cluster - template cluster
       * memory - template memory size
       * cpu_socket - number of cpu sockets
       * cpu_cores - number of cpu cores
       * boot - template boot device
       * type - template type
       * wait - wait until end of creation of template (true) or exit without
                waiting (false)
       * storagedomain - name of storagedomain
       * protected - if template is delete protected
       * copy_permissions - True if perms from vm to template should be copied
    Return: status (True if template was added properly, False otherwise)
    '''

    templ = _prepareTemplateObject(**kwargs)
    templ, status = TEMPLATE_API.create(templ, positive)
    if wait and status and positive:
        status = TEMPLATE_API.waitForElemStatus(templ, 'OK', timeout)

    return status


@is_action()
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


@is_action()
def removeTemplate(positive, template, wait=True, sleepTime=10, timeout=60):
    '''
    Description: remove existed template
    Author: edolinin
    Parameters:
       * template - name of template that should be removed
       * wait - wait until end of action if true, else return without wait
       * sleepTime - How much time wait between validation
       * timeout - maximun waiting time
    Return: status (True if template was removed properly, False otherwise)
    '''
    templObj = TEMPLATE_API.find(template)
    status = TEMPLATE_API.delete(templObj, positive)

    if status and positive and wait:
        handleTimeout = 0
        while handleTimeout <= timeout:
            if not validateTemplate(positive, template):
                # Add a delay, required as a workaround, for actual template
                # removal
                time.sleep(30)
                return True
            time.sleep(sleepTime)
            handleTimeout += sleepTime
        return False
    elif status and positive and not wait:
        return True
    elif status and not positive:
        return True

    return False


@is_action()
def removeTemplates(positive, templates):
    # TODO: Doc
    jobs = [Job(
        target=removeTemplate, args=(True, tmpl)) for tmpl in split(templates)]
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


@is_action()
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
            vnic_profile_obj = getVnicProfileObj(kwargs.get('vnic_profile')
                                                 if 'vnic_profile' in kwargs
                                                 else
                                                 kwargs.get('network'),
                                                 kwargs.get('network'),
                                                 cl_obj.get_name())

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


@is_action()
def addTemplateNic(positive, template, **kwargs):
    '''
    Description: add nic to template
    Author: atal
    Parameters:
       * template - name of template that we add the nic to
       * name - name of nic
       * network - network that nic depends on
       * interface - nic type. available types: virtio, rtl8139 and e1000
                     (for 2.2 also rtl8139_virtio)
       * active - Boolean attribute which present nic hostplug state
    Return: status (True if nic was added properly, False otherwise)
    '''
    templ_obj = TEMPLATE_API.find(template)
    kwargs.update([('cluster', templ_obj.cluster.id)])

    nic_obj = _prepareNicObj(**kwargs)
    nics_coll = getTemplatesNics(template)

    res, status = NIC_API.create(nic_obj, positive, collection=nics_coll)

    return status


@is_action()
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


@is_action()
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


@is_action()
def removeTemplateNic(positive, template, nic):
    '''
    Description: remove nic from template
    Author: atal
    Parameters:
       * template - template where nic should be removed
       * nic - nic name that should be removed
    Return: status (True if nic was removed properly, False otherwise)
    '''
    nic_obj = getTemplatesNic(template, nic)

    return NIC_API.delete(nic_obj, positive)


@is_action()
def removeTemplateFromExportDomain(positive, template, datacenter,
                                   export_storagedomain):
    '''
    Description: removes a template from export domain
    Author: istein
    Parameters:
       * template - template name
       * datacenter - name of data center
       * export_storagedomain - storage domain where to remove vm from
    Return: status (True if template was removed properly, False otherwise)
    '''
    expStorDomObj = SD_API.find(export_storagedomain)
    templObj = TEMPLATE_API.getElemFromElemColl(expStorDomObj, template)
    status = TEMPLATE_API.delete(templObj, positive)
    time.sleep(30)
    return status


@is_action()
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


@is_action()
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


@is_action()
def exportTemplate(positive, template, storagedomain, exclusive='false',
                   wait=False):
    '''
    Description: export template
    Author: edolinin
    Parameters:
       * template - name of template that should be exported
       * storagedomain - name of export storage domain where to export to
       * exclusive - 'true' if overwrite already existed templates with the
                      same name, 'false' otherwise ('false' by default)
       * wait - waits until template is exported
    Return: status (True if template was exported properly, False otherwise)
    '''

    templObj = TEMPLATE_API.find(template)

    sd = StorageDomain(name=storagedomain)
    actionParams = dict(storage_domain=sd, exclusive=exclusive)
    result = TEMPLATE_API.syncAction(templObj, "export", positive,
                                     **actionParams)
    if wait and result:
        return waitForTemplatesStates(names=template)

    return result


@is_action()
def import_template(positive, template, source_storage_domain,
                    destination_storage_domain, cluster, name=None,
                    async=False):
    """
    Description: import template from export_domain
    _author_: edolinin
    :param positive: True if success, False otherwise
    :type positive: bool
    :param template: name of template to be imported
    :type template: str
    :param source_storage_domain: from which to export the template
    :type source_storage_domain: str
    :param destination_storage_domain: which to import the template
    :type destination_storage_domain: str
    :param cluster: cluster into which template will be imported
    :type cluster: str
    :param name: new name for the imported template
    :type name: str
    :param async: True wait for response, False otherwise
    :type async: bool
    :returns: True if function should wait for response, False otherwise
    :rtype: bool
    """

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

    status = TEMPLATE_API.syncAction(
        template_obj,
        action_name,
        positive,
        **action_params
    )

    if not async:
        time.sleep(30)

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


@is_action()
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
    if not DISKS_API.syncAction(disk, 'copy', storage_domain=sd,
                                positive=True):
        raise errors.DiskException("Failed to move disk %s of template %s to "
                                   " storage domain %s"
                                   % (disk_name, template, target_sd))


@is_action()
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


@is_action('waitForTemplateDisksState')
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


@is_action('copyTemplateDisks')
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
        if not TEMPLATE_API.syncAction(disk, action='copy', positive=positive,
                                       async=async,
                                       storage_domain=storage_domain):
            raise exceptions.TemplateException(
                "Copying of disk %s of template %s to storage domain %s "
                "failed." % (disk.name, template, storagedomain))


def get_template_from_cluster(cluster):
    """
    Description: Gets all templates added to the given cluster
    Parameters:
        * *cluster* - cluster name
    **Returns**: List of templates for given cluster
    """
    logging.info("Getting all templates in cluster %s", cluster)
    cluster_id = CLUSTER_API.find(cluster).get_id()
    all_templates = TEMPLATE_API.get(absLink=False)
    templates_in_cluster = [x.get_name() for x in all_templates if
                            x.get_cluster().get_id() == cluster_id]
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
