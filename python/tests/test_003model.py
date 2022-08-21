import re
import sys
sys.path.insert(0,'.')
sys.path.insert(0,'..')
import pytest
from pdb import set_trace
from bento_meta.model import Model, ArgError
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin

def test_init_model():
  with pytest.raises(ArgError, match=".*requires arg 'handle'"):
    Model()
  m = Model('test')
  assert m
  assert m.handle == 'test'

def test_create_model():
  model = Model('test')
  case = Node({"handle":"case"})
#  set_trace()
  case.props['days_to_enrollment'] = Property({"handle":'days_to_enrollment'})
  model.add_node(case)
  assert isinstance(model.nodes['case'],Node)
  assert model.props[('case','days_to_enrollment')]
  model.annotate(case, Term({"value":"case", "origin_name":"CTOS"}))
  assert model.nodes['case'].concept.terms[('case','CTOS')]
  model.add_node({"handle":"sample"})
  assert model.nodes["sample"]
  assert isinstance(model.nodes["sample"],Node)
  assert  model.nodes["sample"].model == 'test'
  case_id = Property({"handle":"case_id","value_domain":"string"})
  model.add_prop(case,case_id)
  assert model.props[("case","case_id")]
  assert model.props[("case","case_id")].value_domain == 'string'
  assert 'case_id' in model.nodes['case'].props
  sample = model.nodes["sample"]
  of_case = Edge({"handle":"of_case","src":sample,"dst":case})
  of_case.props['operator'] = Property({"handle":"operator","value_domain":"boolean"})
  model.annotate(model.props[('case','case_id')],
                 Term({'value': 'case_id', 'origin_name': 'CTOS'}))
  assert case_id.concept.terms[('case_id','CTOS')]
  model.add_edge(of_case)
  assert model.edges[('of_case','sample','case')]
  assert model.contains(of_case.props['operator'])
  assert of_case.props['operator'].model == 'test'
  assert model.props[('of_case','sample','case','operator')]
  assert model.props[('of_case','sample','case','operator')].value_domain == 'boolean'
  model.annotate(of_case, Term({"value": "of_case", "origin_name": "CTOS"}))
  assert model.edges[('of_case','sample','case')].concept.terms[('of_case', 'CTOS')]
  dx = Property({"handle":"diagnosis","value_domain":"value_set"})
  tm = Term({"value":"CRS"})
  model.add_prop(case, dx)
  model.add_terms(dx, tm, 'rockin_pneumonia', 'fungusamongus')
  assert {x.value for x in dx.terms.values()} == { 'CRS', 'rockin_pneumonia', 'fungusamongus'}
  
