from setuptools import setup, find_packages
setup(
  name="bento-meta",
  version="0.0.11",
  author="Mark A. Jensen",
  author_email="mark-dot-jensen-at-nih-dot-gov",
  description="object model for bento metamodel database",
  url="https://github.com/CBIIT/bento-meta",
  python_requires='>=3.6',
  packages=find_packages(),
  install_requires=[
    'PyYAML>=5.1.1',
    'option-merge>=1.6',
    'neo4j>=4.0',
    'requests'
    ],
  tests_require=[
    'pytest',
    'docker-compose',
    'pytest-docker',
    'requests'
  ]
  )
