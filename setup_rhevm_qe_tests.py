#!/bin/env python
import os
from utilities.setup_utils import setup

RELEASE = os.environ.get('RELEASE', '1')
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)

RPM_NAME = 'rhevm-qe-tests'
DESCRIPTION = "QE RHEVM Tests meta package"

DEPS = ['art-tests-rhevm-api = %s' % VERSION,
        'art-plugin-auto-devices = %s' % VERSION,
        'art-plugin-auto-cpu-name-resolution = %s' % VERSION,
        'art-plugin-generate-ds = %s' % VERSION,
        'art-plugin-hosts-cleanup = %s' % VERSION,
        'art-plugin-hosts-nics-resolution = %s' % VERSION,
        'art-plugin-log-capture = %s' % VERSION,
        'art-plugin-xml-test-parser = %s' % VERSION,
        'art-plugin-xunit-reports = %s' % VERSION,
        'art-plugin-unittest-runner = %s' % VERSION]

if __name__ == "__main__":
    setup(name=RPM_NAME,
          version=VERSION,
          release=RELEASE,
          author='Red Hat',
          author_email='lbednar@redhat.com',
          maintainer='Red Hat',
          maintainer_email='lbednar@redhat.com',
          description='RHEVM Meta package',
          long_description=DESCRIPTION,
          platforms='Linux',
          requires=DEPS,
          changelog=CHANGELOG)
