.. _the_object_model:

The Object Model
================

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

Model as a Container
_____________________


The Model object is a direct container of nodes, edges (relationships), and
properties. To get a simple list of all relevant entities in a model, use the
model attributes::

   nodes = model.nodes.values()
   relationships = model.edges.values() 
   properties = model.props.values()

To retrieve a specific entity, provide a key to the relevant
attribute. For nodes, the key is just the node handle (name
string). For edges, the key is a tuple of the edge handle, the source
node handle, and the destination node handle::

  edge = model.edges[(edge.handle, edge.src.handle, edge.dst.handle)]
  
This tuple can be retrived from an edge with :func:`Edge.triplet`::

  edge = model.edges[edge.triplet]

For properties, the key is a tuple that depends on whether the property belongs to a node or an edge::

  node_prop = model.props[ (node.handle, prop.handle) ]
  edge_prop = model.props[ (edge.handle, edge.src.handle, edge.dst.handle, prop.handle) ]

This is not very convenient, but it ensures that a single property instance can be used
on many nodes and edges. To get properties, it is easier to pull them from the
node or edge itself::

  node = model.nodes['case']
  for p in node.props:
    print(node.props[p].handle)

Accessing other objects
^^^^^^^^^^^^^^^^^^^^^^^^

The Model object does not provide access to :class:`Concept`, :class:`ValueSet`, or 
:class:`Origin` objects directly. These are accessible via the linked obects
themselves, according to the `metamodel structure <https://github.com/CBIIT/bento-meta#structure>`_.
For example::

    # all terms for all nodes
    terms=[]
    for n in model.nodes.values()
      if n.concept:
        terms.extend( n.concept.terms.values() )
    strings = [t.value for t in terms]
    
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

.. _object_attribute_lists:

Objects and their Attributes
____________________________


.. py:class:: Entity

Base class for all metamodel objects.  Posesses the following attributes:

  .. py:attribute:: entity._id
       :type: simple
  .. py:attribute:: entity.desc
       :type: simple
  .. py:attribute:: entity._from
       :type: simple
  .. py:attribute:: entity._to
       :type: simple
  .. py:attribute:: entity._next
       :type: 
  .. py:attribute:: entity._prev
       :type: 
  .. py:attribute:: entity.tags
       :type: collection of Tag

.. py:class:: Node

Subclass that models a data node. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: node.handle
       :type: simple
  .. py:attribute:: node.model
       :type: simple
  .. py:attribute:: node.category
       :type: simple
  .. py:attribute:: node.concept
       :type: Concept
  .. py:attribute:: node.props
       :type: collection of Property

.. py:class:: Edge

Subclass that models a relationship between model nodes. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: edge.handle
       :type: simple
  .. py:attribute:: edge.model
       :type: simple
  .. py:attribute:: edge.multiplicity
       :type: simple
  .. py:attribute:: edge.is_required
       :type: simple
  .. py:attribute:: edge.src
       :type: Node
  .. py:attribute:: edge.dst
       :type: Node
  .. py:attribute:: edge.concept
       :type: Concept
  .. py:attribute:: edge.props
       :type: collection of Property

.. py:class:: Property

Subclass that models a property of a node or relationship (edge). Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: property.handle
       :type: simple
  .. py:attribute:: property.model
       :type: simple
  .. py:attribute:: property.value_domain
       :type: simple
  .. py:attribute:: property.units
       :type: simple
  .. py:attribute:: property.pattern
       :type: simple
  .. py:attribute:: property.is_required
       :type: simple
  .. py:attribute:: property.concept
       :type: Concept
  .. py:attribute:: property.value_set
       :type: ValueSet

.. py:class:: Term

Subclass that models a term from a terminology. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: term.value
       :type: simple
  .. py:attribute:: term.origin_id
       :type: simple
  .. py:attribute:: term.origin_definition
       :type: simple
  .. py:attribute:: term.concept
       :type: Concept
  .. py:attribute:: term.origin
       :type: Origin

.. py:class:: Concept

Subclass that models a semantic concept. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: concept.terms
       :type: collection of Term

.. py:class:: Origin

Subclass that models a :class:`Term` 's authoritative source. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: origin.url
       :type: simple
  .. py:attribute:: origin.is_external
       :type: simple
  .. py:attribute:: origin.name
       :type: simple

.. py:class:: Tag

Subclass that allows simple key-value tagging of a model at arbitrary points. Posesses all :class:`Entity` attributes, plus the following:

  .. py:attribute:: tag.value
       :type: simple

