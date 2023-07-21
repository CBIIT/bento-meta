"""Tests for changelog generation scripts """
import os
import sys

from bento_mdf.diff import diff_models
from bento_mdf.mdf import MDF
from bento_meta.objects import Property
from scripts.make_diff_changelog import convert_diff_to_changelog
from scripts.make_mapping_changelog import convert_mappings_to_changelog
from scripts.make_model_changelog import (
    convert_model_to_changelog,
    escape_quotes_in_attr,
)

sys.path.append("../")

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


# test changelog generation
# make_model_changelog
def test_make_model_changelog():
    mdf = MDF(TEST_MDF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
    changelog = convert_model_to_changelog(
        model=mdf.model, author=AUTHOR, config_file_path=TEST_CHANGELOG_CONFIG
    )
    assert len(changelog.subelements) == 46


# make_diff_changelog
def test_make_diff_changelog():
    mdf_old = MDF(TEST_MDF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
    mdf_new = MDF(TEST_MDF_DIFF, handle=MODEL_HDL, _commit=_COMMIT, raiseError=True)
    diff = diff_models(mdl_a=mdf_old.model, mdl_b=mdf_new.model)
    changelog = convert_diff_to_changelog(
        diff=diff,
        model_handle=MODEL_HDL,
        author=AUTHOR,
        config_file_path=TEST_CHANGELOG_CONFIG,
    )
    assert len(changelog.subelements) == 33


# make_mapping_changelog
def test_make_mapping_changelog():
    changelog = convert_mappings_to_changelog(
        mapping_mdf=TEST_MAPPING_MDF,
        author=AUTHOR,
        config_file_path=TEST_CHANGELOG_CONFIG,
        _commit=_COMMIT,
    )
    assert len(changelog.subelements) == 6


def test_escape_quotes_in_attr():
    prop = Property(
        {"handle": "Quote's Handle", "desc": """quote's quote\'s "quotes\""""}
    )
    escape_quotes_in_attr(prop)

    assert prop.handle == r"""Quote\'s Handle"""
    assert prop.desc == r"""quote\'s quote\'s \"quotes\""""


test_make_model_changelog()
