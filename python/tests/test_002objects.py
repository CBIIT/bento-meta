import re
import sys
from pdb import set_trace
sys.path.append('.')
import pytest
from bento_meta.entity import Entity
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin, Tag

def test_create_objects():
  for cls in [Node,Property,Edge,Term,ValueSet,Concept,Origin,Tag]:
    n = cls()
    assert n
    assert isinstance(n, Entity)

def test_init_and_link_objects():
  case = Node({"model":"test","handle":"case"})
  assert case
  assert case.model == "test"
  assert case.handle == "case"
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

  concept.terms["sample"]=term
  sample.concept = concept
  [o] = [x for x in term.belongs.values()]
  assert o == concept
  assert of_sample.src.concept.terms["sample"].value == "sample"

def test_tags_on_objects():
  nodeTag = Tag({"key":"name","value":"Neddy"})
  relnTag = Tag({"key":"name","value":"Robby"})
  conceptTag = Tag({"key":"name","value":"Catty"})
  conceptTag2 = Tag({"key":"aka","value":"Jehoshaphat"})
  termTag = Tag({"key":"name","value":"Termy"})
  propTag = Tag({"key":"name","value":"Puppy"})
  
  case = Node({"model":"test","handle":"case"})
  of_sample = Edge({"model":"test","handle":"of_sample"})
  sample = Node({"model":"test","handle":"sample"})  
  of_sample.src = sample
  of_sample.dst = case
  term = Term({"value":"sample"})
  concept = Concept();
  term.concept = concept
  concept.terms["sample"]=term
  sample.concept = concept
  sample.props['this'] = Property({"that":"this"})

  case.tags[nodeTag.key] = nodeTag
  of_sample.tags[relnTag.key] = relnTag
  term.tags[termTag.key] = termTag
  concept.tags[conceptTag.key] = conceptTag
  concept.tags[conceptTag2.key] = conceptTag2
  sample.props['this'].tags['name'] = propTag

  names = [x.tags['name'].value for x in [case,of_sample,term,concept,sample.props['this']]];
  assert names == ["Neddy","Robby","Termy","Catty","Puppy"]
  assert concept.tags['aka'].value == "Jehoshaphat"

def test_some_object_methods():
  p = Property({"handle":"complaint"})
  assert p
  t = Term({"value":"halitosis"})
  assert t
  u = Term({"value":"ptomaine"})
  assert u
  vs = ValueSet({"_id":"1"})
  assert vs
  p.value_set = vs
  vs.terms['ptomaine'] = u
  assert p.terms['ptomaine'].value == 'ptomaine'
  p.terms['halitosis'] = t
  assert vs.terms['halitosis'].value == 'halitosis'
  vals = p.values
  assert isinstance(vals,list)
  assert 'ptomaine' in vals
  assert 'halitosis' in vals
  s = Node({'handle':"case"})
  assert s
  d = Node({'handle':"cohort"})
  assert d
  e = Edge({'handle':"member_of",'src':s,'dst':d})
  assert e
  assert e.triplet == ('member_of','case','cohort')
  

  
