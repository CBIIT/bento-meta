import re
import sys
sys.path.append('.')
import pytest
from bento_meta.entity import Entity
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin

def test_create_objects():
  for cls in [Node,Property,Edge,Term,ValueSet,Concept,Origin]:
    n = cls()
    assert n
    assert isinstance(n, Entity)

def test_init_objects():
  case = Node({"model":"test","handle":"case"})
  assert case
  assert case.model == "test"
  assert case['handle'] == "case"
  sample = Node({"model":"test","handle":"sample"})
  assert sample
  of_sample = Edge({"model":"test","handle":"of_sample"})
  assert of_sample
  assert of_sample.model == "test"
  assert of_sample.handle == "of_sample"
  of_sample.src = sample
  of_sample.dst = case
  assert of_sample.dst == case
  assert of_sample.src == sample
  term = Term({"value":"sample"})
  concept = Concept();
  term.concept = concept
  concept.terms={"sample":term}
  sample.concept = concept
  assert of_sample.src.concept.terms["sample"].value == "sample"
  
  
