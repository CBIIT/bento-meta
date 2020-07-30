Object Map Specifications
=========================


Defining and Updating Objects
______________________________

Objects (i.e., subclasses of class :class:`bento_meta.entity.Entity`) are really just containers for :ref:`simple, object and collection attributes <object-attributes>`. They are special, however, in that an object can map to an instance of a `Neo4j graph node <https://neo4j.com/docs/getting-started/4.1/graphdb-concepts/#graphdb-nodes>`_ that has a particular `label <https://neo4j.com/docs/getting-started/4.1/graphdb-concepts/#graphdb-labels>`_. Having this mapping means that changes to the object attributes can be pushed to the corresponding node in the graph database, and changes in the graph can be pulled to the object.

Defining a new object (or changing the attributes on an existing object) is a matter of telling the subclass what the relationships are between the object class and node labels, and object attributes and node `properties <https://neo4j.com/docs/getting-started/4.1/graphdb-concepts/#graphdb-properties>`_ or `links <https://neo4j.com/docs/getting-started/4.1/graphdb-concepts/#graphdb-relationships>`_ to other nodes. In the process, you are declaring the attributes that are associated with the object.

These *declared attributes* can be used in code like standard attributes (i.e., with the dot operator). 

Subclasses are derived from Entity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`bento_meta.entity.Entity` class is the base for all mapped objects. :class:`Entity` contains almost all the functionality required for mapping, including magic setters that perform versioning bookkeeping, and connecting objects with :class:`bento_meta.object_map.ObjectMap` classes that perform the database interactions.

The :class:`Entity` class also provides attributes that are common to all objects. These include ``_from`` and ``_to`` that indicate the versioned "lifetime" of an objects, and ``_next`` and ``_prev``, that point to next and previous versions of an object.

attspec and mapspec
^^^^^^^^^^^^^^^^^^^

Two subclass properties declare attributes and specify the mapping: *attspec* and *mapspec*. 
*attspec* is a dictionary whose keys are the attribute names, and values are the attribute type: ``simple``, ``object``, or ``collection``. *mapspec* is a dictionary that specifies the database mapping, as described below.

.. code-block:: python
                
    class Node(Entity):
      """Subclass that models a data node."""
      attspec_ = {"handle":"simple","model":"simple",
                 "category":"simple","concept":"object",
                 "props":"collection"}
      mapspec_ = {"label":"node",
                  "key":"handle",
                 "property": {"handle":"handle","model":"model","category":"category"},
                 "relationship": {
                   "concept": { "rel" : ":has_concept>",
                                "end_cls" : "Concept" },
                   "props": { "rel" : ":has_property>",
                              "end_cls" : "Property" }
                   }}

In this example, the :class:`Node` subclass of :class:`Entity` declares five attributes: ``handle``, ``model``, ``category``, ``concept``, and ``props``. The first three are simple scalars, ``concept`` is an object attribute, and ``props`` is a collection attribute.

The ``mapspec`` has four keys:

* ``label``: indicates the precise label name of Neo4j nodes that should map to this class.
* ``key``: indicates which (simple) object attribute should serve as the key in a collection of objects of this class.
* ``property``: is a dict that relates the simple object attributes (key) to the Neo4j node properties (value).
* ``relationship``: is a dict that relates the object and collection attributes (key) to the Neo4j relationship type and the name(s) of the object class that are the values of the attribute. The value is a dict with keys ``rel`` and ``end_cls``.

So, in the example, ``props`` is an attribute of :class:`Node` objects that refers to a collection of
:class:`Property` objects. In the database, each :class:`Property` object is connected to its owning :class:`Node` by a Neo4j relationship with type ``has_property``, with the :class:`Node` object as source and :class:`Property` as destination of that relationship.

Looking at the class def for :class:`Property`,

.. code-block:: python

    class Property(Entity):
      """Subclass that models a property of a node or relationship (edge)."""
      attspec_ = {"handle":"simple","model":"simple",
                 "value_domain":"simple","units":"simple",
                 "pattern":"simple","is_required":"simple",
                 "concept":"object","value_set":"object"}
      mapspec_ = {"label":"property",
                  "key":"handle",
                  "property": {"handle":"handle","model":"model",
                               "value_domain":"value_domain",
                               "pattern":"pattern",
                               "units":"units",
                               "is_required":"is_required"},
                  "relationship": {
                    "concept": { "rel" : ":has_concept>",
                                 "end_cls" : "Concept" },
                    "value_set": { "rel" : ":has_value_set>",
                                   "end_cls" : "ValueSet" }
                  }}

we see from the mapspec that :class:`Property` objects are represented by Neo4j nodes with the ``property`` label. Also, the attribute that serves as a key to :attr:`Node.props` is :attr:`Property.handle`::

  n = Node({"handle":"mynode", "model":"test"})
  # create property with handle "myprop"
  p = Property({"handle":"myprop", "model":"test", "value_domain":"string"})
  # place in a model
  model.add_node(n)
  model.add_property(n, p)
  # access property from collection attribute with key "myprop"
  assert n.props['myprop'].value_domain == "string"

Changing the attributes declared for an object therefore is a matter of adding the attribute to the ``attspec_``, designating the appropriate attribute type, and adding the attribute to ``mapspec_`` (*note the underscores*) under the ``property`` key (for simple attributes) or the ``relationship`` key (for object or collection attributes).
