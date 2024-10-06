import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")
import pytest
import pytest_docker
from pdb import set_trace
from bento_meta.mdb import MDB

@pytest.mark.docker
def test_mdb(mdb_local):
    (b, h) = mdb_local
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    assert mdb


@pytest.mark.docker
def test_non_versioned_getters(mdb_local):
    (b, h) = mdb_local
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    result = mdb.get_model_handles()
    assert set(result) == {"A", "B"}
    result = mdb.get_origins()
    assert {x["o"]["name"] for x in result} == {"C"}

    result = mdb.get_node_edges_by_node_id("6VGSf7")
    assert len([x for x in result if x['near_type'] == "has_dst"]) == 2
    assert len([x for x in result if x['near_type'] == "has_src"]) == 0
    assert result[0]['version'] == '1.0'

    result = mdb.get_node_and_props_by_node_id("8AfXR5")
    assert result[0]['model'] == 'A'
    assert result[0]['version'] == '1.0'
    assert len(result[0]['props']) == 2
    
    result = mdb.get_prop_node_and_domain_by_prop_id("GnAPFa")  # no valueset
    assert result[0]['value_domain'] == "number"
    result = mdb.get_prop_node_and_domain_by_prop_id("7bcQ3U")  # with valueset
    assert result[0]['value_domain'] == "value_set"
    assert len(result[0]['terms']) == 2
    result = mdb.get_prop_node_and_domain_by_prop_id("msck2R")  # with valueset
    assert result[0]['value_domain'] == "value_set"
    assert len(result[0]['terms']) == 3
    
    result = mdb.get_valueset_by_id("wzDQiX")
    assert result[0]['handle'] == '1'
    assert len(result[0]['terms']) == 2
    assert len(result[0]['props']) == 3

    result = mdb.get_term_by_id("fqF28o")
    assert result[0]['term']['handle'] == "BAM"
    
    result = mdb.get_tags_and_values()
    assert len(result) == 2
    assert "mappingSource" in [r["key"] for r in result]
    assert "Source" in [r["key"] for r in result]
    
    result = mdb.get_tags_and_values("Source")
    assert len(result) == 1
    assert "calculated" in result[0]['values']
    assert "submitted" in result[0]['values']
    
    result = mdb.get_tags_for_entity_by_id("DB4RYd")
    assert len(result) == 1
    assert result[0]['tags'][0]['key'] == "mappingSource"
    assert result[0]['tags'][0]['value'] == "NCIt"
    
    result = mdb.get_entities_by_tag(key="Source")
    assert sum([len(r['entities']) for r in result]) == 6
    result = mdb.get_entities_by_tag(key="Source",value="calculated")
    assert sum([len(r['entities']) for r in result]) == 4

@pytest.mark.docker
def test_versioned_getters(mdb_local):
    (b, h) = mdb_local
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")

    result = mdb.get_nodes_by_model()
    assert len(result) == 17
    result = mdb.get_nodes_by_model("A")
    assert len(result) == 5
    result = mdb.get_nodes_by_model("A","1.0")
    assert len(result) == 4
    result = mdb.get_nodes_by_model("A","*")
    assert len(result) == 9

    result = mdb.get_model_nodes_edges("A")
    assert len(result) == 6
    result = mdb.get_model_nodes_edges("A","1.1")
    assert len(result) == 6
    result = mdb.get_model_nodes_edges("A","1.0")
    assert len(result) == 5
    result = mdb.get_model_nodes_edges("A","*")
    assert len(result) == 11
    
    result = mdb.get_nodes_and_props_by_model("A")
    assert len(result) == 5
    assert any([x=="investigator" for x in [y['handle'] for y in result]])
    result = mdb.get_nodes_and_props_by_model("A","1.0")
    assert len(result) == 4
    result = mdb.get_nodes_and_props_by_model("A","*")
    assert len(result) == 9

    result = mdb.get_valuesets_by_model()
    assert len(result) == 3
    result = mdb.get_valuesets_by_model("B")
    assert len(result) == 1
    result = mdb.get_valuesets_by_model("A")
    assert len(result) == 2
    result = mdb.get_valuesets_by_model("A","1.0")
    assert len(result) == 1
    result = mdb.get_valuesets_by_model("A","*")
    assert len(result) == 3
    
    result = mdb.get_props_and_terms_by_model()
    assert len(result) == 5
    result = mdb.get_props_and_terms_by_model("B")
    assert len(result) == 1
    result = mdb.get_props_and_terms_by_model("B", "v0.1.0")
    assert len(result) == 1
    assert result[0]['prop']['handle'] == 'specimen_type'
    assert "tumor" in [t['handle'] for t in result[0]['terms']]
    assert "normal" in [t['handle'] for t in result[0]['terms']]
    result = mdb.get_props_and_terms_by_model("B", "*")
    assert len(result) == 2
