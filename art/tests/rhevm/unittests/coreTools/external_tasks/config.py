"""
External Tasks config module
"""

__test__ = False

from . import ART_CONFIG

TEST_NAME = "External_Tasks"
PARAMETERS = ART_CONFIG['PARAMETERS']
VDC = PARAMETERS.get('host', None)
VDC_PASSWORD = PARAMETERS.get('password', None)

base_name = PARAMETERS.get('test_name', TEST_NAME)
job_description = PARAMETERS.get('job_description', 'job_%s' % base_name)
step_description = PARAMETERS.get('step_description', 'step_%s' % base_name)
sub_step_description = PARAMETERS.get('sub_step_description',
                                      'sub_step_%s' % base_name)