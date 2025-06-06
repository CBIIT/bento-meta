"""
bento_meta.entity
=================

This module contains
* `Entity`, the base class for metamodel objects,
* the `CollValue` class to manage collection-valued attributes, and
* the `ArgError` exception.
"""

from __future__ import annotations

from collections import UserDict
from typing import TYPE_CHECKING, Any
from warnings import warn

if TYPE_CHECKING:
    import neo4j


class ArgError(Exception):
    """Exception for method argument errors."""


class Entity:
    """
    Base class for all metamodel objects.

    Entity contains all the magic for metamodel objects such as
    `bento_meta.objects.Node` and 'bento_meta.object.Edge`. It will rarely
    be used directly. Entity redefines `__setattr__` and `__getattr__` to
    enable necessary bookkeeping for model versioning and graph database
    object mapping under the hood.

    The Entity class also defines private and declared attributes that are
    common to all metamodel objects. It provides the machinery to manage
    private attributes separately from declared attributes, and to raise
    exceptions when attempts are made to access attributes that are not
    declared.
    """

    pvt_attr = [
        "pvt",
        "neoid",
        "dirty",
        "removed_entities",
        "attspec",
        "mapspec",
        "belongs",
    ]
    defaults = ({},)
    attspec_ = {
        "_id": "simple",
        "nanoid": "simple",
        "desc": "simple",
        "_next": "object",
        "_prev": "object",
        "_from": "simple",
        "_to": "simple",
        "_commit": "simple",
        "tags": "collection",
    }
    attspec = attspec_
    mapspec_ = {
        "label": None,
        "key": "_id",
        "property": {
            "_id": "id",
            "desc": "desc",
            "_from": "_from",
            "_to": "_to",
            "_commit": "_commit",
            "nanoid": "nanoid",
        },
        "relationship": {
            "_next": {"rel": ":_next>", "end_cls": set()},
            "_prev": {"rel": ":_prev>", "end_cls": set()},
            "tags": {"rel": ":has_tag", "end_cls": {"Tag"}},
        },
    }
    object_map = None
    version_count = None
    versioning_on = False

    def __init__(self, init: dict | neo4j.graph.Node | Entity | None = None) -> None:
        """
        Entity constructor. Always called by subclasses.

        .. py:function:: Node(init)
        :param dict init: A dict of attribute names and values. Undeclared attributes
            are ignored.
        :param neo4j.graph.Node init: a `neo4j.graph.Node` object to be stored as a
            model object.
        :param `bento_meta.Entity` init: an Entity (of matching subclass).
            Used to duplicate another model object.
        """
        if not set(type(self).attspec.values()) <= set(
            ["simple", "object", "collection"],
        ):
            msg = "unknown attribute type in attspec"
            raise ArgError(msg)

        # private
        self.pvt = {}
        self.neoid = None
        self.dirty = 1
        self.removed_entities = []
        self.belongs = {}
        # merge to universal map - no, do in the subclasses
        # type(self).mergespec()

        if init:
            if isinstance(init, Entity):
                self.set_with_entity(init)
            elif isinstance(init, dict):
                self.set_with_dict(init)
            elif (
                type(init).__name__ == "Node"
            ):  # neo4j.graph.Node - but don't want to import that
                self.set_with_node(init)
        for att in type(self).attspec:
            if att not in self.__dict__:
                if self.attspec[att] == "collection":
                    setattr(self, att, CollValue({}, owner=self, owner_key=att))
                else:
                    setattr(self, att, None)
        if type(self).versioning_on:
            self._from = type(self).version_count

    @classmethod
    def mapspec(cls) -> dict[str, str | dict[str, str]]:
        """
        The object to database mapping specification.

        Is a class method, not a property.
        """
        if not hasattr(cls, "_mapspec"):
            cls.mergespec()
        return cls._mapspec

    @classmethod
    def versioning(cls, on: bool | None = None) -> bool:
        """
        Get or set whether versioning is applied to object manipulations.

            :param boolean on: True, apply versioning. False, do not.
        """
        if on is None:
            return cls.versioning_on
        cls.versioning_on = on
        return cls.versioning_on

    @classmethod
    def set_version_count(cls, ct: int) -> None:
        """
        Set the integer version counter.

        This will usually be accessed via a `bento_meta.Model` instance.

            :param int ct: Set version counter to this value
        """
        if not isinstance(ct, int) or ct < 0:
            msg = "arg must be a positive integer"
            raise ArgError(msg)
        cls.version_count = ct

    @classmethod
    def default(cls, propname: str):
        """Return a default value for the property named, or None if no default defined."""
        if cls.defaults.get(propname):
            return cls.defaults[propname]
        return None

    # @classmethod
    def get_by_id(self, id: str):
        """
        Get an object from the db with the id attribute (not the Neo4j id).

        Returns a new object.
        :param string id: value of id for desired object
        """
        if self.object_map:
            print(f"  > now in entity.get_by_id where self is {self}")
            print(f"  > and class is {self.__class__}")
            return self.object_map.get_by_id(self, id)
        print("    _NO_ cls.object_map detected")

    @property
    def dirty(self):
        """
        Flag whether this instance has been changed since retrieval from the database.

        Set to -1, ensure that the next time an attribute is accessed, the instance
        will retrieve itself from the database.
        """
        return self.pvt["dirty"]

    @dirty.setter
    def dirty(self, value):
        self.pvt["dirty"] = value

    @property
    def versioned(self):
        """Is this instance versioned?"""
        return self._from

    @property
    def removed_entities(self):
        return self.pvt["removed_entities"]

    @property
    def object_map(self):
        return self.pvt["object_map"]

    @property
    def belongs(self):
        """
        Dict that stores information on the owners (referents) of this instance
        in the model
        """
        return self.pvt["belongs"]

    def clear_removed_entities(self):
        self.pvt["removed_entities"] = []

    def set_with_dict(self, init: dict) -> None:
        for att in type(self).attspec:
            if att in init:
                if type(self).attspec[att] == "collection":
                    setattr(self, att, CollValue(init[att], owner=self, owner_key=att))
                else:
                    setattr(self, att, init[att])

    def set_with_node(self, init):
        # this unsets any attribute that is not present in the Node's properties
        for att in [a for a in type(self).attspec if type(self).attspec[a] == "simple"]:
            patt = type(self).mapspec()["property"][att]
            if patt in init:
                setattr(self, att, init[patt])
            else:
                setattr(self, att, None)
        self.neoid = init.id

    def set_with_entity(self, ent):
        if not isinstance(self, type(ent)):
            msg = (
                f"class mismatch: I am a {type(self).__name__}, "
                f"but arg is a {type(ent).__name__}"
            )
            raise ArgError(msg)
        for k in type(self).attspec:
            atts = type(self).attspec[k]
            if k == "_next" or k == "_prev":
                break
            if atts == "simple" or atts == "object":
                setattr(self, k, getattr(ent, k))
            elif atts == "collection":
                setattr(self, k, CollValue(getattr(ent, k), owner=self, owner_key=k))
            else:
                msg = f"unknown attribute type '{atts}'"
                raise RuntimeError(msg)
        for okey in ent.belongs:
            self.belongs[okey] = ent.belongs[okey]
        self.neoid = ent.neoid
        self.dirty = 1
        return self

    def __getattribute__(self, name: str) -> Any:  # noqa: ANN401
        if name in type(self).attspec:
            # declared attr, send to __getattr__ for magic
            return self.__getattr__(name)
        return object.__getattribute__(self, name)

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        if name in type(self).pvt_attr:
            return self.__dict__["pvt"].get(name)
        if name in type(self).attspec:
            if name not in self.__dict__ or self.__dict__[name] is None:
                return None
            if type(self).attspec[name] == "object" and self.__dict__[name].dirty < 0:
                # magic - lazy getting
                self.__dict__[name].dget()
            return self.__dict__[name]
        msg = (
            f"get: attribute '{name}' neither private nor declared "
            f"for subclass {type(self).__name__}"
        )
        raise AttributeError(msg)

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        if name == "pvt":
            self.__dict__["pvt"] = value
        elif name in type(self).pvt_attr:
            self.__dict__["pvt"][name] = value
        elif name in type(self).attspec:
            self._check_value(name, value)
            if name in ["_prev", "_next", "_from", "_to"]:
                self.dirty = 1
                self.__dict__[name] = value
            else:
                self._set_declared_attr(name, value)
        else:
            msg = (
                f"get: attribute '{name}' neither private nor declared "
                f"for subclass {type(self).__name__}"
            )
            raise AttributeError(msg)

    def version_me(setattr_func):
        def _version_set_declared_attr(self, name, value):
            if not type(self).versioning_on:
                return setattr_func(self, name, value)
            if not self.versioned:
                return setattr_func(self, name, value)
            if (type(self).version_count > self._from) and (self._to is None):
                # dup becomes the "old" object and self the "new":
                dup = self.dup()
                dup._to = type(self).version_count
                dup._from = self._from
                self._from = type(self).version_count
                if self._prev:
                    dup._prev = self._prev
                    self._prev._next = dup
                dup._next = self
                self._prev = dup
                self.neoid = None
                # make the owners own dup, rather than self - this is under the radar of
                # version_me
                for okey in dup.belongs:
                    owner = dup.belongs[okey]
                    (oid, *att) = okey
                    if len(att) == 2:
                        getattr(owner, att[0]).data[att[1]] = dup
                    else:
                        owner.__dict__[att[0]] = dup
                setattr_func(self, name, value)
                # this is on version_me's radar- dups the owning entity if nec
                for okey in self.belongs:
                    owner = self.belongs[okey]
                    (oid, *att) = okey
                    if len(att) == 2:
                        getattr(owner, att[0])[att[1]] = self
                    else:
                        # if att[0]=='category':
                        #   set_trace()
                        setattr(owner, att[0], self)
                    if owner._prev:
                        # dup (old entity) needs to belong to the prev version of owner
                        del dup.belongs[(id(owner), *att)]
                        dup.belongs[(id(owner._prev), *att)] = owner._prev
            else:
                return setattr_func(self, name, value)

        return _version_set_declared_attr

    @version_me
    def _set_declared_attr(self, name: str, value: Any) -> None:  # noqa: ANN401
        atts = type(self).attspec[name]
        if atts == "simple":
            pass
        elif atts == "object":
            oldval = self.__dict__.get(name)
            if oldval:
                if oldval == value:
                    # a wash
                    return
                if not self.versioned:
                    del oldval.belongs[(id(self), name)]
                    self.removed_entities.append((name, oldval))
            if isinstance(value, Entity):
                value.belongs[(id(self), name)] = self
        elif atts == "collection":
            if isinstance(value, dict):
                value = CollValue(value, owner=self, owner_key=name)
            if isinstance(value, list):  # convert list of objs to CollValue
                d = {}
                for v in value:
                    d[getattr(v, type(v).mapspec()["key"])] = v
                value = CollValue(d, owner=self, owner_key=name)
        else:
            msg = f"unknown attspec value '{atts}'"
            raise RuntimeError(msg)
        self.dirty = 1
        self.__dict__[name] = value

    def __delattr__(self, name: str) -> None:
        del self.__dict__[name]

    def _check_init(self, init) -> None:
        for att in type(self).attspec:
            if init[att]:
                self._check_value(att, init[att])

    def _check_value(self, att, value):
        spec = type(self).attspec[att]
        try:
            if spec == "simple":
                if (
                    not (isinstance(value, (bool, float, int, str)))
                    and value is not None
                ):
                    raise ArgError(
                        f"value for key '{att}' is not a simple scalar",
                    )
            elif spec == "object":
                if not (isinstance(value, Entity) or value is None):
                    raise ArgError(
                        f"value for key '{att}' is not an Entity subclass",
                    )
            elif spec == "collection":
                if not (isinstance(value, (dict, list, CollValue))):
                    raise AttributeError(
                        f"value for key '{att}' is not a dict,list, or CollValue",
                    )
            else:
                raise ArgError(
                    f"unknown attribute type '{spec}' for attribute '{att}' in attspec",
                )
        except Exception:
            raise

    def dup(self):
        """
        Duplicate the object, but not too deeply.

        Mainly for use of the versioning machinery.
        """
        return type(self)(self)

    def delete(self) -> None:
        """
        Delete self from the database.

        If versioning is active, this will 'deprecate' the entity, but not actually
            remove it from the db.
        """
        if self.versioning_on and self.versioned:
            if type(self).version_count > self._from:
                self._to = type(self).version_count
            else:
                msg = (
                    f"delete - current version count {type(self).version_count} "
                    f"is <= entity's _to attribute"
                )
                warn(msg, stacklevel=2)
        else:
            # unlink from other entities
            for okey in self.belongs:
                owner = self.belongs[okey]
                (oid, *att) = okey
                if len(att) == 2:
                    del getattr(owner, att[0])[att[1]]
                else:
                    setattr(owner, att[0], None)

    def dget(self, *, refresh: bool = False):
        """
        Update self from the database.

        :param boolean refresh: if True, force a retrieval from db;
        if False, retrieve from cache;
        don't disrupt changes already made
        """
        if type(self).object_map:
            return type(self).object_map.get(self, refresh)

    def dput(self):
        """
        Put self to the database.

        This will set the `neoid` property if not yet set.
        """
        if type(self).object_map:
            return type(self).object_map.put(self)

    def rm(self, force):
        """Delete self from the database. The object instance survives."""
        if type(self).object_map:
            return type(self).object_map.rm(self, force)

    @classmethod
    def attr_doc(cls):
        """Create a docstring for declared attributes on class as configured."""

        def str_for_obj(thing):
            if isinstance(thing, set):
                return "|".join(thing)
            return thing

        (first, *rest) = cls.__doc__.split("\n")
        if cls.__name__ == "Entity":
            first += " Posesses the following attributes:"
        else:
            first += " Posesses all :class:`Entity` attributes, plus the following:"
        doc = f"""\
.. py:class:: {cls.__name__}

{first}

"""
        for att in [x for x in cls.attspec_ if cls.attspec[x] == "simple"]:
            doc += """\
  .. py:attribute:: {att}
       :type: simple
""".format(
                att=cls.__name__.lower() + "." + att,
            )
        for att in [x for x in cls.attspec_ if cls.attspec[x] == "object"]:
            doc += """\
  .. py:attribute:: {att}
       :type: {obj}
""".format(
                att=cls.__name__.lower() + "." + att,
                obj=str_for_obj(cls.mapspec_["relationship"][att]["end_cls"]),
            )
        for att in [x for x in cls.attspec_ if cls.attspec[x] == "collection"]:
            doc += """\
  .. py:attribute:: {att}
       :type: collection of {obj}
""".format(
                att=cls.__name__.lower() + "." + att,
                obj=str_for_obj(cls.mapspec_["relationship"][att]["end_cls"]),
            )
        doc += "\n"
        return doc

    def get_label(self) -> str:
        """Return type of entity as label."""
        return self.mapspec_["label"]

    def get_attr_dict(self) -> dict[str, str]:
        """
        Return simple attributes set for Entity as a dict.

        Attr values are converted to strings. Doesn't include attrs with None values.
        """
        return {
            k: str(getattr(self, k))
            for k in self.attspec
            if self.attspec[k] == "simple" and getattr(self, k) is not None
        }


class CollValue(UserDict):
    """
    A UserDict for housing Entity collection attributes.

    This class contains a hook for recording the Entity that
    owns the value that is being set. The value is marked as belonging
    to the *containing object*, not this collection object.
    It also protects against adding arbitrarily typed elements to the
    collection; it throws unless a value to set is an `Entity`. `__setitem__`
    is instrumented for managing versioning.

    :param owner: `Entity` object of which this collection is an attribute
    :param owner_key: the attribute name of this collection on the owner
    """

    def __init__(self, init=None, *, owner: Entity, owner_key: str):
        self.__dict__["__owner"] = owner
        self.__dict__["__owner_key"] = owner_key
        super().__init__(init)

    @property
    def owner(self) -> Entity:
        """The entity instance of which this collection is an attribute."""
        return self.__dict__["__owner"]

    @property
    def owner_key(self) -> str:
        """The attribute name of this collection on the `owner`."""
        return self.__dict__["__owner_key"]

    def version_me(setitem_func):
        def _version_set_collvalue_item(self, name, value):
            if not self.owner.versioning_on:
                return setitem_func(self, name, value)
            if not self.owner.versioned:
                return setitem_func(self, name, value)
            if (Entity.version_count > self.owner._from) and (self.owner._to is None):
                # dup becomes the "old" object and self the "new":
                dup = self.owner.dup()
                dup._to = Entity.version_count
                self.owner._from = Entity.version_count
                if self.owner._prev:
                    dup._prev = self.owner._prev
                    self.owner._prev._next = dup
                dup._next = self.owner
                self.owner._prev = dup
                self.owner.neoid = None
                # make the owners own dup, rather than self.owner
                for okey in dup.belongs:
                    owner = dup.belongs[okey]
                    (oid, *att) = okey
                    if len(att) == 2:
                        getattr(owner, att[0]).data[att[1]] = dup
                    else:
                        owner.__dict__[att[0]] = dup
                setitem_func(self, name, value)
                for okey in self.owner.belongs:
                    owner = self.owner.belongs[okey]
                    (oid, *att) = okey
                    if len(att) == 2:
                        getattr(owner, att[0])[att[1]] = (
                            self.owner
                        )  # this dups the owning entity if nec
                    else:
                        setattr(owner, att[0], self.owner)
                    if owner._prev:
                        # dup (old entity) needs to belong to the prev version of owner
                        del dup.belongs[(id(owner), *att)]
                        dup.belongs[(id(owner._prev), *att)] = owner._prev
            else:
                return setitem_func(self, name, value)

        return _version_set_collvalue_item

    @version_me
    def __setitem__(self, name, value):
        if not isinstance(value, Entity):
            raise ArgError(
                f"a collection-valued attribute can only accept Entity members, not '{type(value)}'s",
            )
        if name in self:
            oldval = self.data.get(name)
            if oldval:
                if oldval == value:
                    # a wash
                    return
                if not self.owner.versioned:
                    del oldval.belongs[(id(self.owner), self.owner_key, name)]
                    self.owner.removed_entities.append((self.owner_key, oldval))
        value.belongs[(id(self.owner), self.owner_key, name)] = self.owner
        # smudge the owner
        self.owner.dirty = 1
        self.data[name] = value
        return

    def __getitem__(self, name: str) -> Any:  # noqa: ANN401
        if name not in self.data:
            return None
        if self.data[name].dirty < 0:
            self.data[name].dget()
        return self.data[name]

    def __delitem__(self, name: str) -> None:
        self[name] == None  # trigger __setitem__
        super().__delitem__(name)
