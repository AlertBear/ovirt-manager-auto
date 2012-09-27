[PARAMETERS]
datacenter = string(default='DataCenterTest')
cluster = string(default='ClusterTest')
storage = string(default='DataDomainTest')

# Variables related to Network Scenarios
vm_network = boolean(default=True)
networks = force_list(default=list('sw1', 'sw2'))
bond = force_list(default=list('bond0', 'bond1'))
vlan_id = force_list(default=list('166', '167', '168', '169'))
run_topologies = force_list(default=list('sanity-30', 'sanity-31', 'negative', 'topology-a-30', 'topology-a-31', 'topology-b-30', 'topology-b-31', 'topology-c-30','topology-c-31', 'topology-d', 'topology-e', 'topology-f', 'topology-g'))
vm_name = force_list(default=list('VMTest1', 'VMTest2'))
template_name = string(default='tempTest1')
vm_os = option('Red Hat Enterprise Linux 6.x x64', 'Windows 7 x64', 'Windows 2008 R2 x64', 'Windows XP', default='Red Hat Enterprise Linux 6.x x64')