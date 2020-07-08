.. bento_meta documentation master file, created by
   sphinx-quickstart on Tue Jul  7 15:39:59 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

bento_meta 
================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

:class:`bento_meta.model.Model` provides an object representation of a single
`property graph <https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph>`_
based data model, as embodied in the structure of the
`Bento Metamodel Database <https://github.com/CBIIT/bento-mdf>`_, or
MDB. The MDB can store multiple such models in terms of their nodes,
relationships, and properties. The MDB links these entities according to the structure of
the individual models. For example, model nodes are represented as
metamodel nodes of type "node", model relationships as metamodel nodes
of type "relationship", that themselves link to the relevant source
and destination metamodel nodes, representing the two end nodes in the
model itself. :class:`Model` can create, read, update, and link
these entities together according to the
`MDB structure <https://github.com/CBIIT/bento-meta#structure>`_.

The MDB also provides entities for defining and maintaining
terminology associated with the stored models. These include the
``terms``  themselves, their ``origin``, and associated ``concepts``. Each
of these entities can be created, read, and updated using `Model`
and the component objects.

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

Working with Models
____________________

Each model stored in the MDB has a simple name, or handle. The word
**handle** is used throughout the metamodel to distinguish internal
names (strings that are used within the system and downstream
applications to refer to entities) and the external **terms** that are
employed by users and standards. Handles can be understood as *local
vocabulary*. The mode handle is usually the name of the CRDC node that the
model supports.

A :class:`Model` object is meant to represent only one model.

Component Objects
_____________________

Individual entities in the MDB - nodes, relationships, properties,
value sets, terms, concepts, and origins, are represented by instances
of corresponding :class:`Entity` subclasses:

* :class:`Node`
* :class:`Edge`  ("Edge" is easier to type than "relationship".)
* :class:`Property`
* :class:`ValueSet`
* :class:`Term`
* :class:`Concept`
* :class:`Origin`

:class:`Model` methods generally accept these objects as
arguments and/or return these objects. To obtain specific scalar
information (for example, the handle string) of the object, use the
attribute on the object itself::

    # print the 'handle' for every property in the model
    for p in model.props:
      print(p.handle)

.. _object-attributes:

Object attributes
^^^^^^^^^^^^^^^^^^^^^^^

A node in the graph database can possess two kinds of related data. In
the (Neo4j) database, *node properties* are named items of scalar
data. These belong directly to the individual nodes, and are
referenced via the node. These map very naturally to scalar attributes
of a model object. For example, ``handle`` is a metamodel node property,
and it is accessed simply by the object attribute of the same name,
``node.handle``. In the code, these are referred to as *property
attributes* or *scalar-valued attributes*.

The other kind of data related to a given node is present in other nodes
that are linked to it via graph database relationships. In the
MDB, for example, a model edge (e.g., ``of_sample``) is represented by
its own graph node with label ``relationship``, and the source and
destination nodes for that edge are two graph nodes with label ``node``,
one of which is linked to the ``relationship`` node with a graph
relationship ``has_src``, and the other with a graph relationship
``has_dst``. (Refer to `this diagram <https://github.com/CBIIT/bento-meta#structure>`_.)

In the object model, the source and destination nodes of an edge are
also represented as object attributes: in this case, ``edge.src``
and ``edge.dst``. This representation encapsulates the ``has_src`` and
``has_dst`` graph relationships, so that the programmer can ignore the
metamodel structure and concentrate on the model structure. Note that
the value of such an attribute is an object (or an array of objects).
In the code, such attributes are referred to as *relationship*,
*object-valued* or *collection-valued* attributes.


Model as Container
_____________________


The Model object is a direct container of nodes, edges (relationships), and
properties. To get a simple list of all relevant entities in a model, use the
model attributes::

   nodes = model.nodes
   relationships = model.edges 
   properties = model.props

To retrieve a specific entity, provide a key to the relevant
attribute. For nodes, the key is just the node handle (name
string). For edges, the key is a tuple of the edge handle, the source
node handle, and the destination node handle::

  edge = model.edges[(edge.handle, edge.src.handle, edge.dst.handle)]
  
This tuple can be retrived from an edge with `Edge.edge.triplet`::

  edge = model.edges[edge.triplet]

For properties, the key is a tuple that depends on whether the property belongs to a node or an edge::

  node_prop = model.props[ (node.handle, prop.handle) ]
  edge_prop = model.props[ (edge.handle, edge.src.handle, edge.dst.handle, prop.handle) ]

This is not very convenient, but it ensures that a single property instance can be used
on many nodes and edges. To get properties, it is easier to pull them from the
node or edge itself::

  node = model.nodes['case']
  for p in node.props:
    print(p.handle)

Accessing other objects
^^^^^^^^^^^^^^^^^^^^^^^^

The Model object does not provide access to :class:`Concept`, :class:`ValueSet`, or 
:class:`Origin` objects directly. These are accessible via the linked obects
themselves, according to the `metamodel structure <https://github.com/CBIIT/bento-meta#structure>`_.
For example::

    # all terms for all nodes
    terms=[]
    for n in model.nodes
      terms.extend( n.concept.terms )

Model as an Interface
_________________________

The :class:`Model` object has methods that allow the user to add, remove and
modify entities in the model. The Model object is an interface, in that it loosely
encapsulates the MDB structure and tries to relieve the user from having to
remember that structure and guards against deviations from it. 

The main methods are

* :meth:`Model.add_node`
* :meth:`Model.add_edge`
* :meth:`Model.add_prop`
* :meth:`Model.add_terms`
* :meth:`Model.rm_node`
* :meth:`Model.rm_edge`
* :meth:`Model.rm_prop`
* :meth:`Model.rm_terms` (coming soon)

The main idea is that these methods operate on either the relevant
component object or on a dict that specifies an object by its
attributes. In the latter case, a new component object is created.

Here's a pattern for creating two nodes and an edge in a model::

  src_node = model.add_node( {"handle":"sample"} )
  dst_node = model.add_node( {"handle":"case"} )
  edge = model.add_edge( {"handle":"of_case", "src":src_node, "dst":dst_node} )

These new entities are registered in the model, and can be retrieved::

  case = model.nodes('case')
  of_case = model.edges( ("of_case","sample","case") )

Removing entities from the model "deregisters" them, but does not destroy
the object itself::
  
    model.rm_edge(of_case);
    model.rm_node(case);
    other_model.add_node(case);

Note that the edge needs to be removed for this to work in the
example. Analogous to Neo4j, attempting to remove a node will throw,
if the node participates in any relationships/edges.

Manipulating Terms
^^^^^^^^^^^^^^^^^^^^

One of the key uses of the MDB is for storing lists of acceptable values for
properties that require them. In the MDB schema, a property is linked to 
a value set entity, and the value set aggregates the term entities. The model
object tries to hide some of this structure. It will also create a set of 
:class:`Term` objects from a list of strings as a shortcut::

    prop = model.add_prop( sample, {"handle":"sample_type",
                                                         "value_domain":"value_set"})
    # prop has domain of 'value_set', so you can add terms to it
    value_set = model.add_terms( prop, ["normal", "tumor"] )
    terms = value_set.terms # set of 2 term objects
    same_terms = prop.terms # prop object also has a shortcut 

Database Interaction
________________________

The approach to the back and forth between the object representation
and the database attempts to be simple and robust. The pattern is a
push/pull cycle to and from the database. The database instrumentation
is also encapsulated from the rest of the object functionality, so
that even if no database is specified or connected, all the object
manipulations are available.

The Model methods are :meth:`Model.dget` and :meth:`Model.dput`.
:meth:`Model.dget` pulls the metamodel nodes for
the model that have ``handle`` property equal to `Model.handle`
from the connected database. It will not disturb any modifications made to
objects in the program, unless called with a True argument. In that case,
``model.dget(True)`` (e.g.) will refresh all objects from current metamodel nodes
in the database, overwriting any changes.

:meth:`Model.put` pushes the model objects, with any changes to attributes, to
the database. It will build and execute queries correctly to convert, for
example, collection attributes to multiple nodes and corresponding
relationships. :meth:`Model.put` adds and removes relationships in the database as
necessary, but will not fully delete nodes. To completely remove objects
from the database, use ``rm()`` on the objects themselves::

    model.rm_edge(edge); # edge detached from nodes and removed from model
    model.dput(); # metamodel node representing the edge is still present in db
                          # but is detached from the source node and destination node
    edge.rm(); # metamodel node representing the edge is deleted from db

.. autoclass:: bento_meta.model.Model
               :members:

.. automodule:: bento_meta.objects
               :members:

.. autoclass:: bento_meta.entity.Entity
               :members:

.. autoclass:: bento_meta.object_map.ObjectMap
               :members:

                  

    
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
