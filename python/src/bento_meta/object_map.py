"""
bento_meta.object_map
=====================

This module contains :class:`ObjectMap`, a class which provides the
machinery for mapping bento_meta objects to a Bento Metamodel Database
in Neo4j. Mostly not for human consumption. The ObjectMap:

* interprets the attribute specification (attspec) and map
  specification (mapspec) associated with :class:`Entity` subclasses
* provides the :meth:`get` and :meth:`put` methods to subclasses, that
  enable them to get and put themselves to the database
* generates appropriate
 `Cypher <https://neo4j.com/docs/cypher-manual/current/>`
 queries to do gets and puts
 One ObjectMap instance should be generated for each Entity subclass (see, e.g.,
 :class:`bento_meta.model.Model`)
"""

from __future__ import annotations

import re
import sys

sys.path.append("..")
from typing import Any, ClassVar, cast
from warnings import warn

from neo4j import BoltDriver, Driver, Neo4jDriver, Transaction
from typing_extensions import LiteralString

from bento_meta.entity import ArgError, CollValue, Entity
from bento_meta.objects import (
    Concept,
    Edge,
    Node,
    Origin,
    Predicate,
    Property,
    Tag,
    Term,
    ValueSet,
)


class ObjectMap:
    """
    Machinery for mapping bento_meta objects to a Bento Metamodel Database in Neo4j.

    Mostly not for human consumption.
    """

    cache: ClassVar[dict] = {}

    def __init__(
        self,
        *,
        cls: type[Entity] | None = None,
        drv: Driver | None = None,
    ) -> None:
        """
        Initialize the ObjectMap.

        Args:
            cls: The class to map.
            drv: The Neo4j driver.
        """
        if not cls:
            msg = "arg cls= is required"
            raise ArgError(msg)
        self.cls = cls
        if drv:
            if isinstance(drv, (Neo4jDriver, BoltDriver)):
                self.drv = drv
            else:
                msg = (
                    "drv= arg must be Neo4jDriver or BoltDriver "
                    "(returned from GraphDatabase.driver())"
                )
                raise ArgError(msg)
        self.maps = {}

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cache."""
        cls.cache = {}

    @classmethod
    def cls_by_label(cls, lbl: str) -> type[Entity] | None:
        """Get the class by label."""
        if not hasattr(cls, "_clsxlbl"):
            cls._clsxlbl = {}
            for o in (Node, Edge, Property, ValueSet, Term, Concept, Origin, Tag):
                cls._clsxlbl[o.mapspec()["label"]] = o
        return cls._clsxlbl.get(lbl)

    @classmethod
    def keys_by_cls_and_reln(
        cls,
        qcls: type[Entity],
        reln: str,
    ) -> tuple[str, str | None] | None:
        """Get the keys by class and relationship."""
        if not hasattr(cls, "_keysxcls"):
            cls._keysxcls = {}
            for o in (
                Node,
                Edge,
                Property,
                ValueSet,
                Term,
                Concept,
                Predicate,
                Origin,
                Tag,
            ):
                for oatt in [x for x in o.attspec if o.attspec[x] == "object"]:
                    r = o.mapspec()["relationship"][oatt]["rel"]
                    r = re.match("[:<>]*([a-zA-Z_]+)[:<>]*", r).group(1)
                    cls._keysxcls[(o.__name__, r)] = (oatt, None)
                for catt in [x for x in o.attspec if o.attspec[x] == "collection"]:
                    r = o.mapspec()["relationship"][catt]["rel"]
                    r = re.match("[:<>]*([a-zA-Z_]+)[:<>]*", r).group(1)
                    cls._keysxcls[(o.__name__, r)] = (catt, o.mapspec()["key"])
        return cls._keysxcls.get((qcls.__name__, reln))

    @classmethod
    def _quote_val(
        cls,
        value: str | float | None,
        *,
        single: bool | None = None,
    ) -> str | float | None:  # double quote unless single is set
        """Quote the value unless single is set."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value  # no quote
        if single:
            return f"'{value}'"  # quote
        return f'"{value}"'  # quote

    def get_by_id(
        self,
        obj: Entity,
        id: str,
        *,
        refresh: bool = False,
    ) -> Entity | None:
        """Get an entity given an id attribute value (not the Neo4j id)."""
        neoid = None

        if self.drv is None:
            msg = "get_by_id() requires Neo4j driver instance"
            raise ArgError(msg)

        with self.drv.session() as session:
            result = session.run(cast("LiteralString", self.get_by_id_q()), {"id": id})
            rec = (
                result.single()
            )  # should be unique - this call will warn if there are more than one

            if rec is not None:
                neoid = rec["id(n)"]

        if neoid is not None:
            obj.neoid = neoid
            return self.get(obj, refresh=True)
        return None

    def get_by_node_nanoid(
        self,
        obj: Entity,
        nanoid: str,
        *,
        refresh: bool = False,
    ) -> Entity | None:
        """PROTOTYPE: Get an entity given an id attribute value (not the Neo4j id)."""
        neo4jid = None

        if not self.drv:
            msg = "get_by_id() requires Neo4j driver instance"
            raise ArgError(msg)

        with self.drv.session() as session:
            result = session.run(
                cast("LiteralString", self.get_by_node_nanoid_q()),
                {"nanoid": nanoid},
            )
            rec = (
                result.single()
            )  # should be unique - this call will warn if there are more than one
            if rec is not None:
                neo4jid = rec["id(n)"]

        if neo4jid is None:
            obj.neoid = neo4jid
            return self.get(obj, refresh=True)
        return None

    def get(self, obj: Entity, *, refresh: bool = False) -> Entity:
        """Get the data for an object instance from the db and load the instance with it."""
        if not self.drv:
            msg = "get() requires Neo4j driver instance"
            raise ArgError(msg)

        if refresh:
            pass
        elif (obj.neoid in ObjectMap.cache) and (ObjectMap.cache[obj.neoid].dirty >= 0):
            return obj

        with self.drv.session() as session:
            result = session.run(cast("LiteralString", self.get_q(obj)))
            rec = result.single()
            if not rec:
                msg = f"object with id {obj.neoid} not found in db"
                raise RuntimeError(msg)

        if obj.neoid not in ObjectMap.cache:
            ObjectMap.cache[obj.neoid] = obj

        with self.drv.session() as session:
            for att in self.cls.mapspec()["relationship"]:
                result = session.run(cast("LiteralString", self.get_attr_q(obj, att)))
                values = {}
                first_val = None
                for rec in result:
                    o = ObjectMap.cache.get(rec["a"].id)
                    if o:
                        if not first_val:
                            first_val = o
                        values[getattr(o, type(o).mapspec()["key"])] = o
                    else:
                        c = None
                        for lbl in rec["a"].labels:
                            c = ObjectMap.cls_by_label(lbl)
                            if c:
                                break
                        if not c:
                            msg = (
                                f"node labels {rec['a'].labels} "
                                "have no associated class in the object model"
                            )
                            raise RuntimeError(msg)
                        o = c(rec["a"])
                        o.dirty = -1
                        ObjectMap.cache[o.neoid] = o
                        if not first_val:
                            first_val = o
                        values[getattr(o, type(o).mapspec()["key"])] = o
                if self.cls.attspec[att] == "object" and len(values) > 1:
                    warn(
                        (
                            f"expected one node for attribute {att} on class "
                            f"{self.cls.__name__}, but got {len(values)}; using first one"
                        ),
                        stacklevel=2,
                    )
                if self.cls.attspec[att] == "object":
                    setattr(obj, att, first_val)
                elif self.cls.attspec[att] == "collection":
                    setattr(obj, att, values)
                else:
                    msg = (
                        f"attribute '{att}' has unknown attribute type "
                        f"'{self.cls.attspec[att]}'"
                    )
                    raise RuntimeError(msg)

        obj.clear_removed_entities()
        obj.dirty = 0
        return obj

    def put(self, obj: Entity) -> Entity:
        """Put the object instance's attributes to the mapped data node in the database."""
        if not self.drv:
            msg = "put() requires Neo4j driver instance"
            raise ArgError(msg)
        with self.drv.session() as session:
            result = None
            with session.begin_transaction() as tx:
                for qry in self.put_q(obj):
                    result = tx.run(cast("LiteralString", qry))
                if result is None:
                    msg = "no result from put_q"
                    raise RuntimeError(msg)
                obj.neoid = result.single().value("id(n)")
                if obj.neoid is None:
                    msg = (
                        "no neo4j id retrived on put for obj "
                        f"'{getattr(obj, self.cls.mapspec()['key'])}'"
                    )
                    raise RuntimeError(msg)
                for att in self.cls.mapspec()["relationship"]:
                    values = getattr(obj, att)
                    if not values:
                        continue
                    if isinstance(values, CollValue):
                        items = values.values()
                    else:
                        items = [values]
                    for val in items:
                        if val.neoid is not None:
                            continue
                        # put val as a node
                        for qry in ObjectMap(cls=type(val), drv=self.drv).put_q(val):
                            result = tx.run(cast("LiteralString", qry))
                        val.neoid = result.single().value("id(n)")
                        if val.neoid is None:
                            msg = (
                                "no neo4j id retrived on put for obj "
                                f"'{val[type(val).mapspec()['key']]}'"
                            )
                            raise RuntimeError(msg)
                        val.dirty = 1
                        ObjectMap.cache[val.neoid] = val
                    for qry in self.put_attr_q(obj, att, values):
                        tx.run(cast("LiteralString", qry))
                    # drop removed entities here
                    while obj.removed_entities:
                        ent = obj.removed_entities.pop()
                        self.drop(obj, *ent, tx)
        ObjectMap.cache[obj.neoid] = obj
        obj.dirty = 0
        return obj

    def rm(self, obj: Entity, *, force: bool | int = False) -> Any | None:
        """'Delete' the object's mapped node from the database."""
        if not self.drv:
            msg = "rm() requires Neo4j driver instance"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        with self.drv.session() as session:
            result = session.run(cast("LiteralString", self.rm_q(obj, detach=force)))
            s = result.single()
            if s is None:
                warn("rm() - corresponding db node not found", stacklevel=2)
            else:
                return s.value()
        return None

    def add(self, obj: Entity, att: str, tgt: Entity) -> Any:
        """
        Create a link between an object instance and a target object in the database.

        This represents adding an object-valued attribute to the object.

        Args:
            obj: The object instance to add attribute to.
            att: The attribute name.
            tgt: The target entity to link.

        Returns:
            The Neo4j ID of the target, or None if not found.
        """
        if not self.drv:
            msg = "add() requires Neo4j driver instance"
            raise ArgError(msg)
        with self.drv.session() as session:
            for qry in self.put_attr_q(obj, att, tgt):
                result = session.run(cast("LiteralString", qry))
            tgt_id = result.single().value()
            if tgt_id is None:
                warn("add() - corresponding db node not found", stacklevel=2)
            return tgt_id

    def drop(
        self,
        obj: Entity,
        att: str,
        tgt: Entity,
        tx: Transaction | None = None,
    ) -> Any:
        """
        Remove an existing link between an object instance and a target object in the database.

        This represents dropping an object-valued attribute from the object.

        Args:
            obj: The object instance to remove attribute from.
            att: The attribute name.
            tgt: The target entity to unlink.
            tx: Optional transaction to use for the operation.

        Returns:
            The result value, or None if not found.
        """
        if not self.drv:
            msg = "rm() requires Neo4j driver instance"
            raise ArgError(msg)
        # if the tgt is not in the database, then dropping it is a no-op:
        if not tgt.neoid:
            return None

        if tx:
            result = None
            for qry in self.rm_attr_q(obj, att, tgt):
                result = tx.run(cast("LiteralString", qry))
            s = result.single()
            if s is None:
                warn("drop() - corresponding target db node not found", stacklevel=2)
            else:
                return s.value()
        else:
            with self.drv.session() as session:
                result = None
                for qry in self.rm_attr_q(obj, att, tgt):
                    result = session.run(cast("LiteralString", qry))
                s = result.single()
                if s is None:
                    warn(
                        "drop() - corresponding target db node not found",
                        stacklevel=2,
                    )
                else:
                    return s.value()
        return None

    def get_owners(
        self,
        obj: Entity,
    ) -> list[tuple[Entity, tuple[str, str | None] | None]]:
        """Get the nodes which are linked to the object instance (the owners of the object)."""
        if not self.drv:
            msg = "get_owners() requires Neo4j driver instance"
            raise ArgError(msg)
        ret = []
        with self.drv.session() as session:
            result = session.run(cast("LiteralString", self.get_owners_q(obj)))
            for rec in result:
                if rec["reln"][0] == "_":  # skip _prev, _next, and convenience links
                    break
                ocls = None
                for lbl in rec["a"].labels:
                    ocls = self.cls_by_label(lbl)
                    if ocls:
                        break
                assert ocls
                o = ocls(rec["a"])
                # creating object but not putting in the cache - why?
                keys = self.keys_by_cls_and_reln(type(o), rec["reln"])
                # obj.belongs[(id(o),*keys)] = o
                # not setting the belongs on the obj - why?
                ret.append((o, keys))
        return ret

    def get_q(self, obj: Entity) -> str:
        """Get the query for an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        return (
            f"MATCH (n:{self.cls.mapspec()['label']}) "
            f"WHERE id(n)={obj.neoid} RETURN n,id(n)"
        )

    def get_by_id_q(self) -> str:
        """Get the query for an entity by its Neo4j id."""
        return (
            f"MATCH (n:{self.cls.mapspec()['label']}) "
            "WHERE id(n)=$id and n._to IS NULL RETURN id(n)"
        )

    def get_by_node_nanoid_q(self) -> str:
        """PROTOTYPE: Get the query for an entity given its nanoid."""
        return "MATCH (n:node) WHERE n.nanoid=$nanoid and n._to is NULL RETURN id(n)"

    def get_attr_q(self, obj: Entity, att: str) -> str:
        """Get the query for an attribute of an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        label = self.cls.mapspec()["label"]
        if att in self.cls.mapspec()["property"]:
            pr = self.cls.mapspec()["property"][att]
            return f"MATCH (n:{label}) WHERE id(n)={obj.neoid} RETURN n.{pr}"
        if att in self.cls.mapspec()["relationship"]:
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[\2]-\3", spec["rel"])
            if len(end_lbls) == 1:
                qry = (
                    f"MATCH (n:{label}){rel}(a:{end_lbls[0]}) "
                    f"WHERE id(n)={obj.neoid} RETURN a"
                )
                if self.cls.attspec[att] == "object":
                    qry += " LIMIT 1"
                return qry
            # multiple end classes possible
            cond = " OR ".join([f"'{lbl}' IN labels(a)" for lbl in end_lbls])
            return (
                f"MATCH (n:{label}){rel}(a) WHERE id(n)={obj.neoid} AND ({cond}) "
                "RETURN a"
            )
        msg = f"'{att}' is not a registered attribute for class '{self.cls.__name__}'"
        raise ArgError(msg)

    def get_owners_q(self, obj: Entity) -> str:
        """Get the query for the owners of an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)

        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        label = self.cls.mapspec()["label"]
        return (
            f"MATCH (n:{label})<-[r]-(a) WHERE id(n)={obj.neoid} "
            "RETURN TYPE(r) as reln, a"
        )

    def put_q(self, obj: Entity) -> list[str]:
        """Get the query for putting an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        props = {}
        null_props = []
        for pr in self.cls.mapspec()["property"]:
            if getattr(obj, pr) is None:
                null_props.append(self.cls.mapspec()["property"][pr])
            else:
                props[self.cls.mapspec()["property"][pr]] = getattr(obj, pr)
        stmts = []
        if obj.neoid is not None:
            set_clause = "SET " + ",".join(
                [f"n.{pr}={ObjectMap._quote_val(props[pr])}" for pr in props],
            )
            stmts.append(
                f"MATCH (n:{self.cls.mapspec()['label']}) WHERE id(n)={obj.neoid} "
                f"{set_clause} RETURN n,id(n)",
            )
            stmts.extend(
                [
                    (
                        f"MATCH (n:{self.cls.mapspec()['label']}) WHERE id(n)="
                        f"{obj.neoid} REMOVE n.{pr} RETURN n,id(n)"
                    )
                    for pr in null_props
                ],
            )
            return stmts
        spec = ",".join([f"{pr}:{ObjectMap._quote_val(props[pr])}" for pr in props])
        return [
            f"CREATE (n:{self.cls.mapspec()['label']} {{{spec}}}) RETURN n,id(n)",
        ]

    def put_attr_q(
        self,
        obj: Entity,
        att: str,
        values: Entity | list[Entity] | CollValue,
    ) -> str | list[str]:
        """Get the query for putting an attribute of an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        if not isinstance(values, (Entity, list, CollValue)):
            msg = "'values' must be a list of values suitable for the attribute"
            raise ArgError(msg)
        if isinstance(values, CollValue):
            values = values.values()
        elif isinstance(values, Entity):
            values = [values]
        if att in self.cls.mapspec()["property"]:
            return (
                f"MATCH (n:{self.cls.mapspec()['label']}) WHERE id(n)={obj.neoid} "
                f"SET {self.cls.mapspec()['property'][att]}="
                f"{ObjectMap._quote_val(values[0])} RETURN id(n)"
            )
        if att in self.cls.mapspec()["relationship"]:
            if not self._check_values_list(att, values):
                msg = (
                    "'values' must be a list of mapped Entity objects of "
                    f"the appropriate subclass for attribute '{att}'",
                )
                raise ArgError(msg)
            stmts = []
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[\2]-\3", spec["rel"])
            cond = " OR ".join([f"'{lbl}' IN labels(a)" for lbl in end_lbls])
            for avalue in values:
                if len(end_lbls) == 1:
                    stmts.append(
                        f"MATCH (n:{self.cls.mapspec()['label']}),(a:{end_lbls[0]}) "
                        f"WHERE id(n)={obj.neoid} AND id(a)={avalue.neoid} "
                        f"MERGE (n){rel}(a) RETURN id(a)",
                    )
                else:
                    stmts.append(
                        f"MATCH (n:{self.cls.mapspec()['label']}),(a) "
                        f"WHERE id(n)={obj.neoid} AND id(a)={avalue.neoid} AND "
                        f"({cond}) MERGE (n){rel}(a) RETURN id(a)",
                    )
            return stmts
        msg = f"'{att}' is not a registered attribute for class '{self.cls.__name__}'"
        raise ArgError(msg)

    def rm_q(self, obj: Entity, *, detach: bool = False) -> str:
        """Get the query for removing an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        dlt = "DETACH DELETE n" if detach else "DELETE n"
        qry = f"MATCH (n:{self.cls.mapspec()['label']}) WHERE id(n)={obj.neoid} "
        return qry + dlt

    def rm_attr_q(
        self,
        obj: Entity,
        att: str,
        values: list[Entity] | None = None,
    ) -> str | list[str]:
        """Get the query for removing an attribute of an object."""
        if not isinstance(obj, self.cls):
            msg = f"arg1 must be object of class {self.cls.__name__}"
            raise ArgError(msg)
        if obj.neoid is None:
            msg = "object must be mapped (i.e., obj.neoid must be set)"
            raise ArgError(msg)
        if values and not isinstance(values, list):
            values = [values]
        if att in self.cls.mapspec()["property"]:
            return (
                f"MATCH (n:{self.cls.mapspec()['label']}) "
                f"WHERE id(n)={obj.neoid} REMOVE n.{att} RETURN id(n)"
            )
        if att in self.cls.mapspec()["relationship"]:
            many = self.cls.attspec[att] == "collection"
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            cond = " OR ".join([f"'{lbl}' IN labels(a)" for lbl in end_lbls])
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[r\2]-\3", spec["rel"])
            if values and values[0] == ":all":
                if len(end_lbls) == 1:
                    return (
                        f"MATCH (n:{self.cls.mapspec()['label']}){rel}(a:{end_lbls[0]})"
                        f" WHERE id(n)={obj.neoid} DELETE r RETURN id(n),id(a)"
                    )
                return (
                    f"MATCH (n:{self.cls.mapspec()['label']}){rel}(a) "
                    f"WHERE id(n)={obj.neoid} AND ({cond}) DELETE r RETURN id(n)"
                )
            stmts = []

            if not self._check_values_list(att, values):
                msg = (
                    "'values' must be a list of mapped Entity objects of the "
                    f"appropriate subclass for attribute '{att}'",
                )
                raise ArgError(msg)
            for val in values:
                qry = ""
                if len(end_lbls) == 1:
                    qry = (
                        f"MATCH (n:{self.cls.mapspec()['label']}){rel}(a:{end_lbls[0]})"
                        f" WHERE id(n)={obj.neoid} AND id(a)={val.neoid} "
                        f"DELETE r RETURN id(n),id(a)"
                    )
                else:
                    qry = (
                        f"MATCH (n:{self.cls.mapspec()['label']}){rel}(a) "
                        f"WHERE id(n)={obj.neoid} AND id(a)={val.neoid} AND ({cond}) "
                        f"DELETE r RETURN id(n),id(a)"
                    )
                stmts.append(qry)
            return stmts
        msg = f"'{att}' is not a registered attribute for class '{self.cls.__name__}'"
        raise ArgError(msg)

    def _check_values_list(self, att: str, values: list[Entity] | CollValue) -> bool:
        """Check if the values are a list of mapped Entity objects of the appropriate subclass for an attribute."""
        v = values
        if isinstance(values, CollValue):
            v = values.values()
        chk = [x.neoid is None for x in v]
        if True in chk:
            return False
        end_cls = self.cls.mapspec()["relationship"][att]["end_cls"]
        if isinstance(end_cls, str):
            end_cls = {end_cls}
        cls_set = tuple([eval(x) for x in end_cls])
        print(f"{cls_set=}")
        print(f"{v=}")
        chk = [isinstance(x, cls_set) for x in v]
        return True in chk
