import re
import sys
sys.path.extend(['.','..'])
import pytest
import pytest_docker
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from pdb import set_trace
import requests
from bento_meta.object_map import ObjectMap
from bento_meta.entity import *
from bento_meta.objects import *

def test_get(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
  node_map = ObjectMap(cls=Node,drv=drv)
  n_id=None
  with node_map.drv.session() as session:
    result = session.run("match (a:node) return id(a) limit 1")
    n_id = result.single().value()
  assert n_id
  node = Node()
  node.neoid = n_id
  node_map.get(node)
  assert node.dirty==0
  assert node['concept'].dirty == -1
  assert node['concept']._id == "a5b87a02-1eb3-4ec9-881d-f4479ab917ac"
  assert len(node['props']) == 3
  assert node['props']['site_short_name'].dirty == -1
  assert node['props']['site_short_name'].model == 'ICDC'
  concept = node['concept']
  assert concept.belongs[(id(node), 'concept')] == node
  owners = node_map.get_owners(node)
  assert len(owners) == 1

def test_put(bento_neo4j):  
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
  quilm = vs['terms']['quilm']
  del vs['terms']['quilm']
  assert len(vs['terms'])==2
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
