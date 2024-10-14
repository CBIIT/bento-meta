import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")
import pytest
import pytest_docker
from pdb import set_trace
from bento_meta.mdb import MDB, WriteableMDB

@pytest.mark.docker
def test_mdb(mdb):
    (b, h) = mdb
    mdb = WriteableMDB(uri=b, user="neo4j", password="neo4j1")
    assert mdb
    # add Model nodes to the example DB
    mdb.put_with_statement('create (:model {handle: $hdl})',{"hdl":"ICDC"});
    mdb.put_with_statement('create (:model {handle: $hdl})',{"hdl":"CTDC"});
    mdb.put_with_statement('create (:model {handle: $hdl})',{"hdl":"Bento"});    

@pytest.mark.docker
def test_rd_txns(mdb):
    (b, h) = mdb
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    result = mdb.get_model_handles()
    assert set(result) == {"ICDC", "CTDC", "Bento"}
    result = mdb.get_origins()
    assert {x["o"]["name"] for x in result} == {"ICDC", "CTDC", "Bento", "NCIt"}
    result = mdb.get_nodes_by_model()
    assert len(result) == 65
    result = mdb.get_nodes_by_model("CTDC")
    assert len(result) == 18
    result = mdb.get_model_nodes_edges("ICDC")
    assert len(result) == 43
    result = mdb.get_node_edges_by_node_id("zwr37o")
    assert len([x for x in result if x['near_type'] == "has_dst"]) == 8
    assert len([x for x in result if x['near_type'] == "has_src"]) == 5
    result = mdb.get_node_and_props_by_node_id("gpKKCs")
    assert len(result[0]['props']) == 6
    result = mdb.get_nodes_and_props_by_model("Bento")
    assert len(result) == 19
    assert len([x for x in result if x['handle'] == "diagnosis"][0]["props"]) == 124
    result = mdb.get_prop_node_and_domain_by_prop_id("JcAf94")  # no valueset
    assert result[0]['value_domain'] == "TBD"
    result = mdb.get_prop_node_and_domain_by_prop_id("mWWiz9")  # with valueset
    assert result[0]['value_domain'] == "value_set"
    assert len(result[0]['terms']) == 2
    result = mdb.get_valueset_by_id("o3wWJX")
    result = mdb.get_valuesets_by_model("ICDC")
    result = mdb.get_term_by_id("oa4EN7")
    result = mdb.get_props_and_terms_by_model()
    result = mdb.get_props_and_terms_by_model("ICDC")
    result = mdb.get_tags_for_entity_by_id("o3wWJX")
    assert result == None
    result = mdb.get_entities_by_tag(key="gleb", value="blurg")
    assert result == None
