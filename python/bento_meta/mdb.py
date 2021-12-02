"""
bento_meta.mdb
==============

This module contains machinery for efficiently querying a Neo4j instance
of a Metamodel Database.
"""
import os
from neo4j import GraphDatabase 
from pdb import set_trace

class MDB:
    def __init__(self, uri=os.environ.get("NEO4J_MDB_URI"),
                 user=os.environ.get("NEO4J_MDB_USER"),
                 password=os.environ.get("NEO4J_MDB_PASS")):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(self.uri,
                                           auth=(self.user, self.password))
        self._txfns = {}

    def close(self):
        self.driver.close()

    # Decorator functions to produce executed transactions based on an
    # underlying query/param function:
    
    def read_txn(func):
        """Decorates a query function to run a read transaction based on
its query.
Query function should return a tuple (qry_string, param_dict).
Returns list of driver Records."""

        def rd(self, *args, **kwargs):
            def txn_q(tx):
                (qry,parms)=func(self, *args, **kwargs)
                result = tx.run(qry,parameters=parms)
                return [rec for rec in result]
            with self.driver.session() as session:
                result = session.read_transaction(txn_q)
                return result
        return rd

    def read_txn_value(func):
        """Decorates a query function to run a read transaction based on
its query.
Query function should return a tuple (qry_string, param_dict, values_key).
Returns list of values for key specified by query function."""

        def rd(self, *args, **kwargs):
            def txn_q(tx):
                (qry,parms,values_key)=func(self, *args, **kwargs)
                result = tx.run(qry,parameters=parms)
                return result.value(values_key)
            with self.driver.session() as session:
                result = session.read_transaction(txn_q)
                return result
        return rd

    def read_txn_data(func):
        """Decorates a query function to run a read transaction based on
its query.
Query function should return a tuple (qry_string, param_dict).
Returns records as a list of simple dicts."""

        def rd(self, *args, **kwargs):
            (qry,parms)=func(self, *args, **kwargs)
            def txn_q(tx):
                result = tx.run(qry,parameters=parms)
                return result.data()
            with self.driver.session() as session:
                result = session.read_transaction(txn_q)
                return result
        return rd

    def write_txn(func):
        """Decorates a query function to run a write transaction based
on its query.
Query function should return a tuple (qry_string, param_dict)."""
        def wr(self, *args, **kwargs):
            def txn_q(tx):
                (qry,parms)=func(self, *args, **kwargs)
                result = tx.run(qry,parameters=parms)
                return [rec for rec in result]
            with self.driver.session() as session:
                result = session.write_transaction(txn_q)
                return result
        return wr

    def register_txfn(self, name, fn):
        """Register a transaction function

(see https://neo4j.com/docs/api/python-driver/current/api.html#managed-transactions-transaction-functions) # noqa E501
with the class for later use."""

        self._txfns[name] = fn

    # def run_txfn(self, name, *args, **kwargs):

    @read_txn_value
    def get_model_handles(self):
        """Return a simple list of model handles available."""
        qry = (
            "match (p:node) "
            "where not exists(p._to) "
            "return distinct p.model"
            )
        return (qry, None,"p.model")

    @read_txn_value
    def get_nodes_by_model(self, model=None):
        """Get all nodes for a given model. If :param:model is None, 
get all nodes in database.
Returns [ <node> ]."""
        qry = (
            "match (n:node) {}"
            "with n "
            "where not exists(n._to) "
            "return n"
            ).format("where n.model = $model" if model else "")
        return (qry, {model: "$model"} if model else None, "n")
    
    @read_txn_data
    def get_model_nodes_edges(self, handle):
        """Get all node-relationship-node paths for a given model.
Returns [ path ]"""
        qry = (
            "match p = (s:node {model: $model})<-[:has_src]-"
            "          (r:relationship {model: $model})-[:has_dst]->"
            "          (d:node {model: $model}) "
            "where not exists(s._to) and not exists(r._to) and not exists(d._to) "
            "return p as path"
            )
        return (qry, {"model":handle})

    @read_txn_data
    def get_node_edges_by_node_id(self, nanoid):
        """Get incoming and outgoing relationship information for a node, 
given its nanoid.
Returns [ {id, handle, model, near_type, far_type, rln, far_node} ]."""
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "where not exists(n._to) "
            "with n "
            "optional match (n)<-[e1]-(r:relationship)-[e2]->(m:node) "
            "where not exists(r._to) and not exists(m._to) "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       type(e1) as near_type, type(e2) as far_type, r as rln, m as far_node"
            )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_node_and_props_by_node_id(self, nanoid):
        """Get a node and its properties, given the node nanoid.
Returns [ {id, handle, model, node, props[]} ]."""
        qry = (
            "match (n:node {nanoid:$nanoid}) "
            "where not exists(n._to) "
            "with n "
            "optional match (n)-[:has_property]->(p) "
            "where not exists(p._to) "
            "return n.nanoid as id, n.handle as handle, n.model as model, n as node, "
            "       collect(p) as props"
            )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_nodes_and_props_by_model(self, model=None):
        """Get all nodes with associated properties given a model handle. If
model is None, get all nodes with their properties.
Returns [ {id, handle, model, props[]} ]"""
        qry = (
            "match (n:node)-[:has_property]->(p:property) "
            "where not exists(n._to) and not exists(p._to) {} "
            "return n.nanoid as id, n.handle as handle, n.model as model, "
            "       collect(p) as props"
            ).format("and n.model = $model" if model else "")
        return (qry, {"model":model})
    
            
    @read_txn_data
    def get_prop_node_and_domain_by_prop_id(self, nanoid):
        """Get a property, its node, and its value domain or value set
of terms, given the property nanoid.
Returns [ { id, handle, model, value_domain, prop, node, value_set, terms[] } ]."""
        qry = (
            "match (p:property {nanoid:$nanoid})<-[:has_property]-(n:node),  "
            "where not exists(p._to) "
            "with p,n "
            "optional match (p)-[:has_value_set]->(vs:value_set)-[:has_term]->(t:term) "
            "return p.nanoid as id, p.handle as handle, p.model as model, "
            "p.value_domain as value_domain, p as prop, n as node, vs as value_set collect(t) as terms"
            )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_valueset_by_id(self, nanoid):
        """Get a valueset with the properties that use it and the terms
that constitute it.
Returns [ {id, handle, url, terms[], props[]} ]"""
        qry = (
            "match (vs:value_set {nanoid:$nanoid} "
            "with vs "
            "match (t)<-[:has_term]-(vs)-[:has_value_set]->(p:property) "
            "where not exists(t._to) and not exists(p._to) "
            "return vs.nanoid as id, vs.handle as handle, vs.url as url, "
            "       collect(t) as terms, collect(p) as props"
            )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_valuesets_by_model(self, model=None):
        """Get all valuesets that are used by properties in the given
model (or all valuesets if model is None). Also return list of properties using
each valueset.
Returns [ {value_set, props[]} ]."""
        qry = (
            "match (vs:value_set)<-[:has_value_set]-(p:property) "
            "where not exists(vs._to) and not exists(p._to) {} "
            "return vs as value_set, collect(p) as props"
            ).format("and p.model=$model" if model else "")
        return (qry, {"model": model})

        
    @read_txn_data
    def get_term_by_id(self, nanoid):
        """Get a term having the given nanoid, with its origin.
Returns {term, origin}."""
        qry = (
            "match (t:term {nanoid:$nanoid}) "
            "where not exists(t._to) "
            "with t "
            "optional match (t)-[:has_origin]->(o:origin) "
            "where not exists(o._to) "
            "return t as term, o as origin "
            )
        return (qry, {"nanoid": nanoid})

    @read_txn_data
    def get_prop_terms_by_model(self, model=None):
        """Get terms from valuesets associated with properties in a given model
(or all such terms if model is None).
Returns [ {prop, terms[]} ]"""
        qry = (
            "match (p:property)-[:has_value_set]->(v:value_set)"
            "-[:has_term]->(t:term) "
            "where not( exists(p._to) or exists(v._to) or exists(t._to)) {} "
            "return p as prop, collect(t) as terms"
            ).format("and p.model = $model" if model else "")
        return (qry, {"model": model})

    @read_txn_value
    def get_origins(self):
        """Get all origins.
Returns [ <origin> ]"""
        qry = (
            "match (o:origin) "
            "where not exists (o._to) "
            "return o"
            )
        return (qry, None, "o")
    
    @read_txn_data
    def get_tags_for_entity_by_id(self, nanoid):
        """Get all tags attached to an entity, given the entity's nanoid.
Returns [ {model(str), tags[]} ]."""
        qry = (
            "match (a {nanoid:$nanoid}) "
            "where not exists(a._to) "
            "with a "
            "optional match (a)-[:has_tag]->(g:tag) "
            "return a.nanoid as id, head(labels(a)) as label, a.handle as handle, "
            "a.model as model, collect(g) as tags"
            )
        return (qry, {"nanoid":nanoid})

    @read_txn_data
    def get_entities_by_tag(self, key, value=None):
        """Get all entities tagged with a given key or key:value pair.
Returns [ {tag_key(str), tag_value(str), entities[]} ]"""
        qry = (
            "match (t:tag {{key:$key}}) {}"
            "with t "
            "match (e)-[:has_tag]->(t) "
            "return t.key as tag_key, t.value as tag_value, collect(e) as entities"
            ).format("where t.value = $value" if value else "")
        parms = {"key":key}
        if value:
            parms["value"]=value
        return (qry, parms)

    
if __name__ == "__main__":
    mdb = MDB(uri="bolt://localhost",
              user="neo4j",
              password="1cDcj4oen")
    set_trace()
    result = mdb.get_model_handles()
    result = mdb.get_model("ICDC")
    result = mdb.get_node_and_props_by_node_id("Ufwtax") # a property
    result = mdb.get_node_and_props_by_node_id("9pPHzh") # a node
    result = mdb.get_node_edges_by_node_id("9pPHzh") # a node
    result = mdb.get_prop_domain_by_prop_id("gsQc3K") # a property
    pass
