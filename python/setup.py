from setuptools import setup, find_packages
setup(
  name="bento-meta",
  version="0.0.1",
  packages=find_packages(),
  install_requires=[
    'PyYAML>=5.1.1',
    'option-merge>=1.6',
    'neo4j>=4.0'
    ],
  tests_require=[
    'pytest',
    'docker-compose',
    'pytest-docker',
    'requests'
  ]
  )
