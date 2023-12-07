"""Tests for changelog generation scripts """
import os
import re
import sys

from bento_mdf.mdf import MDF
from bento_meta.model import Model
from bento_meta.objects import Node, Property
from bento_meta.util.changelog import update_config_changeset_id
from liquichange.changelog import Changeset

sys.path.append("../")

from scripts.make_mapping_changelog import convert_mappings_to_changelog
from scripts.make_model_changelog import (
    convert_model_to_changelog,
    escape_quotes_in_attr,
)

# define filepaths for sample MDFs
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEST_MODEL_MDF = os.path.join(CURRENT_DIRECTORY, "samples", "test_mdf.yml")
TEST_MAPPING_MDF = os.path.join(CURRENT_DIRECTORY, "samples", "test_mapping_mdf.yml")
# changelog config probably not needed for these tests? remove below & file from samples?
TEST_CHANGELOG_CONFIG = os.path.join(CURRENT_DIRECTORY, "samples", "test_changelog.ini")
AUTHOR = "Tolkien"
MODEL_HDL = "TEST"
_COMMIT = "_COMMIT_123"


def remove_nanoids_from_str(statement: str) -> str:
    """removes values for 'nanoid' attr from string if present"""
    return re.sub(r"nanoid:'[^']*'", "nanoid:''", statement)


class TestMakeModelChangelog:
    def test_make_model_changelog_length(self):
        mdf = MDF(TEST_MODEL_MDF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
        changelog = convert_model_to_changelog(
            model=mdf.model, author=AUTHOR, config_file_path=TEST_CHANGELOG_CONFIG
        )
        update_config_changeset_id(TEST_CHANGELOG_CONFIG, 1)
        actual = len(changelog.subelements)
        expected = 46
        assert actual == expected

    def test_make_model_changelog_shared_props(self):
        """multiple nodes share property with the same handle"""
        model = Model(handle=MODEL_HDL)
        node_1 = Node({"handle": "cell_line", "model": MODEL_HDL})
        node_2 = Node({"handle": "clinical_measure_file", "model": MODEL_HDL})
        prop_1 = Property(
            {
                "handle": "id",
                "model": "TEST",
                "value_domain": "string",
                "desc": "desc of id",
            }
        )
        node_1.props = {prop_1.handle: prop_1}
        node_2.props = {prop_1.handle: prop_1}
        model.nodes = {node_1.handle: node_1, node_2.handle: node_2}
        model.props = {
            (node_1.handle, prop_1.handle): prop_1,
            (node_2.handle, prop_1.handle): prop_1,
        }
        changelog = convert_model_to_changelog(
            model=model, author=AUTHOR, config_file_path=TEST_CHANGELOG_CONFIG
        )
        update_config_changeset_id(TEST_CHANGELOG_CONFIG, 1)
        actual = [
            remove_nanoids_from_str(x.change_type.text) for x in changelog.subelements
        ]
        expected = [
            "CREATE (n0:node {handle:'cell_line',model:'TEST'})",
            "CREATE (n0:property "
            "{handle:'id',model:'TEST',value_domain:'string',desc:'desc of "
            "id',nanoid:''})",
            "CREATE (n0:node {handle:'clinical_measure_file',model:'TEST'})",
            "CREATE (n0:property "
            "{handle:'id',model:'TEST',value_domain:'string',desc:'desc of "
            "id',nanoid:''})",
            "MATCH (n0:node {handle:'cell_line',model:'TEST'}), (n1:property "
            "{handle:'id',model:'TEST',value_domain:'string',desc:'desc of "
            "id',nanoid:''}) MERGE (n0)-[r0:has_property]->(n1)",
            "MATCH (n0:node {handle:'clinical_measure_file',model:'TEST'}), (n1:property "
            "{handle:'id',model:'TEST',value_domain:'string',desc:'desc of "
            "id',nanoid:''}) MERGE (n0)-[r0:has_property]->(n1)",
        ]
        assert actual == expected


# make_mapping_changelog
def test_make_mapping_changelog():
    changelog = convert_mappings_to_changelog(
        mapping_mdf=TEST_MAPPING_MDF,
        author=AUTHOR,
        config_file_path=TEST_CHANGELOG_CONFIG,
        _commit=_COMMIT,
    )
    update_config_changeset_id(TEST_CHANGELOG_CONFIG, 1)
    sample_changeset = changelog.subelements[0]
    assert isinstance(sample_changeset, Changeset)
    assert sample_changeset.run_always is True
    assert len(changelog.subelements) == 6


def test_escape_quotes_in_attr():
    prop = Property(
        {"handle": "Quote's Handle", "desc": """quote's quote\'s "quotes\""""}
    )
    escape_quotes_in_attr(prop)

    assert prop.handle == r"""Quote\'s Handle"""
    assert prop.desc == r"""quote\'s quote\'s \"quotes\""""
