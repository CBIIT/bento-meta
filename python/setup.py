from setuptools import setup, find_packages
setup(
    name="bento-meta",
    version="0.0.32",
    author="Mark A. Jensen",
    author_email="mark-dot-jensen-at-nih-dot-gov",
    description="object model for bento metamodel database",
    url="https://github.com/CBIIT/bento-meta",
    python_requires='>=3.6',
    packages=find_packages(),
    dependency_links=[
        'git+https://github.com/CBIIT/bento-mdf'
        ],
    install_requires=[
        'PyYAML>=5.1.1',
        'delfick-project',
        'neo4j>=4.0',
        'nanoid',
        'requests',
        'mdf-validate>=0.3'
        ],
    tests_require=[
        'pytest',
        'docker-compose',
        'pytest-docker',
        'requests'
        ]
    )
