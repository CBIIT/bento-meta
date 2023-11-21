"""Tests for diffr changelog generation script"""
import os
import sys

from bento_mdf.diff import diff_models
from bento_mdf.mdf import MDF
from bento_meta.objects import Concept, Property, Tag, Term, ValueSet
from bento_meta.util.changelog import update_config_changeset_id

sys.path.append("../")

from scripts.make_diff_changelog import DiffSplitter, convert_diff_to_changelog

# define filepaths for sample MDFs
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEST_MDF = os.path.join(CURRENT_DIRECTORY, "samples", "test_mdf.yml")
TEST_MDF_DIFF = os.path.join(CURRENT_DIRECTORY, "samples", "test_mdf_diff.yml")
TEST_MAPPING_MDF = os.path.join(CURRENT_DIRECTORY, "samples", "test_mapping_mdf.yml")
# changelog config probably not needed for these tests? remove below & file from samples?
TEST_CHANGELOG_CONFIG = os.path.join(CURRENT_DIRECTORY, "samples", "test_changelog.ini")
AUTHOR = "Tolkien"
MODEL_HDL = "TEST"
_COMMIT = "_COMMIT_123"

NODES = "nodes"
EDGES = "edges"
PROPS = "props"
TERMS = "terms"
NODE_HANDLE_1 = "subject"
NODE_HANDLE_2 = "diagnosis"
EDGE_HANDLE = "of_subject"
EDGE_KEY = (EDGE_HANDLE, NODE_HANDLE_2, NODE_HANDLE_1)
PROP_HANDLE_1 = "primary_disease_site"
PROP_KEY = (PROP_HANDLE_1, NODE_HANDLE_2)
PROP_HANDLE_2 = "id"
TERM_VALUE_1 = "Lung"
TERM_ORIGIN_1 = "NCIt"
TERM_KEY = (TERM_VALUE_1, TERM_ORIGIN_1)
TERM_VALUE_2 = "Kidney"
TERM_ORIGIN_2 = "NCIm"
TERM_KEY = (TERM_VALUE_2, TERM_ORIGIN_2)


def test_make_diff_changelog_length():
    mdf_old = MDF(TEST_MDF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
    mdf_new = MDF(TEST_MDF_DIFF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
    diff = diff_models(mdl_a=mdf_old.model, mdl_b=mdf_new.model)
    changelog = convert_diff_to_changelog(
        diff=diff,
        model_handle=MODEL_HDL,
        author=AUTHOR,
        config_file_path=TEST_CHANGELOG_CONFIG,
    )
    update_config_changeset_id(TEST_CHANGELOG_CONFIG, 1)
    assert len(changelog.subelements) == 39


class TestGetDiffStatements:
    SIMP_ATT = "nanoid"
    SIMP_ATT_1 = "abc123"
    SIMP_ATT_2 = "def456"
    OBJ_ATT_C = "concept"
    OBJ_ATT_C1 = Concept({"nanoid": "abc123"})
    OBJ_ATT_C2 = Concept({"nanoid": "def456"})
    OBJ_ATT_V = "value_set"
    OBJ_ATT_V1 = ValueSet({"handle": "vs252"})
    OBJ_ATT_V2 = ValueSet({"handle": "vs596"})
    TERM_1 = Term({"value": TERM_VALUE_1, "origin_name": TERM_ORIGIN_1})
    TERM_2 = Term({"value": TERM_VALUE_2, "origin_name": TERM_ORIGIN_2})
    OBJ_ATT_C1.terms[TERM_VALUE_1] = TERM_1
    OBJ_ATT_C2.terms[TERM_VALUE_2] = TERM_2
    OBJ_ATT_V1.terms[TERM_VALUE_1] = TERM_1
    OBJ_ATT_V2.terms[TERM_VALUE_2] = TERM_2
    COLL_ATT_P = "props"
    COLL_ATT_P1 = Property({"handle": PROP_HANDLE_1, "_parent_handle": NODE_HANDLE_2})
    COLL_ATT_P2 = Property({"handle": PROP_HANDLE_2, "_parent_handle": NODE_HANDLE_1})
    COLL_ATT_T = "tags"
    COLL_ATT_T1 = Tag({"key": "class", "value": "primary"})
    COLL_ATT_T2 = Tag({"key": "class", "value": "secondary"})

    def test_add_node_nanoid(self) -> None:
        splitter = DiffSplitter(
            diff={
                NODES: {
                    "changed": {
                        NODE_HANDLE_1: {
                            self.SIMP_ATT: {"added": self.SIMP_ATT_2, "removed": None}
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            "MATCH (n0:node {handle:'subject',model:'TEST'}) SET n0.nanoid = 'def456'"
        ]
        assert actual == expected

    def test_remove_edge_nanoid(self):
        splitter = DiffSplitter(
            diff={
                EDGES: {
                    "changed": {
                        EDGE_KEY: {
                            self.SIMP_ATT: {"added": None, "removed": self.SIMP_ATT_1}
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n2:node {handle:'subject',model:'TEST'})"
                "<-[r1:has_dst]-(n0:relationship {handle:'of_subject',model:'TEST'})"
                "-[r0:has_src]->(n1:node {handle:'diagnosis',model:'TEST'}) "
                "REMOVE n0.nanoid"
            )
        ]
        assert actual == expected

    def test_change_prop_nanoid(self):
        splitter = DiffSplitter(
            diff={
                PROPS: {
                    "changed": {
                        PROP_KEY: {
                            self.SIMP_ATT: {
                                "added": self.SIMP_ATT_2,
                                "removed": self.SIMP_ATT_1,
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n2 {handle:'primary_disease_site'})-[r0:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) "
                "SET n0.nanoid = 'def456'"
            )
        ]
        assert actual == expected

    def test_add_prop_value_set(self) -> None:
        splitter = DiffSplitter(
            diff={
                PROPS: {
                    "changed": {
                        PROP_KEY: {
                            self.OBJ_ATT_V: {
                                "added": {self.TERM_2.value: self.TERM_2},
                                "removed": None,
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n2 {handle:'primary_disease_site'})-[r1:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) "
                "MERGE (n0)-[r0:has_value_set]->(n1:value_set)"
            ),
            (
                "MATCH (n3 {handle:'primary_disease_site'})-[r2:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_value_set]->(n1:value_set) , "
                "(n2:term {value:'Kidney',origin_name:'NCIm'}) "
                "MERGE (n1)-[r1:has_term]->(n2)"
            ),
        ]
        assert actual == expected

    def test_add_two_terms_to_prop(self) -> None:
        splitter = DiffSplitter(
            diff={
                PROPS: {
                    "changed": {
                        PROP_KEY: {
                            self.OBJ_ATT_V: {
                                "added": {
                                    self.TERM_1.value: self.TERM_1,
                                    self.TERM_2.value: self.TERM_2,
                                },
                                "removed": None,
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n2 {handle:'primary_disease_site'})-[r1:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) "
                "MERGE (n0)-[r0:has_value_set]->(n1:value_set)"
            ),
            (
                "MATCH (n3 {handle:'primary_disease_site'})-[r2:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_value_set]->(n1:value_set) , "
                "(n2:term {value:'Lung',origin_name:'NCIt'}) "
                "MERGE (n1)-[r1:has_term]->(n2)"
            ),
            (
                "MATCH (n3 {handle:'primary_disease_site'})-[r2:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_value_set]->(n1:value_set) , "
                "(n2:term {value:'Kidney',origin_name:'NCIm'}) "
                "MERGE (n1)-[r1:has_term]->(n2)"
            ),
        ]
        assert actual == expected

    def test_remove_node_concept(self) -> None:
        splitter = DiffSplitter(
            diff={
                NODES: {
                    "changed": {
                        NODE_HANDLE_1: {
                            self.OBJ_ATT_C: {
                                "added": None,
                                "removed": {self.TERM_1.value: self.TERM_1},
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n0:node {handle:'subject',model:'TEST'}) , "
                "(n0)-[r0:has_concept]->(n2:concept) , "
                "(n1:term {value:'Lung',origin_name:'NCIt'})-[r1:represents]->(n2) "
                "DELETE n0"
            ),
        ]
        assert actual == expected

    def test_change_edge_concept(self) -> None:
        splitter = DiffSplitter(
            diff={
                EDGES: {
                    "changed": {
                        EDGE_KEY: {
                            self.OBJ_ATT_C: {
                                "added": {self.TERM_2.value: self.TERM_2},
                                "removed": {self.TERM_1.value: self.TERM_1},
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n4:node {handle:'subject',model:'TEST'})<-[r3:has_dst]-"
                "(n0:relationship {handle:'of_subject',model:'TEST'})-[r2:has_src]->"
                "(n3:node {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_concept]->(n2:concept) , "
                "(n1:term {value:'Lung',origin_name:'NCIt'})-[r1:represents]->(n2) "
                "DELETE n0"
            ),
            (
                "MATCH (n4:node {handle:'subject',model:'TEST'})<-[r3:has_dst]-"
                "(n0:relationship {handle:'of_subject',model:'TEST'})-[r2:has_src]->"
                "(n3:node {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_concept]->(n2:concept) , "
                "(n1:term {value:'Kidney',origin_name:'NCIm'}) "
                "MERGE (n1)-[r1:represents]->(n2)"
            ),
        ]
        assert actual == expected

    def test_change_prop_value_set(self) -> None:
        splitter = DiffSplitter(
            diff={
                PROPS: {
                    "changed": {
                        PROP_KEY: {
                            self.OBJ_ATT_V: {
                                "added": {self.TERM_2.value: self.TERM_2},
                                "removed": {self.TERM_1.value: self.TERM_1},
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n3 {handle:'primary_disease_site'})-[r2:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_value_set]->(n1:value_set) , "
                "(n1)-[r1:has_term]->(n2:term {value:'Lung',origin_name:'NCIt'}) DELETE n0"
            ),
            (
                "MATCH (n3 {handle:'primary_disease_site'})-[r2:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) , "
                "(n0)-[r0:has_value_set]->(n1:value_set) , "
                "(n2:term {value:'Kidney',origin_name:'NCIm'}) "
                "MERGE (n1)-[r1:has_term]->(n2)"
            ),
        ]
        assert actual == expected

    def test_change_node_prop(self) -> None:
        splitter = DiffSplitter(
            diff={
                NODES: {
                    "changed": {
                        NODE_HANDLE_1: {
                            self.COLL_ATT_P: {
                                "added": {PROP_HANDLE_2: self.COLL_ATT_P2},
                                "removed": {PROP_HANDLE_1: self.COLL_ATT_P1},
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n0:node {handle:'subject',model:'TEST'})-[r0:has_property]->"
                "(n1:property {handle:'primary_disease_site'}) "
                "DELETE r0"
            ),
            (
                "MERGE (n0:node {handle:'subject',model:'TEST'})-[r0:has_property]->"
                "(n1:property {handle:'id'})"
            ),
        ]
        assert actual == expected

    def test_change_prop_tag(self) -> None:
        splitter = DiffSplitter(
            diff={
                PROPS: {
                    "changed": {
                        PROP_KEY: {
                            self.COLL_ATT_T: {
                                "added": {self.COLL_ATT_T2.key: self.COLL_ATT_T2},
                                "removed": {self.COLL_ATT_T1.key: self.COLL_ATT_T1},
                            }
                        }
                    }
                }
            },
            model_handle=MODEL_HDL,
        )
        actual = [str(x) for x in splitter.get_diff_statements()]
        expected = [
            (
                "MATCH (n2 {handle:'primary_disease_site'})-[r0:has_property]->"
                "(n1:property {handle:'diagnosis',model:'TEST'}), "
                "(n1)-[r1:has_tag]->(n0:tag {key:'class',value:'primary'}) "
                "DETACH DELETE n0"
            ),
            "MERGE (n0:tag {key:'class',value:'secondary'})",
            (
                "MATCH (n2 {handle:'primary_disease_site'})-[r1:has_property]->"
                "(n0:property {handle:'diagnosis',model:'TEST'}) "
                "MERGE (n0)-[r0:has_tag]->(n1:tag {key:'class',value:'secondary'})"
            ),
        ]
        assert actual == expected
