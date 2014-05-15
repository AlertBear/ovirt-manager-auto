"""
External Tasks config module
"""

__test__ = False

from art.test_handler.settings import ART_CONFIG

TEST_NAME = "External_Tasks"
PARAMETERS = ART_CONFIG['PARAMETERS']

base_name = PARAMETERS.get('test_name', TEST_NAME)
job_description = PARAMETERS.get('job_description', 'job_%s' % base_name)
step_description = PARAMETERS.get('step_description', 'step_%s' % base_name)
sub_step_description = PARAMETERS.get('sub_step_description',
                                      'sub_step_%s' % base_name)
