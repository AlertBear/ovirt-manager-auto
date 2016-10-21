#!/usr/bin/env python
"""
This script register our customization to pytest.
"""
from setuptools import setup


if __name__ == "__main__":
    setup(
        name="pytest-art",
        packages=['_pytest_art'],
        package_dir={'': 'pytest_customization/'},
        entry_points={
            'pytest11': [
                'artlib = _pytest_art.artlib',
                'artmatrix = _pytest_art.matrix',
                'fixtures = _pytest_art.fixtures',
                'artmarks = _pytest_art.marks',
                'artpackagesetup = _pytest_art.package_fixtures',
                'artautodevices = _pytest_art.autodevices',
                'artlogging = _pytest_art.testlogger',
                'artmac2ip = _pytest_art.mac2ip',
            ],
        },
    )
