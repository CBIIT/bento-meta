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
* generates appropriate `Cypher <https://neo4j.com/docs/cypher-manual/current/>`_ queries to do gets and puts

One ObjectMap instance should be generated for each Entity subclass (see, e.g., 
:class:`bento_meta.model.Model`)

"""
import re
import sys
sys.path.append("..")
from neo4j import BoltDriver, Neo4jDriver
from bento_meta.entity import *
from bento_meta.objects import *
# from pdb import set_trace


class ObjectMap(object):
    cache = {}

    def __init__(self, *, cls=None, drv=None):
        if not cls:
            raise ArgError("arg cls= is required")
        self.cls = cls
        if drv:
            if isinstance(drv, (Neo4jDriver, BoltDriver)):
                self.drv = drv
            else:
                raise ArgError(
                    "drv= arg must be Neo4jDriver or BoltDriver (returned from GraphDatabase.driver())"
                )
        self.maps = {}

    @classmethod
    def clear_cache(cls):
        cls.cache = {}

    @classmethod
    def cls_by_label(cls, lbl):
        if not hasattr(cls, "_clsxlbl"):
            cls._clsxlbl = {}
            for o in (Node, Edge, Property, ValueSet, Term, Concept, Origin, Tag):
                cls._clsxlbl[o.mapspec()["label"]] = o
        return cls._clsxlbl.get(lbl)

    @classmethod
    def keys_by_cls_and_reln(cls, qcls, reln):
        if not hasattr(cls, "_keysxcls"):
            cls._keysxcls = {}
            for o in (Node, Edge, Property, ValueSet, Term, Concept, Predicate, Origin, Tag):
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
    def _quote_val(cls, value, single=None):  # double quote unless single is set
        if value is None:
            return
        if isinstance(value, (int, float)):
            return value  # no quote
        else:
            if single:
                return "'{val}'".format(val=value)  # quote
            else:
                return '"{val}"'.format(val=value)  # quote

    def get_by_id(self, obj, id, refresh=False):
        """Get an entity given an id attribute value (not the Neo4j id)"""
        neoid = None

        if self.drv is None:
            raise ArgError("get_by_id() requires Neo4j driver instance")

        with self.drv.session() as session:
            result = session.run(self.get_by_id_q(), {"id": id})
            rec = (
                result.single()
            )  # should be unique - this call will warn if there are more than one

            if rec is not None:
                neoid = rec["id(n)"]

        if neoid is not None:
            obj.neoid = neoid
            return self.get(obj, refresh=True)
        else:
            return

    def get_by_node_nanoid(self, obj, nanoid, refresh=False):
        """PROTOTYPE
        Get an entity given an id attribute value (not the Neo4j id)
        """

        neo4jid = None

        if not self.drv:
            raise ArgError("get_by_id() requires Neo4j driver instance")

        with self.drv.session() as session:
            result = session.run(self.get_by_node_nanoid_q(), {"nanoid": nanoid})
            rec = (
                result.single()
            )  # should be unique - this call will warn if there are more than one
            if rec is not None:
                neo4jid = rec["id(n)"]
           
        if neo4jid is None:
            obj.neoid = neo4jid
            return self.get(obj, refresh=True)
        else:
            return

    def get(self, obj, refresh=False):
        """Get the data for an object instance from the db and load the instance with it"""
        if not self.drv:
            raise ArgError("get() requires Neo4j driver instance")

        if refresh:
            pass
        elif (obj.neoid in ObjectMap.cache) and (ObjectMap.cache[obj.neoid].dirty >= 0):
            return obj

        with self.drv.session() as session:
            result = session.run(self.get_q(obj))
            rec = result.single()
            if not rec:
                raise RuntimeError(
                    "object with id {neoid} not found in db".format(neoid=obj.neoid)
                )

        if obj.neoid not in ObjectMap.cache:
            ObjectMap.cache[obj.neoid] = obj

        with self.drv.session() as session:
            for att in self.cls.mapspec()["relationship"]:
                result = session.run(self.get_attr_q(obj, att))
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
                        for l in rec["a"].labels:
                            c = ObjectMap.cls_by_label(l)
                            if c:
                                break
                        if not c:
                            raise RuntimeError(
                                "node labels {lbls} have no associated class in the object model".format(
                                    lbls=rec["a"].labels
                                )
                            )
                        o = c(rec["a"])
                        o.dirty = -1
                        ObjectMap.cache[o.neoid] = o
                        if not first_val:
                            first_val = o
                        values[getattr(o, type(o).mapspec()["key"])] = o
                if self.cls.attspec[att] == "object" and len(values) > 1:
                    warn(
                        "expected one node for attribute {att} on class {cls}, but got {n}; using first one".format(
                            att=att, cls=self.cls.__name__, n=len(values)
                        )
                    )
                if self.cls.attspec[att] == "object":
                    setattr(obj, att, first_val)
                elif self.cls.attspec[att] == "collection":
                    setattr(obj, att, values)
                else:
                    raise RuntimeError(
                        "attribute '{att}' has unknown attribute type '{atype}'".format(
                            att=att, atype=self.cls.attspec[att]
                        )
                    )

        obj.clear_removed_entities()
        obj.dirty = 0
        return obj

    def put(self, obj):
        """Put the object instance's attributes to the mapped data node in the database"""
        if not self.drv:
            raise ArgError("put() requires Neo4j driver instance")
            pass
        with self.drv.session() as session:
            result = None
            with session.begin_transaction() as tx:
                for qry in self.put_q(obj):
                    result = tx.run(qry)
                obj.neoid = result.single().value("id(n)")
                if obj.neoid is None:
                    raise RuntimeError(
                        "no neo4j id retrived on put for obj '{name}'".format(
                            name=getattr(obj, self.cls.mapspec()["key"])
                        )
                    )
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
                            result = tx.run(qry)
                        val.neoid = result.single().value("id(n)")
                        if val.neoid is None:
                            raise RuntimeError(
                                "no neo4j id retrived on put for obj '{name}'".format(
                                    name=val[type(val).mapspec()["key"]]
                                )
                            )
                        val.dirty = 1
                        ObjectMap.cache[val.neoid] = val
                    for qry in self.put_attr_q(obj, att, values):
                        tx.run(qry)
                    # drop removed entities here
                    while obj.removed_entities:
                        ent = obj.removed_entities.pop()
                        self.drop(obj, *ent, tx)
        ObjectMap.cache[obj.neoid] = obj
        obj.dirty = 0
        return obj

    def rm(self, obj, force=False):
        """'Delete' the object's mapped node from the database"""
        if not self.drv:
            raise ArgError("rm() requires Neo4j driver instance")
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        with self.drv.session() as session:
            result = session.run(self.rm_q(obj, force))
            s = result.single()
            if s is None:
                warn("rm() - corresponding db node not found")
            else:
                return s.value()

    def add(self, obj, att, tgt):
        """Create a link between an object instance and a target object in the database.
        This represents adding an object-valued attribute to the object.
        """
        if not self.drv:
            raise ArgError("add() requires Neo4j driver instance")
        with self.drv.session() as session:
            for qry in self.put_attr_q(obj, att, tgt):
                result = session.run(qry)
            tgt_id = result.single().value()
            if tgt_id is None:
                warn("add() - corresponding db node not found")
            return tgt_id

    def drop(self, obj, att, tgt, tx=None):
        """Remove an existing link between an object instance and a target object in the database.
        This represents dropping an object-valued attribute from the object.
        """
        if not self.drv:
            raise ArgError("rm() requires Neo4j driver instance")
        # if the tgt is not in the database, then dropping it is a no-op:
        if not tgt.neoid:
            return

        if tx:
            result = None
            for qry in self.rm_attr_q(obj, att, tgt):
                result = tx.run(qry)
            s = result.single()
            if s is None:
                warn("drop() - corresponding target db node not found")
            else:
                return s.value()
        else:
            with self.drv.session() as session:
                result = None
                for qry in self.rm_attr_q(obj, att, tgt):
                    result = session.run(qry)
                s = result.single()
                if s is None:
                    warn("drop() - corresponding target db node not found")
                else:
                    return s.value()

    def get_owners(self, obj):
        """Get the nodes which are linked to the object instance (the owners of the object)"""
        if not self.drv:
            raise ArgError("get_owners() requires Neo4j driver instance")
        ret = []
        with self.drv.session() as session:
            result = session.run(self.get_owners_q(obj))
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

    def get_q(self, obj):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        return "MATCH (n:{lbl}) WHERE id(n)={neoid} RETURN n,id(n)".format(
            lbl=self.cls.mapspec()["label"], neoid=obj.neoid
        )

    def get_by_id_q(self):
        return "MATCH (n:{lbl}) WHERE id(n)=$id and n._to IS NULL RETURN id(n)".format(
            lbl=self.cls.mapspec()["label"]
        )

    def get_by_node_nanoid_q(self):
        """PROTOTYPE"""
        return "MATCH (n:node) WHERE n.nanoid=$nanoid and n._to is NULL RETURN id(n)"

    def get_attr_q(self, obj, att):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            return ""
        label = self.cls.mapspec()["label"]
        if att in self.cls.mapspec()["property"]:
            pr = self.cls.mapspec()["property"][att]
            return "MATCH (n:{lbl}) WHERE id(n)={neoid} RETURN n.{pr}".format(
                lbl=label, neoid=obj.neoid, pr=pr
            )
        elif att in self.cls.mapspec()["relationship"]:
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[\2]-\3", spec["rel"])
            if len(end_lbls) == 1:
                qry = "MATCH (n:{llbl}){rel}(a:{rlbl}) WHERE id(n)={neoid} RETURN a".format(
                    neoid=obj.neoid, llbl=label, rel=rel, rlbl=end_lbls[0]
                )
                if self.cls.attspec[att] == "object":
                    qry += " LIMIT 1"
                return qry
            else:  # multiple end classes possible
                cond = []
                for l in end_lbls:
                    cond.append("'{lbl}' IN labels(a)".format(lbl=l))
                cond = " OR ".join(cond)
                return "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND ({cond}) RETURN a".format(
                    lbl=label, rel=rel, neoid=obj.neoid, cond=cond
                )
        else:
            raise ArgError(
                "'{att}' is not a registered attribute for class '{cls}'".format(
                    att=att, cls=self.cls.__name__
                )
            )

    def get_owners_q(self, obj):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        label = self.cls.mapspec()["label"]
        return "MATCH (n:{lbl})<-[r]-(a) WHERE id(n)={neoid} RETURN TYPE(r) as reln, a".format(
            neoid=obj.neoid, lbl=label
        )

    def put_q(self, obj):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        props = {}
        null_props = []
        for pr in self.cls.mapspec()["property"]:
            if getattr(obj, pr) is None:
                null_props.append(self.cls.mapspec()["property"][pr])
            else:
                props[self.cls.mapspec()["property"][pr]] = getattr(obj, pr)
        stmts = []
        if obj.neoid is not None:
            set_clause = []
            for pr in props:
                set_clause.append(
                    "n.{pr}={val}".format(pr=pr, val=ObjectMap._quote_val(props[pr]))
                )
            set_clause = "SET " + ",".join(set_clause)
            stmts.append(
                "MATCH (n:{lbl}) WHERE id(n)={neoid} {set_clause} RETURN n,id(n)".format(
                    lbl=self.cls.mapspec()["label"],
                    neoid=obj.neoid,
                    set_clause=set_clause,
                )
            )
            for pr in null_props:
                stmts.append(
                    "MATCH (n:{lbl}) WHERE id(n)={neoid} REMOVE n.{pr} RETURN n,id(n)".format(
                        lbl=self.cls.mapspec()["label"], neoid=obj.neoid, pr=pr
                    )
                )
            return stmts
        else:
            spec = []
            for pr in props:
                spec.append(
                    "{pr}:{val}".format(pr=pr, val=ObjectMap._quote_val(props[pr]))
                )
            spec = ",".join(spec)
            return [
                "CREATE (n:%s {%s}) RETURN n,id(n)"
                % (self.cls.mapspec()["label"], spec)
            ]

    def put_attr_q(self, obj, att, values):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        if not isinstance(values, (Entity, list, CollValue)):
            raise ArgError(
                "'values' must be a list of values suitable for the attribute"
            )
        if isinstance(values, CollValue):
            values = values.values()
        elif isinstance(values, Entity):
            values = [values]
        if att in self.cls.mapspec()["property"]:
            return "MATCH (n:{lbl}) WHERE id(n)={neoid} SET {pr}={val} RETURN id(n)".format(
                lbl=self.cls.mapspec()["label"],
                neoid=obj.neoid,
                pr=self.cls.mapspec()["property"][att],
                val=ObjectMap._quote_val(values[0]),
            )
        elif att in self.cls.mapspec()["relationship"]:
            if not self._check_values_list(att, values):
                raise ArgError(
                    "'values' must be a list of mapped Entity objects of "
                    "the appropriate subclass for attribute '{att}'".format(
                        att=att
                    )
                )
            stmts = []
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[\2]-\3", spec["rel"])
            cond = []
            for l in end_lbls:
                cond.append("'{lbl}' IN labels(a)".format(lbl=l))
            cond = " OR ".join(cond)
            for avalue in values:
                if len(end_lbls) == 1:
                    stmts.append(
                        "MATCH (n:{lbl}),(a:{albl}) WHERE id(n)={neoid} AND id(a)={aneoid} "
                        "MERGE (n){rel}(a) RETURN id(a)".format(
                            lbl=self.cls.mapspec()["label"],
                            albl=end_lbls[0],
                            neoid=obj.neoid,
                            aneoid=avalue.neoid,
                            rel=rel,
                        )
                    )
                else:
                    stmts.append(
                        "MATCH (n:{lbl}),(a) WHERE id(n)={neoid} AND id(a)={aneoid} AND ({cond}) "
                        "MERGE (n){rel}(a) RETURN id(a)".format(
                            lbl=self.cls.mapspec()["label"],
                            cond=cond,
                            neoid=obj.neoid,
                            aneoid=avalue.neoid,
                            rel=rel,
                        )
                    )
            return stmts

        else:
            raise ArgError(
                "'{att}' is not a registered attribute for class '{cls}'".format(
                    att=att, cls=self.cls.__name__
                )
            )

    def rm_q(self, obj, detach=False):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        dlt = "DETACH DELETE n" if detach else "DELETE n"
        qry = "MATCH (n:{lbl}) WHERE id(n)={neoid} ".format(
            lbl=self.cls.mapspec()["label"], neoid=obj.neoid
        )
        return qry + dlt
        pass

    def rm_attr_q(self, obj, att, values=None):
        if not isinstance(obj, self.cls):
            raise ArgError(
                "arg1 must be object of class {cls}".format(cls=self.cls.__name__)
            )
        if obj.neoid is None:
            raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
        if values and not isinstance(values, list):
            values = [values]
        if att in self.cls.mapspec()["property"]:
            return "MATCH (n:{lbl}) WHERE id(n)={neoid} REMOVE n.{att} RETURN id(n)".format(
                lbl=self.cls.mapspec()["label"], neoid=obj.neoid, att=att
            )
        elif att in self.cls.mapspec()["relationship"]:
            many = self.cls.attspec[att] == "collection"
            spec = self.cls.mapspec()["relationship"][att]
            end_cls = spec["end_cls"]
            if isinstance(end_cls, str):
                end_cls = {end_cls}
            end_lbls = [eval(x).mapspec()["label"] for x in end_cls]
            cond = []
            for l in end_lbls:
                cond.append("'{lbl}' IN labels(a)".format(lbl=l))
            cond = " OR ".join(cond)
            rel = re.sub("^([^:]?)(:[a-zA-Z0-9_]+)(.*)$", r"\1-[r\2]-\3", spec["rel"])
            if values[0] == ":all":
                if len(end_lbls) == 1:
                    return "MATCH (n:{lbl}){rel}(a:{albl}) WHERE id(n)={neoid} DELETE r RETURN id(n),id(a)".format(
                        lbl=self.cls.mapspec()["label"],
                        albl=end_lbls[0],
                        rel=rel,
                        neoid=obj.neoid,
                    )
                else:
                    return "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND ({cond}) DELETE r RETURN id(n)".format(
                        lbl=self.cls.mapspec()["label"],
                        cond=cond,
                        neoid=obj.neoid,
                        rel=rel,
                    )
            else:
                stmts = []

                if not self._check_values_list(att, values):
                    raise ArgError(
                        "'values' must be a list of mapped Entity objects of the "
                        "appropriate subclass for attribute '{att}'".format(att=att)
                    )
                for val in values:
                    qry = ""
                    if len(end_lbls) == 1:
                        qry = "MATCH (n:{lbl}){rel}(a:{albl}) WHERE id(n)={neoid} AND id(a)={aneoid} " \
                              "DELETE r RETURN id(n),id(a)".format(
                                  lbl=self.cls.mapspec()["label"],
                                  albl=end_lbls[0],
                                  neoid=obj.neoid,
                                  aneoid=val.neoid,
                                  rel=rel)
                    else:
                        qry = "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND id(a)={aneoid} AND ({cond}) " \
                              "DELETE r RETURN id(n),id(a)".format(
                                  lbl=self.cls.mapspec()["label"],
                                  neoid=obj.neoid,
                                  aneoid=val.neoid,
                                  cond=cond,
                                  rel=rel)
                    stmts.append(qry)
                return stmts
        else:
            raise ArgError(
                "'{att}' is not a registered attribute for class '{cls}'".format(
                    att=att, cls=self.cls.__name__
                )
            )

    def _check_values_list(self, att, values):
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
        chk = [isinstance(x, cls_set) for x in v]
        if True in chk:
            return True
        return False
