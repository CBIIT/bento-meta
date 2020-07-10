bento_meta and MDF
==================


Model Description Files
_______________________


`Model description files <https://github.com/CBIIT/bento-mdf>`_, or MDF, are simple descriptions of a graph data model, usually written in `YAML <https://learnxinyminutes.com/docs/yaml/>`_. They are organized in terms of sections defined by the top-level keys ``Nodes``, ``Relationships``, and ``PropDefinitions``. They describe the graph nodes and relationships belonging to a model, the properties associated with each. The MDF details and documents:
 
* the "local" or internal names for each of these entities,
* the node types that are allowed as the source and destination for each relationship, 
* detailed attributes that may be associated with any of these entities, for example:

  * the data types or enumerated values that are valid for a given property
  * whether a particular relationship or property is required to be present, for data to be valid
  * the cardinality (one-to-one, one-to-many, etc.) that is valid for a given relationship.

Examples of valid MDF are available for the `Integrated Canine Data Commons <https://cbiit.github.io/icdc-model-tool/model-desc/>`_ and the `Clinical Trials Data Commons <https://cbiit.github.io/ctdc-model/model-desc/>`_ models. 

The MDF syntax is described `here in detail <https://github.com/CBIIT/bento-mdf#model-description-files-mdf>`_. This syntax is defined by and can be validated against a `JSONSchema <https://json-schema.org/understanding-json-schema/>`_ document. This document lives `here <https://github.com/CBIIT/bento-mdf/blob/master/schema/mdf-schema.yaml>`_. 


Slurping MDF with bento_meta
____________________________

Create a :class:`bento_meta.model.Model` from MDF files as follows::

  from bento_meta.mdf import MDF

  mdf = MDF('model.yml','model-props.yml', handle="test")
  model = mdf.model

The model object can be used and modified as discussed in :ref:`the_object_model`. No database connection is necessary.
  
Note that the MDF can be spread out over multiple YAML files. Typically, the
nodes and relationships are defined in one file, and the properties in a separate files. `MDF` merges the files provided according to `the spec <https://github.com/CBIIT/bento-mdf#multiple-input-yaml-files-and-overlays>`_.

``handle=`` is a keyword-only argument that must be provided, which sets the name (a.k.a. handle) for the model. This is used, for example, in setting the `Entity.model` attribute for the model objects. It enables pushing and pulling a model to and from a Neo4j database in a single call.

URLs that resolve to MDF files can also be used. To load the latest CTDC model, for example::

  >>> from bento_meta.mdf import MDF
  >>> mdf = MDF('https://cbiit.github.io/ctdc-model/model-desc/ctdc_model_file.yaml',
  >>>           'https://cbiit.github.io/ctdc-model/model-desc/ctdc_model_properties_file.yaml',
  >>>            handle='CTDC')
  >>> ctdc_model = mdf.model
  >>> [x for x in mdf.model.nodes]
  ['case', 'specimen', 'metastatic_site', 'nucleic_acid', 'ihc_assay_report', 'sequencing_assay', 'variant_report', 'file', 'snv_variant', 'delins_variant', 'indel_variant', 'copy_number_variant', 'gene_fusion_variant', 'assignment_report', 'disease_eligibility_criterion', 'drug_eligibility_criterion', 'arm', 'clinical_trial']
  >>> [x for x in mdf.model.nodes['case'].props]
  ['show_node', 'case_id', 'source_id', 'gender', 'race', 'ethnicity', 'patient_status', 'current_step', 'disease', 'ctep_category', 'ctep_subcategory', 'meddra_code', 'prior_drugs', 'extent_of_disease', 'ecog_performance_status']

Squirting a Model into MDF YAML
_______________________________

Coming soon.


