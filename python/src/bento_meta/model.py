"""
bento_meta.model
================

This module contains :class:`Model`, a class for managing data models housed
in the Bento Metamodel Database. Models are built from `bento_meta.Entity`
subclasses (see :mod:`bento_meta.objects`). A Model can be used with or
without a Neo4j database connection.

"""

from __future__ import annotations

import re
import sys

sys.path.append("..")
import builtins
import contextlib
from uuid import uuid4
from warnings import warn

import neo4j.graph

from bento_meta.entity import ArgError, Entity
from bento_meta.mdb import MDB, make_nanoid
from bento_meta.object_map import ObjectMap
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


class Model:
    """Model class for managing data models housed in the Bento Metamodel Database."""

    def __init__(
        self,
        handle: str | None = None,
        version: str | None = None,
        uri: str | None = None,
        mdb: MDB | None = None,
    ) -> None:
        """
        Model constructor.

        Args:
            handle: A string name for the model. Corresponds to the model property
                in MDB database nodes.
            version: Version string for the model.
            uri: URI for the model.
            mdb: An MDB object containing the db connection.
        """
        if not handle:
            msg = "model requires arg 'handle' set"
            raise ArgError(msg)
        self.handle = handle
        self.version = version
        self.uri = uri
        self.repository = None
        self._mdb: MDB | None = None
        self.nodes: dict[str, Node] = {}
        self.edges: dict[
            tuple[str, str, str],
            Edge,
        ] = {}  # keys are (edge.handle, src.handle, dst.handle) tuples
        self.props: dict[
            tuple[str, str],
            Property,
        ] = {}  # keys are ({edge|node}.handle, prop.handle) tuples
        self.terms: dict[
            tuple[str, str, str | None, str | None],
            Term,
        ] = {}  # keys are (term.handle, term.origin_name, term.origin_id, term.origin_version) tuples
        self.removed_entities: list[Entity] = []

        if mdb:
            self.mdb = mdb

    @property
    def drv(self) -> neo4j.Driver | None:
        """Neo4j database driver from MDB object."""
        return self._mdb.driver if self._mdb else None

    @property
    def mdb(self) -> MDB | None:
        """MDB object containing the db connection."""
        return self._mdb

    @mdb.setter
    def mdb(self, value: MDB | None) -> None:
        """Set the MDB object containing the db connection."""
        if isinstance(value, MDB):
            self._mdb = value
            for cls in (
                Node,
                Property,
                Edge,
                Term,
                ValueSet,
                Concept,
                Predicate,
                Origin,
                Tag,
            ):
                cls.object_map = ObjectMap(cls=cls, drv=value.driver)
        elif not value:
            self._mdb = None
            for cls in (Node, Property, Edge, Term, ValueSet, Concept, Origin, Tag):
                cls.object_map = None
        else:
            msg = "mdb= arg must be a bento_meta.mdb.MDB object"
            raise ArgError(msg)

    def add_node(self, node: Node | dict | neo4j.graph.Node | None = None) -> Node:
        """
        Add a Node to the model.

        The model attribute of node is set to Model.handle.

        Args:
            node: A Node instance, a neo4j.graph.Node, or a dict.

        Returns:
            The added Node instance.
        """
        if not node:
            msg = "arg must be Node, dict, or graph.Node"
            raise ArgError(msg)
        if isinstance(node, (dict, neo4j.graph.Node)):
            node = Node(node)
        if not node.model:
            node.model = self.handle
        for p in node.props.values():
            self.add_prop(node, p)
        self.nodes[node.handle] = node
        return node

    def add_edge(self, edge: Edge | dict | neo4j.graph.Node | None = None) -> Edge:
        """
        Add an Edge to the model.

        The model attribute of edge is set to Model.handle.

        Args:
            edge: An Edge instance, a neo4j.graph.Node, or a dict.

        Returns:
            The added Edge instance.
        """
        if not edge:
            msg = "arg must be Edge, dict, or graph.Node"
            raise ArgError(msg)
        if isinstance(edge, (dict, neo4j.graph.Node)):
            edge = Edge(edge)
        if not edge.src or not edge.dst:
            msg = "edge must have both src and dst set"
            raise ArgError(msg)
        if not edge.model:
            edge.model = self.handle
        if not self.contains(edge.src):
            warn("Edge source node not yet in model; adding it", stacklevel=2)
            self.add_node(edge.src)
        if not self.contains(edge.dst):
            warn("Edge destination node not yet in model; adding it", stacklevel=2)
            self.add_node(edge.dst)
        for p in edge.props.values():
            self.add_prop(edge, p)
        self.edges[edge.triplet] = edge
        return edge

    def add_prop(
        self,
        ent: Node | Edge,
        prop: Property | dict | neo4j.graph.Node | None = None,
        *,
        reuse: bool = False,
    ) -> Property:
        """
        Add a Property to the model.

        The model attribute of prop is set to Model.handle. Within a model,
        Property entities are unique with respect to their handle (but can be reused).
        This method will look for an existing property within the model with the given
        handle, and add an item to Model.props pointing to it if found.

        Args:
            ent: Attach prop to this entity (Node or Edge).
            prop: A Property instance, a neo4j.graph.Node, or a dict.
            reuse: If True, reuse existing property with same handle.

        Returns:
            The added Property instance.
        """
        if not isinstance(ent, (Node, Edge)):
            msg = "arg 1 must be Node or Edge"
            raise ArgError(msg)
        if not prop:
            msg = "arg 2 must be Property, dict, or graph.Node"
            raise ArgError(msg)
        if isinstance(prop, (dict, neo4j.graph.Node)):
            prop = Property(prop)
        if not prop.model:
            prop.model = self.handle
        if prop.value_domain == "value_set" and not prop.value_set:
            warn(
                "(add_prop) Creating ValueSet object for Property " + prop.handle,
                stacklevel=2,
            )
            prop.value_set = ValueSet({"prop": prop, "_id": str(uuid4())})
            prop.value_set.handle = self.handle + prop.value_set._id[0:8]  # noqa: SLF001
        key = [ent.handle] if isinstance(ent, Node) else list(ent.triplet)
        key.append(prop.handle)
        ent.props[getattr(prop, type(prop).mapspec()["key"])] = prop
        if tuple(key) not in self.props:
            self.props[tuple(key)] = prop
        return prop

    def annotate(self, ent: Entity, term: Term) -> None:
        """
        Associate a single Term with an Entity.

        This creates a Concept entity if needed and links both the Entity and the Term
        to the concept, in keeping with the MDB spec. It supports the Term key in MDF.

        Args:
            ent: Entity object to annotate.
            term: Term object to describe the Entity.
        """
        if not isinstance(ent, Entity):
            msg = "arg1 must be Entity"
            raise ArgError(msg)
        if not isinstance(term, Term):
            msg = "arg2 must be Term"
            raise ArgError(msg)
        if not ent.concept:
            ent.concept = Concept({"nanoid": make_nanoid()})
        term_key = term.handle if term.handle else term.value
        full_term_key = (
            term_key,
            term.origin_name,
            term.origin_id,
            term.origin_version,
        )
        if full_term_key in ent.concept.terms:
            msg = (
                "Concept already represented by a Term with handle or value "
                f"'{term_key}', origin_name '{term.origin_name}', origin_id '{term.origin_id}', "
                f"and origin_version '{term.origin_version}'"
            )
            raise ValueError(msg)
        ent.concept.terms[full_term_key] = term
        self.terms[full_term_key] = term

    def add_terms(self, prop: Property, *terms: list[Term | str]) -> None:
        """
        Add a list of Term and/or strings to a Property.

        Property must have a value domain of value_set or enum.
        Term instances are created for strings; Term.value and Term.handle
        is set to the string.

        Args:
            prop: Property to modify.
            terms: A list of Term instances and/or str.
        """
        if not isinstance(prop, Property):
            msg = "arg1 must be Property"
            raise ArgError(msg)
        if not re.match("value_set|enum", prop.value_domain):
            msg = "Property value domain is not value_set or enum, can't add terms"
            raise AttributeError(msg)
        if not prop.value_set:
            warn(
                "(add_terms) Creating ValueSet object for Property " + prop.handle,
                stacklevel=2,
            )
            prop.value_set = ValueSet({"prop": prop, "_id": str(uuid4())})
            prop.value_set.handle = self.handle + prop.value_set._id[0:8]  # noqa: SLF001

        for item in terms:
            if isinstance(item, str):
                warn(f"Creating Term object for string '{item}'", stacklevel=2)
                term = Term({"handle": item, "value": item})
            elif isinstance(item, Term):
                term = item
            else:
                msg = "encountered arg that was not a str or Term object"
                raise ArgError(msg)
            tm_key = term.handle if term.handle else term.value
            prop.value_set.terms[tm_key] = term
            full_term_key = (
                tm_key,
                term.origin_name,
                term.origin_id,
                term.origin_version,
            )
            self.terms[full_term_key] = term

    def rm_node(self, node: Node) -> Node | None:
        """
        Remove a Node from the Model instance.

        Note: A node can't be removed if it is participating in an edge (i.e.,
        if the node is some edge's src or dst attribute).

        Args:
            node: Node to be removed.

        Returns:
            The removed Node, or None if not found.
        """
        if not isinstance(node, Node):
            msg = "arg must be a Node object"
            raise ArgError(msg)
        if not self.contains(node):
            warn(
                f"node '{node.handle}' not contained in model '{self.handle}'",
                stacklevel=2,
            )
            return None
        if self.edges_by_src(node) or self.edges_by_dst(node):
            msg = f"can't remove node '{node.handle}', it is participating in edges"
            raise ValueError(msg)
        for p in node.props:
            with contextlib.suppress(builtins.BaseException):
                del self.props[(node.handle, p.handle)]
        del self.nodes[node.handle]
        self.removed_entities.append(node)
        return node

    def rm_edge(self, edge: Edge) -> Edge | None:
        """
        Remove an Edge instance from the Model instance.

        Args:
            edge: Edge to be removed.

        Returns:
            The removed Edge, or None if not found.
        """
        if not isinstance(edge, Edge):
            msg = "arg must be an Edge object"
            raise ArgError(msg)
        if not self.contains(edge):
            warn(
                f"edge '{edge.triplet}' not contained in model '{self.handle}'",
                stacklevel=2,
            )
            return None
        for p in edge.props:
            with contextlib.suppress(builtins.BaseException):
                k = list(edge.triplet)
                k.append(p.handle)
                del self.props[tuple(k)]
        del self.edges[edge.triplet]
        edge.src = None
        edge.dst = None
        self.removed_entities.append(edge)
        return edge

    def rm_prop(self, prop: Property) -> Property | None:
        """
        Remove a Property instance from the Model instance.

        Args:
            prop: Property to be removed.

        Returns:
            The removed Property, or None if not found.
        """
        if not isinstance(prop, Property):
            msg = "arg must be a Property object"
            raise ArgError(msg)
        if not self.contains(prop):
            warn(
                f"prop '{prop.handle}' not contained in model '{self.handle}'",
                stacklevel=2,
            )
            return
        for okey in prop.belongs:
            owner = prop.belongs[okey]
            (i, att, key) = okey
            del getattr(owner, att)[key]
            k = [owner.handle] if isinstance(owner, Node) else list(owner.triplet)
            k.append(key)
            del self.props[tuple(k)]
        self.removed_entities.append(prop)

    def rm_term(self, term: Term) -> None:
        """Not implemented."""
        if not isinstance(term, Term):
            msg = "arg must be a Term object"
            raise ArgError(msg)

    def assign_edge_end(
        self,
        edge: Edge | None = None,
        end: str | None = None,
        node: Node | None = None,
    ) -> Edge | None:
        """
        Move the src or dst of an Edge to a different Node.

        Note: Both node and edge must be present in the Model instance
        (via add_node and add_edge).

        Args:
            edge: Edge to manipulate.
            end: Edge end to change (src|dst).
            node: Node to be connected.

        Returns:
            The modified Edge, or None if operation failed.
        """
        if not isinstance(edge, Edge):
            msg = "edge= must an Edge object"
            raise ArgError(msg)
        if not isinstance(node, Node):
            msg = "node= must a Node object"
            raise ArgError(msg)
        if end not in ["src", "dst"]:
            msg = "end= must be one of 'src' or 'dst'"
            raise ArgError(msg)
        if not self.contains(edge) or not self.contains(node):
            warn("model must contain both edge and node", stacklevel=2)
            return None
        del self.edges[edge.triplet]
        setattr(edge, end, node)
        self.edges[edge.triplet] = edge
        return edge

    def contains(self, ent: Entity) -> bool | None:
        """
        Ask whether an entity is present in the Model instance.

        Note: Only works on Nodes, Edges, and Properties.

        Args:
            ent: Entity in question.

        Returns:
            True if entity is in model, False otherwise, None if entity type not supported.
        """
        if not isinstance(ent, Entity):
            warn("argument is not an Entity subclass", stacklevel=2)
            return None
        if isinstance(ent, Node):
            return ent in set(self.nodes.values())
        if isinstance(ent, Edge):
            return ent in set(self.edges.values())
        if isinstance(ent, Property):
            return ent in set(self.props.values())
        if isinstance(ent, Term):
            return ent in set(self.terms.values())
        return None

    def edges_in(self, node: Node) -> list[Edge]:
        """
        Get all Edge that have a given Node as their dst attribute.

        Args:
            node: The node.

        Returns:
            List of Edge instances.
        """
        if not isinstance(node, Node):
            msg = "arg must be Node"
            raise ArgError(msg)
        return [self.edges[i] for i in self.edges if i[2] == node.handle]

    def edges_out(self, node: Node) -> list[Edge]:
        """
        Get all Edge that have a given Node as their src attribute.

        Args:
            node: The node.

        Returns:
            List of Edge instances.
        """
        if not isinstance(node, Node):
            msg = "arg must be Node"
            raise ArgError(msg)
        return [self.edges[i] for i in self.edges if i[1] == node.handle]

    def edges_by(self, key: str, item: Node | str) -> list[Edge]:
        """
        Get all Edge that have a given Node as their src or dst or Edge handle as their type attribute.

        Args:
            key: The attribute to search on.
            item: The node or edge handle to search for.

        Returns:
            List of Edge instances.
        """
        if key not in ["src", "dst", "type"]:
            msg = "arg 'key' must be one of src|dst|type"
            raise ArgError(msg)
        if isinstance(item, Node):
            idx = 1 if key == "src" else 2
            return [self.edges[x] for x in self.edges if x[idx] == item.handle]
        return [self.edges[x] for x in self.edges if x[0] == item]

    def edges_by_src(self, node: Node) -> list[Edge]:
        """
        Get all Edge that have a given Node as their src attribute.

        Args:
            node: The node.

        Returns:
            List of Edge instances.
        """
        return self.edges_by("src", node)

    def edges_by_dst(self, node: Node) -> list[Edge]:
        """
        Get all Edge that have a given Node as their dst attribute.

        Args:
            node: The node.

        Returns:
            List of Edge instances.
        """
        return self.edges_by("dst", node)

    def edges_by_type(self, edge_handle: str) -> list[Edge]:
        """
        Get all Edge that have a given edge type (i.e., handle).

        Args:
            edge_handle: The edge type.

        Returns:
            List of Edge instances.
        """
        if not isinstance(edge_handle, str):
            msg = "arg must be str"
            raise ArgError(msg)
        return self.edges_by("type", edge_handle)

    def dget(self, *, refresh: bool = False) -> Model | None:
        """
        Pull model from MDB into this Model instance, based on its handle.

        Note: is a noop if Model.mdb is unset.

        Args:
            refresh: If True, clear cache before retrieving.

        Returns:
            The Model instance, or None if mdb is not set.
        """
        if not self.mdb or self.drv is None:
            return None
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
                (
                    "match (n:node)-[:has_property]->(p:property) where n.model=$hndl "
                    "and p.model=$hndl return id(n), p"
                ),
                {"hndl": self.handle},
            )
            for rec in result:
                n = ObjectMap.cache.get(rec["id(n)"])
                if n is None:
                    warn(
                        "node with id {nid} not yet retrieved".format(nid=rec["id(n)"]),
                        stacklevel=2,
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
                            rid=rec["id(r)"],
                        ),
                        stacklevel=2,
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

    def dput(self) -> None:
        """
        Push this Model's objects to MDB.

        Note: is a noop if Model.mdb is unset.
        """
        if not self.mdb or self.drv is None:
            return
        seen = {}

        def do_(obj: Entity) -> None:
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
                session.run(
                    "match (e)-[r]-() where id(e)=$eid delete r return id(e)",
                    {"eid": e.neoid},
                ).consume()
        for e in self.nodes.values():
            do_(e)
        for e in self.edges.values():
            do_(e)
        for e in self.props.values():
            do_(e)
        return
