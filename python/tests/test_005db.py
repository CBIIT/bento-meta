import re
import sys
sys.path.extend(['.','..'])
import pytest
import pytest_docker
from neo4j import GraphDatabase
import neo4j.graph
from neo4j.exceptions import Neo4jError
from pdb import set_trace
from bento_meta.object_map import ObjectMap
from bento_meta.entity import *
from bento_meta.objects import *

def test_get(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
  node_map = ObjectMap(cls=Node,drv=drv)
  Node.object_map=node_map
  Concept.object_map=ObjectMap(cls=Concept,drv=drv)
  Property.object_map=ObjectMap(cls=Property,drv=drv)  
  n_id=None
  with node_map.drv.session() as session:
    result = session.run("match (a:node) return id(a) limit 1")
    n_id = result.single().value()
  assert n_id
  node = Node()
  node.neoid = n_id
  node_map.get(node)
  assert node.dirty==0
  assert node.__dict__['concept'].dirty == -1 # before dget()
  assert node.concept.dirty == 0 # after dget()
  assert node.concept._id == "a5b87a02-1eb3-4ec9-881d-f4479ab917ac"
  assert len(node.props) == 3
  assert node.props.data['site_short_name'].dirty == -1  # before dget()
  assert node.props['site_short_name'].dirty == 0 # after dget()
  assert node.props['site_short_name'].model == 'ICDC'
  concept = node.concept
  assert concept.belongs[(id(node), 'concept')] == node
  owners = node_map.get_owners(node)
  assert len(owners) == 1
  cncpt = Concept()
  Concept.object_map.get_by_id(cncpt,"a5b87a02-1eb3-4ec9-881d-f4479ab917ac")
  assert cncpt.terms[0] == concept.terms[0]
  pass


def test_put_rm(bento_neo4j):  
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  vs_map = ObjectMap(cls=ValueSet,drv=drv)
  term_map = ObjectMap(cls=Term,drv=drv)
  vs = ValueSet({"_id":"narb"})
  terms = [Term({"value":x}) for x in ['quilm','ferb','narquit']]
  vs.terms=terms
  assert vs.terms['ferb'].value == 'ferb'
  vs_map.put(vs)
  rt = []
  with vs_map.drv.session() as session:
    result = session.run("match (v:value_set)-[:has_term]->(t:term) where v.id='narb' return t order by t.value")
    for rec in result:
      rt.append(rec['t']['value'])
  assert set(rt) == set(['ferb','narquit','quilm'])
  quilm = vs.terms['quilm']
  del vs.terms['quilm']
  assert len(vs.terms)==2
  with pytest.raises(Neo4jError,match='.*Cannot delete'):
    term_map.rm(quilm)
  t_id=None
  with term_map.drv.session() as session:
    result = session.run("match (t:term {value:'quilm'}) return id(t)")
    t_id = result.single().value()
  assert t_id == quilm.neoid
  term_map.rm(quilm, 1)
  with term_map.drv.session() as session:
    result = session.run("match (t:term {value:'quilm'}) return id(t)")
    assert result.single() == None

  new_term = Term({"value":"belpit"})
  term_map.put(new_term)
  vs_map.add(vs, 'terms', new_term)
  assert len(vs.terms) == 2
  vs_map.get(vs,True)
  assert len(vs.terms) == 3
  assert vs.terms['belpit']
  old_term = vs.terms['ferb']
  r = None
  with term_map.drv.session() as session:
    result = session.run("match (t:term {value:'ferb'})<-[r]-(v:value_set) return r")
    r = result.single().value()
    assert isinstance(r,neo4j.graph.Relationship)
  vs_map.drop(vs,'terms',old_term)
  with term_map.drv.session() as session:
    result = session.run("match (t:term {value:'ferb'})<-[r]-(v:value_set) return r")
    assert result.single() == None
  old_term = vs.terms['belpit']
