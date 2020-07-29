import re
import sys
sys.path.extend(['.','..'])
import pytest
from pdb import set_trace
from bento_meta.object_map import ObjectMap
from bento_meta.entity import Entity, ArgError
from bento_meta.objects import Node,Property,Term,Concept,Origin,ValueSet,Tag,mergespec

# FakeNode for testing ['relationship']['endcls'] = a _tuple_
class FakeNode(Entity):
  attspec = {"handle":"simple","model":"simple",
             "category":"simple", "concept":"object",
             "props":"collection"}
  
  mapspec_={"label":"node",
             "property": {"handle":"handle","model":"model","category":"category"},
             "relationship": {
               "concept": { "rel" : ":has_concept>",
                            "end_cls" : {"Concept","Term"} },
               "props": { "rel" : ":has_property>",
                          "end_cls" : "Property" }
               }}
  (attspec, _mapspec) = mergespec('FakeNode',attspec,mapspec_)
  def __init__(self, init=None):
    super().__init__(init=init)
  

def test_class():
  m = ObjectMap(cls=Node)
  assert isinstance(m, ObjectMap)
  assert m.cls.mapspec()["label"] == 'node'
  assert m.cls.attspec["props"] == 'collection'
  assert m.cls.attspec["_next"] == 'object'
  for c in (Node,Property,Term,Concept,Origin,Tag):
    assert isinstance(ObjectMap(cls=c),ObjectMap)
    assert c.mapspec()["label"] == c.__name__.lower()

def test_get_queries():
  m = ObjectMap(cls=Node)
  with pytest.raises(ArgError, match='arg1 must be object of class'):
    m.get_q(ValueSet())
  with pytest.raises(ArgError, match='object must be mapped'):
    m.get_q(Node())
  n = Node({"handle":"test","model":"test"})
  n.neoid=1
  qry = m.get_q(n)
  assert qry == "MATCH (n:node) WHERE id(n)=1 RETURN n,id(n)"
  with pytest.raises(ArgError,match="'flerb' is not a registered attribute"):
    m.get_attr_q(n,'flerb')
  qry = m.get_attr_q(n,'model')
  assert qry == "MATCH (n:node) WHERE id(n)=1 RETURN n.model"
  qry = m.get_attr_q(n,'props')
  assert qry == "MATCH (n:node)-[:has_property]->(a:property) WHERE id(n)=1 RETURN a"
  qry = m.get_attr_q(n,'concept')
  assert qry == "MATCH (n:node)-[:has_concept]->(a:concept) WHERE id(n)=1 RETURN a LIMIT 1"  

def test_put_queries():
  m = ObjectMap(cls=Node)
  n = Node({"handle":"test","model":"test_model","category":1})
  qry = m.put_q(n)
  assert qry==['CREATE (n:node {handle:"test",model:"test_model",category:1}) RETURN n,id(n)']
  n.neoid=2
  stmts = m.put_q(n)
  assert stmts[0]=='MATCH (n:node) WHERE id(n)=2 SET n.handle="test",n.model="test_model",n.category=1 RETURN n,id(n)'
  assert len(stmts[1:]) == len([x for x in Node.attspec if Node.attspec[x] == 'simple'])-3
  for s in stmts[1:]:
    assert re.match('^MATCH \\(n:node\\) WHERE id\\(n\\)=2 REMOVE n.[a-z_]+ RETURN n,id\\(n\\)$',s)
  n.neoid=None
  with pytest.raises(ArgError, match='object must be mapped'):
    m.put_attr_q(n,'category',2)
  n.neoid=1
  c = Concept({"_id":"blarf"})
  with pytest.raises(ArgError, match="'values' must be a list of mapped Entity objects"):
    m.put_attr_q(n,'concept',c)
  with pytest.raises(ArgError, match="'values' must be a list of mapped Entity objects"):  
    m.put_attr_q(n,'concept',[c])
  qry = m.put_attr_q(n,'category',[3])
  assert qry=="MATCH (n:node) WHERE id(n)=1 SET category=3 RETURN id(n)"
  c.neoid=2
  stmts = m.put_attr_q(n,'concept',[c])
  assert stmts[0] == "MATCH (n:node),(a:concept) WHERE id(n)=1 AND id(a)=2 MERGE (n)-[:has_concept]->(a) RETURN id(a)"
  assert len(stmts) == 1
  prps = [Property(x) for x in ( {"model":"test","handle":"prop1"},
                                 {"model":"test","handle":"prop2"},
                                 {"model":"test","handle":"prop3"} )]
  i=5
  for p in prps:
    p.neoid=i
    i+=1
  stmts = m.put_attr_q(n,'props',prps)
  assert stmts[0] == "MATCH (n:node),(a:property) WHERE id(n)=1 AND id(a)=5 MERGE (n)-[:has_property]->(a) RETURN id(a)"
  assert len(stmts) == 3
  m=ObjectMap(cls=FakeNode)
  n=FakeNode({"handle":"test","model":"test_model","category":1})
  n.neoid=1
  t = Term({"value":"boog"})
  t.neoid=6
  stmts = m.put_attr_q(n,"concept",[t])
  assert re.match("MATCH \\(n:node\\),\\(a\\) WHERE id\\(n\\)=1 AND id\\(a\\)=6 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) MERGE \\(n\\)-\\[:has_concept\\]->\\(a\\) RETURN id\\(a\\)",stmts[0])
  qry = m.get_attr_q(n,"concept")
  assert re.match("MATCH \\(n:node\\)-\\[:has_concept\\]->\\(a\\) WHERE id\\(n\\)=1 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) RETURN a",qry)
  pass

def test_rm_queries():
  m = ObjectMap(cls=FakeNode)
  n = FakeNode({"handle":"test","model":"test_model","category":1})
  assert FakeNode.mapspec()["relationship"]["concept"]["end_cls"] == {"Concept","Term"}
  with pytest.raises(ArgError,match="object must be mapped"):
    m.rm_q(n)
  n.neoid=1
  qry = m.rm_q(n)
  assert qry=='MATCH (n:node) WHERE id(n)=1 DELETE n'
  qry = m.rm_q(n,detach=True)
  assert qry=='MATCH (n:node) WHERE id(n)=1 DETACH DELETE n'
  c = Concept({"_id":"blerf"})
  qry = m.rm_attr_q(n,'model')
  assert qry=='MATCH (n:node) WHERE id(n)=1 REMOVE n.model RETURN id(n)'
  qry = m.rm_attr_q(n,'props',[':all'])
  assert qry=='MATCH (n:node)-[r:has_property]->(a:property) WHERE id(n)=1 DELETE r RETURN id(n),id(a)'
  qry = m.rm_attr_q(n,'concept',[':all'])
  assert re.match("MATCH \\(n:node\\)-\\[r:has_concept\\]->\\(a\\) WHERE id\\(n\\)=1 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) DELETE r",qry)
  prps = [Property(x) for x in ( {"model":"test","handle":"prop1"},
                                 {"model":"test","handle":"prop2"},
                                 {"model":"test","handle":"prop3"} )]
  i=5
  for p in prps:
    p.neoid=i
    i+=1
  stmts = m.rm_attr_q(n,'props',prps)
  assert stmts[0] == "MATCH (n:node)-[r:has_property]->(a:property) WHERE id(n)=1 AND id(a)=5 DELETE r RETURN id(n),id(a)"
  assert len(stmts) == 3


def test_put_then_rm_queries():
  """test adding then removing attr"""
  m = ObjectMap(cls=Node)
  n = Node({"handle":"test_","model":"test_model_","category":1})
  qry = m.put_q(n)
  assert qry==['CREATE (n:node {handle:"test_",model:"test_model_",category:1}) RETURN n,id(n)']

  # manually set neoid
  n.neoid=2
  stmts = m.put_q(n)
  assert stmts[0]=='MATCH (n:node) WHERE id(n)=2 SET n.handle="test_",n.model="test_model_",n.category=1 RETURN n,id(n)'
  assert len(stmts[1:]) == len([x for x in Node.attspec if Node.attspec[x] == 'simple'])-3
  for s in stmts[1:]:
    assert re.match('^MATCH \\(n:node\\) WHERE id\\(n\\)=2 REMOVE n.[a-z_]+ RETURN n,id\\(n\\)$',s)

  n.neoid=None
  with pytest.raises(ArgError, match='object must be mapped'):
    m.put_attr_q(n,'category',2)

  n.neoid=1
  c = Concept({"_id":"blarfblark"})
  with pytest.raises(ArgError, match="'values' must be a list of mapped Entity objects"):
    m.put_attr_q(n,'concept',c)
  with pytest.raises(ArgError, match="'values' must be a list of mapped Entity objects"):  
    m.put_attr_q(n,'concept',[c])

  qry = m.put_attr_q(n,'category',[3])
  assert qry=="MATCH (n:node) WHERE id(n)=1 SET category=3 RETURN id(n)"

  c.neoid=2
  stmts = m.put_attr_q(n,'concept',[c])
  #assert stmts[0] == "MATCH (n:node),(a:concept) WHERE id(n)=1 AND id(a)=2 MERGE (n)-[:has_concept]->(a) RETURN id(a)"
  assert len(stmts) == 1

  prps = [Property(x) for x in ( {"model":"test_","handle":"prop1"},
                                 {"model":"test_","handle":"prop2"},
                                 {"model":"test_","handle":"prop3"} )]
  i=5
  for p in prps:
    p.neoid=i
    i+=1
  stmts = m.put_attr_q(n,'props',prps)
  assert stmts[0] == "MATCH (n:node),(a:property) WHERE id(n)=1 AND id(a)=5 MERGE (n)-[:has_property]->(a) RETURN id(a)"
  assert len(stmts) == 3
  Node.mapspec_={"label":"node",
             "property": {"handle":"handle","model":"model","category":"category"},
             "relationship": {
               "concept": { "rel" : ":has_concept>",
                            "end_cls" : {"Concept","Term"} },
               "props": { "rel" : ":has_property>",
                          "end_cls" : "Property" }
               }}
  (Node.attspec, Node._mapspec) = mergespec('Node',Node.attspec,Node.mapspec_)
  assert Node.mapspec()["relationship"]["concept"]["end_cls"] == {"Concept","Term"}
  t = Term({"value":"boogblark"})
  t.neoid=6
  stmts = m.put_attr_q(n,"concept",[t])
  assert re.match("MATCH \\(n:node\\),\\(a\\) WHERE id\\(n\\)=1 AND id\\(a\\)=6 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) MERGE \\(n\\)-\\[:has_concept\\]->\\(a\\) RETURN id\\(a\\)",stmts[0])
  qry = m.get_attr_q(n,"concept")
  assert re.match("MATCH \\(n:node\\)-\\[:has_concept\\]->\\(a\\) WHERE id\\(n\\)=1 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) RETURN a",qry)

  # now delete the attr I just added....
  qry2 = m.rm_attr_q(n, "concept", [t])
  assert re.match("MATCH \\(n:node\\)-\\[r:has_concept\\]->\\(a\\) WHERE id\\(n\\)=1 AND id\\(a\\)=6 AND \\('[a-z]+' IN labels\\(a\\) OR '[a-z]+' IN labels\\(a\\)\\) DELETE r RETURN id\\(n\\),id\\(a\\)",qry2[0])

