"""tests for ToolsMDB & EntityValidator"""
import pytest
import bento_meta
from bento_meta.mdb.mdb_tools import ToolsMDB, EntityValidator
from bento_meta.objects import Concept, Edge, Entity, Node, Property, Term


@pytest.mark.dumb
def test_tools_mdb(mdb):
    (b, h) = mdb
    mdb = ToolsMDB(uri=b, user="neo4j", password="neo4j1")
    assert mdb

def test_node_validation_success():
    node = Node({"handle": "test", "model": "test_model"})
    EntityValidator.validate_entity(node)


def test_edge_validation_success():
    edge = Edge(
        {
            "handle": "test",
            "model": "test_model",
            "src": Node({"handle": "source", "model": "test_model"}),
            "dst": Node({"handle": "destination", "model": "test_model"}),
        }
    )
    EntityValidator.validate_entity(edge)


def test_property_validation_success():
    prop = Property({"handle": "test", "model": "test_model"})
    EntityValidator.validate_entity(prop)


def test_term_validation_success():
    term = Term(
        {
            "origin_name": "test",
            "origin_id": "test_id",
            "origin_version": "test_version",
            "value": "test_value",
        }
    )
    EntityValidator.validate_entity(term)


def test_concept_validation_success():
    concept = Concept({"nanoid": "test_nanoid"})
    EntityValidator.validate_entity(concept)


def test_validation_failure_missing_attr():
    node = Node({"model": "test_model"})
    with pytest.raises(EntityValidator.MissingAttributeError):
        EntityValidator.validate_entity(node)


def test_validation_failure_edge_src_dst_attr_missing():
    edge = Edge(
        {
            "handle": "test",
            "model": "test_model",
            "src": Node({"model": "test_model"}),
            "dst": Node({"handle": "destination"}),
        }
    )
    with pytest.raises(EntityValidator.MissingAttributeError):
        EntityValidator.validate_entity(edge)


def test_validation_failure_unsupported_entity():
    class TestEntity(Entity):
        """fake class to fail entity validation"""

    entity = TestEntity()
    with pytest.raises(ValueError):
        EntityValidator.validate_entity(entity)
