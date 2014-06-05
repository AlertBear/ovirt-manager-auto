[PARAMETERS]
datacenter = string(default='DataCenterTest')
cluster = string(default='ClusterTest')
storage = string(default='DataDomainTest')

# Variables related to Network Scenarios
networks = force_list(default=list('sw1', 'sw2', 'sw3', 'sw4', 'sw5', 'sw6', 'sw7', 'sw8'))
bond = force_list(default=list('bond0', 'bond1', 'bond2', 'bond3', 'bond4'))
vlan_id = force_list(default=list('162', '163', '164', '165', '166', '167', '168', '169'))
vlan_networks = force_list(default=list('sw162', 'sw163', 'sw164', 'sw165','sw166', 'sw167', 'sw168', 'sw169'))
vm_name = force_list(default=list('VMTest1', 'VMTest2', 'VMTest3', 'VMTest4', 'VMTest5'))
template_name = string(default='tempTest1')
vm_os = option('Red Hat Enterprise Linux 6.x x64', 'Windows 7 x64', 'Windows 2008 R2 x64', 'Windows XP', default='Red Hat Enterprise Linux 6.x x64')
vnic_profile = force_list(default=list('vnic_profile1', 'vnic_profile2', 'vnic_profile3', 'vnic_profile4', 'vnic_profile5', 'vnic_profile6', 'vnic_profile7', 'vnic_profile8'))
bond_modes = force_list(default=list(0, 1, 2, 3, 4, 5, 6))
#Running arguments
vm_network = boolean(default=False)
run_topologies = force_list(default=list('sanity-30', 'sanity-31', 'negative', 'topology-a-30', 'topology-a-31', 'topology-b-30', 'topology-b-31', 'topology-c-30','topology-c-31', 'topology-d', 'topology-e', 'topology-f', 'topology-g'))
run_groups = force_list(default=list('migration', 'vlan', 'vlansoverbond', 'bondmodes', 'clustepolicyvalidation', 'nicdrivers', 'networksanity'))

# regression tests
migration = force_list(default=list('positive', '*'))
vlan = force_list(default=list('positive', '*'))
vlansoverbond = force_list(default=list('positive', '*'))
bondmodes = force_list(default=list('positive', '*'))
clustepolicyvalidation = force_list(default=list('positive', '*'))
nicdrivers = force_list(default=list('positive', '*'))
networksanity = force_list(default=list('positive', '*'))

# new features tests
hotplugnic = force_list(default=list('positive', '*'))
jumboframes = force_list(default=list('positive', '*'))
networkfiltering = force_list(default=list('positive', '*'))
portmirroring = force_list(default=list('positive', '*'))
requirednetwork = force_list(default=list('positive', '*'))
syncnetwork = force_list(default=list('positive', '*'))
