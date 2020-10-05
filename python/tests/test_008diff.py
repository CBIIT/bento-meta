import re
import sys
sys.path.extend(['.','..'])
import pytest
#from pdb import set_trace
from bento_meta.mdf import MDF
from bento_meta.diff import diff_models
#from bento_meta.entity import ArgError
#from bento_meta.model import Model
#from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin


def test_diff_of_same_yaml():
    '''diff of a yml against a copy of itself better darn be empty'''
    a = MDF('tests/samples/test-model.yml', handle='test')
    b = MDF('tests/samples/test-model-a.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {}
    assert actual == expected


def test_diff_of_extra_node_properties_and_terms():
    '''a_b'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-b.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'nodes': {'file': {'props': {'a': set(), 'b': {'encryption_type'}}}}, 'props': {('sample', 'sample_type'): {'value_set': {'a': set(), 'b': {'not a tumor'}}}, 'a': set(), 'b': {('file', 'encryption_type')}}}
    assert actual == expected


def test_diff_of_extra_node_property():
    '''a_d'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-d.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'nodes': {'diagnosis': {'props': {'a': set(), 'b': {'fatal'}}}}, 'props': {'a': set(), 'b': {('diagnosis', 'fatal')}}}
    assert actual == expected


def test_diff_of_extra_node_edge_and_property():
    '''a_e'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-e.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'nodes': {'a': set(), 'b': {'outcome'}}, 'edges': {'a': set(), 'b': {('end_result', 'diagnosis', 'outcome')}}, 'props': {'a': set(), 'b': {('outcome', 'fatal')}}}
    assert actual == expected


def test_diff_where_yaml_has_extra_term():
    '''c_d'''
    a = MDF('tests/samples/test-model-c.yml', handle='test')
    b = MDF('tests/samples/test-model-d.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'props': {('diagnosis', 'fatal'): {'value_set': {'a': set(), 'b': {'unknown'}}}}}
    assert actual == expected


def test_diff_of_assorted_changes():
    '''d_e'''
    a = MDF('tests/samples/test-model-d.yml', handle='test')
    b = MDF('tests/samples/test-model-e.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'nodes': {'diagnosis': {'props': {'a': {'fatal'}, 'b': set()}}, 'a': set(), 'b': {'outcome'}}, 'edges': {'a': set(), 'b': {('end_result', 'diagnosis', 'outcome')}}, 'props': {'a': {('diagnosis', 'fatal')}, 'b': {('outcome', 'fatal')}}}
    assert actual == expected
