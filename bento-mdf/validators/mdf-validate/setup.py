from setuptools import setup, find_packages
setup(
  name="mdf-validate",
  version="0.1",
  packages=find_packages(),
  scripts=['test-mdf.py'],
  install_requires=[
    'jsonschema>=3.0.1',
    'PyYAML>=5.1.1',
    'option-merge>=1.6',
    'requests'
    ],
  tests_require=[
    'jsonschema>=3.0.1',
    'PyYAML>=5.1.1',
    'pytest'
    ]
  )
