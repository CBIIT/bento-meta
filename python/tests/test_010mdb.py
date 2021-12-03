import sys
sys.path.insert(0,".")
sys.path.insert(0,"..")
import pytest
import pytest_docker
import neo4j.graph
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from pdb import set_trace
from bento_meta.mdb import MDB


def test_mdb(mdb_local):
    (b, h) = mdb_local
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    assert mdb

    
def test_rd_txns(mdb_local):
    (b, h) = mdb_local
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    result = mdb.get_model_handles()
    assert set(result) == {"ICDC", "CTDC", "Bento"}
    result = mdb.get_origins()
    assert set([x["name"] for x in result]) == {"ICDC", "CTDC", "Bento", "NCIt"}
    result = mdb.get_nodes_by_model()
    result = mdb.get_nodes_by_model("CTDC")
    result = mdb.get_model_nodes_edges("ICDC")
    result = mdb.get_node_edges_by_node_id("gpKKCs")
    result = mdb.get_node_and_props_by_node_id("gpKKCs")
    result = mdb.get_nodes_and_props_by_model("Bento")
    result = mdb.get_prop_node_and_domain_by_prop_id("JcAf94")  # no valueset
    result = mdb.get_prop_node_and_domain_by_prop_id("mWWiz9")  # with valueset
    result = mdb.get_valueset_by_id("o3wWJX")
    result = mdb.get_valuesets_by_model("ICDC")
    result = mdb.get_term_by_id("oa4EN7")
    result = mdb.get_props_and_terms_by_model()
    result = mdb.get_props_and_terms_by_model("ICDC")
    result = mdb.get_tags_for_entity_by_id("o3wWJX")
    assert result == []
    result = mdb.get_entities_by_tag(key="gleb",value="blurg")
    assert result == []
