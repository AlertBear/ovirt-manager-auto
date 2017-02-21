import logging

import art.rhevm_api.utils.test_utils as utils
import art.rhevm_api.tests_lib.low_level.datacenters as ll_dc
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
from art.test_handler.settings import opts

PRINT_1 = "*" * 41
PRINT_2 = "-" * 20
PRINT_3 = "=" * 30
MB = 1024 ** 2
DEFAULT_NAME = "Default"
ENUMS = opts['elements_conf']['RHEVM Enums']
STORAGE_DOMAIN_STATUS_INACTIVE = ENUMS["storage_domain_state_inactive"]
STORAGE_DOMAIN_STATUS_UNATTACHED = ENUMS["storage_domain_state_unattached"]
logger = logging.getLogger("art.inventory")


class Inventory(object):
    def __init__(self):
        self.initialize_parameters()

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    def initialize_parameters(self):
        """
        Clean parameters for reuse
        """
        self._dc_info = []
        self._clusters_info = []
        self._host_info = []
        self._vms_info = []
        self._templates_info = []
        self._storage_domains_info = []
        self._summary = {}

    def get_summary(self):
        """
        Return inventory summary
        :return: summary dict
        :rtype: dict
        """
        return self._summary

    def find_hosts_in_cluster(self, cluster_id):
        """
        Gets all Hosts in current cluster
        :param cluster_id: id of current cluster
        :type: str
        :return list of hosts
        :rtype list
        """
        data = []
        for host in ll_hosts.get_host_list():
            cluster = host.get_cluster()
            if cluster and cluster.id == cluster_id:
                data.append(
                    {
                        'name': host.name,
                        'address': host.address,
                        'status': host.get_status()
                    }
                )
        return data

    def find_vms_in_cluster(self, cluster_name):
        """"
        Gets all VMs in current cluster
        :param cluster_name: cluster name
        :type cluster_name: str
        :return list of vms in cluster
        :rtype: list
        """
        data = []
        for vm in hl_vms.get_vms_objects_from_cluster(cluster_name):
            data.append(
                {
                    'name': vm.name,
                    'status': vm.get_status(),
                    'os': vm.os.type_,
                    'memory': vm.memory / MB
                }
            )
        return data

    def get_setup_inventory_report(self,
                                   print_report=False,
                                   check_inventory=False,
                                   summary_to_compare=None,
                                   rhevm_config_file=None):
        """
        Go over RHEVM setup inventory and return inventory in GE data structure
        :param print_report: True in case the report should be printed,
               False otherwise
        :type print_report: bool
        :param check_inventory: True in case the report should check results
               with yaml info, False otherwise
        :type: check_inventory: bool
        :param summary_to_compare: A dictionary for comparing the current
               summary
        :type summary_to_compare: dict
        :param rhevm_config_file: rhevm GE config data
        :type rhevm_config_file: module
        :return: A dictionary with setup inventory
        :rtype: dict
        """
        logger.info("Clean parameters")
        self.initialize_parameters()
        logger.info("Running setup inventory report")
        try:
            self.list_data_centers()
            # gets storage domains list
            self.list_storage_domains(self._storage_domains_info)
            self._summary['storage_domains'] = self._storage_domains_info
            # parse data centers info
            self.extract_data_centers_info(self._summary)
            if print_report:
                logger.info(PRINT_1)
                logger.info("Set status:")
                logger.info(PRINT_1)
                self.print_report_status()
                logger.info(PRINT_1)
            if check_inventory:
                if rhevm_config_file:
                    self.compare_with_ge_config_file(rhevm_config_file)
                if summary_to_compare:
                    if cmp(summary_to_compare, self._summary) != 0:
                        logger.warning(
                            "The setup inventory and the summary "
                            "to compare to are not the same"
                        )
                        logger.info(
                            "current setup inventory: %s",
                            self._summary
                        )
                        logger.info(
                            "last setup inventory: %s",
                            summary_to_compare
                        )
        except Exception as e:
            logger.error("Failed to run setup inventory")
            logger.error(e)
            self._summary = {}
        return self._summary

    def list_data_centers(self):
        """
        Go over each data center and gets it's info
        And returns the inventory in GE data structure
        :return: Summary of Data Centers
        :rtype: list
        """
        data = []
        data_center_api = utils.get_api("data_center", "datacenters")
        for current_data_center in data_center_api.get(abs_link=False):
            if current_data_center.name != DEFAULT_NAME:
                current_clusters = []
                data.append({
                    'name': current_data_center.name,
                    'status': current_data_center.get_status(),
                    'compatibility_version': "%s.%s" % (
                        current_data_center.version.major,
                        current_data_center.version.minor,
                    ),
                    'clusters': current_clusters,
                })
                self.list_clusters(current_data_center.id, current_clusters)
            self._summary['dcs'] = data

    def list_storage_domains(self, data):
        """
        Gets all storage domains and check their status in data center
        :param data: list of storage domains
        :type: list
        """
        current_storage_domains = utils.get_api(
            "storagedomain", "storagedomains"
        ).get(abs_link=False)
        for storage_domain in current_storage_domains.storage_domain:
            data.append(
                {
                    'name': storage_domain.name,
                    'storage_type': storage_domain.storage.type_,
                    'domain_type': storage_domain.type_,
                    'status': self.get_sd_status(storage_domain.name),
                }
            )

    def list_clusters(self, data_center_id, data):
        """
        Gets all Clusters for the current data center
        :param data_center_id: id of current data center
        :type: str
        :param data: list of clusters
        :type: list
        """
        current_clusters = utils.get_api(
            "cluster", "clusters"
        ).get(abs_link=False)
        for cluster in current_clusters:
            data_center = cluster.get_data_center()
            if (
                data_center and
                data_center.id == data_center_id and
                cluster.name != DEFAULT_NAME
            ):
                current_hosts = self.find_hosts_in_cluster(cluster.id)
                current_vms = self.find_vms_in_cluster(cluster.name)
                current_templates = self.find_templates_in_cluster(cluster.id)
                data.append(
                    {
                        'name': cluster.name,
                        'cpu_name':
                            "" if cluster.cpu is None else cluster.cpu.type_,
                        'compatibility_version': "%s.%s" % (
                            str(cluster.version.major),
                            str(cluster.version.minor)
                        ),
                        'hosts': current_hosts,
                        'vms': current_vms,
                        'templates': current_templates,
                    }
                )

    def find_templates_in_cluster(self, cluster_id):
        """
        Gets all templates in current cluster
        :param cluster_id: cluster id
        :type cluster_id: str
        :return: list of templates in cluster
        :rtype: list
        """
        data = []
        current_templates = ll_templates.get_all_template_objects()
        for template in current_templates:
            if template.cluster:
                if template.cluster.id == cluster_id:
                    data.append(
                        {
                            'name': template.name,
                            'status': template.get_status(),
                            'cluster': cluster_id,
                        }
                    )
        return data

    def get_sd_status(self, storage_domain):
        """
        Return storage domain status by cases:
         1. Search in Data Centers by storage domain
         2. If not found in [1] return inactive/unattached
         since not found in any Data Center

        :param storage_domain: storage domain
        :type storage_domain: str
        :return: storage domain status
        :rtype: str
        """
        data_center = ll_dc.get_sd_datacenter(storage_domain)
        if data_center:
            sd_obj = ll_sd.getDCStorage(data_center.name, storage_domain)
            return sd_obj.get_status()
        return STORAGE_DOMAIN_STATUS_INACTIVE

    def extract_data_centers_info(self, data_centers):
        """
        Go over summary data and extract the data center info
        of the current inventory, And save it to lists by resource type.
        :param data_centers: data centers in the setup
        :type data_centers: dict
        """

        for data_center in data_centers['dcs']:
            self._dc_info.append({
                'name': data_center['name'],
                'compatibility_version':
                    data_center['compatibility_version'],
                'status': data_center['status']
            })
            clusters_list = data_center['clusters']
            for cluster in clusters_list:
                self._clusters_info.append({
                    'name': cluster['name'],
                    'cpu_name': cluster['cpu_name'],
                    'compatibility_version':
                        cluster['compatibility_version'],
                })

            for cluster in clusters_list:
                for host in cluster['hosts']:
                    self._host_info.append({
                        'name': host['name'],
                        'address': host['address'],
                        'status': host['status']
                    })
            for cluster in clusters_list:
                for vm in cluster['vms']:
                    self._vms_info.append({
                        'name': vm['name'],
                        'status': vm['status'],
                        'os': vm['os'],
                        'memory': str(vm['memory']) + " MB"
                    })

            for cluster in clusters_list:
                for template in cluster['templates']:
                    self._templates_info.append({
                        'name': template['name'],
                        'status': template['status'],
                    })

    def print_report_status(self):
        """
        Print each resource type list.
        """
        self.print_resource_info("Data centers ", self._dc_info)
        self.print_resource_info(
            "Storage domains ", self._storage_domains_info
        )
        self.print_resource_info("Cluster ", self._clusters_info)
        self.print_resource_info("Hosts ", self._host_info)
        self.print_resource_info("Templates ", self._templates_info)
        self.print_resource_info("VMS ", self._vms_info)

    def print_resource_info(self, resource_name, resource_data):
        """
        Prints resource info
        :param resource_name: Resource name for output
        :type resource_name: str
        :param resource_data: Resource data
        :type resource_data: list
        """
        logger.info(resource_name + ":")
        logger.info(PRINT_2)
        self.print_info(resource_data)
        logger.info(PRINT_3)

    def print_info(self, resource_obj):
        """
        Used by print_report_status, print each object info
        :param resource_obj: list of resource data
        :type resource_obj : list
        """
        for entry in resource_obj:
            output = ""
            output += self.get_entry_data(entry, 'name')
            output += self.get_entry_data(entry, 'status')
            output += self.get_entry_data(entry, 'cpu_name')
            output += self.get_entry_data(entry, 'address')
            output += self.get_entry_data(entry, 'storage_type')
            output += self.get_entry_data(entry, 'domain_type')
            output += self.get_entry_data(entry, 'os')
            output += self.get_entry_data(entry, 'memory')
            output += self.get_entry_data(entry, 'compatibility_version')
            logger.info(output)

    def get_entry_data(self, entry, name):
        if entry.get(name):
            return '\t%s: %s' % (name, entry.get(name))
        else:
            return ""

    def compare_with_ge_config_file(self, rhevm_config_file):
        """
        Compare resource list name with data in rhevmtests.config,
        In order to check that the setup contains all the yaml info.
        Checks each resource and prints his compare status.
        :param rhevm_config_file: rhevm config data
        :type rhevm_config_file: module
        """
        clusters_names = [x['name'] for x in self._clusters_info]
        host_names = [x['name'] for x in self._host_info]
        templates_names = [x['name'] for x in self._templates_info]
        vms_names = [x['name'] for x in self._vms_info]
        storage_domains_names = [x['name'] for x in self._storage_domains_info]

        self.compare_resource(
            rhevm_config_file.CLUSTER_NAME, clusters_names, 'Clusters'
        )
        self.compare_resource(rhevm_config_file.HOSTS, host_names, 'Hosts')
        self.compare_resource(rhevm_config_file.TEMPLATE_NAME, templates_names,
                              'Templates')
        self.compare_resource(rhevm_config_file.VM_NAME, vms_names, 'VMs')
        self.compare_resource(rhevm_config_file.STORAGE_NAME,
                              storage_domains_names,
                              'Storage domains')

    def compare_resource(self, yaml_names, setup_names, resource_type):
        """
        compare between yaml names and setup name by resource type.

        :param yaml_names:list of name from config
        :type yaml_names: list
        :param setup_names: names of resources by type in the setup
        :type setup_names: list
        :param resource_type: resource type
        :type resource_type: str
        :return: True is resource are equals else False
        :rtype: bool
        """
        if cmp(yaml_names, setup_names) != 0:
            logger.warning("%s in setup are not as expected in yaml",
                           resource_type)
