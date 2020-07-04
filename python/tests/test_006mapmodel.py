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
from bento_meta.object_map import ObjectMap

def test_get_model(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
  ObjectMap.clear_cache()
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
  ObjectMap.clear_cache()
  m = Model('ICDC',drv)
  m.dget()
  prop = m.props[('sample','sample_type')]
  sample = m.nodes['sample']
  edge = m.edges[('on_visit','sample', 'visit')]
  term = Term({"value":"electric_boogaloo"})
  m.add_terms(prop, term)
  node = m.nodes['lab_exam']
  node.category = 'boog'
  m.dput()
  with drv.session() as session:
    result = session.run('match (v:value_set)-->(t:term {value:"electric_boogaloo"}) return v,t')
    rec = result.single()
    assert rec['v'].id == prop.value_set.neoid
    assert rec['t'].id == term.neoid
    assert rec['t']['value'] == term.value
    result = session.run('match (n:node {handle:"lab_exam",category:"boog"}) return n')
    rec = result.single()
    assert rec['n'].id == node.neoid

  term = m.props[('demographic','sex')].terms['M']
  assert term.concept
  assert term.concept._id == "337c0e4f-506a-4f4e-95f6-07c3462b81ff"

  concept = term.concept
  assert term in concept.belongs.values()
  term.concept=None
  assert not term in concept.belongs.values()
  assert ('concept',concept) in term.removed_entities
  m.dput()
  with drv.session() as session:
    result = session.run('match (t:term) where id(t)=$id return t',{"id":term.neoid})
    assert result.single() # term there
    result = session.run('match (c:concept) where id(c)=$id return c',{"id":concept.neoid})
    assert result.single() # concept there
    result = session.run('match (t:term)-->(c:concept) where id(t)=$id return t',{"id":term.neoid})
    assert not result.single() # but link is gone
  
    concept._id="heydude"
    term.concept = concept
    prop.model = None
    assert not prop.model

  m.dput()

  with drv.session() as session:
    result = session.run('match (t:term)--(c:concept) where id(t)=$id return c',{"id":term.neoid})
    s = result.single()
    assert s
    assert s['c'].id == concept.neoid
    assert s['c']['id'] == "heydude"
    result = session.run('match (p:property) where id(p)=$id return p',{"id":prop.neoid})
    s = result.single()
    assert s
    assert s['p'].id == prop.neoid
    assert not 'model' in s['p']

  prop.model = 'ICDC'
  at_enrollment = m.edges[('at_enrollment','prior_surgery','enrollment')]
  prior_surgery = m.nodes['prior_surgery']
  with drv.session() as session:
    result = session.run('match (n:node)<-[:has_src]-(r:relationship {handle:"at_enrollment"})-[:has_dst]->(:node {handle:"enrollment"}) where id(n)=$id return r',{"id":prior_surgery.neoid})
    s = result.single()
    assert s

  m.rm_edge(at_enrollment)
  assert not at_enrollment.src
  assert not at_enrollment.dst
  assert not at_enrollment in m.edges_out(prior_surgery)
  m.dput()
  with drv.session() as session:
    result = session.run('match (n:node)<-[:has_src]-(r:relationship {handle:"at_enrollment"})-[:has_dst]->(:node {handle:"enrollment"}) where id(n)=$id return r',{"id":prior_surgery.neoid})
    s = result.single()
    assert not s
    result = session.run('match (e:relationship) where id(e)=$id return e',{"id":at_enrollment.neoid})
    s = result.single()
    assert s
