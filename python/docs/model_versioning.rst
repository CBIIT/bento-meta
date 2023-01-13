Model Versioning
================

The MDB can store separate versions of the models it contains.
More description about that will be here later.

Using Model Versioning
______________________

The versioning machinery "decorates" the object setters, duplicating deprecated objects
for storage in the database, and setting the attributes ``_from`` and ``_to`` to indicate
the "lifetime" of the object.

Versioned objects have a history, which can be walked by using the attributes ``_prev`` and
``_next``.

To use versioning, turn it on using :meth:`Model.versioning`, and set the version count::

  Model.versioning(True)
  Model.set_version_count(1)

Objects created from this point ( until ``Model.versioning(False)`` ) will be "versioned". That is,
the ``_from`` attribute will be set::

  >>> case = Node({"handle":"case"})
  >>> case.versioned
  True
  >>> case._from
  1
  >>> model.add_node(case)

 Bump the version up, and subsequent changes to ``case`` will be recorded in a new version::

   >>> Model.set_version_count(2)
   >>> case.handle = "case2"
   >>> case._from
   2
   >>> case._prev._from
   1
   >>> case._prev._to
   2
   >>> case._prev._next == case



 

 



  


