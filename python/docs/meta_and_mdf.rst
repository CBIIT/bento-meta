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







