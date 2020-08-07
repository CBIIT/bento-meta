.. bento_meta documentation master file, created by
   sphinx-quickstart on Tue Jul  7 15:39:59 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: _static/forkme_right_green_007200.svg
	   :align: right
	   :scale: 80%
	   :alt: Fork me on GitHub
	   :target: https://github.com/CBIIT/bento-meta

bento_meta  
================

.. image:: https://travis-ci.org/CBIIT/bento-meta.svg?branch=master
	   :alt: Build Status
	   :target: https://travis-ci.org/CBIIT/bento-meta

**bento_meta** provides an object representation of 
`property graph <https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph>`_
based data models, as embodied in the structure of the
`Bento Metamodel Database <https://github.com/CBIIT/bento-meta>`_, or
MDB. The MDB can store multiple data models in terms of their nodes,
relationships, and properties. The MDB links these entities according to the structure of
the individual models:

.. image:: https://raw.githubusercontent.com/CBIIT/bento-meta/master/metamodel.svg
           :target: https://github.com/CBIIT/bento-meta#bento-meta-db
           :width: 500px
           :height: 600px
           :align: center

For example, model nodes are represented as metamodel nodes of type
``node``, model relationships as metamodel nodes of type
``relationship``, and metamodel ``relationship`` link to the
appropriate "source" and "destination" ``nodes``. Classes in
*bento_meta* can create, read, update, and link these entities
together according to the MDB structure, and push and pull them to and
from a backing `Neo4j <https://neo4j.com>`_ database.

The MDB also provides entities for defining and maintaining
terminology associated with the stored models. These include the
``terms``  themselves, their ``origin``, and associated ``concepts``. Each
of these entities can be created, read, and updated using *bento_meta*.

Installation
____________

Run::

  pip install https://github.com/CBIIT/bento-meta/raw/master/python/dist/bento-meta-0.0.1.tar.gz


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   ./the_object_model
   ./meta_and_mdf
   ./model_versioning
   ./object_mapping
   ./classes

A Note on "Nodes"
_______________________

The metamodel is a property graph, designed to store specific property
graph models, in a database built for property graphs. The word "node"
is therefore used in different contexts and can be confusing,
especially since the `Cancer Research Data Commons
<https://datascience.cancer.gov/data-commons>`_ is also set up in terms
of "nodes", which are central repositories of cancer data of
different kinds. This and related documentation will attempt to
distinguish these concepts as follows.

* A "graph node" is a instance of the node concept in the
  property graph model, that usually represents a category or item of
  interest in the real world, and has associate properties that
  distinguish it from other instances.
* A "model node" is a graph node within a specific data model, and
  represents groups of data items (properties) and can be related to
  other model nodes via model relationships. 
* A "metamodel node" is a graph node that represents a model node,
  model relationship, or model property, in the metamodel database.
* A "Neo4j node" refers generically to the representation of a node in
  the Neo4j database engine.
* A "CRDC node" refers to a data commons repository that is part of
  the CRDC, such as the `ICDC <https://caninecommons.cancer.gov>`_.

A Note on Objects, Properties, and Attributes
_______________________________________________________

:class:`bento_meta` creates a mapping between Neo4j nodes and Python
objects. Of course, the objects have data associated with them,
accessed via setters and getters. These object-associated data are
referred to exclusively as **attributes** in the documentation.

Thus, a :class:`Node` object has an attribute ``props`` (that is,
properties), which is an associative array of :class:`Property`
objects. The ``props`` attribute is a representation of the
``has_property`` relationships between the metamodel node-type node
to its metamodel property-type nodes.

See :ref:`object-attributes` for more details.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
