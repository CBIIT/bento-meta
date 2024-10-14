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

import os
import re
from functools import wraps
from warnings import warn

from nanoid import generate as nanoid_generate
from neo4j import GraphDatabase

from pdb import set_trace

# Decorator functions to produce executed transactions based on an
# underlying query/param function:


def read_txn(func):
    """
    Decorates a query function to run a read transaction based on
    its query.
    Query function should return a tuple (qry_string, param_dict).
    Returns list of driver Records.
    """

    @wraps(func)
    def rd(self, *args, **kwargs):
        def txn_q(tx):
            (qry, parms) = func(self, *args, **kwargs)
            result = tx.run(qry, parameters=parms)
            return [rec for rec in result]

        with self.driver.session() as session:
            result = session.read_transaction(txn_q)
            return result

    return rd


def read_txn_value(func):
    """
    Decorates a query function to run a read transaction based on
    its query.
    Query function should return a tuple (qry_string, param_dict, values_key).
    Returns list of values for key specified by query function.
    """

    @wraps(func)
    def rd(self, *args, **kwargs):
        def txn_q(tx):
            (qry, parms, values_key) = func(self, *args, **kwargs)
            result = tx.run(qry, parameters=parms)
            return result.value(values_key)

        with self.driver.session() as session:
            result = session.read_transaction(txn_q)
            return result

    return rd


def read_txn_data(func):
    """
    Decorates a query function to run a read transaction based on
    its query.
    Query function should return a tuple (qry_string, param_dict).
    Returns records as a list of simple dicts.
    """

    @wraps(func)
    def rd(self, *args, **kwargs):
        (qry, parms) = func(self, *args, **kwargs)

        def txn_q(tx):
            result = tx.run(qry, parameters=parms)
            return result.data()

        with self.driver.session() as session:
            result = session.read_transaction(txn_q)
            if len(result):
                return result
            else:
                return None

    return rd


class MDB:
    def __init__(
        self,
        uri=os.environ.get("NEO4J_MDB_URI"),
        user=os.environ.get("NEO4J_MDB_USER"),
        password=os.environ.get("NEO4J_MDB_PASS"),
    ):
        """
        Create an :class:`MDB` object, with a connection to a Neo4j instance of a metamodel database.
        :param bolt_url uri: The Bolt protocol endpoint to the Neo4j instance (default, use the
        ``NEO4J_MDB_URI`` env variable)
        :param str user: Username for Neo4j access (default, use the ``NEO4J_MDB_USER`` env variable)
        :param str password: Password for user (default, use the ``NEO4J_MDB_PASS`` env variable)
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.models = {}
        self.latest_version = {}
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
        except Exception as e:
            warn(f"MDB not connected: {e}")
        try:
            # query DB and cache the models and their versions in the MDB object
            info = self.get_model_info()
            if not info or len(info) == 0:
                raise RuntimeError("No Model nodes found")
            for m in info:
                if self.models.get(m['handle']):
                    self.models[m['handle']].append(m['version'])
                else:
                    self.models[m['handle']] = [m['version']]
                if m['is_latest'] and not self.latest_version.get(m['handle']):
                    self.latest_version[m['handle']] = m['version']
            for hdl in self.models:
                if not self.latest_version.get(hdl):
                    if len(self.models[hdl]) == 1:  # only one version
                        self.latest_version[hdl] = self.models[hdl][0] or "unversioned"
                    else:
                        self.latest_version[hdl] = None
        except Exception as e:
            # raise RuntimeError
            warn(f"Database doesn't look like an MDB: {e}")
        self._txfns = {}

    def close(self):
        self.driver.close()

    def register_txfn(self, name, fn):
        """
        Register a transaction function
        (see https://neo4j.com/docs/api/python-driver/current/api.html#managed-transactions-transaction-functions)
        with the class for later use.
        """
        self._txfns[name] = fn

    # def run_txfn(self, name, *args, **kwargs):

    @read_txn_value
    def get_model_info(self):
        """
        Get models, versions, and latest versions from MDB Model nodes
        """
        return ("match (m:model) return m", None, "m")
    
    def get_model_handles(self):
        """
        Return a simple list of model handles available.
        Queries Model nodes (not model properties in Entity nodes)
        """
        return [x for x in self.models.keys()]

    def get_model_versions(self, model):
        """
        Get list of version strings present in database for a given model.
        Returns [ <string> ].
        """
        if self.models.get(model):
            return self.models[model]
        else:
            return
    
    def get_latest_version(self, model):
        """
        Get the version string from Model node marked is_latest:True for a given
        model handle.
        Returns <string>
        """
        if self.models.get(model):
            return self.latest_version[model]
        else:
            return

    @read_txn_data
    def get_model_nodes(self, model=None):
        """
        Return a list of dicts representing Model nodes.
        Returns all versions.
        """
        qry = ("match (m:model) {} return m").format(
            "where m.handle = $model" if model else ""
        )
        return (qry, {"model": model} if model else None)

    @read_txn_value
    def get_nodes_by_model(self, model=None, version=None):
        """
        Get all nodes for a given model.
        If :param:model is set but :param:version is None, get nodes from model version
        marked is_latest:true
        If :param:model is set and :param:version is '*', get nodes from all model versions.
        If :param:model is None, get all nodes in database.
        Returns [ <node> ].
        """
        cond = "where n.model = $model and n.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model,
                         "version": latest}
            elif version == "*" or latest == "unversioned":
                cond = "where n.model = $model" 
                parms = {"model": model}
            else:
                parms = {"model": model, "version": version}
        else:
            cond = ""
        
        qry = f"match (n:node) {cond} return n"

        return (qry, parms, "n")

    @read_txn_data
    def get_model_nodes_edges(self, model, version=None):
        """
        Get all node-relationship-node paths for a given model and version.
        If :param:version is None, use version marked is_latest:true for
        :param:model.
        If :param:version is '*', retrieve from all versions.
        Returns [ path ]
        """
        cond = ("where s.model = $model and s.version = $version and "
                "r.model = $model and r.version = $version and "
                "d.model = $model and d.version = $version ")
        parms = {}
        latest = self.get_latest_version(model)
        if version is None and latest != "unversioned":
            parms = {"model": model,
                     "version": latest}
        elif version == "*" or latest == "unversioned":
            cond = ("where s.model = $model and "
                    "r.model = $model and "
                    "d.model = $model ")
            parms = {"model": model}
        else:
            parms = {"model": model, "version": version}
        qry = (
            "match p = (s:node)<-[:has_src]-(r:relationship)-[:has_dst]->(d:node)"
            f"{cond} "
            "return p as path"
            )
        return (qry, parms)

    @read_txn_data
    def get_node_edges_by_node_id(self, nanoid):
        """
        Get incoming and outgoing relationship information for a node,
        given its nanoid.
        Returns [ {id, handle, model, version, near_type, far_type, rln, far_node} ].
        """
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "with n "
            "optional match (n)<-[e1]-(r:relationship)-[e2]->(m:node) "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       n.version as version, "
            "       type(e1) as near_type, type(e2) as far_type, r as rln, m as far_node"
        )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_node_and_props_by_node_id(self, nanoid):
        """
        Get a node and its properties, given the node nanoid.
        Returns [ {id, handle, model, version, node, props[]} ].
        """
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "with n "
            "optional match (n)-[:has_property]->(p) "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       n.version as version, n as node, "
            "       collect(p) as props"
        )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_nodes_and_props_by_model(self, model=None, version=None):
        """
        Get all nodes with associated properties given a model handle.
        If model is None, get all nodes with their properties.
        If :param:model is set but :param:version is None, get nodes and props
        from model version marked is_latest:true
        If :param:model is set and :param:version is '*', get nodes and props
        from all model versions.
        
        Returns [ {id, handle, model, version, props[]} ]
        """
        cond = ("where n.model = $model and n.version = $version and "
                "p.model = $model and p.version = $version ")
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model,
                         "version": latest}
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
        return (qry, parms)

    @read_txn_data
    def get_prop_node_and_domain_by_prop_id(self, nanoid):
        """
        Get a property, its node, and its value domain or value set
        of terms, given the property nanoid.
        Returns [ { id, handle, model, version, value_domain, prop, node, value_set, terms[] } ].
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
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_valueset_by_id(self, nanoid):
        """
        Get a valueset with the properties that use it and the terms
        that constitute it.
        Returns [ {id, handle, url, terms[], props[]} ]
        """
        qry = (
            "match (vs:value_set {nanoid:$nanoid})-[:has_term]->(t) "
            "with vs, collect(t) as terms "
            "match (vs)<-[:has_value_set]-(p:property) "
            "return vs.nanoid as id, vs.handle as handle, vs.url as url, "
            "       terms, collect(p) as props"
        )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_valuesets_by_model(self, model=None, version=None):
        """
        Get all valuesets that are used by properties in the given
        model and version (or all valuesets if model is None).
        Also return list of properties using each valueset.
        If version is None, get value sets associated with latest model version.
        If version is '*', get those associated with all versions of given model.
        Returns [ {value_set, props[]} ].
        """
        cond = "where p.model = $model and p.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned":
                parms = {"model": model,
                         "version": latest}
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
        return (qry, parms)

    @read_txn_data
    def get_term_by_id(self, nanoid):
        """
        Get a term having the given nanoid, with its origin.
        Returns {term, origin}.
        """
        qry = (
            "match (t:term {nanoid:$nanoid}) "
            "with t, t.origin_name as origin_name "
            "optional match (o:origin {name: origin_name}) "
            "return t as term, o as origin "
        )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_props_and_terms_by_model(self, model=None, version=None):
        """
        Get terms from valuesets associated with properties in a given model
        and version (or all such terms if model is None).
        If version is None, get props and terms from the latest model version.
        If version is set to '*', get those from all versions of the given model.
        Returns [ {prop, terms[]} ]
        """
        cond = "where p.model = $model and p.version = $version"
        parms = {}
        if model:
            latest = self.get_latest_version(model)
            if version is None and latest != "unversioned": 
                parms = {"model": model,
                         "version": latest}
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
        return (qry, parms)

    @read_txn_data
    def get_origins(self):
        """
        Get all origins.
        Returns [ <origin> ]
        """
        qry = "match (o:origin) return o"
        return (qry, None)

    @read_txn_value
    def get_origin_by_id(self, oid):
        """Get an origin by nanoid."""
        qry = "match (o:origin {nanoid:$oid}) where not exists (o._to) return o "
        return (qry, {"oid": oid}, "o")

    @read_txn_data
    def get_tags_for_entity_by_id(self, nanoid):
        """
        Get all tags attached to an entity, given the entity's nanoid.
        Returns [ {model(str), tags[]} ].
        """
        qry = (
            "match (a {nanoid:$nanoid})-[:has_tag]->(g:tag) "
            "with a, g "
            "return a.nanoid as id, head(labels(a)) as label, a.handle as handle, "
            "a.model as model, collect(g) as tags"
        )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_tags_and_values(self, key=None):
        """
        Get all tag key/value pairs that are present in database.
        Returns [ { key(str) : values[] } ]
        """
        cond = ""
        parms = {}
        if key is not None:
            cond = "where t.key = $key "
            parms = {"key":key}
        qry = (
            "match (t:tag) "
            f"{cond} "
            "return t.key as key, collect(distinct t.value) as values "
            )
        return (qry, parms)

    @read_txn_data
    def get_entities_by_tag(self, key, value=None):
        """
        Get all entities, tagged with a given key or key:value pair.
        Returns [ {tag_key(str), tag_value(str), entity(str - label), entities[]} ]
        """
        cond = "where t.key = $key "
        parms = {"key":key}
        if value is not None:
            cond = "where t.key = $key and t.value = $value "
            parms = {"key":key, "value": value}
        qry = (
            "match (t:tag) "
            f"{cond} "
            "with t "
            "match (e)-[:has_tag]->(t) "
            "return t.key as tag_key, t.value as tag_value, collect(e) as entities"
        )
        return (qry, parms)

    @read_txn_data
    def get_with_statement(self, qry, parms={}):
        """Run an arbitrary read statement and return data."""
        if not isinstance(qry, str):
            raise RuntimeError("qry= must be a string")
        if not re.match(".*return.*", qry, flags=re.I):
            raise RuntimeError("Read statement needs a RETURN clause.")
        if not isinstance(parms, dict):
            raise RuntimeError("parms= must be a dict")
        return (qry, parms)


def make_nanoid(
    alphabet="abcdefghijkmnopqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ0123456789",
    size=6,
):
    """Create a random nanoid and return it as a string."""
    return nanoid_generate(alphabet=alphabet, size=size)
