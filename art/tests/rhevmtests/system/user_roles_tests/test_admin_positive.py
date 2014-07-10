'''
Testing admin roles positive actions.
1 Hosts, 2 SDs, 2 DCs, 1 export, 1 iso is created on startup.
Then every test case try to create object it should test.
For every possitive action that admin role has try to do this action.
'''

from rhevmtests.system.user_roles_tests import test_actions


def setUpModule():
    test_actions.setUpModule()


def tearDownModule():
    test_actions.tearDownModule()
