"""
bento_meta.model
================

This module contains :class:`Model`, a class for managing data models housed
in the Bento Metamodel Database. Models are built from `bento_meta.Entity`
subclasses (see :mod:`bento_meta.objects`). A Model can be used with or 
without a Neo4j database connection.

"""
import re
import sys
sys.path.append("..")
from uuid import uuid4
from warnings import warn
import neo4j.graph
from bento_meta.mdb import MDB, make_nanoid
from bento_meta.object_map import ObjectMap
from bento_meta.entity import Entity, ArgError
from bento_meta.objects import (
    Node,
    Property,
    Edge,
    Term,
    ValueSet,
    Concept,
    Predicate,
    Origin,
    Tag,
)
# from pdb import set_trace


class Model(object):
    def __init__(self, handle=None, mdb=None):
        """Model constructor.

        :param str handle: A string name for the model. Corresponds to the model property in MDB database nodes.
        :param bento_meta.mdb.MDB mdb: An MDB object containing the db connection (see :class:`bento_meta.mdb.MDB`)
        """
        if not handle:
            raise ArgError("model requires arg 'handle' set")
        self.handle = handle
        self._mdb = None
        self.nodes = {}
        self.edges = {}  # keys are (edge.handle, src.handle, dst.handle) tuples
        self.props = {}  # keys are ({edge|node}.handle, prop.handle) tuples
        self.terms = {}  # keys are (term.handle, term.origin) tuples
        self.removed_entities = []

        if mdb:
            self.mdb = mdb

    @classmethod
    def versioning(cls, on=None):
        """Get or set versioning state.

        :param boolean on: True, apply versioning. False, do not.

        Note: this delegates to :meth:`Entity.versioning`.
        """
        if on is None:
            return Entity.versioning_on
        Entity.versioning_on = on
        return Entity.versioning_on

    @classmethod
    def set_version_count(cls, ct):
        """Set the integer version counter.

        :param int ct: Set version counter to this value.

        Note: this delegates to :meth:`Entity.set_version_count`.
        """
        Entity.set_version_count(ct)

    @property
    def drv(self):
        """Neo4j database driver from MDB object"""
        return self._mdb.driver if self._mdb else None

    @property
    def mdb(self):
        return self._mdb
    
    @mdb.setter
    def mdb(self, value):
        if isinstance(value, MDB):
            self._mdb = value
            for cls in (Node, Property, Edge, Term, ValueSet, Concept, Predicate, Origin, Tag):
                cls.object_map = ObjectMap(cls=cls, drv=value.driver)
        elif not value:
            self._mdb = None
            for cls in (Node, Property, Edge, Term, ValueSet, Concept, Origin, Tag):
                cls.object_map = None
        else:
            raise ArgError(
                "mdb= arg must be a bento_meta.mdb.MDB object"
            )

    def add_node(self, node=None):
        """Add a :class:`Node` to the model.

        :param Node node: A :class:`Node` instance, a :class:`neo4j.graph.Node`, or a dict

        The model attribute of ``node`` is set to `Model.handle`
        """
        if not node:
            raise ArgError("arg must be Node, dict, or graph.Node")
        if isinstance(node, (dict, neo4j.graph.Node)):
            node = Node(node)
        if not node.model:
            node.model = self.handle
        for p in node.props.values():
            self.add_prop(node, p)
        self.nodes[node.handle] = node
        return node

    def add_edge(self, edge=None):
        """Add an :class:`Edge` to the model.

        :param Edge edge: A :class:`Edge` instance, a :class:`neo4j.graph.Node`, or a dict

        The model attribute of ``edge`` is set to `Model.handle`
        """
        if not edge:
            raise ArgError("arg must be Edge, dict, or graph.Node")
        if isinstance(edge, (dict, neo4j.graph.Node)):
            edge = Edge(edge)
        if not edge.src or not edge.dst:
            raise ArgError("edge must have both src and dst set")
        if not edge.model:
            edge.model = self.handle
        if not self.contains(edge.src):
            warn("Edge source node not yet in model; adding it")
            self.add_node(edge.src)
        if not self.contains(edge.dst):
            warn("Edge destination node not yet in model; adding it")
            self.add_node(edge.dst)
        for p in edge.props.values():
            self.add_prop(edge, p)
        self.edges[edge.triplet] = edge
        return edge

    def add_prop(self, ent, prop=None):
        """Add a :class:`Property` to the model.

        :param Node|Edge ent: Attach ``prop`` to this entity
        :param Property prop: A :class:`Property` instance, a :class: `neo4j.graph.Node`, or a dict
        :param boolean reuse: If True, reuse existing property with same handle

        The model attribute of ``prop`` is set to `Model.handle`. Within a model,
        :class:`Property` entities are unique with respect to their
        handle (but can be reused). This method will look for an existing
        property within the model with the given handle, and add an item to
        Model.props pointing to it if found.
        """
        if not isinstance(ent, (Node, Edge)):
            raise ArgError("arg 1 must be Node or Edge")
        if not prop:
            raise ArgError("arg 2 must be Property, dict, or graph.Node")
        if isinstance(prop, (dict, neo4j.graph.Node)):
            prop = Property(prop)
        if not prop.model:
            prop.model = self.handle
        key = [ent.handle] if isinstance(ent, Node) else list(ent.triplet)
        key.append(prop.handle)
        ent.props[getattr(prop, type(prop).mapspec()["key"])] = prop
        if not tuple(key) in self.props:
            self.props[tuple(key)] = prop
        return prop

    def annotate(self, ent, term):
        """
        Associate a single :class:`Term` with an :class:`Entity`. This creates a Concept entity
        if needed and links both the Entity and the Term to the concept, in keeping with the MDB
        spec. It supports the Term key in MDF.
        :param Entity ent: :class:`Entity` object to annotate
        :param Term term: :class:`Term` object to describe the Entity
        """
        if not isinstance(ent, Entity):
            raise ArgError("arg1 must be Entity")
        if not isinstance(term, Term):
            raise ArgError("arg2 must be Term")
        if not ent.concept:
            ent.concept = Concept({"nanoid":make_nanoid()})
        term_key = term.handle if term.handle else term.value;
        if (term_key, term.origin_name) in ent.concept.terms:
            raise ValueError("Concept already represented by a Term with handle or value '{}'"
                             "and origin_name '{}'".format(term_key, term.origin_name))
        ent.concept.terms[(term_key, term.origin_name)] = term
        self.terms[(term_key, term.origin_name)] = term
        
    def add_terms(self, prop, *terms):
        """Add a list of :class:`Term` and/or strings to a :class:`Property` with a value domain of ``value_set``

        :param Property prop: :class:`Property` to modify
        :param list terms: A list of :class:`Term` instances and/or str

        :class:`Term` instances are created for strings; 
        `Term.value` and `Term.handle` is set to the string.
        """
        if not isinstance(prop, Property):
            raise ArgError("arg1 must be Property")
        if not re.match("value_set|enum", prop.value_domain):
            raise AttributeError(
                "Property value domain is not value_set or enum, can't add terms"
            )
        if not prop.value_set:
            warn("Creating ValueSet object for Property " + prop.handle)
            prop.value_set = ValueSet({"prop": prop, "_id": str(uuid4())})
            prop.value_set.handle = self.handle + prop.value_set._id[0:8]

        for t in terms:
            if isinstance(t, str):
                warn("Creating Term object for string '{term}'".format(term=t))
                t = Term({"handle":t, "value": t})
            elif not isinstance(t, Term):
                raise ArgError("encountered arg that was not a str or Term object")
            tm_key = t.handle if t.handle else t.value
            prop.value_set.terms[tm_key] = t
            self.terms[(tm_key, t.origin_name)] = t

    def rm_node(self, node):
        """Remove a :class:`Node` from the Model instance.

        :param Node node: Node to be removed

        Note: A node can't be removed if it is participating in an edge (i.e.,
        if the node is some edge's src or dst attribute)

        *Clarify what happens in the Model object, in the database when versioning
        is off, in the database when versioning is on*
        """
        if not isinstance(node, Node):
            raise ArgError("arg must be a Node object")
        if not self.contains(node):
            warn(
                "node '{node}' not contained in model '{model}'".format(
                    node=node.handle, model=self.handle
                )
            )
            return
        if self.edges_by_src(node) or self.edges_by_dst(node):
            raise ValueError(
                "can't remove node '{node}', it is participating in edges".format(
                    node=node.handle
                )
            )
        for p in node.props:
            try:
                del self.props[(node.handle, p.handle)]
            except:
                pass
        del self.nodes[node.handle]
        self.removed_entities.append(node)
        return node

    def rm_edge(self, edge):
        """Remove an :class:`Edge` instance from the Model instance.

        :param Edge edge: Edge to be removed

        *Clarify what happens in the Model object, in the database when versioning
        is off, in the database when versioning is on*
        """
        if not isinstance(edge, Edge):
            raise ArgError("arg must be an Edge object")
        if not self.contains(edge):
            warn(
                "edge '{edge}' not contained in model '{model}'".format(
                    edge=edge.triplet, model=self.handle
                )
            )
            return
        for p in edge.props:
            try:
                k = list(edge.triplet)
                k.append(p.handle)
                del self.props[tuple(k)]
            except:
                pass
        del self.edges[edge.triplet]
        edge.src = None
        edge.dst = None
        self.removed_entities.append(edge)
        return edge

    def rm_prop(self, prop):
        """Remove a :class:`Property` instance from the Model instance.

        :param Property prop: Property to be removed

        *Clarify what happens in the Model object, in the database when versioning
        is off, in the database when versioning is on*
        """
        if not isinstance(prop, Property):
            raise ArgError("arg must be a Property object")
        if not self.contains(prop):
            warn(
                "prop '{prop}' not contained in model '{model}'".format(
                    prop=prop.handle, model=self.handle
                )
            )
            return
        for okey in prop.belongs:
            owner = prop.belongs[okey]
            (i, att, key) = okey
            getattr(owner, att)[key] == None
            k = [owner.handle] if isinstance(owner, Node) else list(owner.triplet)
            k.append(key)
            del self.props[tuple(k)]
        self.removed_entities.append(prop)
        pass

    def rm_term(self, term):
        """Not implemented."""
        if not isinstance(term, Term):
            raise ArgError("arg must be a Term object")
        pass

    def assign_edge_end(self, edge=None, end=None, node=None):
        """Move the src or dst of an :class:`Edge` to a different :class:`Node`.

        :param Edge edge: Edge to manipulate
        :param str end: Edge end to change (src|dst)
        :param Node node: Node to be connected

        Note: Both ``node`` and ``edge`` must be present in the Model instance
        (via :meth:`add_node` and :meth:`add_edge`)
        """
        if not isinstance(edge, Edge):
            raise ArgError("edge= must an Edge object")
        if not isinstance(node, Node):
            raise ArgError("node= must a Node object")
        if end not in ["src", "dst"]:
            raise ArgError("end= must be one of 'src' or 'dst'")
        if not self.contains(edge) or not self.contains(node):
            warn("model must contain both edge and node")
            return
        del self.edges[edge.triplet]
        setattr(edge, end, node)
        self.edges[edge.triplet] = edge
        return edge

    def contains(self, ent):
        """Ask whether an entity is present in the Model instance.

        :param Entity ent: Entity in question

        Note: Only works on Nodes, Edges, and Properties
        """
        if not isinstance(ent, Entity):
            warn("argument is not an Entity subclass")
            return
        if isinstance(ent, Node):
            return ent in set(self.nodes.values())
        if isinstance(ent, Edge):
            return ent in set(self.edges.values())
        if isinstance(ent, Property):
            return ent in set(self.props.values())
        if isinstance(ent, Term):
            return ent in set(self.terms.values())
        pass

    def edges_in(self, node):
        """Get all :class:`Edge` that have a given :class:`Node` as their dst attribute

        :param Node node: The node
        :return: list of :class:`Edge`
        """
        if not isinstance(node, Node):
            raise ArgError("arg must be Node")
        return [self.edges[i] for i in self.edges if i[2] == node.handle]
        pass

    def edges_out(self, node):
        """Get all :class:`Edge` that have a given :class:`Node` as their src attribute

        :param Node node: The node
        :return: list of :class:`Edge`
        """
        if not isinstance(node, Node):
            raise ArgError("arg must be Node")
        return [self.edges[i] for i in self.edges if i[1] == node.handle]
        pass

    def edges_by(self, key, item):
        if key not in ["src", "dst", "type"]:
            raise ArgError("arg 'key' must be one of src|dst|type")
        if isinstance(item, Node):
            idx = 1 if key == "src" else 2
            return [self.edges[x] for x in self.edges if x[idx] == item.handle]
        else:
            return [self.edges[x] for x in self.edges if x[0] == item]

    def edges_by_src(self, node):
        """Get all :class:`Edge` that have a given :class:`Node` as their src attribute

        :param Node node: The node
        :return: list of :class:`Edge`
        """
        return self.edges_by("src", node)

    def edges_by_dst(self, node):
        """Get all :class:`Edge` that have a given :class:`Node` as their dst attribute

        :param Node node: The node
        :return: list of :class:`Edge`
        """
        return self.edges_by("dst", node)

    def edges_by_type(self, edge_handle):
        """Get all :class:`Edge` that have a given edge type (i.e., handle)

        :param str edge_handle: The edge type
        :return: list of :class:`Edge`
        """
        if not isinstance(edge_handle, str):
            raise ArgError("arg must be str")
        return self.edges_by("type", edge_handle)

    def dget(self, refresh=False):
        """Pull model from MDB into this Model instance, based on its handle

        Note: is a noop if `Model.mdb` is unset.
        """
        if not self.mdb:
            return
        if refresh:
            ObjectMap.clear_cache()
        with self.drv.session() as session:
            result = session.run(
                "match p = (s:node)<-[:has_src]-(r:relationship)-[:has_dst]->(d:node) "
                "where s.model=$hndl and r.model=$hndl and d.model=$hndl return p",
                {"hndl": self.handle},
            )
            for rec in result:
                (ns, nr, nd) = rec["p"].nodes
                ns = Node(ns)
                nr = Edge(nr)
                nd = Node(nd)
                ObjectMap.cache[ns.neoid] = ns
                ObjectMap.cache[nr.neoid] = nr
                ObjectMap.cache[nd.neoid] = nd
                nr.src = ns
                nr.dst = nd
                self.nodes[ns.handle] = ns
                self.nodes[nd.handle] = nd
                self.edges[nr.triplet] = nr

        with self.drv.session() as session:
            result = session.run(
                "match (n:node)-[:has_property]->(p:property) where n.model=$hndl and p.model=$hndl return id(n), p",
                {"hndl": self.handle},
            )
            for rec in result:
                n = ObjectMap.cache.get(rec["id(n)"])
                if n is None:
                    warn(
                        "node with id {nid} not yet retrieved".format(nid=rec["id(n)"])
                    )
                    continue
                p = Property(rec["p"])
                ObjectMap.cache[p.neoid] = p
                self.props[(n.handle, p.handle)] = p
                n.props[p.handle] = p
                p.dirty = -1
        with self.drv.session() as session:
            result = session.run(
                "match (r:relationship)-[:has_property]->(p:property) "
                "where r.model=$hndl and p.model=$hndl return id(r), p",
                {"hndl": self.handle},
            )
            for rec in result:
                e = ObjectMap.cache.get(rec["id(r)"])
                if e is None:
                    warn(
                        "relationship with id {rid} not yet retrieved".format(
                            rid=rec["id(r)"]
                        )
                    )
                    continue
                p = Property(rec["p"])
                ObjectMap.cache[p.neoid] = p
                k = list(e.triplet)
                k.append(p.handle)
                self.props[tuple(k)] = p
                e.props[p.handle] = p
                p.dirty = -1
        return self

    def dput(self):
        """Push this Model's objects to MDB.

        Note: is a noop if `Model.mdb` is unset.
        """
        if not self.mdb:
            return
        seen = {}

        def do_(obj):
            if id(obj) in seen:
                return
            seen[id(obj)] = 1
            if obj.dirty == 1:
                obj.dput()
            atts = [x for x in type(obj).attspec if type(obj).attspec[x] == "object"]
            for att in atts:
                ent = getattr(obj, att)
                if ent:
                    do_(ent)
            atts = [
                x for x in type(obj).attspec if type(obj).attspec[x] == "collection"
            ]
            for att in atts:
                ents = getattr(obj, att)
                if ents:
                    for ent in ents:
                        do_(ents[ent])

        for e in self.removed_entities:
            # detach
            with self.drv.session() as session:
                result = session.run(
                    "match (e)-[r]-() where id(e)=$eid delete r return id(e)",
                    {"eid": e.neoid},
                )
                for rec in result:
                    pass
        for e in self.nodes.values():
            do_(e)
        for e in self.edges.values():
            do_(e)
        for e in self.props.values():
            do_(e)
        return
