"""
bento_meta.mdb
==============

This module contains :class:`MDB`, with machinery for efficiently
querying a Neo4j instance of a Metamodel Database.

The constructor queries the database for registered models.
The attribute models : Dict contains model handles (names) as keys,
and a list of version strings as values.
The attribute latest_version : Dict contains model handles as keys
and the version string tagged "is_latest" as values.
"""

from __future__ import annotations

import os
import re
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    TypeVar,
    cast,
)
from warnings import warn

from nanoid import generate as nanoid_generate
from neo4j import Driver, GraphDatabase, ManagedTransaction, Record
from typing_extensions import LiteralString

if TYPE_CHECKING:
    from collections.abc import Callable

# Type variables for proper decorator typing
P = ParamSpec("P")
T = TypeVar("T")


# Decorator functions to produce executed transactions based on an
# underlying query/param function:
def read_txn(
    func: Callable[Concatenate[MDB, P], tuple[str, dict[str, Any] | None]],
) -> Callable[Concatenate[MDB, P], list[Record]]:
    """
    Decorate a query function to run a read transaction based on its query.

    Query function should return a tuple (qry_string, param_dict).

    Args:
        func: The query function to decorate.

    Returns:
        Decorated function that returns list of driver Records.
    """

    @wraps(func)
    def rd(self: MDB, *args: P.args, **kwargs: P.kwargs) -> list[Record]:
        def txn_q(tx: ManagedTransaction) -> list[Record]:
            (qry, parms) = func(self, *args, **kwargs)
            result = tx.run(cast("LiteralString", qry), parameters=parms)
            return list(result)

        with self.driver.session() as session:
            return session.execute_read(txn_q)

    return rd


def read_txn_value(
    func: Callable[Concatenate[MDB, P], tuple[str, dict[str, Any] | None, str]],
) -> Callable[Concatenate[MDB, P], list[Any]]:
    """
    Decorate a query function to run a read transaction based on its query.

    Query function should return a tuple (qry_string, param_dict, values_key).

    Args:
        func: The query function to decorate.

    Returns:
        Decorated function that returns list of values for key specified by query function.
    """

    @wraps(func)
    def rd(self: MDB, *args: P.args, **kwargs: P.kwargs) -> list[Any]:
        def txn_q(tx: ManagedTransaction) -> list[Any]:
            (qry, parms, values_key) = func(self, *args, **kwargs)
            result = tx.run(cast("LiteralString", qry), parameters=parms)
            return result.value(values_key)

        with self.driver.session() as session:
            return session.execute_read(txn_q)

    return rd


def read_txn_data(
    func: Callable[Concatenate[MDB, P], tuple[str, dict[str, Any] | None]],
) -> Callable[Concatenate[MDB, P], list[dict[str, Any]] | None]:
    """
    Decorate a query function to run a read transaction based on its query.

    Query function should return a tuple (qry_string, param_dict).

    Args:
        func: The query function to decorate.

    Returns:
        Decorated function that returns records as a list of simple dicts.
    """

    @wraps(func)
    def rd(self: MDB, *args: P.args, **kwargs: P.kwargs) -> list[dict[str, Any]] | None:
        (qry, parms) = func(self, *args, **kwargs)

        def txn_q(tx: ManagedTransaction) -> list[dict[str, Any]]:
            result = tx.run(cast("LiteralString", qry), parameters=parms)
            return result.data()

        with self.driver.session() as session:
            result = session.execute_read(txn_q)
            if len(result):
                return result
            return None

    return rd


class MDB:
    """A class representing a Metamodel Database."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        """
        Create an MDB object, with a connection to a Neo4j instance of a metamodel database.

        Args:
            uri: The Bolt protocol endpoint to the Neo4j instance.
                Defaults to NEO4J_MDB_URI env variable.
            user: Username for Neo4j access.
                Defaults to NEO4J_MDB_USER env variable.
            password: Password for user.
                Defaults to NEO4J_MDB_PASS env variable.
        """
        self.uri = uri or os.environ.get("NEO4J_MDB_URI")
        self.user = user or os.environ.get("NEO4J_MDB_USER")
        self.password = password or os.environ.get("NEO4J_MDB_PASS")
        self.driver: Driver | None = None
        self.models: dict[str, list[str]] = {}
        self.latest_version: dict[str, str | None] = {}
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        except Exception as e:
            warn(f"MDB not connected: {e}", stacklevel=2)
        try:
            # query DB and cache the models and their versions in the MDB object
            info = self.get_model_info()
            if not info or len(info) == 0:
                msg = "No Model nodes found"
                raise RuntimeError(msg)
            for m in info:
                if self.models.get(m["handle"]):
                    self.models[m["handle"]].append(m["version"])
                else:
                    self.models[m["handle"]] = [m["version"]]
                if m["is_latest"] and not self.latest_version.get(m["handle"]):
                    self.latest_version[m["handle"]] = m["version"]
            for hdl in self.models:
                if not self.latest_version.get(hdl):
                    if len(self.models[hdl]) == 1:  # only one version
                        self.latest_version[hdl] = self.models[hdl][0] or "unversioned"
                    else:
                        self.latest_version[hdl] = None
        except Exception as e:
            # raise RuntimeError
            warn(f"Database doesn't look like an MDB: {e}", stacklevel=2)
        self._txfns = {}

    def close(self) -> None:
        """Close the driver connection."""
        if self.driver:
            self.driver.close()

    def register_txfn(self, name: str, fn: Callable) -> None:
        """
        Register a transaction function with the class for later use.

        See https://neo4j.com/docs/api/python-driver/current/api.html#managed-transactions-transaction-functions

        Args:
            name: Name to register the function under.
            fn: The transaction function to register.
        """
        self._txfns[name] = fn

    # def run_txfn(self, name, *args, **kwargs):

    @read_txn_value
    def get_model_info(self) -> tuple[str, None, str]:
        """Get models, versions, and latest versions from MDB Model nodes."""
        return ("match (m:model) return m", None, "m")

    def get_model_handles(self) -> list[str]:
        """
        Return a simple list of model handles available.

        Queries Model nodes (not model properties in Entity nodes).

        Returns:
            List of model handle strings.
        """
        return list(self.models.keys())

    def get_model_versions(self, model: str) -> list[str] | None:
        """
        Get list of version strings present in database for a given model.

        Args:
            model: Model handle to get versions for.

        Returns:
            List of version strings, or None if model not found.
        """
        if self.models.get(model):
            return self.models[model]
        return None

    def get_latest_version(self, model: str) -> str | None:
        """
        Get the version string from Model node marked is_latest:True for a model handle.

        Args:
            model: Model handle to get latest version for.

        Returns:
            Version string, or None if model not found.
        """
        if self.models.get(model):
            return self.latest_version[model]
        return None

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_model_nodes(
        self,
        model: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Return a list of dicts representing Model nodes.

        Returns all versions.

        Args:
            model: Optional model handle to filter by.

        Returns:
            List of dicts representing Model nodes, or None if not found.
        """
        qry = ("match (m:model) {} return m").format(
            "where m.handle = $model" if model else "",
        )
        return (qry, {"model": model} if model else None)  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_nodes_by_model(
        self,
        model: str | None = None,
        version: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all nodes for a given model.

        Args:
            model: Model handle to get nodes for. If None, get all nodes in database.
            version: Version to filter by. If None, get nodes from model version marked
                is_latest:true. If '*', get nodes from all model versions.

        Returns:
            List of node dicts.
        """
        cond = "where n.model = $model and n.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model, "version": latest}
            elif version == "*" or latest == "unversioned":
                cond = "where n.model = $model"
                parms = {"model": model}
            else:
                parms = {"model": model, "version": version}
        else:
            cond = ""

        qry = f"match (n:node) {cond} return n"

        return (qry, parms, "n")  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_model_nodes_edges(
        self,
        model: str,
        version: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all node-relationship-node paths for a given model and version.

        Args:
            model: Model handle to get paths for.
            version: Version to filter by. If None, use version marked is_latest:true
                for model. If '*', retrieve from all versions.

        Returns:
            List of path dicts.
        """
        cond = (
            "where s.model = $model and s.version = $version and "
            "r.model = $model and r.version = $version and "
            "d.model = $model and d.version = $version "
        )
        parms = {}
        latest = self.get_latest_version(model)
        if version is None and latest != "unversioned":
            parms = {"model": model, "version": latest}
        elif version == "*" or latest == "unversioned":
            cond = "where s.model = $model and r.model = $model and d.model = $model "
            parms = {"model": model}
        else:
            parms = {"model": model, "version": version}
        qry = (
            "match p = (s:node)<-[:has_src]-(r:relationship)-[:has_dst]->(d:node)"
            f"{cond} "
            "return p as path"
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_node_edges_by_node_id(self, nanoid: str) -> list[dict[str, str]]:
        """
        Get incoming and outgoing relationship information for a node from its nanoid.

        Args:
            nanoid: The nanoid of the node to get edges for.

        Returns:
            List of dicts with id, handle, model, version, near_type, far_type, rln, far_node.
        """
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "with n "
            "optional match (n)<-[e1]-(r:relationship)-[e2]->(m:node) "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       n.version as version, "
            "       type(e1) as near_type, type(e2) as far_type, r as rln, m as far_node"
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_node_and_props_by_node_id(self, nanoid: str) -> list[dict[str, Any]] | None:
        """
        Get a node and its properties, given the node nanoid.

        Args:
            nanoid: The nanoid of the node to get.

        Returns:
            List with dict containing id, handle, model, version, node, props[].
        """
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "with n "
            "optional match (n)-[:has_property]->(p) "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       n.version as version, n as node, "
            "       collect(p) as props"
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_nodes_and_props_by_model(
        self,
        model: str | None = None,
        version: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all nodes with associated properties given a model handle.

        Args:
            model: Model handle to get nodes for. If None, get all nodes with their properties.
            version: Version to filter by. If None, get nodes and props from model version
                marked is_latest:true. If '*', get nodes and props from all model versions.

        Returns:
            List of dicts with id, handle, model, version, props[].
        """
        cond = (
            "where n.model = $model and n.version = $version and "
            "p.model = $model and p.version = $version "
        )
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model, "version": latest}
            elif version == "*" or latest == "unversioned":
                cond = "where n.model = $model and p.model = $model "
                parms = {"model": model}
            else:
                parms = {"model": model, "version": version}
        else:
            cond = ""
        qry = (
            "match (n:node)-[:has_property]->(p:property) "
            f"{cond} "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "n.version as version, collect(p) as props"
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_prop_node_and_domain_by_prop_id(
        self,
        nanoid: str,
    ) -> list[dict[str, Any]] | None:
        """
        Get a property, its node, and its value domain or value set of terms by nanoid.

        Args:
            nanoid: The nanoid of the property to get.

        Returns:
            List with dict containing id, handle, model, version, value_domain, prop,
            node, value_set, terms[].
        """
        qry = (
            "match (p:property {nanoid:$nanoid})<-[:has_property]-(n:node) "
            "with p,n "
            "optional match (p)-[:has_value_set]->(vs:value_set)-[:has_term]->(t:term) "
            "return p.nanoid as id, p.handle as handle, p.model as model, "
            "p.version as version, "
            "p.value_domain as value_domain, p as prop, n as node, "
            "  vs as value_set, collect(t) as terms"
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_valueset_by_id(self, nanoid: str) -> list[dict[str, Any]] | None:
        """
        Get a valueset with the properties that use it and the terms that constitute it.

        Args:
            nanoid: The nanoid of the valueset to get.

        Returns:
            List with dict containing id, handle, url, terms[], props[].
        """
        qry = (
            "match (vs:value_set {nanoid:$nanoid})-[:has_term]->(t) "
            "with vs, collect(t) as terms "
            "match (vs)<-[:has_value_set]-(p:property) "
            "return vs.nanoid as id, vs.handle as handle, vs.url as url, "
            "       terms, collect(p) as props"
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_valuesets_by_model(
        self,
        model: str | None = None,
        version: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all valuesets that are used by properties in the given model and version.

        Gets all valuesets if model is None. Also returns list of properties using each valueset.

        Args:
            model: Model handle to get valuesets for. If None, get all valuesets.
            version: Version to filter by. If None, get value sets associated with
                latest model version. If '*', get those associated with all versions.

        Returns:
            List of dicts with value_set, props[].
        """
        cond = "where p.model = $model and p.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model, "version": latest}
            elif version == "*" or latest == "unversioned":
                cond = "where p.model = $model"
                parms = {"model": model}
            else:
                parms = {"model": model, "version": version}
        else:
            cond = ""

        qry = (
            "match (vs:value_set)<-[:has_value_set]-(p:property) "
            f"{cond} "
            "return vs as value_set, collect(p) as props"
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_term_by_id(self, nanoid: str) -> list[dict[str, Any]] | None:
        """
        Get a term having the given nanoid, with its origin.

        Args:
            nanoid: The nanoid of the term to get.

        Returns:
            Dict with term, origin.
        """
        qry = (
            "match (t:term {nanoid:$nanoid}) "
            "with t, t.origin_name as origin_name "
            "optional match (o:origin {name: origin_name}) "
            "return t as term, o as origin "
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_props_and_terms_by_model(
        self,
        model: str | None = None,
        version: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get terms from valuesets associated with properties in a model and version.

        Gets all terms if model is None.

        Args:
            model: Model handle to get props and terms for. If None, get all terms.
            version: Version to filter by. If None, get props and terms from the
                latest model version. If '*', get those from all versions.

        Returns:
            List of dicts with prop, terms[].
        """
        cond = "where p.model = $model and p.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model, "version": latest}
            elif version == "*" or latest == "unversioned":
                cond = "where p.model = $model"
                parms = {"model": model}
            else:
                parms = {"model": model, "version": version}
        else:
            cond = ""
        qry = (
            "match (p:property)-[:has_value_set]->(v:value_set)"
            "-[:has_term]->(t:term) "
            f"{cond} "
            "return p as prop, collect(t) as terms"
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_origins(self) -> list[dict[str, Any]] | None:
        """
        Get all origins.

        Returns:
            List of origin dicts.
        """
        qry = "match (o:origin) return o"
        return (qry, None)  # type: ignore[reportReturnType]

    @read_txn_value  # type: ignore[reportArgumentType]
    def get_origin_by_id(self, oid: str) -> list[dict[str, Any]] | None:
        """Get an origin by nanoid."""
        qry = "match (o:origin {nanoid:$oid}) where not exists (o._to) return o "
        return (qry, {"oid": oid}, "o")  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_tags_for_entity_by_id(self, nanoid: str) -> list[dict[str, Any]] | None:
        """
        Get all tags attached to an entity, given the entity's nanoid.

        Args:
            nanoid: The nanoid of the entity to get tags for.

        Returns:
            List with dict containing model(str), tags[].
        """
        qry = (
            "match (a {nanoid:$nanoid})-[:has_tag]->(g:tag) "
            "with a, g "
            "return a.nanoid as id, head(labels(a)) as label, a.handle as handle, "
            "a.model as model, collect(g) as tags"
        )
        return (qry, {"nanoid": nanoid})  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_tags_and_values(
        self,
        key: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all tag key/value pairs that are present in database.

        Args:
            key: Optional key to filter by.

        Returns:
            List of dicts with key(str) : values[].
        """
        cond = ""
        parms = {}
        if key is not None:
            cond = "where t.key = $key "
            parms = {"key": key}
        qry = (
            "match (t:tag) "
            f"{cond} "
            "return t.key as key, collect(distinct t.value) as values "
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_entities_by_tag(
        self,
        key: str,
        value: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Get all entities, tagged with a given key or key:value pair.

        Args:
            key: Tag key to filter by.
            value: Optional tag value to filter by.

        Returns:
            List of dicts with tag_key(str), tag_value(str), entity(str - label), entities[].
        """
        cond = "where t.key = $key "
        parms = {"key": key}
        if value is not None:
            cond = "where t.key = $key and t.value = $value "
            parms = {"key": key, "value": value}
        qry = (
            "match (t:tag) "
            f"{cond} "
            "with t "
            "match (e)-[:has_tag]->(t) "
            "return t.key as tag_key, t.value as tag_value, collect(e) as entities"
        )
        return (qry, parms)  # type: ignore[reportReturnType]

    @read_txn_data  # type: ignore[reportArgumentType]
    def get_with_statement(
        self,
        qry: str,
        parms: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Run an arbitrary read statement and return data."""
        if parms is None:
            parms = {}
        if not isinstance(qry, str):
            msg = "qry= must be a string"
            raise TypeError(msg)
        if not re.match(".*return.*", qry, flags=re.IGNORECASE):
            msg = "Read statement needs a RETURN clause."
            raise RuntimeError(msg)
        if not isinstance(parms, dict):
            msg = "parms= must be a dict"
            raise TypeError(msg)
        return (qry, parms)  # type: ignore[reportReturnType]


def make_nanoid(
    alphabet: str = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789",
    size: int = 6,
) -> str:
    """Create a random nanoid and return it as a string."""
    return nanoid_generate(alphabet=alphabet, size=size)
