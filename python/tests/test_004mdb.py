import sys

sys.path.insert(0, ".")
sys.path.insert(0, "..")

import pytest
from bento_meta.mdb import MDB, WriteableMDB
from pdb import set_trace

@pytest.mark.docker
def test_rd_txns(test_mdb):
    (b, h) = test_mdb
    mdb = MDB(uri=b, user="neo4j", password="neo4j1")
    result = mdb.get_model_handles()
    assert set(result) == {
        "C3DC",
        "CCDI",
        "CCDI-DCC",
        "CDS",
        "CRDC",
        "CRDCSearch",
        "CRDCSubmission",
        "CTDC",
        "GDC",
        "HTAN",
        "ICDC",
        "PDC",
        "mCODE",
    }

    result = mdb.get_origins()
    assert {x["o"]["name"] for x in result} > {
        "PSI MS",
        "PubMedCentral",
        "RAC39299LEX",
        "RADLEX",
        "SNOMED CT",
        "SNOMEDCT_US",
        "SpecimenType (HL7)",
        }
    
    #result = mdb.get_nodes_by_model()
    #assert len(result) == 1202
    result = mdb.get_nodes_by_model("CTDC")
    assert len(result) == 18
    result = mdb.get_nodes_by_model("CTDC","1.19.0")
    assert len(result) == 18
    result = mdb.get_model_nodes_edges("ICDC")
    assert len(result) == 40 
    result = mdb.get_node_edges_by_node_id("qJKDxq") # ICDC visit node
    assert len([x for x in result if x["near_type"] == "has_dst"]) == 6
    assert len([x for x in result if x["near_type"] == "has_src"]) == 3
    result = mdb.get_node_and_props_by_node_id("qJKDxq")
    assert len(result[0]["props"]) == 4
    result = mdb.get_nodes_and_props_by_model("CTDC", "1.19.0")
    assert len(result) == 18
    assert len([x for x in result if x["handle"] == "diagnosis"][0]["props"]) == 13
    result = mdb.get_prop_node_and_domain_by_prop_id("UZfZBw")  # no valueset HTAN 24.3.1 PairOnDiffCHR
    assert result[0]["value_domain"] == "TBD"
    result = mdb.get_prop_node_and_domain_by_prop_id("vhCH83")  # with valueset CDS 8.0.0 library_selection
    assert result[0]["value_domain"] == "value_set"
    assert len(result[0]["terms"]) == 36
    result = mdb.get_valueset_by_id("o3wWJX")
    result = mdb.get_valuesets_by_model("ICDC")
    result = mdb.get_term_by_id("oa4EN7")
    result = mdb.get_props_and_terms_by_model()
    result = mdb.get_props_and_terms_by_model("ICDC")
    result = mdb.get_tags_for_entity_by_id("o3wWJX")
    assert result == None
    result = mdb.get_entities_by_tag(key="gleb", value="blurg")
    assert result == None
