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
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    import neo4j

    from bento_meta.object_map import ObjectMap


class ArgError(Exception):
    """Exception for method argument errors."""


class Entity:
    """
    Base class for all metamodel objects.

    Entity contains all the magic for metamodel objects such as
    `bento_meta.objects.Node` and 'bento_meta.object.Edge`. It will rarely
    be used directly. Entity redefines `__setattr__` and `__getattr__` to
    enable graph database object mapping under the hood.

    The Entity class also defines private and declared attributes that are
    common to all metamodel objects. It provides the machinery to manage
    private attributes separately from declared attributes, and to raise
    exceptions when attempts are made to access attributes that are not
    declared.
    """

    pvt_attr: ClassVar[list[str]] = [
        "pvt",
        "neoid",
        "dirty",
        "removed_entities",
        "attspec",
        "mapspec",
        "belongs",
    ]
    defaults = ({},)
    attspec_: ClassVar[dict[str, str]] = {
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
    mapspec_: ClassVar[
        dict[str, str | dict[str, str] | dict[str, dict[str, str | set[str]]] | None]
    ] = {
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
    object_map: ClassVar[ObjectMap | None] = None

    def __init__(self, init: dict | neo4j.graph.Node | Entity | None = None) -> None:
        """
        Entity constructor. Always called by subclasses.

        Args:
            init: One of the following:
                - dict: A dict of attribute names and values. Undeclared attributes
                    are ignored.
                - neo4j.graph.Node: A Neo4j node object to be stored as a model object.
                - Entity: An Entity (of matching subclass) used to duplicate another
                    model object.
        """
        if not set(type(self).attspec.values()) <= {"simple", "object", "collection"}:
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

    @classmethod
    def mapspec(cls) -> dict[str, str | dict[str, str]]:
        """
        Get object to database mapping specification.

        Is a class method, not a property.
        """
        if not hasattr(cls, "_mapspec"):
            cls.mergespec()
        return cls._mapspec

    @classmethod
    def default(cls, propname: str) -> Any:
        """
        Return a default value for the property named.

        Args:
            propname: Name of the property to get default for.

        Returns:
            Default value if defined, None otherwise.
        """
        if cls.defaults.get(propname):
            return cls.defaults[propname]
        return None

    # @classmethod
    def get_by_id(self, id: str) -> Entity | None:
        """
        Get an object from the db with the id attribute (not the Neo4j id).

        Args:
            id: Value of id for desired object.

        Returns:
            A new object if found, None otherwise.
        """
        if self.object_map:
            print(f"  > now in entity.get_by_id where self is {self}")
            print(f"  > and class is {self.__class__}")
            return self.object_map.get_by_id(self, id)
        print("    _NO_ cls.object_map detected")
        return None

    @property
    def dirty(self) -> int:
        """
        Flag whether this instance has been changed since retrieval from the database.

        Set to -1, ensure that the next time an attribute is accessed, the instance
        will retrieve itself from the database.
        """
        return self.pvt["dirty"]

    @dirty.setter
    def dirty(self, value: int) -> None:
        """Set dirty flag."""
        self.pvt["dirty"] = value

    @property
    def removed_entities(self) -> list[Any]:
        """Return list of removed entities."""
        return self.pvt["removed_entities"]

    @removed_entities.setter
    def removed_entities(self, value: list[Any]) -> None:
        """Set list of removed entities."""
        self.pvt["removed_entities"] = value

    @property
    def object_map(self) -> ObjectMap | None:
        """Return object map."""
        return self.pvt.get("object_map")

    @object_map.setter
    def object_map(self, value: ObjectMap | None) -> None:
        """Set object map."""
        self.pvt["object_map"] = value

    @property
    def belongs(self) -> dict[tuple[int, str, str] | tuple[int, str], Entity]:
        """Return dict that stores information on the owners (referents) of this instance in the model."""
        return self.pvt["belongs"]

    @belongs.setter
    def belongs(
        self,
        value: dict[tuple[int, str, str] | tuple[int, str], Entity],
    ) -> None:
        """Set belongs dict."""
        self.pvt["belongs"] = value

    def clear_removed_entities(self) -> None:
        """Clear the list of removed entities."""
        self.pvt["removed_entities"] = []

    def set_with_dict(self, init: dict) -> None:
        """Set the entity with a dict."""
        for att in type(self).attspec:
            if att in init:
                if type(self).attspec[att] == "collection":
                    setattr(self, att, CollValue(init[att], owner=self, owner_key=att))
                else:
                    setattr(self, att, init[att])

    def set_with_node(self, init: neo4j.graph.Node) -> None:
        """Set the entity with a Neo4j node."""
        # this unsets any attribute that is not present in the Node's properties
        for att in [a for a in type(self).attspec if type(self).attspec[a] == "simple"]:
            patt = type(self).mapspec()["property"][att]
            if patt in init:
                setattr(self, att, init[patt])
            else:
                setattr(self, att, None)
        self.neoid = init.id

    def set_with_entity(self, ent: Entity) -> Entity:
        """Set the entity with another entity."""
        if not isinstance(self, type(ent)):
            msg = (
                f"class mismatch: I am a {type(self).__name__}, "
                f"but arg is a {type(ent).__name__}"
            )
            raise ArgError(msg)
        for k in type(self).attspec:
            atts = type(self).attspec[k]
            if atts in {"simple", "object"}:
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
        """Get the attribute of the entity."""
        if name in type(self).attspec:
            # declared attr, send to __getattr__ for magic
            return self.__getattr__(name)
        return object.__getattribute__(self, name)

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Get the attribute of the entity."""
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
        """Set the attribute of the entity."""
        if name == "pvt":
            self.__dict__["pvt"] = value
        elif name in type(self).pvt_attr:
            self.__dict__["pvt"][name] = value
        elif name in type(self).attspec:
            self._check_value(name, value)
            self._set_declared_attr(name, value)
        else:
            msg = (
                f"get: attribute '{name}' neither private nor declared "
                f"for subclass {type(self).__name__}"
            )
            raise AttributeError(msg)

    def _set_declared_attr(self, name: str, value: Any) -> None:
        """Set the declared attribute of the entity."""
        atts = type(self).attspec[name]
        if atts == "simple":
            pass
        elif atts == "object":
            oldval = self.__dict__.get(name)
            if oldval and oldval == value:
                return  # a wash
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
        """Delete the attribute of the entity."""
        del self.__dict__[name]

    def _check_init(self, init: dict) -> None:
        """Check the initial value of the entity."""
        for att in type(self).attspec:
            if init[att]:
                self._check_value(att, init[att])

    def _check_value(self, att: str, value: Any) -> None:
        """Check the value of the attribute."""
        spec = type(self).attspec[att]
        if spec == "simple":
            if not (isinstance(value, (bool, float, int, str))) and value is not None:
                msg = f"value for key '{att}' is not a simple scalar"
                raise ArgError(msg)
        elif spec == "object":
            if not (isinstance(value, Entity) or value is None):
                msg = f"value for key '{att}' is not an Entity subclass"
                raise ArgError(msg)
        elif spec == "collection":
            if not (isinstance(value, (dict, list, CollValue))):
                msg = f"value for key '{att}' is not a dict,list, or CollValue"
                raise AttributeError(msg)
        else:
            msg = f"unknown attribute type '{spec}' for attribute '{att}' in attspec"
            raise ArgError(msg)

    def dup(self) -> Entity:
        """Duplicate the object, but not too deeply."""
        return type(self)(self)

    def delete(self) -> None:
        """Delete self from the database."""
        # unlink from other entities
        for okey in self.belongs:
            owner = self.belongs[okey]
            (oid, *att) = okey
            if len(att) == 2:
                del getattr(owner, att[0])[att[1]]
            else:
                setattr(owner, att[0], None)

    def dget(self, *, refresh: bool = False) -> Entity | None:
        """
        Update self from the database.

        Args:
            refresh: If True, force a retrieval from db. If False, retrieve from cache
                and don't disrupt changes already made.

        Returns:
            The entity if found, None otherwise.
        """
        if type(self).object_map:
            return type(self).object_map.get(self, refresh=refresh)
        return None

    def dput(self) -> None:
        """
        Put self to the database.

        This will set the neoid property if not yet set.
        """
        if type(self).object_map:
            return type(self).object_map.put(self)
        return None

    def rm(self, *, force: bool = False) -> None:
        """
        Delete self from the database.

        The object instance survives.

        Args:
            force: If True, detach and delete the node.
        """
        if type(self).object_map:
            return type(self).object_map.rm(self, force=force)
        return None

    @classmethod
    def attr_doc(cls) -> str:
        """Create a docstring for declared attributes on class as configured."""

        def str_for_obj(thing: set | str) -> str:
            """Convert a set of classes to a string."""
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

    def get_label(
        self,
    ) -> str | dict[str, str] | dict[str, dict[str, str | set[str]]] | None:
        """Return type of entity as label."""
        return self.mapspec_["label"]

    def get_attr_dict(self) -> dict[str, str]:
        """
        Return simple attributes set for Entity as a dict.

        Attr values are converted to strings. Doesn't include attrs with None values.

        Returns:
            Dictionary of attribute names to string values.
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
    to the containing object, not this collection object.
    It also protects against adding arbitrarily typed elements to the
    collection; it throws unless a value to set is an Entity.

    Attributes:
        owner: Entity object of which this collection is an attribute.
        owner_key: The attribute name of this collection on the owner.
    """

    def __init__(
        self,
        init: dict | None = None,
        *,
        owner: Entity,
        owner_key: str,
    ) -> None:
        """
        Initialize the CollValue.

        Args:
            init: The initial value for the collection.
            owner: The entity instance of which this collection is an attribute.
            owner_key: The attribute name of this collection on the owner.
        """
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

    def __setitem__(self, name: str, value: Entity) -> None:
        """Set the value for the collection."""
        if not isinstance(value, Entity):
            msg = (
                "a collection-valued attribute can only accept Entity members, "
                "not '{type(value)}'s"
            )
            raise ArgError(msg)
        if name in self:
            oldval = self.data.get(name)
            if oldval and oldval == value:
                return  # a wash
        value.belongs[(id(self.owner), self.owner_key, name)] = self.owner
        # smudge the owner
        self.owner.dirty = 1
        self.data[name] = value
        return

    def __getitem__(self, name: str) -> Any:  # noqa: ANN401
        """Get the value for the collection."""
        if name not in self.data:
            return None
        if self.data[name].dirty < 0:
            self.data[name].dget()
        return self.data[name]

    def __delitem__(self, name: str) -> None:
        """Delete the value for the collection."""
        if name in self.data: # cleanup belongs and set owner dirty
            entity = self.data[name]
            belongs_key = (id(self.owner), self.owner_key, name)
            if belongs_key in entity.belongs:
                del entity.belongs[belongs_key]
            self.owner.dirty = 1
        super().__delitem__(name)
