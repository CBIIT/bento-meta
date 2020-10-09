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
    #expected = {'nodes': {'file': {'props': {'a': set(), 'b': {'encryption_type'}}}}, 'props': {('sample', 'sample_type'): {'value_set': {'a': set(), 'b': {'not a tumor'}}}, 'a': set(), 'b': {('file', 'encryption_type')}}}
    expected = {'nodes': {'file': {'props': {'a': None, 'b': ['encryption_type']}}}, 'props': {('sample', 'sample_type'): {'value_set': {'a': None, 'b': ['not a tumor']}}, 'a': None, 'b': [('file', 'encryption_type')]}}
    assert actual == expected


def test_diff_of_extra_node_property():
    '''a_d'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-d.yml', handle='test')
    actual = diff_models(a.model, b.model)
    #expected = {'nodes': {'diagnosis': {'props': {'a': set(), 'b': {'fatal'}}}}, 'props': {'a': set(), 'b': {('diagnosis', 'fatal')}}}
    expected = {'nodes': {'diagnosis': {'props': {'a': None, 'b': ['fatal']}}}, 'props': {'a': None, 'b': [('diagnosis', 'fatal')]}}
    assert actual == expected


def test_diff_of_extra_node_edge_and_property():
    '''a_e'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-e.yml', handle='test')
    actual = diff_models(a.model, b.model)
    #expected = {'nodes': {'a': set(), 'b': {'outcome'}}, 'edges': {'a': set(), 'b': {('end_result', 'diagnosis', 'outcome')}}, 'props': {'a': set(), 'b': {('outcome', 'fatal')}}}
    expected = {'nodes': {'a': None, 'b': ['outcome']}, 'edges': {'a': None, 'b': [('end_result', 'diagnosis', 'outcome')]}, 'props': {'a': None, 'b': [('outcome', 'fatal')]}}
    assert actual == expected

def test_diff_of_extra_node():
    '''a_f'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-f.yml', handle='test')
    actual = diff_models(a.model, b.model)
    #expected = {'nodes': {'a': {'diagnosis'}, 'b': set()}, 'edges': {'a': {('of_case', 'diagnosis', 'case')}, 'b': set()}, 'props': {'a': {('diagnosis', 'disease')}, 'b': set()}}
    expected = {'nodes': {'a': ['diagnosis'], 'b': None}, 'edges': {'a': [('of_case', 'diagnosis', 'case')], 'b': None}, 'props': {'a': [('diagnosis', 'disease')], 'b': None}}
    assert actual == expected


def test_diff_of_missing_node():
    '''a_g'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-g.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'nodes': {'a': None, 'b': ['outcome']}, 'props': {'a': None, 'b': [('outcome', 'disease')]}}
    assert actual == expected


def test_diff_of_swapped_nodeprops():
    '''a_h'''
    a = MDF('tests/samples/test-model-a.yml', handle='test')
    b = MDF('tests/samples/test-model-h.yml', handle='test')
    actual = diff_models(a.model, b.model)
    #expected = {'nodes': {'file': {'props': {'a': {'file_name', 'file_size', 'md5sum'}, 'b': {'disease'}}}, 'diagnosis': {'props': {'a': {'disease'}, 'b': {'file_name', 'file_size', 'md5sum'}}}}, 'props': {'a': {('file', 'file_name'), ('file', 'file_size'), ('diagnosis', 'disease'), ('file', 'md5sum')}, 'b': {('diagnosis', 'file_name'), ('file', 'disease'), ('diagnosis', 'file_size'), ('diagnosis', 'md5sum')}}}
    #expected = {'nodes': {'file': {'props': {'a': ['file_name', 'file_size', 'md5sum'], 'b': ['disease']}}, 'diagnosis': {'props': {'a': ['disease'], 'b': ['file_name', 'file_size', 'md5sum']}}}, 'props': {'a': [('file', 'file_name'), ('file', 'file_size'), ('diagnosis', 'disease'), ('file', 'md5sum')], 'b': [('diagnosis', 'file_name'), ('file', 'disease'), ('diagnosis', 'file_size'), ('diagnosis', 'md5sum')]}}
    expected = {'nodes': {
                          'diagnosis': {'props': {'a': ['disease'], 'b': ['file_name', 'file_size', 'md5sum']}},
                           'file': {'props': {'a': ['file_name', 'file_size', 'md5sum'], 'b': ['disease']}}
                         },
                'props': {'a': [ 
                                 ('diagnosis', 'disease'), 
                                 ('file', 'file_name'), 
                                 ('file', 'file_size'), 
                                 ('file', 'md5sum')
                               ], 
                          
                          'b': [('diagnosis', 'file_name'), 
                                ('diagnosis', 'file_size'), 
                                ('diagnosis', 'md5sum'),
                                ('file', 'disease')
                               ] 
                         }
              }
    assert actual == expected


def test_diff_where_yaml_has_extra_term():
    '''c_d'''
    a = MDF('tests/samples/test-model-c.yml', handle='test')
    b = MDF('tests/samples/test-model-d.yml', handle='test')
    actual = diff_models(a.model, b.model)
    expected = {'props': {('diagnosis', 'fatal'): {'value_set': {'a': None, 'b': ['unknown']}}}}
    assert actual == expected


def test_diff_of_assorted_changes():
    '''d_e'''
    a = MDF('tests/samples/test-model-d.yml', handle='test')
    b = MDF('tests/samples/test-model-e.yml', handle='test')
    actual = diff_models(a.model, b.model)
    #expected = {'nodes': {'diagnosis': {'props': {'a': {'fatal'}, 'b': set()}}, 'a': set(), 'b': {'outcome'}}, 'edges': {'a': set(), 'b': {('end_result', 'diagnosis', 'outcome')}}, 'props': {'a': {('diagnosis', 'fatal')}, 'b': {('outcome', 'fatal')}}}
    expected = {'nodes': {'diagnosis': {'props': {'a': ['fatal'], 'b': None}}, 'a': None, 'b': ['outcome']}, 'edges': {'a': None, 'b': [('end_result', 'diagnosis', 'outcome')]}, 'props': {'a': [('diagnosis', 'fatal')], 'b': [('outcome', 'fatal')]}}
    assert actual == expected
