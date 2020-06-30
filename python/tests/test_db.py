import re
import sys
sys.path.extend(['.','..'])
import pytest
import pytest_docker
from neo4j import GraphDatabase
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

  
