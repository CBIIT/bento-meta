"""tests for ToolsMDB & EntityValidator"""
import pytest
from bento_meta.mdb.mdb_tools import EntityValidator, ToolsMDB
from bento_meta.objects import Concept, Edge, Entity, Node, Property, Term, ValueSet
from bento_meta.util.cypher.entities import G, N, R, T


class TestToolsMDB:
    """tests ToolsMDB"""

    MODEL = "test_model"
    MAPPING_SOURCE_1 = "map_src_1"
    MAPPING_SOURCE_2 = "map_src_2"

    node_1 = Node({"handle": "node_1", "model": MODEL, "nanoid": "nnano1"})
    pg_node_1 = N(label=node_1.get_label(), props=node_1.get_attr_dict())
    node_2 = Node({"handle": "node_2", "model": MODEL, "nanoid": "nnano2"})
    pg_node_2 = N(label=node_2.get_label(), props=node_2.get_attr_dict())
    edge_1 = Edge(
        {
            "handle": "edge_1",
            "model": MODEL,
            "nanoid": "enano1",
            "src": node_1,
            "dst": node_2,
        }
    )
    pg_edge_1 = N(label=edge_1.get_label(), props=edge_1.get_attr_dict())
    prop_1 = Property({"handle": "prop_1", "model": MODEL, "nanoid": "pnano1"})
    pg_prop_1 = N(label=prop_1.get_label(), props=prop_1.get_attr_dict())
    prop_2 = Property({"handle": "prop_2", "model": MODEL, "nanoid": "pnano2"})
    pg_prop_2 = N(label=prop_2.get_label(), props=prop_2.get_attr_dict())
    valset_1 = ValueSet({"handle": "valset_1", "nanoid": "vnano1"})
    pg_valset_1 = N(label=valset_1.get_label(), props=valset_1.get_attr_dict())
    valset_2 = ValueSet({"handle": "valset_2", "nanoid": "vnano2"})
    pg_valset_2 = N(label=valset_2.get_label(), props=valset_2.get_attr_dict())
    term_1 = Term(
        {"value": "term_1", "origin_name": "origin_name_1", "nanoid": "tnano1"}
    )
    pg_term_1 = N(label=term_1.get_label(), props=term_1.get_attr_dict())
    term_2 = Term(
        {"value": "term_2", "origin_name": "origin_name_2", "nanoid": "tnano2"}
    )
    pg_term_2 = N(label=term_2.get_label(), props=term_2.get_attr_dict())
    term_3 = Term(
        {"value": "term_3", "origin_name": "origin_name_3", "nanoid": "tnano3"}
    )
    pg_term_3 = N(label=term_3.get_label(), props=term_3.get_attr_dict())
    add_ents = [
        node_1,
        node_2,
        edge_1,
        prop_1,
        prop_2,
        valset_1,
        valset_2,
        term_1,
        term_2,
        term_3,
    ]

    @pytest.mark.dumb
    def test_tools_mdb(self, mdb):
        (b, h) = mdb
        mdb = ToolsMDB(uri=b, user="neo4j", password="neo4j1")
        assert mdb

    @pytest.fixture
    def tools_mdb(self, mdb) -> ToolsMDB:
        (b, h) = mdb
        return ToolsMDB(uri=b, user="neo4j", password="neo4j1")

    def test_add_entity_to_mdb(self, tools_mdb) -> None:
        for ent in self.add_ents:
            tools_mdb.add_entity_to_mdb(ent)
            assert tools_mdb._get_entity_count(ent)[0] == 1
        edge_path = G(
            T(self.pg_edge_1, R(Type="has_src"), self.pg_node_1),
            T(self.pg_edge_1, R(Type="has_dst"), self.pg_node_2),
        )
        assert tools_mdb._get_pattern_count(edge_path)[0] == 1

    def test_add_relationship_to_mdb(self, tools_mdb) -> None:
        tools_mdb.add_relationship_to_mdb("has_property", self.node_1, self.prop_1)
        tools_mdb.add_relationship_to_mdb("has_value_set", self.prop_1, self.valset_1)
        tools_mdb.add_relationship_to_mdb("has_term", self.valset_1, self.term_1)
        relationship_path = G(
            T(self.pg_node_1, R(Type="has_property"), self.pg_prop_1),
            T(self.pg_prop_1, R(Type="has_value_set"), self.pg_valset_1),
            T(self.pg_valset_1, R(Type="has_term"), self.pg_term_1),
        )
        assert tools_mdb._get_pattern_count(relationship_path)[0] == 1

    def test_link_synonyms(self, tools_mdb) -> None:
        tools_mdb.link_synonyms(
            self.term_1, self.term_2, mapping_source=self.MAPPING_SOURCE_1
        )
        tools_mdb.link_synonyms(
            self.node_1, self.term_1, mapping_source=self.MAPPING_SOURCE_1
        )
        concept_nanos = tools_mdb.get_concept_nanoids_linked_to_entity(
            entity=self.term_1, mapping_source=self.MAPPING_SOURCE_1
        )
        # should reuse concept created in first link_synonyms() here
        assert len(concept_nanos) == 1
        pg_concept = N(label="concept", props={"nanoid": concept_nanos[0]})
        pg_tag = N(
            label="tag", props={"key": "mapping_source", "value": self.MAPPING_SOURCE_1}
        )
        synonym_path = G(
            T(self.pg_term_1, R(Type="represents"), pg_concept),
            T(self.pg_term_2, R(Type="represents"), pg_concept),
            T(self.pg_node_1, R(Type="has_concept"), pg_concept),
            T(pg_concept, R(Type="has_tag"), pg_tag),
        )
        print(synonym_path.pattern())
        assert tools_mdb._get_pattern_count(synonym_path)[0] == 1

    def test_link_synonyms_diff_src_diff_map(self, tools_mdb) -> None:
        # should add a new concept
        tools_mdb.link_synonyms(
            self.term_2, self.term_3, mapping_source=self.MAPPING_SOURCE_2
        )
        # any mapping source
        concept_nanos = tools_mdb.get_concept_nanoids_linked_to_entity(self.term_2)
        assert len(concept_nanos) == 2
        # source 1
        concept_nanos = tools_mdb.get_concept_nanoids_linked_to_entity(
            self.term_2, self.MAPPING_SOURCE_1
        )
        assert len(concept_nanos) == 1
        # source 2
        concept_nanos = tools_mdb.get_concept_nanoids_linked_to_entity(
            self.term_2, self.MAPPING_SOURCE_2
        )
        assert len(concept_nanos) == 1


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
