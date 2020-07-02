import re
import sys
sys.path.extend(['.','..'])
import pytest
import pytest_docker
from neo4j import GraphDatabase
import neo4j.graph
from neo4j.exceptions import Neo4jError
from pdb import set_trace
from bento_meta.entity import *
from bento_meta.objects import *
from bento_meta.model import Model

def test_get_model(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
  m = Model('ICDC',drv)
  m.dget()

  with drv.session() as session:
    result = session.run('match (n:node) where n.model="ICDC" return count(n)')
    assert len(m.nodes) == result.single().value()
    result = session.run('match (n:relationship) where n.model="ICDC" return count(n)')
    assert len(m.edges) == result.single().value()
    result = session.run('match (p:property)<--(n:node) where p.model="ICDC" and  n.model="ICDC" return count(p)')
    assert len(m.props) == result.single().value()
    result = session.run(
      'match (s:node)<-[:has_src]-(e:relationship)-[:has_dst]->(d:node) where e.model="ICDC" return s,e,d')
    for rec in result:
      (s,e,d) = (rec['s'],rec['e'],rec['d'])
      triplet = (e['handle'], s['handle'], d['handle'])
      assert m.edges[triplet].handle == e['handle']
      assert m.edges[triplet].src.handle == s['handle']
      assert m.edges[triplet].dst.handle == d['handle']

    result = session.run(
      'match (n:node)-[:has_property]->(p:property) where (n.model="ICDC") return n, collect(p) as pp')
    for rec in result:
      for p in rec['pp']:
        key = (rec['n']['handle'], p['handle'])
        assert m.props[key]
        assert m.props[key].neoid == p.id
        assert m.nodes[rec['n']['handle']].props[p['handle']].neoid == p.id

    result = session.run(
      'match (t:term)<-[:has_term]-(v:value_set)<-[:has_value_set]-(p:property) where p.model="ICDC" return p, v, collect(t) as tt')
    for rec in result:
      (p, v, tt) = (rec['p'],rec['v'],rec['tt'])
      [op] = [ x for x in m.props.values() if x.handle == p['handle'] ]
      vs = op.value_set
      assert op
      assert set( op.values ) == { t['value'] for t in tt }

def test_put_model(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
  m = Model('ICDC',drv)
  pass
