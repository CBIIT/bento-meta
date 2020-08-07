# mdf-validate / test-mdf.py

This directory provides ``test-mdf.py``, a standalone command line MDF validator.

## Installation

The validator is written in Python 3. Use ``pip`` to install.

       cd bento-mdf
       pip install ./validators/mdf-validate

## Usage

    $ test-mdf.py -h
    usage: test-mdf.py [-h] [--schema SCHEMA] mdf-file [mdf-file ...]

    Validate MDF against JSONSchema

    positional arguments:
      mdf-file         MDF yaml files for validation

    optional arguments:
      -h, --help       show this help message and exit
      --schema SCHEMA  MDF JSONschema file

## Notes

The ``--schema`` argument is optional. ``test-mdf.py`` will automatically retrieve the latest [mdf-schema.yaml](../../schema/mdf-schema.yaml) in the master branch of [this repo](https://github.com/CBIIT/bento-mdf).

The script tests both the syntax of the YAML (for both schema and MDF files), and the validity of the files with respect to the JSONSchema (for both schema and MDF files).

The errors are as emitted from the [PyYaml](https://pyyaml.org/wiki/PyYAMLDocumentation) and [jsonschema](https://python-jsonschema.readthedocs.io/en/stable/) packages, and can be rather obscure.

* Successful test

        $ test-mdf.py samples/ctdc_model_file.yaml samples/ctdc_model_properties_file.yaml 
        Checking schema YAML =====
        Checking as a JSON schema =====
        Checking instance YAML =====
        Checking instance against schema =====

* Bad YAML syntax

        $ test-mdf.py samples/ctdc_model_bad.yaml samples/ctdc_model_properties_file.yaml 
        Checking schema YAML =====
        Checking as a JSON schema =====
        Checking instance YAML =====
        YAML error in 'samples/ctdc_model_bad.yaml':
        while parsing a block mapping
          in "samples/ctdc_model_bad.yaml", line 1, column 1
        expected <block end>, but found '<block mapping start>'
          in "samples/ctdc_model_bad.yaml", line 3, column 3

* Schema-invalid YAML

        $ test-mdf.py samples/ctdc_model_file_invalid.yaml samples/ctdc_model_properties_file.yaml 
        Checking schema YAML =====
        Checking as a JSON schema =====
        Checking instance YAML =====
        Checking instance against schema =====
        ['show_node', 'specimen_id', 'biopsy_sequence_number', 'specimen_type'] is not of type 'object'
        
        Failed validating 'type' in schema['properties']['Nodes']['additionalProperties']:
            {'$id': '#nodeSpec',
             'properties': {'Category': {'$ref': '#/defs/snake_case_id'},
                            'Props': {'oneOf': [{'items': {'$ref': '#/defs/snake_case_id'},
                                                 'type': 'array',
                                                 'uniqueItems': True},
                                                {'type': 'null'}]},
                            'Tags': {'$ref': '#/defs/tagsSpec'}},
             'required': ['Props'],
             'type': 'object'}
        
        On instance['Nodes']['specimen']:
            ['show_node', 'specimen_id', 'biopsy_sequence_number', 'specimen_type']

## Testing the tester

The validator code itself can be tested as follows:

    pip install tox
    cd bento-mdf/validators/mdf-validate
    tox




